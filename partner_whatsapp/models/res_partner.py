from odoo import api, fields, models, _

class ResPartner(models.Model):
    
    _inherit = "res.partner"
    
    x_whatsapp_opt_in = fields.Boolean(string="WhatsApp Opt-In",default = False)
