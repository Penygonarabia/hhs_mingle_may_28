from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PartnerClassification(models.Model):
    
    _name = "partner.classification"
    
    _description = "Partner Classification"
    
    _rec_name = "complete_name"
    
    
    
    pc_partner_type = fields.Selection([
    ('customer', 'Customer'),
    ('vendor', 'Vendor'),
    ('both', 'Both'),
    ('u', 'User'),
    ], string='Partner Type', store=True, 
       )
    
    pc_partner_sub_type = fields.Selection([
        ('retail','Retail Customer'),
        ('dealer','Dealer'),
    ], string="Partner Sub-type", store=True,
       )
    
    pc_code = fields.Char(string = "Code")
    
    pc_classification1 = fields.Char(string = "Partner Classification1")
    
    pc_classification2 = fields.Char(string = "Partner Classification2")
    
    complete_name = fields.Char(string = "Complete Name", compute = "_compute_complete_name", store=True)
    
    
    @api.depends('pc_code', 'pc_classification1')
    def _compute_complete_name(self):
        for rec in self:
            if rec.pc_code and rec.pc_classification1:
                rec.complete_name = '[%s]-%s' %(rec.pc_code,rec.pc_classification1)
            
            else:
                rec.complete_name = rec.pc_classification1
                    
        
        
        
    
    @api.constrains('pc_code','pc_partner_type','pc_partner_sub_type')
    def _check_constrains_code(self):
        
        for rec in self:
            
            classification_search = self.env['partner.classification'].search([
                                        ('pc_code','=', rec.pc_code),
                                        ('pc_partner_type' ,'=', rec.pc_partner_type),
                                        ('pc_partner_sub_type' , '=' , rec.pc_partner_sub_type)
                
                ])
            

            if len(classification_search) >1 :
                
                raise ValidationError(_("Already Code '%s' is used for Partner '%s'" %(rec.pc_code,rec.pc_classification1)))
    
    
    
    
