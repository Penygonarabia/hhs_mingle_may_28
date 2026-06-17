from odoo import api, fields, models

class DealerShowroomSalesApproveWizard(models.TransientModel):
    _name = 'dsales.showroom.sales.approve.wizard'
    _description = 'Approve Shop Sales Wizard'

    invoice_id = fields.Many2one(
        'dsales.showroom.sales',
        string="Invoice No",
        required=True,
        domain="[('state', '=', 'submitted'), ('requires_approval', '=', True)]"
    )

    dealer_id = fields.Many2one(related='invoice_id.dealer_id', string='Dealer')
    dealer_showroom_id = fields.Many2one(related='invoice_id.dealer_showroom_id', string='Showroom')
    user_id = fields.Many2one(related='invoice_id.user_id', string='Salesman')
    date_time = fields.Datetime(related='invoice_id.date_time', string='Date')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], related='invoice_id.state', string='Status')
    
    reject_reason = fields.Text(related='invoice_id.reject_reason', string='Reject Reason')
    
    line_ids = fields.One2many(related='invoice_id.line_ids', string='Item Details')
    
    invoice_attachment = fields.Binary(related='invoice_id.invoice_attachment', string="Invoice Scan Copy")
    invoice_attachment_name = fields.Char(related='invoice_id.invoice_attachment_name')

    def action_approve(self):
        if self.invoice_id:
            # Need to close the wizard window explicitly, but wait, action_approve returns something?
            # action_approve normally returns True or nothing.
            res = self.invoice_id.action_approve()
            # If we want the wizard to stay open to approve another one, we can return an action, but usually it closes.
            return {'type': 'ir.actions.act_window_close'}
        return {'type': 'ir.actions.act_window_close'}

    def action_open_reject_wizard(self):
        if self.invoice_id:
            # action_open_reject_wizard returns an ir.actions.act_window
            return self.invoice_id.action_open_reject_wizard()
        return {'type': 'ir.actions.act_window_close'}
