from odoo import models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    spare_parts_discount_limit = fields.Float(
        string="Maximum Allowed spare parts Margin  Discount %?"
    )
