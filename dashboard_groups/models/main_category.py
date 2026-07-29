from odoo import models, fields

class MainCategory(models.Model):
    _name = 'main_category'
    _description = 'Main Category'
    _rec_name = 'maincat_name'

    maincat_ref = fields.Char(string='Reference', required=True)
    maincat_name = fields.Char(string='Name', required=True)
    maincat_name2 = fields.Char(string='Name 2')

    _sql_constraints = [
        ('maincat_ref_unique', 'unique(maincat_ref)', 'Reference must be unique!')
    ]
