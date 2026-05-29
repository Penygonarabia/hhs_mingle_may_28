from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = ['res.partner'] 

    is_dealer = fields.Boolean(string='Promoter Required', tracking=True)
    is_showroom = fields.Boolean(string="Is Showroom", tracking=True)
    showroom_code = fields.Char(string="Showroom Code")
    region_id = fields.Many2one('res.region', string="Region")

    promoter_showroom_ids = fields.One2many(
        'promoter.showroom',
        'dealer_id',
        string="Showrooms"
    )

    # @api.constrains('is_dealer')
    # def _check_dealer_region(self):
    #     for rec in self:
    #         if not rec.is_dealer:
    #             raise ValidationError("'Promoter Required' must be checked.")

