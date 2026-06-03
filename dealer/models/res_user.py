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

    floor_sales_approval_auth = fields.Boolean(
        string="Floor Sales Invoice Approval Authority",
        default=False
    )

    default_authority = fields.Boolean(
        string="Default Authority",
        default=False
    )

    @api.constrains('default_authority')
    def _check_default_authority(self):
        for rec in self:
            if rec.default_authority:
                existing = self.search([('default_authority', '=', True), ('id', '!=', rec.id)])
                if existing:
                    raise ValidationError(_("Only one user in the entire system can be marked as Default Authority."))
