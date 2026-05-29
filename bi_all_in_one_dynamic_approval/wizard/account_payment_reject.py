# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AccountPaymentReject(models.TransientModel):
    _name = "account.payment.reject"
    _description = "Payment Reject Wizard"

    order_id = fields.Many2one('account.payment', string="Payment")
    reason = fields.Text("Rejection Reason")

    def action_reject_payment_order(self):
        if not self.order_id:
            raise ValidationError(_('Payment not found!\n Refresh the page and try again.'))
        if self.order_id and self.order_id.current_waiting_approval_line_id and not self.order_id.current_waiting_approval_line_id.state and not self.order_id.current_approval_state:
            self.order_id.reject_date = fields.Datetime.now()
            self.order_id.rejected_user_id = self.env.user.id
            self.order_id.reject_reason = self.reason if self.reason else False
            self.order_id.state = 'reject'
            self.order_id.is_rejected = True
            template = self.env.ref('bi_all_in_one_dynamic_approval.reject_approval_email_template_payment')
            if template:
                mail = template.send_mail(int(self.order_id.id))
                if mail:
                    mail_id = self.env['mail.mail'].browse(mail)
                    mail_id[0].sudo().send()
        return True