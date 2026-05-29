from odoo import api, fields, models, _

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # Fields for accrual leave accounts
    accrual_leave_debit_account_id = fields.Many2one(
        'account.account',
        string="Accrual Leave Debit Account"
    )
    accrual_leave_credit_account_id = fields.Many2one(
        'account.account',
        string="Accrual Leave Credit Account"
    )

    # Fields for accrual ticket accounts
    accrual_ticket_debit_account_id = fields.Many2one(
        'account.account',
        string="Accrual Ticket Debit Account"
    )
    accrual_ticket_credit_account_id = fields.Many2one(
        'account.account',
        string="Accrual Ticket Credit Account"
    )

    # Boolean fields to show or hide the accrual leave and ticket fields
    show_accrual_leave_accounts = fields.Boolean(
        string="Show Accrual Leave Accounts"
    )
    show_accrual_ticket_accounts = fields.Boolean(
        string="Show Accrual Ticket Accounts"
    )

    custom_is_gratuity_journal = fields.Boolean(
        string='Is Gratuity Journal?',
        copy=False,
    )
    default_debit_account_id = fields.Many2one('account.account', string="Default Debit Account")
    default_credit_account_id = fields.Many2one('account.account', string="Default Credit Account")

