from odoo import models, fields


class ProductCategory(models.Model):
    _inherit = 'product.category'

    allowed_is_contract = fields.Boolean(
        string='Use for Contract',
        default=False,
        help='If ticked, this category will be available in AMC Price Calculation.',
    )
