from odoo import api, fields, models, _
from datetime import timedelta, time
from dateutil.relativedelta import relativedelta


class ProductTemplate(models.Model):

    _inherit = "product.template"

    is_cost_price = fields.Boolean(compute='check_group', invisible=True)

    @api.depends('standard_price')
    def check_group(self):
        if self.user_has_groups('selling_cost_price_restrict.group_product_price_user'):
            self.is_cost_price = True
        else:
            self.is_cost_price = False

class ProductProduct(models.Model):

    _inherit = "product.product"

    is_cost_price = fields.Boolean(compute='check_group', invisible=True)

    @api.depends('standard_price')
    def check_group(self):
        if self.user_has_groups('selling_cost_price_restrict.group_product_price_user'):
            self.is_cost_price = True
        else:
            self.is_cost_price = False
    
