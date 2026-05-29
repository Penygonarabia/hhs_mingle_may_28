from odoo import models, fields, api
from .financial_statements import FinancialStatementBase


class CashFlow(models.Model):
    _name = 'cash.flow'
    _inherit = 'financial.statement.base'
    _description = 'Cash Flow Statement'

    # Operating Activities
    profit_before_tax = fields.Float(string='Profit Before Tax')
    depreciation = fields.Float(string='Depreciation')
    bank_charges = fields.Float(string='Bank Charges')
    change_receivables = fields.Float(string='Change in Receivables')
    change_payables = fields.Float(string='Change in Payables')
    income_tax_paid = fields.Float(string='Income Tax Paid')

    # Investing Activities
    purchase_fixed_assets = fields.Float(string='Purchase of Fixed Assets')

    # Financing Activities
    issue_shares = fields.Float(string='Issue of Shares')

    # Beginning and Ending Cash
    cash_beginning = fields.Float(string='Cash at Beginning')

    # Calculated Fields
    operating_cash_flow = fields.Float(string='Operating Cash Flow', compute='_compute_totals')
    cash_from_operations = fields.Float(string='Cash from Operations', compute='_compute_totals')
    net_operating_cash = fields.Float(string='Net Cash from Operating Activities', compute='_compute_totals')
    net_investing_cash = fields.Float(string='Net Cash from Investing Activities', compute='_compute_totals')
    net_financing_cash = fields.Float(string='Net Cash from Financing Activities', compute='_compute_totals')
    net_cash_change = fields.Float(string='Net Increase in Cash', compute='_compute_totals')
    cash_ending = fields.Float(string='Cash at End', compute='_compute_totals')

    @api.depends('profit_before_tax', 'depreciation', 'bank_charges', 'change_receivables',
                 'change_payables', 'income_tax_paid', 'purchase_fixed_assets', 'issue_shares',
                 'cash_beginning')
    def _compute_totals(self):
        for record in self:
            # Operating Activities
            record.operating_cash_flow = record.profit_before_tax + record.depreciation + record.bank_charges
            record.cash_from_operations = record.operating_cash_flow + record.change_receivables + record.change_payables
            record.net_operating_cash = record.cash_from_operations - record.income_tax_paid - record.bank_charges

            # Investing Activities
            record.net_investing_cash = -record.purchase_fixed_assets

            # Financing Activities
            record.net_financing_cash = record.issue_shares

            # Net Change and Ending
            record.net_cash_change = record.net_operating_cash + record.net_investing_cash + record.net_financing_cash
            record.cash_ending = record.cash_beginning + record.net_cash_change