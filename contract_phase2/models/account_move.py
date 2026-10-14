# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    """Link a customer invoice back to the Service & Repair quotation it was
    raised from, so Contract Phase 2 invoices can be listed on their own menu
    and traced to the consolidated quotation."""

    _inherit = "account.move"

    cp2_quotation_id = fields.Many2one(
        "service.sale.order",
        string="Service & Repair Quotation",
        index=True,
        copy=False,
        help="Consolidated Service & Repair quotation this invoice was raised from.",
    )
