from odoo import fields, models,api

class Partner(models.Model):
    _inherit = 'res.partner'
    
    district_id=fields.Many2one('res.state.district', string="Customer District")    
