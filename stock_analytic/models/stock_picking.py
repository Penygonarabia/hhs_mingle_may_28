# Copyright 2023 Quartile Limited
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = "stock.picking"

    internal_picking_type = fields.Selection([
        ('stock_request', 'Stock Request Type'),
        ('bin_location', 'Bin Location Type'),
        ('transfer', 'Transfer Type'),
    ], string='Internal Picking Type', default='transfer')
    
    analytic_account_id = fields.Many2one('account.analytic.account',
                                              string='Analytic Account',
                                              help="Analytic account of the warehouse",
                                              compute="_compute_analytic_account_id",
                                              store = True
                                              )
    
    @api.depends('picking_type_id')
    def _compute_analytic_account_id(self):
        for rec in self:
            rec.analytic_account_id = False
            if rec.picking_type_id:
                if rec.picking_type_id.warehouse_id.analytic_id:
                    rec.analytic_account_id = rec.picking_type_id.warehouse_id.analytic_id.id or False
                    
    
    @api.onchange('move_ids_without_package')
    def _onchange_line_ids(self):
        for rec in self:
            if rec.move_ids_without_package:
                analytic_id = rec.analytic_account_id
                rec.move_ids_without_package.analytic_distribution = {analytic_id.id:100}

    def button_validate(self):
        self = self.with_context(validate_analytic=True)
        return super().button_validate()
