from odoo import api, fields, models, _
from datetime import timedelta, time


class SaleOrder(models.Model):

    _inherit = "service.sale.order"

    is_cost_price = fields.Boolean(string="Is Cost Price",compute='check_cost_price_service_sale')

    # @api.depends('is_cost_price')
    def check_cost_price_service_sale(self):
        self.is_cost_price = False
        if self.user_has_groups('selling_cost_price_restrict.group_product_price_sales_manager'):
            self.is_cost_price = True
        elif self.user_has_groups('selling_cost_price_restrict.group_product_price_sales_user'):
            self.is_cost_price = False


