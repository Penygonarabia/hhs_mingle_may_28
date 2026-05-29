from odoo import api,fields,models,_
from odoo.exceptions import ValidationError

class DashboardRights(models.Model):
    
    _name = "dashboard.user.rights"
    
    
    name = fields.Char(string = "Dashboard Rights")
    
    
    @api.constrains('name')
    def _valid_name_check(self):
        for rec in self:
            search_name_count = self.env['dashboard.user.rights'].search([('name','=',rec.name)])
            if len(search_name_count) >1:
                raise ValidationError(_("Already Name is There.Please Give another one"))