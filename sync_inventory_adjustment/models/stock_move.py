# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    inventory_id = fields.Many2one('stock.inventory', string='Inventory')
    adj_unit_cost = fields.Float('Unit Cost', compute="_compute_unit_cost")
    adj_subtotal = fields.Float('Sub Total')
    analytic_account_id = fields.Many2one(
        string="Analytic Account", comodel_name="account.analytic.account", readonly=True,
    )
    inventory_adjustment = fields.Boolean("Inventory Adjustment")
    
    @api.depends('inventory_id', 'product_id')
    def _compute_unit_cost(self):
        for rec in self:
            if rec.inventory_id and rec.product_id:
                for line in rec.inventory_id.line_ids.filtered(lambda line: line.product_id == rec.product_id):
                    rec.adj_unit_cost = line.product_id.standard_price
                    rec.quantity = rec.product_uom_qty
                    rec.adj_subtotal = rec.adj_unit_cost * rec.quantity
                    rec.reference = rec.inventory_id.name
                    rec.analytic_account_id = rec.inventory_id.analytic_account_id

  
    
    def _account_entry_move(self, qty, description, svl_id, cost):
        """ Accounting Valuation Entries """
        self.ensure_one()
        am_vals = []
        if self.product_id.type != 'product':
            # no stock valuation for consumable products
            return am_vals
        if self.restrict_partner_id and self.restrict_partner_id != self.company_id.partner_id:
            # if the move isn't owned by the company, we don't make any valuation
            return am_vals
        
        if self.inventory_id and self.inventory_adjustment == True:
            return am_vals

        company_from = self._is_out() and self.mapped('move_line_ids.location_id.company_id') or False
        company_to = self._is_in() and self.mapped('move_line_ids.location_dest_id.company_id') or False

        journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
        # Create Journal Entry for products arriving in the company; in case of routes making the link between several
        # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
        if self._is_in():
            if self._is_returned(valued_type='in'):
                am_vals.append(self.with_company(company_to)._prepare_account_move_vals(acc_dest, acc_valuation, journal_id, qty, description, svl_id, cost))
            else:
                am_vals.append(self.with_company(company_to)._prepare_account_move_vals(acc_src, acc_valuation, journal_id, qty, description, svl_id, cost))

        # Create Journal Entry for products leaving the company
        if self._is_out():
            cost = -1 * cost
            if self._is_returned(valued_type='out'):
                am_vals.append(self.with_company(company_from)._prepare_account_move_vals(acc_valuation, acc_src, journal_id, qty, description, svl_id, cost))
            else:
                am_vals.append(self.with_company(company_from)._prepare_account_move_vals(acc_valuation, acc_dest, journal_id, qty, description, svl_id, cost))

        if self.company_id.anglo_saxon_accounting:
            # Creates an account entry from stock_input to stock_output on a dropship move. https://github.com/odoo/odoo/issues/12687
            if self._is_dropshipped():
                if cost > 0:
                    am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals(acc_src, acc_valuation, journal_id, qty, description, svl_id, cost))
                else:
                    cost = -1 * cost
                    am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals(acc_valuation, acc_dest, journal_id, qty, description, svl_id, cost))
            elif self._is_dropshipped_returned():
                if cost > 0 and self.location_dest_id._should_be_valued():
                    am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals(acc_valuation, acc_src, journal_id, qty, description, svl_id, cost))
                elif cost > 0:
                    am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals(acc_dest, acc_valuation, journal_id, qty, description, svl_id, cost))
                else:
                    cost = -1 * cost
                    am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals(acc_valuation, acc_src, journal_id, qty, description, svl_id, cost))

        return am_vals
    
    
    
class InternalPickingType(models.Model):
    _inherit = 'stock.picking'

    journal_pick_count = fields.Integer(compute="_compute_journal_pick_count")

    def _compute_journal_pick_count(self):
        for rec in self:
            rec.journal_pick_count = len(rec.move_ids.mapped('account_move_ids'))

    def action_view_journal_entries(self):
       
        move_ids = self.move_lines.mapped('account_move_ids')
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entries',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', move_ids.ids)],
        }
        return action
    
