from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    _inherit = "res.users"

    dealer_salesman = fields.Boolean(
        string="Dealer Salesman",
        default=False
    )

    dealer_city_id = fields.Many2one(
        'res.city',
        string="Working City"
    )

    dealer_showroom_id=fields.Many2one(
        'dsales.showroom',
        string='Dealer Showroom'
    )
    
    @api.onchange('dealer_salesman')
    def _onchange_dealer_salesman(self):
        if not self.dealer_salesman:
            self.dealer_city_id = False

