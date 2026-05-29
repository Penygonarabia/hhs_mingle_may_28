# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    custom_is_gratuity_journal = fields.Boolean(
        string='Is Gratuity Journal?',
        copy=False,
    )
    default_debit_account_id = fields.Many2one('account.account', string="Default Debit Account")
    default_credit_account_id = fields.Many2one('account.account', string="Default Credit Account")
