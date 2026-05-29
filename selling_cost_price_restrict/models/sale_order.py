from odoo import api, fields, models, _
from datetime import timedelta, time


class SaleOrder(models.Model):

    _inherit = "sale.order"

    is_selling_price = fields.Boolean(string="Is Selling Price",compute='check_selling_price_sale')

    @api.depends('is_selling_price')
    def check_selling_price_sale(self):
        if self.user_has_groups('selling_cost_price_restrict.group_product_selling_price_user'):
            self.is_selling_price = True
        else:
            self.is_selling_price = False


class SaleOrderLine(models.Model):

    _inherit = "sale.order.line"

    is_selling_price = fields.Boolean(string="Is Selling Price",compute='check_selling_price_sale')

    @api.depends('order_id.is_selling_price')
    def check_selling_price_sale(self):
        for rec in self:
            if rec.order_id.is_selling_price == True:
                rec.is_selling_price = True
            else:
                rec.is_selling_price = False


class AccountMove(models.Model):

    _inherit = "account.move"

    is_invoice_selling_price = fields.Boolean(string="Is Invoice Selling Price", compute='check_selling_price')

    @api.depends('is_invoice_selling_price')
    def check_selling_price(self):
        if self.user_has_groups('selling_cost_price_restrict.group_product_selling_price_user'):
            self.is_invoice_selling_price = True
        else:
            self.is_invoice_selling_price = False

class AccountMoveLine(models.Model):

    _inherit = "account.move.line"

    is_invoice_selling_price = fields.Boolean(string="Is Invoice Selling Price", compute='check_selling_price')

    @api.depends('move_id.is_invoice_selling_price')
    def check_selling_price(self):
        for rec in self:
            if rec.move_id.is_invoice_selling_price == True:
                rec.is_invoice_selling_price = True
            else:
                rec.is_invoice_selling_price = False
