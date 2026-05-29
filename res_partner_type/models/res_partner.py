from odoo import models, fields, api, _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('both', 'Both'),
        ('u', 'User'),
    ], string='Partner Type', required=True, store=True)
    
    # vendor_lead_time = fields.Integer(string="Vendor Lead Time")


