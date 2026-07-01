from odoo import fields, models


class CustomerLoyaltyPointsHistory(models.Model):
    _inherit = "customer.loyalty.points.history"

    transaction_date = fields.Date(
        string="Transaction Date",
        related="clph_date",
        store=True,
    )
    customer_no = fields.Many2one(
        "res.partner",
        string="Customer",
        related="clph_cstid",
        store=True,
    )
    work_center_id = fields.Many2one(
        "work.center.location",
        string="City Work Center",
        related="clph_cstid.customer_city_id.def_work_center_id",
        store=True,
    )
    work_center_group_id = fields.Many2one(
        "work.center.group",
        string="Region",
        related="clph_cstid.customer_city_id.def_work_center_id.work_center_group_id",
        store=True,
    )
