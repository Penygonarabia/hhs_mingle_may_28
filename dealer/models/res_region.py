from odoo import models, fields

class ResRegion(models.Model):
    _inherit = 'res.region'
    _description = 'Region'

    name = fields.Char(string='Region Name', required=True)
    code = fields.Char(string='Region Code')
    description = fields.Text(string='Description')
    partner_id = fields.Many2one('res.partner', string='Partner')
