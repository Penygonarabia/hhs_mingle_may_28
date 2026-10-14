# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    """Job card extensions for Contract Phase 2 (Service & Repair)."""
    _inherit = "project.task"

    @staticmethod
    def _cp2_is_service_repair_query(domain):
        """True if the domain explicitly targets Service & Repair job cards.

        Either ``job_card_type = service_repair`` (the S&R job-card menus) or
        ``contract_phase2_lead_id = <lead>`` (the lead's Job Cards smart button)
        pin the query to Service & Repair cards, which have no work center.
        """
        for leaf in domain or []:
            if not (isinstance(leaf, (list, tuple)) and len(leaf) == 3):
                continue
            field, _op, val = leaf
            if field == "job_card_type" and (
                val == "service_repair"
                or (isinstance(val, (list, tuple)) and "service_repair" in val)
            ):
                return True
            if field == "contract_phase2_lead_id" and val:
                return True
        return False

    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        """Bypass the base work-center / AMC-project scoping for Service &
        Repair queries.

        machine_repair_management.search_fetch narrows the job-card list to the
        user's ``default_work_center_id`` and AMC projects for Supervisor / Parts
        / Technician users. Service & Repair cards have no work center or AMC
        project, so that filter would hide them entirely (search returns 0 while
        search_count still counts them, breaking grouped list expansion). When
        the query is explicitly for Service & Repair cards, go straight to the
        ORM implementation, skipping that scoping.
        """
        if self._cp2_is_service_repair_query(domain):
            return models.Model.search_fetch(
                self, domain, field_names, offset, limit, order
            )
        return super().search_fetch(domain, field_names, offset, limit, order)

    @api.depends("team_id", "product_category_id")
    def _compute_warehouse_lst_ids(self):
        """Skip the technician/warehouse-availability validation for Service &
        Repair cards.

        The base compute (a validation hook) requires the assigned technician to
        have a warehouse for the card's product category *via the card's work
        center*. Service & Repair cards have no work center, so assigning any
        technician raises "<category> Main warehouse is not available to the
        technician". These cards only quote required parts (see
        include_zero_stock_bool), so no technician-warehouse binding is needed.
        """
        sr = self.filtered(lambda r: r.job_card_type == "service_repair")
        for rec in sr:
            rec.warehouse_lst_ids = [(5, 0, 0)]
        others = self - sr
        if others:
            super(ProjectTask, others)._compute_warehouse_lst_ids()

    def write(self, vals):
        """Service & Repair cards follow the lightweight lead-driven quoting flow,
        not the on-site technician workflow, so exempt them from the base
        per-state gates (Unit Name Plate photo, Model No, District, ...) when a
        state transition is written.

        The base ``write`` bundles those validations with the status-sync and
        early-returns on ``skip_state_validation``, so we skip validation for the
        S&R cards but sync the derived state fields ourselves (notably
        ``customer_need_quote_status_check``, which the quotation populate relies
        on). Non-S&R cards and non-state writes are untouched.
        """
        if not self.env.context.get("skip_state_validation") and (
            "job_state" in vals or "job_card_state_code" in vals
        ):
            sr = self.filtered(lambda r: r.job_card_type == "service_repair")
            if sr:
                v = dict(vals)
                if v.get("job_state"):
                    stage = self.env["project.task.type"].browse(v["job_state"])
                    v.setdefault("job_card_state", stage.name)
                    v.setdefault("job_card_state_code", stage.code)
                if v.get("job_card_state_code") == "129":  # Customer Need Quote
                    v["customer_need_quote_status_check"] = True
                res = super(
                    ProjectTask, sr.with_context(skip_state_validation=True)
                ).write(v)
                others = self - sr
                if others:
                    res = super(ProjectTask, others).write(vals) and res
                return res
        return super().write(vals)

    # ------------------------------------------------------------------
    # Job card TYPE (spec: Regular / AMC / Service & Repair)
    # ------------------------------------------------------------------
    job_card_type = fields.Selection(
        selection=[
            ("regular", "Regular Service"),
            ("amc", "AMC Contract"),
            ("service_repair", "Service & Repair"),
        ],
        string="Job Card Type",
        default="regular",
        index=True,
        help="Regular Service - assigned automatically from the call centre.\n"
             "AMC Contract - shows the contract-no selection.\n"
             "Service & Repair - assigned automatically from the lead screen "
             "(may also be selected manually).",
    )

    # Shown when job_card_type = 'amc'. Kept as a free-text reference to avoid a
    # hard dependency on the subscription/contract module; can be upgraded to a
    # Many2one to subscription.contracts if required.
    cp2_amc_contract_ref = fields.Char(string="AMC Contract No")

    # ------------------------------------------------------------------
    # Service & Repair link + payment flags
    # ------------------------------------------------------------------
    contract_phase2_lead_id = fields.Many2one(
        "crm.lead", string="Service & Repair Lead", index=True,
        help="Lead this job card was generated from (Contract Phase 2).",
    )

    # Technician captured on the lead grid at generation time (informational).
    # Kept separate from technician_id so generating cards does NOT auto-schedule
    # them - the coordinator assigns the real technician after payment.
    cp2_planned_technician_id = fields.Many2one(
        "res.users", string="Planned Technician",
        help="Technician planned for this unit on the Service & Repair lead grid.",
    )

    cp2_inspection_received = fields.Boolean(string="Inspection Received")
    cp2_payment_received = fields.Boolean(
        string="Job Payment Received",
        help="Set automatically when the consolidated quotation's job payment "
             "is received.",
    )
    cp2_balance_payment_received = fields.Boolean(
        string="Balance Payment Received",
        help="Set when the remaining balance for the quotation is collected.",
    )

    @api.onchange("job_card_type")
    def _onchange_job_card_type(self):
        """Keep the AMC contract reference tidy when the type changes."""
        if self.job_card_type != "amc":
            self.cp2_amc_contract_ref = False
        # Service & Repair cards LIST the parts required for the quotation; they
        # are not consuming technician-warehouse stock at this stage, so allow
        # zero-stock products (bypasses the "no Stock in the Warehouse" block).
        if self.job_card_type == "service_repair":
            self.include_zero_stock_bool = True

    # ------------------------------------------------------------------
    # Auto-fill the customer address details from the selected customer
    # (partner) - email, city, address, zip, state, region, country,
    # building number, plot identification.
    # ------------------------------------------------------------------
    @api.model
    def _cp2_partner_address_vals(self, partner):
        if not partner:
            return {}
        vals = {
            "email": partner.email,
            "address_one": partner.street,
            "zip_code": partner.zip,
            "country_state_id": partner.state_id.id or False,
            "country_id": partner.country_id.id or False,
        }
        # Custom partner fields (present via machine_repair / loyalty modules).
        for pf, cf in [
            ("customer_city_id", "customer_city_id"),
            ("region_id", "region_id"),
            ("building_number", "building_number"),
            ("plot_identification", "plot_identification"),
        ]:
            if pf in partner._fields:
                val = partner[pf]
                vals[cf] = val.id if hasattr(val, "id") and val._name else val
        return vals

    @api.onchange("partner_id")
    def _cp2_onchange_partner_id(self):
        """Fill the address block from the customer for Service & Repair cards."""
        if self.job_card_type == "service_repair" and self.partner_id:
            for field, value in self._cp2_partner_address_vals(self.partner_id).items():
                self[field] = value

    # ------------------------------------------------------------------
    # Coordinator action: send a Service & Repair card to "Customer Need
    # Quote" (state 129) so it joins the lead's consolidated quotation.
    #
    # The base on-site technician workflow reaches this state through the
    # field-visit screens, which Service & Repair cards skip. Without a
    # control the coordinator has no way to advance the card, so expose a
    # header button (view: job_card_views.xml). The write() override syncs
    # the derived state fields and customer_need_quote_status_check.
    # ------------------------------------------------------------------
    def action_cp2_mark_customer_need_quote(self):
        stage = self.env["project.task.type"].search(
            [("code", "=", "129")], limit=1
        )
        if not stage:
            raise UserError(_("The 'Customer Need Quote' stage is not configured."))
        for rec in self:
            if rec.job_card_type != "service_repair":
                raise UserError(_(
                    "This action is only for Service & Repair job cards."
                ))
            if not rec.product_line_ids:
                raise UserError(_(
                    "Add at least one required part/service to %s before "
                    "sending it for quotation."
                ) % rec.name)
        self.write({"job_state": stage.id})
        return True

    # ------------------------------------------------------------------
    # Quoting: Service & Repair cards are consolidated onto ONE quotation
    # per lead. Block the base per-card "Create Quotation" so a service's
    # cards can't each spawn a separate quotation (the button is also hidden
    # in the view; this guards any other call path).
    # ------------------------------------------------------------------
    def create_quotation(self):
        for rec in self:
            if rec.job_card_type == "service_repair":
                lead = rec.contract_phase2_lead_id
                raise UserError(_(
                    "Service & Repair job cards are quoted together on a single "
                    "consolidated quotation. Open the lead%(lead)s and use "
                    "'Populate from Job Cards' instead of creating a per-card "
                    "quotation."
                ) % {"lead": (" '%s'" % lead.display_name) if lead else ""})
        return super().create_quotation()

    # ------------------------------------------------------------------
    # Invoicing: Service & Repair cards must NOT auto-send the invoice.
    # Only job sheets are sent. Inventory + accounting posting is unchanged -
    # it happens via the normal Closed (126) job-card lifecycle, exactly like
    # current cards.
    # ------------------------------------------------------------------
    def send_scheduler_whatsapp_invoice_receipt(self):
        """Skip the automatic WhatsApp invoice for Service & Repair cards."""
        self.ensure_one()
        if self.job_card_type == "service_repair":
            _logger.info(
                "CP2: skipping automatic invoice WhatsApp for %s "
                "(Service & Repair - job sheet only).", self.name
            )
            return False
        return super().send_scheduler_whatsapp_invoice_receipt()

    def _send_whatsapp_to_customer_after_invoice_no(self):
        """Skip the direct invoice WhatsApp send for Service & Repair cards."""
        if self.job_card_type == "service_repair":
            _logger.info(
                "CP2: skipping invoice WhatsApp for %s (Service & Repair).", self.name
            )
            return False
        return super()._send_whatsapp_to_customer_after_invoice_no()

    def send_whatsapp_service_charges_receipt(self):
        """Skip the per-card proforma invoice for Service & Repair cards.

        The service is billed on ONE consolidated invoice raised from the lead's
        quotation (see contract_phase2/models/service_sale_order.py), so no card
        sends its own proforma invoice — only job sheets are sent, per spec.
        """
        self.ensure_one()
        if self.job_card_type == "service_repair":
            _logger.info(
                "CP2: skipping per-card proforma invoice for %s "
                "(Service & Repair - single consolidated invoice).", self.name
            )
            return False
        return super().send_whatsapp_service_charges_receipt()

    # ------------------------------------------------------------------
    # Time display: match the lead's technician grid (HH:MM, no seconds).
    #
    # The base *_time fields (call_time, appt_time, closed_time,
    # service_request_time) are Char computes formatted "%H:%M:%S". The lead's
    # technician grid shows its start_time with the float_time widget, which
    # renders HH:MM. Trim the seconds off those same fields for Service &
    # Repair cards only, so the S&R job-card list (the only place these
    # fields are shown for S&R cards) matches that format; other job card
    # types keep the base HH:MM:SS untouched.
    # ------------------------------------------------------------------
    def _cp2_trim_time_seconds(self, fname):
        for rec in self:
            if rec.job_card_type == "service_repair" and rec[fname] and len(rec[fname]) >= 5:
                rec[fname] = rec[fname][:5]

    @api.depends("service_created_datetime")
    def _compute_job_request_date_time(self):
        super()._compute_job_request_date_time()
        self._cp2_trim_time_seconds("call_time")

    @api.depends("closed_datetime")
    def _compute_job_close_datetime(self):
        super()._compute_job_close_datetime()
        self._cp2_trim_time_seconds("closed_time")

    @api.depends("planned_date_begin")
    def _compute_job_appointment_datetime(self):
        super()._compute_job_appointment_datetime()
        self._cp2_trim_time_seconds("appt_time")

    @api.depends("service_requested_datetime")
    def _compute_service_requested_date(self):
        super()._compute_service_requested_date()
        self._cp2_trim_time_seconds("service_request_time")


class ProductLines(models.Model):
    """Consume-parts line on a job card."""

    _inherit = "product.lines"

    @api.depends(
        "project_task_id",
        "location_id",
        "product_categ_id",
        "project_task_id.product_group_id",
    )
    def _compute_product_id_domain(self):
        """For Service & Repair cards, filter the product list by the card's
        product category AND product group, and hide the bad-data products whose
        name is empty / "False". Other job card types keep the base behaviour.
        """
        sr = self.filtered(
            lambda r: r.project_task_id.job_card_type == "service_repair"
        )
        Product = self.env["product.product"]
        for rec in sr:
            task = rec.project_task_id
            categ = task.product_group_id or task.product_category_id
            domain = [
                ("active", "=", True),
                ("name", "!=", False),
                ("name", "!=", "False"),
            ]
            if categ:
                domain = [("categ_id", "child_of", categ.id)] + domain
            products = Product.search(domain)
            rec.product_id_domain = (
                "[('id', 'in', %s)]" % products.ids
                if products
                else "[('id', 'in', [])]"
            )
        others = self - sr
        if others:
            super(ProductLines, others)._compute_product_id_domain()
