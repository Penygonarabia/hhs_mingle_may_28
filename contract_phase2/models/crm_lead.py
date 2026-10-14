# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    # ------------------------------------------------------------------
    # Service & Repair (Contract Phase 2) marker
    # ------------------------------------------------------------------
    is_service_repair = fields.Boolean(
        string="Service & Repair Lead",
        help="Mark this lead as a Contract Phase 2 (Service & Repair) lead so "
             "the inspection payment and job-card generation tools appear.",
    )

    # ------------------------------------------------------------------
    # Inspection payment
    # ------------------------------------------------------------------
    cp2_inspection_amount = fields.Float(string="Inspection Amount")
    cp2_inspection_link_sent = fields.Boolean(
        string="Inspection Link Sent", readonly=True
    )
    cp2_inspection_received = fields.Boolean(string="Inspection Payment Received")

    cp2_total_qty = fields.Integer(
        string="Total No. of Qty",
        help="Total number of AC units / job cards expected for this lead.",
    )

    # ------------------------------------------------------------------
    # Technician grid + generated job cards
    # ------------------------------------------------------------------
    cp2_technician_line_ids = fields.One2many(
        "contract.phase2.technician.line", "lead_id", string="Technician Grid"
    )
    cp2_job_card_ids = fields.One2many(
        "project.task", "contract_phase2_lead_id", string="Job Cards"
    )
    cp2_job_card_count = fields.Integer(
        string="Job Cards", compute="_compute_cp2_job_card_count"
    )

    @api.depends("cp2_job_card_ids")
    def _compute_cp2_job_card_count(self):
        for lead in self:
            lead.cp2_job_card_count = len(lead.cp2_job_card_ids)

    @api.onchange("cp2_technician_line_ids")
    def _onchange_cp2_technician_line_ids(self):
        """Keep 'Total No. of Qty' as the sum of the technician grid rows.

        New rows default their qty to this total (via the grid's default_qty
        context); once the grid is filled, the total reflects the grid back.
        """
        for lead in self:
            if lead.cp2_technician_line_ids:
                lead.cp2_total_qty = sum(
                    line.qty or 0 for line in lead.cp2_technician_line_ids
                )

    # ------------------------------------------------------------------
    # Inspection Hyperpay link (lead level)
    # ------------------------------------------------------------------
    def action_cp2_send_inspection_link(self):
        """Flag that the inspection Hyperpay link has been sent to the customer.

        The robust Hyperpay/WhatsApp link generation lives on the job card
        (``action_create_hyperbill_inspection_payment``) because it needs the
        work-center-group token. At the lead stage - before job cards exist -
        this records the intent, posts a chatter note and lets the coordinator
        confirm receipt with the ``Inspection Payment Received`` tick.
        """
        self.ensure_one()
        if self.cp2_inspection_amount <= 0:
            raise UserError(_("Please enter an inspection amount first."))
        if not self.partner_id and not (self.contact_name or self.partner_name):
            raise UserError(_("Please set the customer on the lead first."))
        self.cp2_inspection_link_sent = True
        self.message_post(
            body=_("Inspection payment link sent to customer for amount %.2f.")
            % self.cp2_inspection_amount
        )
        return True

    # ------------------------------------------------------------------
    # Bulk job-card creation
    # ------------------------------------------------------------------
    def _cp2_prepare_job_card_vals(self, tech_line, seq):
        """Build the vals for one job card generated from a technician grid row.

        ``seq`` is a running 1-based counter used to build a unique job card
        reference (``name`` is required on the job card and has no auto-default).
        """
        self.ensure_one()
        partner = self.partner_id
        vals = {
            "name": "SR/%s/%02d" % (self.id, seq),
            "partner_id": partner.id if partner else False,
            "customer_name": partner.name if partner else (self.contact_name or self.partner_name),
            "phone": (partner.mobile or partner.phone) if partner else self.phone,
            "job_card_type": "service_repair",
            "contract_phase2_lead_id": self.id,
            # Quoting required parts, not consuming stock: allow zero-stock
            # products so the parts list isn't blocked by warehouse stock.
            "include_zero_stock_bool": True,
            "service_requested_datetime": (
                fields.Datetime.to_datetime(tech_line.visit_date)
                if tech_line.visit_date else False
            ),
            # Inspection: if already paid at lead level, tick it on the card,
            # otherwise leave it so the coordinator collects it per job card.
            "cp2_inspection_received": self.cp2_inspection_received,
        }
        # Copy the customer address details onto the generated card.
        vals.update(self.env["project.task"]._cp2_partner_address_vals(partner))
        if tech_line.technician_id:
            # Informational only - does not auto-schedule the card. The
            # coordinator assigns the working technician after payment.
            vals["cp2_planned_technician_id"] = tech_line.technician_id.id
        return vals

    def action_cp2_create_job_cards(self):
        """Generate ``qty`` job cards for each technician grid row."""
        self.ensure_one()
        if not self.cp2_technician_line_ids:
            raise UserError(_("Add at least one technician row to the grid first."))

        Task = self.env["project.task"]
        created = self.env["project.task"]
        seq = len(self.cp2_job_card_ids)  # continue numbering if re-run
        for line in self.cp2_technician_line_ids:
            qty = max(line.qty or 0, 0)
            if not qty:
                continue
            line_cards = self.env["project.task"]
            for _i in range(qty):
                seq += 1
                line_cards |= Task.create(self._cp2_prepare_job_card_vals(line, seq))
            line.job_cards_created = len(line_cards)
            created |= line_cards

        if not created:
            raise UserError(_("Nothing to create - set 'No. of Qty' on the grid rows."))

        self.message_post(
            body=_("%d Service & Repair job card(s) created from the lead.") % len(created)
        )
        return self.action_cp2_view_job_cards()

    def action_cp2_view_job_cards(self):
        self.ensure_one()
        # Use the dedicated Service & Repair list view so the sticky-header /
        # content-fitted-column styling (and the "Technician (Lead)" column)
        # apply only here, not to other job-card lists.
        tree_view = self.env.ref(
            "contract_phase2.view_project_task_tree_cp2", raise_if_not_found=False
        )
        return {
            "name": _("Job Cards"),
            "type": "ir.actions.act_window",
            "res_model": "project.task",
            "view_mode": "tree,form",
            "views": [
                (tree_view.id if tree_view else False, "tree"),
                (False, "form"),
            ],
            "domain": [("contract_phase2_lead_id", "=", self.id)],
            "context": {"default_contract_phase2_lead_id": self.id},
        }
