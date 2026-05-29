from odoo import api, fields, models, _
from datetime import timedelta, time


class PosOrder(models.Model):

    _inherit = "pos.order"

    is_pos_selling_price = fields.Boolean(string="Is Selling Price",compute='check_selling_price_pos')

    @api.depends('is_pos_selling_price')
    def check_selling_price_pos(self):
        if self.user_has_groups('selling_cost_price_restrict.group_product_selling_price_user'):
            self.is_pos_selling_price = True
        else:
            self.is_pos_selling_price = False


class PosOrderLine(models.Model):

    _inherit = "pos.order.line"

    is_pos_selling_price = fields.Boolean(string="Is Selling Price",compute='check_selling_price_pos')

    @api.depends('order_id.is_pos_selling_price')
    def check_selling_price_pos(self):
        for rec in self:
            if rec.order_id.is_pos_selling_price == True:
                rec.is_pos_selling_price = True
            else:
                rec.is_pos_selling_price = False



