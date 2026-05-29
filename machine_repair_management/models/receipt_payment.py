from odoo import api, fields, models, _


class PaymentReceipt(models.Model):
    _name = "payment.receipt"
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']
    _description = "Payment Receipt"

    name = fields.Char(string="Reference Number", default=lambda self: _('New'))
    # name = fields.Char(string ="Reference Number",  default = lambda self: self.env['ir.sequence'].next_by_code('payment.receipt'))

    date = fields.Date(string="Date", tracking=True)

    job_card_no_id = fields.Many2one('project.task', string="Job Card No.", ondelete="cascade")

    partner_id = fields.Many2one('res.partner', string="Customer", tracking=True)

    amount = fields.Float(string="Amount")

    journal_id = fields.Many2one('account.journal', string="Journal", tracking=True)

    payment_id = fields.Many2one('account.payment.method.line', string="Payment")

    memo = fields.Char(string="Memo")

    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted')], string="State", tracking=True)

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            name = self.env['ir.sequence'].next_by_code('payment.receipt')
            vals['name'] = name
            result = super(PaymentReceipt, self).create(vals)
        return result
