# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from datetime import date,datetime



class InventoryCountBackdateWizard(models.TransientModel):
    _name = 'inventory.count.backdate.wizard'
    _description = "Inventory count Backdate Wizard"

    inventory_count_stock_ids = fields.Many2many('setu.stock.inventory.count', string="Inventory Counts")
    backdate = fields.Datetime(string="Backdate", required=True)

    def open_inventory_count_backdate_wizard(self):
        active_ids = self.env.context.get('active_ids')
        active_record = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_id'))

        return {
            'name': 'Inventory count Backdate',
            'res_model': 'inventory.count.backdate.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('setu_inventory_count_management.inventory_count_backdate_wizard_view_form').id,
            'context': {
                'default_inventory_count_stock_ids': [(6, 0, active_ids)],
            },
            'target': 'new',
            'type': 'ir.actions.act_window'
        }

    def assign_backdate_inventory_counts(self):
        inventory_counts = self.inventory_count_stock_ids
        for count in inventory_counts:
            count.write({'inventory_count_date': self.backdate})
            for session in count.session_ids:
                session.write({'session_submit_date': self.backdate})
            for adjustment in count.inventory_adj_ids:
                adjustment.write({'date': self.backdate})

            stock_moves = self.env['stock.move'].search([('inventory_count_id', '=', count.id)])
            product_moves = self.env['stock.move.line'].search([('move_id', 'in', stock_moves.ids)])
            account_moves = self.env['account.move'].search([('stock_move_id', 'in', stock_moves.ids)])
            valuation_layers = self.env['stock.valuation.layer'].search([('stock_move_id', 'in', stock_moves.ids)])

            for move in stock_moves:
                move.date = self.backdate

            for move in product_moves:
                move.date = self.backdate


            for account_move in account_moves:
                account_move.button_draft()
                account_move.name = False
                account_move.date = self.backdate
                account_move.action_post()

            for layer in valuation_layers:
                self.env.cr.execute("""
                    Update stock_valuation_layer set create_date='%s' where id=%s;
                """ % (self.backdate, layer.id))


