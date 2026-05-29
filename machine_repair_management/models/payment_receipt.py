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
    account_move_id = fields.Many2one('account.move', string="Account Move", store=True)
    customer_name = fields.Char(string="Customer name")
    inspection_charges_amount_received_bool = fields.Boolean('Inspection Charges Amount Received', default=False)
    balance_amount_received_bool = fields.Boolean(string="Balance Amount Received", default=False)
    online_transaction_date = fields.Datetime(string="Online Transaction Date")
    online_transaction_status = fields.Selection([('paid', 'Paid'), ('not_paid', 'Not Paid')],
                                                 string="Online Transaction Status")
    online_transaction_reference = fields.Char(string="Online Transaction Reference")
    mode_of_payment = fields.Selection([('cash', 'Cash'), ('online', 'Online Payment'),
                                        ('bank', 'Bank Transfer'), ('credit', 'Credit')], string="Method of Payment")

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            name = self.env['ir.sequence'].next_by_code('payment.receipt')
            vals['name'] = name
            result = super(PaymentReceipt, self).create(vals)
        return result

    def print_payment_receipt(self):
        return {
            'type': 'ir.actions.report',
            'report_name': 'machine_repair_management.report_receipt_payment',
            'model': 'payment.receipt',
            'docids': self.ids,  # Pass the current record ID(s)
            'report_type': 'qweb-pdf',
        }

    def show_journal_entry(self):
        return {
            'name': 'Journal Entry',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', '=', self.account_move_id.id)]
        }

    def show_job_card(self):
        task_search = self.env['project.task'].search([('name', '=', self.job_card_no_id.name)], limit=1)
        if task_search:
            return {
                'name': 'Job Card',
                'type': 'ir.actions.act_window',
                'res_model': 'project.task',
                'view_mode': 'form',
                'target': 'current',
                'res_id': task_search.id

            }
