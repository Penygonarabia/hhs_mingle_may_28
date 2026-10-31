from odoo import models, fields, api

class ProductCategory(models.Model):
    _inherit = "product.category"
    
    show_in_dealer_app = fields.Boolean(
        string="Show in Dealer salesman app",
        default=False,
    )
