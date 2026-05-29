from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand = fields.Char(string='Brand')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    product_category_id = fields.Many2one(
        'product.category',
        string='Brand Category',
    )
