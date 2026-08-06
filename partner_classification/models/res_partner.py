from odoo import api, fields, models, _

class ResPartner(models.Model):
    
    _inherit = "res.partner"
    
    
    partner_classification_id = fields.Many2one('partner.classification', string = "Partner Classification")
    
    
    @api.onchange('partner_type_hhs','sub_partner_type')
    def _onchange_partner_type(self):
        for rec in self:
            rec.partner_classification_id = False
    