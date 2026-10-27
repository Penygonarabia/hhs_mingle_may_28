# -*- coding: utf-8 -*-
from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # copy=True so return pickings (created via picking.copy()) stay linked to the order
    commercial_order_id = fields.Many2one(
        'crm.commercial.sale.order', string='Commercial Order',
        index=True, copy=True, tracking=True)

    def _action_done(self):
        res = super()._action_done()
        orders = self.filtered('commercial_order_id').mapped('commercial_order_id')
        if orders:
            orders._recompute_actual_delivery()
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    # copy=True so return moves keep the link to the order line
    commercial_order_line_id = fields.Many2one(
        'crm.commercial.sale.order.line', string='Commercial Order Line',
        index=True, copy=True)


class CrmCommercialSaleOrder(models.Model):
    _inherit = 'crm.commercial.sale.order'

    total_delivered_amount = fields.Float(
        string='Actual Delivered Amount', compute='_compute_actual_totals', store=True)
    total_delivered_cost = fields.Float(
        string='Actual Delivered Cost', compute='_compute_actual_totals', store=True)
    actual_gross_margin_amount = fields.Float(
        string='Actual Gross Margin', compute='_compute_actual_totals', store=True)

    @api.depends('line_ids.delivered_amount', 'line_ids.delivered_cost')
    def _compute_actual_totals(self):
        for order in self:
            rev = sum(order.line_ids.mapped('delivered_amount'))
            cost = sum(order.line_ids.mapped('delivered_cost'))
            order.total_delivered_amount = rev
            order.total_delivered_cost = cost
            order.actual_gross_margin_amount = rev - cost

    # ------------------------------------------------------------------
    # Actual cost from delivery notes (deliveries minus returns)
    # ------------------------------------------------------------------
    @staticmethod
    def _move_done_qty(move):
        # Odoo 17+: quantity ; Odoo <= 16: quantity_done
        return move.quantity if 'quantity' in move._fields else move.quantity_done

    def _recompute_actual_delivery(self):
        """Idempotent: rebuilds delivered cost/amount on each line from ALL
        done moves linked to the order. Called after every delivery/return."""
        Move = self.env['stock.move']
        for order in self:
            moves = Move.search([
                ('picking_id.commercial_order_id', '=', order.id),
                ('state', '=', 'done'),
            ])
            vals = {line.id: [0.0, 0.0, 0.0] for line in order.line_ids}  # qty, amount, cost
            for move in moves:
                line = move.commercial_order_line_id
                if not line or line.id not in vals:
                    continue
                # +1 = goods leaving to customer, -1 = coming back from customer
                if move.location_dest_id.usage == 'customer':
                    sign = 1.0
                elif move.location_id.usage == 'customer':
                    sign = -1.0
                else:
                    continue
                qty = self._move_done_qty(move)
                layers = getattr(move, 'stock_valuation_layer_ids', False)
                if layers:
                    # outgoing layers are negative, return layers positive -> -value works for both
                    cost = -sum(layers.mapped('value'))
                else:
                    cost = sign * qty * move.product_id.standard_price
                net_price = line.sale_price * (1.0 - (line.discount_percent or 0.0) / 100.0)
                vals[line.id][0] += sign * qty
                vals[line.id][1] += sign * qty * net_price
                vals[line.id][2] += cost
            for line in order.line_ids:
                qty, amount, cost = vals[line.id]
                line.sudo().write({'delivered_amount': amount, 'delivered_cost': cost})