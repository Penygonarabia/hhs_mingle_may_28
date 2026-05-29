# -*- coding: utf-8 -*-
from odoo import models, fields, api
from .financial_statements import FinancialStatementBase


class BalanceSheet(models.Model):
    _name = 'balance.sheet'
    _inherit = 'financial.statement.base'
    _description = 'Balance Sheet'

    # Assets
    fixed_assets = fields.Float(string='Fixed Assets')
    trade_receivables = fields.Float(string='Trade Receivables')
    advance_to_shareholder = fields.Float(string='Advance to Shareholder')
    cash_equivalents = fields.Float(string='Cash and Cash Equivalents')

    # Equity and Liabilities
    issued_capital = fields.Float(string='Issued Capital')
    accumulated_profit = fields.Float(string='Accumulated Profit')
    accrued_charges = fields.Float(string='Accrued Charges')
    provision_taxation = fields.Float(string='Provision for Taxation')

    # Calculated Fields
    total_non_current_assets = fields.Float(string='Total Non-Current Assets', compute='_compute_totals')
    total_current_assets = fields.Float(string='Total Current Assets', compute='_compute_totals')
    total_assets = fields.Float(string='Total Assets', compute='_compute_totals')
    total_equity = fields.Float(string='Total Equity', compute='_compute_totals')
    total_current_liabilities = fields.Float(string='Total Current Liabilities', compute='_compute_totals')
    total_equity_liabilities = fields.Float(string='Total Equity and Liabilities', compute='_compute_totals')

    @api.depends('fixed_assets', 'trade_receivables', 'advance_to_shareholder', 'cash_equivalents',
                 'issued_capital', 'accumulated_profit', 'accrued_charges', 'provision_taxation')
    def _compute_totals(self):
        for record in self:
            # Assets
            record.total_non_current_assets = record.fixed_assets
            record.total_current_assets = record.trade_receivables + record.advance_to_shareholder + record.cash_equivalents
            record.total_assets = record.total_non_current_assets + record.total_current_assets

            # Equity and Liabilities
            record.total_equity = record.issued_capital + record.accumulated_profit
            record.total_current_liabilities = record.accrued_charges + record.provision_taxation
            record.total_equity_liabilities = record.total_equity - record.total_current_liabilities