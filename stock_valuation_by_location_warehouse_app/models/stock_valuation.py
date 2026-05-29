# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class StockValuationLayer(models.Model):
	_inherit = 'stock.valuation.layer'


	location_id = fields.Many2one('stock.location', string='Location', store=True , compute='_compute_location_id')			
	warehouse_id = fields.Many2one('stock.warehouse',string="Warehouse" , store=True , compute='_compute_warehouse_id')

	@api.depends('stock_move_id.location_id')
	def _compute_location_id(self):
		for layer in self:
			layer.location_id = layer.stock_move_id.location_id


	@api.depends('stock_move_id.picking_id.picking_type_id.warehouse_id')
	def _compute_warehouse_id(self):
		for layer in self:
			layer.warehouse_id = layer.stock_move_id.picking_id.picking_type_id.warehouse_id
