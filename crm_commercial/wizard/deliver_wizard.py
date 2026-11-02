from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CrmCommercialDeliveredQty(models.Model):
    _name = 'crm.commercial.delivered.qty'
    _description = 'Delivered Qty Entry'
    _order = 'delivery_date, id'

    order_line_id = fields.Many2one('crm.commercial.sale.order.line', ondelete='cascade', required=True, index=True)
    order_id = fields.Many2one('crm.commercial.sale.order', related='order_line_id.order_id', store=True, index=True)
    product_id = fields.Many2one('product.product', related='order_line_id.product_id', store=True, string='Product')
    delivery_date = fields.Date(string='Schedule Date', required=True, default=fields.Date.context_today)
    qty = fields.Float(string='Delivery Qty', required=True)

    @api.constrains('qty', 'order_line_id')
    def _check_qty(self):
        for rec in self:
            if rec.qty <= 0:
                raise ValidationError(_("Quantity must be greater than zero."))
        for line in self.mapped('order_line_id'):
            total = sum(line.delivered_entry_ids.mapped('qty'))
            if total > line.qty:
                raise ValidationError(
                    _("Total scheduled quantity (%(total)s) cannot exceed the ordered quantity (%(ordered)s) for %(product)s.",
                      total=total, ordered=line.qty, product=line.product_id.display_name))