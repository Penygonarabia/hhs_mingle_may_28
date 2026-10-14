# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ServiceSaleOrder(models.Model):
    """Consolidated quotation for a Service & Repair lead (Contract Phase 2)."""
    _inherit = "service.sale.order"

    contract_phase2_lead_id = fields.Many2one(
        "crm.lead", string="Lead Reference", index=True,
        domain="[('is_service_repair', '=', True)]",
        help="Service & Repair lead whose job cards are consolidated here.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-link a Service & Repair lead's quotation to itself.

        The lead's "New Quotation" / "New Service Quotation" header buttons
        (sales_contract_and_recurring_invoices) set the base ``crm_id`` but
        know nothing about ``contract_phase2_lead_id`` - so a quotation
        created that way from an S&R lead needs "Lead Reference" picked
        manually before Populate/Confirm work. Fill it in automatically
        whenever the source lead is a Service & Repair lead.
        """
        for vals in vals_list:
            if vals.get("crm_id") and not vals.get("contract_phase2_lead_id"):
                lead = self.env["crm.lead"].browse(vals["crm_id"])
                if lead.is_service_repair:
                    vals["contract_phase2_lead_id"] = lead.id
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Job payment (after approval)
    # ------------------------------------------------------------------
    cp2_job_payment_amount = fields.Float(string="Job Payment Amount")
    cp2_job_payment_link_sent = fields.Boolean(
        string="Job Payment Link Sent", readonly=True
    )
    cp2_job_payment_received = fields.Boolean(string="Job Payment Received")

    # ------------------------------------------------------------------
    # Balance payment (Option A: status block on the quotation)
    # ------------------------------------------------------------------
    cp2_balance_amount = fields.Float(string="Balance Payment Amount")
    cp2_balance_link_sent = fields.Boolean(
        string="Balance Link Sent", readonly=True
    )
    cp2_balance_received = fields.Boolean(string="Balance Payment Received")

    # ------------------------------------------------------------------
    # Manual invoice (Service & Repair cards never auto-invoice; the
    # coordinator generates one customer invoice from the approved quote).
    # ------------------------------------------------------------------
    cp2_invoice_id = fields.Many2one(
        "account.move", string="Customer Invoice", readonly=True, copy=False,
        help="Invoice generated from this consolidated Service & Repair quotation.",
    )
    cp2_invoice_count = fields.Integer(
        string="Invoices", compute="_compute_cp2_invoice_count"
    )

    @api.depends("cp2_invoice_id")
    def _compute_cp2_invoice_count(self):
        for order in self:
            order.cp2_invoice_count = 1 if order.cp2_invoice_id else 0

    # ==================================================================
    # Populate from job cards
    # ==================================================================
    def _cp2_check_job_cards_ready(self, job_cards):
        """All linked job cards must be at 'Customer Need Quote' before populate."""
        pending = job_cards.filtered(lambda c: not c.customer_need_quote_status_check)
        if pending:
            names = ", ".join(pending.mapped(lambda c: c.name or _("New")))
            raise UserError(_(
                "Please complete the pending job card(s) for the selected lead - "
                "all job cards must be at 'Customer Need Quote' first.\n\n"
                "Pending: %s"
            ) % names)

    def _cp2_line_vals_from_product_line(self, part_line):
        """Map a job card ``product.lines`` record to a quotation line."""
        return (0, 0, {
            "product_id": part_line.product_id.id,
            "product_qty": part_line.qty,
            "product_uom": part_line.uom_id.id,
            "price_unit": part_line.price_unit,
            "vat": part_line.vat,
            "under_warranty_bool": part_line.under_warranty_bool,
        })

    def action_cp2_populate(self):
        """Bring all job cards' spare parts + service charges into the quotation."""
        self.ensure_one()
        lead = self.contract_phase2_lead_id
        if not lead:
            raise UserError(_("Select a Lead Reference number first."))

        job_cards = lead.cp2_job_card_ids
        if not job_cards:
            raise UserError(_("The selected lead has no job cards to consolidate."))

        self._cp2_check_job_cards_ready(job_cards)

        # Rebuild the lines from scratch so re-populating stays idempotent.
        line_cmds = [(5, 0, 0)]
        for card in job_cards:
            for part in card.product_line_ids:
                if not part.product_id:
                    continue
                line_cmds.append(self._cp2_line_vals_from_product_line(part))

        if len(line_cmds) == 1:
            raise UserError(_(
                "No spare parts or service charges found on the job cards for "
                "this lead. Add them on the job cards first."
            ))

        vals = {"service_sale_order_line_ids": line_cmds}
        # Carry customer + lead context onto the quotation.
        if lead.partner_id:
            vals["customer_name"] = lead.partner_id.name
        vals["crm_id"] = lead.id
        self.write(vals)

        self.message_post(body=_(
            "Consolidated %d job card(s) from lead %s into this quotation."
        ) % (len(job_cards), lead.display_name))
        return True

    # ==================================================================
    # Confirm (consolidated Service & Repair quotations)
    # ==================================================================
    def action_cp2_confirm_quotation(self):
        """Confirm a consolidated Service & Repair quotation.

        The base ``action_confirm`` only advances quotations tied to a single
        ``job_task_id``; a lead-consolidated quotation has none, so it needs its
        own confirm path to reach ``sale`` (which unlocks the job/balance payment
        and Create Invoice actions).
        """
        self.ensure_one()
        if not self.contract_phase2_lead_id:
            raise UserError(_(
                "This action is only for consolidated Service & Repair quotations."
            ))
        if self.state not in ("draft", "sent"):
            raise UserError(_("Only a draft/sent quotation can be confirmed."))
        if not self.service_sale_order_line_ids:
            raise UserError(_(
                "Populate the quotation from the job cards before confirming."
            ))
        if not self.name or self.name == _("New"):
            seq = self.env["ir.sequence"].next_by_code("service.sale.order")
            if seq:
                self.name = seq
        self.write({"state": "sale"})
        self.message_post(body=_("Service & Repair quotation confirmed."))
        return True

    # ==================================================================
    # Payment propagation to job cards
    # ==================================================================
    def _cp2_job_cards(self):
        self.ensure_one()
        lead = self.contract_phase2_lead_id or self.crm_id
        return lead.cp2_job_card_ids if lead else self.env["project.task"]

    def action_cp2_send_job_payment_link(self):
        self.ensure_one()
        if self.cp2_job_payment_amount <= 0:
            raise UserError(_("Enter a job payment amount first."))
        self.cp2_job_payment_link_sent = True
        self.message_post(body=_("Job payment link sent for amount %.2f.")
                          % self.cp2_job_payment_amount)
        return True

    def action_cp2_confirm_job_payment(self):
        """Mark job payment received and flag all linked job cards."""
        self.ensure_one()
        self.cp2_job_payment_received = True
        cards = self._cp2_job_cards()
        cards.write({"cp2_payment_received": True})
        self.message_post(body=_(
            "Job payment received - flagged %d job card(s) as paid."
        ) % len(cards))
        return True

    def action_cp2_send_balance_link(self):
        self.ensure_one()
        if self.cp2_balance_amount <= 0:
            raise UserError(_("Enter a balance amount first."))
        self.cp2_balance_link_sent = True
        self.message_post(body=_("Balance payment link sent for amount %.2f.")
                          % self.cp2_balance_amount)
        return True

    def action_cp2_confirm_balance_payment(self):
        """Mark balance payment received and flag all linked job cards."""
        self.ensure_one()
        self.cp2_balance_received = True
        cards = self._cp2_job_cards()
        cards.write({"cp2_balance_payment_received": True})
        self.message_post(body=_(
            "Balance payment received - flagged %d job card(s)."
        ) % len(cards))
        return True

    # ==================================================================
    # Manual invoice generation (Phase 2.4)
    # ==================================================================
    def _cp2_invoice_line_vals(self, line):
        """Map one quotation line to an account.move.line command.

        Standard VAT is computed by the accounting engine via ``tax_ids``. This
        invoice form (from sales_contract_and_recurring_invoices) also shows the
        custom Sub Total / VAT Amount / Total fields, which sum the per-line
        ``total_price`` and ``vat_amt``, so populate those too or the displayed
        totals read 0.00 even though the posted invoice is correct.
        """
        product = line.product_id
        taxes = product.taxes_id.filtered(
            lambda t: t.company_id == self.env.company
        ) if product else product.taxes_id
        qty = line.product_qty or 1.0
        line_untaxed = qty * line.price_unit
        vat_pct = line.vat or 0.0
        return (0, 0, {
            "product_id": product.id,
            "name": product.display_name or _("Service & Repair"),
            "quantity": qty,
            "price_unit": line.price_unit,
            "product_uom_id": (line.product_uom.id or product.uom_id.id)
            if product else line.product_uom.id,
            "tax_ids": [(6, 0, taxes.ids)],
            # Custom display fields used by the invoice form's totals block.
            "vat": vat_pct,
            "total_price": line_untaxed,
            "vat_amt": line_untaxed * vat_pct / 100.0,
        })

    def action_cp2_create_invoice(self):
        """Generate a single draft customer invoice from the approved quotation.

        This is the "separate invoice screen populated from the quotation" the
        spec calls for. Service & Repair job cards deliberately never auto-invoice
        (see contract_phase2/models/job_card.py), so the coordinator raises the
        invoice here once the work is done.
        """
        self.ensure_one()
        if self.state not in ("sale", "done"):
            raise UserError(_(
                "Confirm (approve) the quotation before generating the invoice."
            ))
        if self.cp2_invoice_id:
            # Idempotent: never raise a second invoice for the same quotation.
            return self.action_cp2_view_invoice()

        lead = self.contract_phase2_lead_id or self.crm_id
        partner = lead.partner_id if lead else False
        if not partner:
            raise UserError(_(
                "The linked lead has no customer set - cannot create an invoice."
            ))

        lines = [
            self._cp2_invoice_line_vals(line)
            for line in self.service_sale_order_line_ids
            if line.product_id
        ]
        if not lines:
            raise UserError(_(
                "There are no product lines on this quotation to invoice. "
                "Populate it from the job cards first."
            ))

        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "invoice_origin": self.name,
            "ref": lead.display_name if lead else self.name,
            "invoice_line_ids": lines,
            "cp2_quotation_id": self.id,
        })
        self.cp2_invoice_id = move.id
        self.message_post(body=_(
            "Draft invoice %s created from this Service & Repair quotation."
        ) % move.name)
        return self.action_cp2_view_invoice()

    def action_cp2_view_invoice(self):
        self.ensure_one()
        if not self.cp2_invoice_id:
            raise UserError(_("No invoice has been generated yet."))
        return {
            "name": _("Customer Invoice"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.cp2_invoice_id.id,
            "view_mode": "form",
            "target": "current",
        }
