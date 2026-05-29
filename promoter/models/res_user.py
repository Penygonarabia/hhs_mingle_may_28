from odoo import models, fields

class ResUsers(models.Model):
    _inherit = "res.users"

    dealer_id = fields.Many2one("res.partner", string="Current Dealer", domain=[("is_dealer", "=", True)])
    showroom_id = fields.Many2one("promoter.showroom", string="Current Showroom")
