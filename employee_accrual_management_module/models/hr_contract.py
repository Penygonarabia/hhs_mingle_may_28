# -*- coding: utf-8 -*-

# from odoo import api, fields, models, _
#
#
# class HrContract(models.Model):
#     _inherit = 'hr.contract'
#
#     accrual_leave_debit_account_id = fields.Many2one(
#         'account.account',
#         string="Accrual Leave Debit Account"
#     )
#     accrual_leave_credit_account_id = fields.Many2one(
#         'account.account',
#         string="Accrual Leave Credit Account"
#     )
#     accrual_ticket_debit_account_id = fields.Many2one(
#         'account.account',
#         string="Accrual Ticket Debit Account"
#     )
#     accrual_ticket_credit_account_id = fields.Many2one(
#         'account.account',
#         string="Accrual Ticket Credit Account"
#     )

from odoo import api, fields, models, _


class HrContract(models.Model):
    _inherit = 'hr.contract'

    custom_allowance = fields.Float(
        string='Allowance for Gratuity'
    )
