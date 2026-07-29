from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'

    name_ar = fields.Char(string='Name AR')
    sub_category = fields.Char(string='Sub Category')
    merged_subcategory = fields.Char(string='Merged Subcategory')
