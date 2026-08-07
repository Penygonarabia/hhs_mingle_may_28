from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'

    name_ar = fields.Char(string='Name AR')
    sub_category = fields.Many2one('sub_category',string='Sub Category')
    merged_subcategory = fields.Many2one('sub_category',string='Merged Subcategory')
   
