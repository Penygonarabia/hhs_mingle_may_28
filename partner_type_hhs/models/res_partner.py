from odoo import api, fields, models, _


class ResPartner(models.Model):
    
    _inherit = 'res.partner'
    
    
    # partner_type_hhs = fields.Selection([
    #     ('customer', 'Customer'),
    #     ('vendor', 'Vendor'),
    #     ('both', 'Both'),
    #     ('u', 'User'),
    #
    # ], string='Partner Type', store=True)
    #
    # sub_partner_type = fields.Selection([
    #     ('retail','Retail Customer'),
    #     ('dealer','Dealer'),
    #     ],string = "Sub Partner Type",store = True,
    #
    # )
    
    partner_type_hhs = fields.Selection([
    ('customer', 'Customer'),
    ('vendor', 'Vendor'),
    ('both', 'Both'),
    ('u', 'User'),
    ], string='Partner Type', store=True, 
       default=lambda self: self._context.get('default_partner_type_hhs') or False)
    
    sub_partner_type = fields.Selection([
        ('retail','Retail Customer'),
        ('dealer','Dealer'),
    ], string="Sub Partner Type", store=True,
       default=lambda self: self._context.get('default_sub_partner_type') or False)
    
    
    
    
    