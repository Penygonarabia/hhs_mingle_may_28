# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software PVT. LTD.
# See LICENSE file for full copyright & licensing details.

from odoo import api, fields, models


class MaterialRequestLine(models.Model):
    _name = "material.request.line"
    _description = "Material Request Lines"

    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
    )
    description = fields.Char(
        string="Description",
        required=True,
    )
    qty = fields.Float(
        string="Qty",
        default="0",
        required=True,
    )
    on_hand_qty = fields.Float(
        string="O/H Qty",
        compute="_compute_on_hand_qty",  # Compute method to calculate on_hand_qty
        store=True,  # Store the value in the database for persistence
        readonly=True
    )
    product_uom_category_id = fields.Many2one(
        related="product_id.uom_id.category_id", readonly=True
    )
    uom_id = fields.Many2one(
        "uom.uom",
        string="UOM",
        required=True,
        domain="[('category_id', '=', product_uom_category_id)]",
    )
    request_id = fields.Many2one("material.request")

    @api.onchange("product_id")
    def product_id_change(self):
        if self.product_id:
            self.description = self.product_id.name
            self.uom_id = self.product_id.uom_id
            # loc_on_hand_qty = self.env['stock.quant'].search([('location_id', '=', self.request_id.dest_location_id.id),
            #                                                   ('product_id', '=', self.product_id.id)])
            # qty = 0.00
            # for loc in loc_on_hand_qty:
            #     if self.request_id.dest_location_id == loc.location_id:
            #         qty = loc.quantity
            # self.on_hand_qty = qty
        return {'domain': {'product_id': [('stock_quant_ids.location_id', '=', self.request_id.dest_location_id.id)]}}

    @api.depends("product_id", "request_id.dest_location_id")
    def _compute_on_hand_qty(self):
        for line in self:
            if line.product_id and line.request_id.dest_location_id:
                loc_on_hand_qty = self.env['stock.quant'].search([
                    ('location_id', '=', line.request_id.dest_location_id.id),
                    ('product_id', '=', line.product_id.id)
                ])
                qty = sum(loc.quantity for loc in loc_on_hand_qty)
                line.on_hand_qty = qty