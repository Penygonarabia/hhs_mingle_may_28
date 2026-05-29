# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrTransactionRule(models.Model):

    _name = 'hr.transaction.rule'
    _description = 'Transaction Rule'

    name = fields.Char('Name', translate=True)
    code = fields.Char('Code')
    rule_type = fields.Selection([('transaction_allowance', 'Allowance'), ('transaction_detection', 'Deduction'), ('charge_out', 'Charge Out'), ('accrual', 'Accrual(Reserve)'), ('not_applicable', 'Not Applicable')], string='Rule Type')
    unit_type = fields.Selection([('hours', 'Hours'), ('days', 'Days'), ('amount', 'Amount')], string='Unit Type')


