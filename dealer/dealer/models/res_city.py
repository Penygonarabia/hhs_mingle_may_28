from odoo import models, fields,api

class ResCity(models.Model):
    _inherit = 'res.city'

    # country_district_id = fields.Many2one('res.state.district', string="District")
    # region_id = fields.Many2one('res.region', string="Region")

