# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software PVT. LTD.
# See LICENSE file for full copyright & licensing details.

from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = "stock.picking"

    request_id = fields.Many2one(
        "material.request", string="Material Requisition", readonly=True, copy=False
    )

    request_user = fields.Many2one(
        "res.users",
        string="Request By",
    )

    # def _create_backorder(self):
    #     """
    #     Override this method to update material request id in backorder.
    #     """
    #     backorder_recs = super(StockPicking, self)._create_backorder()
    #     for backorder_rec in backorder_recs:
    #         if backorder_rec.backorder_id.request_id:
    #             backorder_rec.write(
    #                 {"request_id": backorder_rec.backorder_id.request_id}
    #             )
    #             for backorder_qty in backorder_rec.move_ids_without_package:
    #                 request_line_ids = backorder_rec.backorder_id.request_id.request_line_ids.filtered(
    #                     lambda r: r.product_id == backorder_qty.product_id
    #                 )
    #                 if len(request_line_ids) == 1:
    #                     backorder_qty.write({
    #                         'order_qty': request_line_ids.qty
    #                     })
    #                 else:
    #                     pass
    #     return backorder_recs

    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        # Check if the user is in the 'stock.group_stock_manager' group
        if self.env.user.has_group('stock.group_stock_manager'):
            # If the user is a stock manager, return all records
            return super(StockPicking, self).search(args, offset=offset, limit=limit, order=order)
        elif self.env.user.has_group('stock.group_stock_user'):
            # For stock users, filter records based on user, partner, and transit locations
            partner = self.env['res.users'].browse(self.env.uid).partner_id
            args += ['|',('user_id', '=', self.env.user.id),('request_user', '=', self.env.user.id)]
            # Perform the search with the modified criteria
            return super(StockPicking, self).search(args, offset=offset, limit=limit, order=order)



# class StockMove(models.Model):
#     _inherit = "stock.move"
#
#     order_qty = fields.Float(
#          string="Order Qty ", readonly=True, copy=False
#     )
#     back_order_qty = fields.Float(
#         string="B/O Qty", compute='_compute_back_order_qty', readonly=True, copy=False
#     )
#
#     @api.depends('order_qty', 'quantity')
#     def _compute_back_order_qty(self):
#         for move in self:
#             # if move.order_qty and move.quantity_done:
#             move.back_order_qty = move.order_qty - move.quantity
