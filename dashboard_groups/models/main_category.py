from odoo import models, fields,_,api
from odoo.exceptions import UserError

class MainCategory(models.Model):
    _name = 'main.category'
    _description = 'Main Category'
    _rec_name = 'maincat_name'

    maincat_ref = fields.Char(string='Reference', required=True)
    maincat_name = fields.Char(string='Name', required=True)
    maincat_name2 = fields.Char(string='Name 2')

    _sql_constraints = [
        ('maincat_ref_unique', 'unique(maincat_ref)', 'Reference must be unique!')
    ]

    def unlink(self):
        for record in self:
            if self.env['sub.category'].search_count([('subcat_maincategory_id', '=', record.id)]) > 0:
                
                raise UserError(f"You cannot delete the Main Category '{record.maincat_name}' because it is currently assigned to one or more Sub Categories. Please reassign or delete the associated Sub Categories first.")
        return super(MainCategory, self).unlink()
