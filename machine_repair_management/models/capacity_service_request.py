from odoo import api,fields,models,_
from odoo.exceptions import ValidationError

class CapacityServiceRequest(models.Model):
    
    _name = "service.capacity"
    
    _description = "Service Capacity"
    
    _rec_name = "complete_name"
    
    
    svc_code = fields.Char(string = "Code")
    
    svc_name = fields.Char(string ="Name")
    
    complete_name = fields.Char('Complete Name',compute = "_compute_complete_name")
    
    
    @api.depends('svc_name','svc_code')
    def _compute_complete_name(self):
        for rec in self:
            if rec.svc_code and rec.svc_name:
                rec.complete_name = '[%s]-%s'%(rec.svc_code,rec.svc_name)
            else:
                rec.complete_name = rec.svc_name
    
    @api.constrains('svc_code')
    def _check_code_validity(self):
        for rec in self:
            code_search = self.env['service.capacity'].search([('svc_code','=',rec.svc_code),('id','!=',rec.id)])
            if len(code_search) > 1:
                raise ValidationError("Code must be unique one")
                            
