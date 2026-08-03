from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = ['res.partner'] 

    dealersalesman_required = fields.Boolean(string='Dealer Salesman Req.', tracking=True)

    dealer_showroom_id = fields.Many2one(
        'dsales.showroom',
        string='Dealer Showroom'
    )

    # @api.constrains('dealersalesman_required')
    # def _check_dealer_region(self):
    #     for rec in self:
    #         if not rec.dealersalesman_required:
    #             raise ValidationError("'Dealer Salesman Required' must be checked.")

