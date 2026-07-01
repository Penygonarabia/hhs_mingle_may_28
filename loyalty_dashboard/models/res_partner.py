from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    work_center_id = fields.Many2one(
        "work.center.location",
        string="City Work Center",
        related="customer_city_id.def_work_center_id",
        store=True,
    )
    work_center_group_id = fields.Many2one(
        "work.center.group",
        string="Region",
        related="customer_city_id.def_work_center_id.work_center_group_id",
        store=True,
    )
