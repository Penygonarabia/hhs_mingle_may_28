from odoo import models, fields, api


class ContractPaymentScheduleLine(models.Model):
    """Individual payment schedule line for a contract."""
    _name = 'contract.payment.schedule.line'
    _description = 'Contract Payment Schedule Line'
    _order = 'sequence, payment_date'

    contract_id = fields.Many2one(
        'subscription.contracts',
        string='Contract',
        ondelete='cascade',
        required=True,
        index=True
    )
    sequence = fields.Integer(string='#', default=10)
    name = fields.Char(string='Payment Label', required=True)
    name_ara = fields.Char(string='Payment Arabic Label')
    payment_date = fields.Date(string='Payment Date', required=True)
    amount = fields.Float(string='Amount (SAR)', digits=(16, 2))
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='contract_id.currency_id',
        store=True
    )
    state = fields.Selection([
        ('pending', 'Pending'),
        ('invoiced', 'Invoiced'),
        ('paid', 'Paid'),
        ], string='Status', default='pending')

