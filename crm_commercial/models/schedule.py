from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleOrderDeliverSchedule(models.Model):
    _name = 'sale.order.deliver.schedule'
    _description = 'Sale Order Delivery Schedule'

    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade')
    line_id = fields.Many2one('sale.order.line', required=True, ondelete='cascade',
                              domain="[('order_id', '=', order_id)]")
    product_id = fields.Many2one('product.product', related='line_id.product_id',
                                 store=True, readonly=True)
    delivery_date = fields.Date(required=True)
    qty = fields.Float('Scheduled Qty', required=True)
    delivered_qty = fields.Float('Delivered Qty', readonly=True)

    def action_open_wizard(self):
        self.ensure_one()
        return {
            'name': 'Deliver Quantity',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.deliver.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_schedule_id': self.id,
                'default_delivery_date': self.delivery_date,
                'default_delivery_qty': self.qty - self.delivered_qty,
            },
        }


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    deliver_schedule_ids = fields.One2many('sale.order.deliver.schedule', 'order_id')