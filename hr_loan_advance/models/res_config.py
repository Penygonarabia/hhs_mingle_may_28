


# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import warnings, RedirectWarning


class hr_config_settings(models.TransientModel):
    _name = 'hr.config.settings'
    _inherit = 'res.config.settings'

    def _get_limit_of_loan_advance(self):
        return self.env['hr.config.settings'].search([], limit=1, order='id desc')

    def _get_limit_of_loan(self):
        config = self._get_limit_of_loan_advance()
        if config: return config.limit_of_loan
        return False

    def _get_loan_amount(self):
        config = self._get_limit_of_loan_advance()
        if config: return config.loan_amount
        return False

    def _get_loan_months(self):
        config = self._get_limit_of_loan_advance()
        if config: return config.loan_months
        return False

    def _get_limit_of_advance(self):
        config = self._get_limit_of_loan_advance()
        if config: return config.limit_of_advance
        return False

    def _get_advance_amount(self):
        config = self._get_limit_of_loan_advance()
        if config: return config.advance_amount
        return False

    def _get_advance_months(self):
        config = self._get_limit_of_loan_advance()
        if config: return config.advance_months
        return False

    limit_of_loan = fields.Selection([('amount', 'Amount'), ('basic', 'Basic Salary'), ], string='Limit of Loan',
                                     default=_get_limit_of_loan)
    loan_amount = fields.Float(string='Amount', default=_get_loan_amount)
    loan_months = fields.Integer(string='Months', default=_get_loan_months)
    limit_of_advance = fields.Selection([('amount', 'Amount'), ('basic', 'Basic Salary'), ], string='Limit of advance',
                                        default=_get_limit_of_advance)
    advance_amount = fields.Float(string='Amount', default=_get_advance_amount)
    advance_months = fields.Integer(string='Months', default=_get_advance_months)
