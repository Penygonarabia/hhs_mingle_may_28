from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    _inherit = "res.users"

    dealer_salesman = fields.Boolean(
        string="Dealer Salesman",
        default=False
    )

    floor_sales_approval_auth = fields.Boolean(
        string="Floor Sales Approval Auth",
        default=False
    )

    @api.constrains('floor_sales_approval_auth')
    def _check_single_floor_sales_auth(self):
        for record in self:
            if record.floor_sales_approval_auth:
                if self.search_count([('floor_sales_approval_auth', '=', True)]) > 1:
                    raise ValidationError(_("Only one Floor Sales Invoice Approval Authority user is allowed for the whole project."))

    default_authority = fields.Boolean(string="Legacy Dummy Field")

    default_authority_id = fields.Many2one('res.users', string="Default Authority")

    @api.onchange('floor_sales_approval_auth')
    def _onchange_floor_sales_approval_auth(self):
        if not self.floor_sales_approval_auth:
            self.default_authority_id = False


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

