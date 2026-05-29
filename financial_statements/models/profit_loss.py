from odoo import models, fields, api
from .financial_statements import FinancialStatementBase


class ProfitLoss(models.Model):
    _name = 'profit.loss'
    _inherit = 'financial.statement.base'
    _description = 'Profit and Loss Statement'

    # Income
    revenue = fields.Float(string='Revenue')
    other_income = fields.Float(string='Other Income')

    # Expenses
    cost_of_services = fields.Float(string='Cost of Services')
    admin_expenses = fields.Float(string='Administrative Expenses')
    other_operating_expenses = fields.Float(string='Other Operating Expenses')
    finance_cost = fields.Float(string='Finance Cost')
    income_tax = fields.Float(string='Income Tax')

    # Detailed Expenses
    directors_fee = fields.Float(string="Directors' Fee")
    printing_stationery = fields.Float(string='Printing and Stationery')
    telecom_internet = fields.Float(string='Telecom and Internet')
    fines_penalties = fields.Float(string='Fines and Penalties')
    refreshment_mess = fields.Float(string='Refreshment and Mess')
    hire_upkeep_lorries = fields.Float(string='Hire and Upkeep of Lorries')
    transport_charges = fields.Float(string='Transport Charges')
    general_expenses = fields.Float(string='General Expenses')
    bank_charges = fields.Float(string='Bank Charges')
    incorporation_fee = fields.Float(string='Incorporation Fee Written Off')
    compilation_filing_fees = fields.Float(string='Compilation and Filing Fees')

    # Depreciation
    depreciation = fields.Float(string='Depreciation of Fixed Assets')

    # Calculated Fields
    gross_profit = fields.Float(string='Gross Profit', compute='_compute_totals')
    profit_from_operations = fields.Float(string='Profit from Operations', compute='_compute_totals')
    profit_before_tax = fields.Float(string='Profit Before Tax', compute='_compute_totals')
    net_profit = fields.Float(string='Net Profit', compute='_compute_totals')

    @api.depends('revenue', 'other_income', 'cost_of_services', 'admin_expenses',
                 'other_operating_expenses', 'finance_cost', 'income_tax', 'depreciation',
                 'directors_fee', 'printing_stationery', 'telecom_internet', 'fines_penalties',
                 'refreshment_mess', 'hire_upkeep_lorries', 'transport_charges', 'general_expenses',
                 'bank_charges', 'incorporation_fee', 'compilation_filing_fees')
    def _compute_totals(self):
        for record in self:
            # Calculate detailed expenses if they exist
            if any([record.directors_fee, record.printing_stationery, record.telecom_internet,
                    record.fines_penalties, record.refreshment_mess, record.hire_upkeep_lorries,
                    record.transport_charges, record.general_expenses, record.bank_charges,
                    record.incorporation_fee, record.compilation_filing_fees]):
                record.admin_expenses = record.directors_fee + record.printing_stationery + record.telecom_internet
                record.other_operating_expenses = (record.fines_penalties + record.refreshment_mess +
                                                   record.hire_upkeep_lorries + record.transport_charges +
                                                   record.general_expenses + record.bank_charges +
                                                   record.incorporation_fee + record.compilation_filing_fees)

            # Main calculations
            record.gross_profit = record.revenue - record.cost_of_services
            record.profit_from_operations = (record.gross_profit - record.admin_expenses -
                                             record.other_operating_expenses)
            record.profit_before_tax = record.profit_from_operations - record.finance_cost - record.depreciation
            record.net_profit = record.profit_before_tax - record.income_tax