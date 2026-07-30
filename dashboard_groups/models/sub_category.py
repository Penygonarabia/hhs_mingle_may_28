from odoo import models, fields

class SubCategory(models.Model):
    _name = 'sub_category'
    _description = 'Sub Category'
    _rec_name = 'subcat_name'

    subcat_ref = fields.Char(string='Reference', required=True)
    subcat_name = fields.Char(string='Name', required=True)
    subcat_name2 = fields.Char(string='Name 2')
    subcat_maincategory_id = fields.Many2one('main_category', string='Main Category', ondelete='restrict', required=True)

    _sql_constraints = [
        ('subcat_ref_unique', 'unique(subcat_ref)', 'Reference must be unique!')
    ]
