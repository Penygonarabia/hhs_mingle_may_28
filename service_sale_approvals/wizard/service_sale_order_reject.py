# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ServiceSaleOrderReject(models.TransientModel):
    _name = "service.sale.order.reject"
    _description = "Service Sale Order Reject Wizard"

    order_id = fields.Many2one('service.sale.order', string="Service Sale Order")
    reason = fields.Text("Rejection Reason")

    # def action_reject_service_sale_order(self):
    #     if not self.order_id:
    #         raise ValidationError(_('Service Sale Order not found! Refresh the page and try again.'))
    #     if self.order_id and self.order_id.current_waiting_approval_line_id and not self.order_id.current_waiting_approval_line_id.state and not self.order_id.current_approval_state:
    #         self.order_id.reject_date = fields.Datetime.now()
    #         self.order_id.rejected_user_id = self.env.user.id
    #         self.order_id.reject_reason = self.reason if self.reason else False
    #         self.order_id.state = 'reject'
    #         self.order_id.is_rejected = True
    #         template = self.env.ref('bi_all_in_one_dynamic_approval.reject_approval_email_template')
    #         if template:
    #             if self.order_id.is_saleperson_in_cc:
    #                 template.email_cc = self.order_id.user_id.email if self.order_id.user_id else False
    #             mail = template.send_mail(int(self.order_id.id))
    #             if mail:
    #                 mail_id = self.env['mail.mail'].browse(mail)
    #                 mail_id[0].sudo().send()
    #     return True

    def action_reject_service_sale_order(self):
        """
        Rejects the AMC sale order referenced in active_id.
        Allowed states: draft, sent, waiting
        Writes rejection info and sends email notification safely.
        """
        active_id = self.env.context.get('active_id')
        if not active_id:
            raise ValidationError(_('No active Sale Order found!'))

        # Fetch the sale order record (respects record rules)
        order = self.env['service.sale.order'].browse(active_id)
        if not order.exists():
            raise ValidationError(_('Sale Order not found or already deleted!'))

        # Check AMC quotation and allowed states
        allowed_states = ['draft', 'sent', 'waiting']
        if order.state not in allowed_states or not order.amc_quotation:
            raise ValidationError(_('Only AMC quotations in Draft, Sent, or Waiting state can be rejected.'))

        # Check approval lines
        if not (order.current_waiting_approval_line_id or order.current_approval_state):
            raise ValidationError(_('No approval line is waiting, cannot reject.'))

        # Write rejection info (no sudo)
        order.write({
            'reject_date': fields.Datetime.now(),
            'rejected_user_id': self.env.user.id,
            'reject_reason': self.reason or False,
            'state': 'reject',
            'is_rejected': True,
        })

        # Send email safely using template.sudo()
        template = self.env.ref(
            'bi_all_in_one_dynamic_approval.reject_approval_email_template',
            raise_if_not_found=False
        )
        if template:
            # Optional: include salesperson in CC
            if order.is_saleperson_in_cc and order.user_id:
                template.email_cc = order.user_id.email

            try:
                template.sudo().send_mail(
                    res_id=order.id,
                    force_send=True,
                    raise_exception=False  # prevent crash if QWeb fails
                )
            except Exception as e:
                _logger.warning('Failed to send rejection email: %s', e)

        return True