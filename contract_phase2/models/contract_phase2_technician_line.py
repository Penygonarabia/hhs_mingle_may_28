# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ContractPhase2TechnicianLine(models.Model):
    """One row of the technician grid on a Service & Repair lead.

    Each row tells the system: this technician, on this date/time, will handle
    ``qty`` air-conditioner units -> ``qty`` job cards will be generated.
    """
    _name = "contract.phase2.technician.line"
    _description = "Contract Phase 2 - Technician Grid Line"

    def _default_start_time(self):
        """Current time as an HH.MM float, in the user's timezone."""
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        return now.hour + now.minute / 60.0

    lead_id = fields.Many2one(
        "crm.lead", string="Lead", required=True, ondelete="cascade", index=True
    )
    technician_id = fields.Many2one(
        "res.users", string="Technician Name", required=True,
        default=lambda self: self.env.user,
    )
    visit_date = fields.Date(string="Date", default=fields.Date.context_today)
    start_time = fields.Float(
        string="Start Time", default=_default_start_time,
        help="Planned start time (HH.MM 24h).",
    )
    # Defaults to the lead's "Total No. of Qty" via the grid's context
    # (default_qty); if that is 0 the coordinator types it here per technician.
    qty = fields.Integer(string="No. of Qty")

    # How many job cards were actually generated from this row (audit).
    job_cards_created = fields.Integer(string="Job Cards Created", readonly=True)
