# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError

class ModelApprovalInherit(models.Model):
    _inherit = 'model.approval'

    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        domain="[('model', 'in', ['sale.order', 'purchase.order', 'account.move', 'account.payment', 'service.sale.order', 'crm.commercial.lead', 'crm.commercial.quotation'])]",
        required=True,
        ondelete='cascade'
    )

class CrmCommercialQuotationApproved(models.Model):
    _name = 'crm.commercial.quotation.approved'
    _description = 'Quotation Approval Line'
    _order = 'approval_level, sequence, id'

    quotation_id = fields.Many2one('crm.commercial.quotation', ondelete='cascade', required=True)
    approval_level = fields.Integer(string='Level')
    sequence = fields.Integer(string='Sequence', default=1)
    user_ids = fields.Many2many('res.users', 'crm_quot_appr_line_user_rel', 'line_id', 'user_id', string='Allowed Users')
    group_ids = fields.Many2many('res.groups', 'crm_quot_appr_line_group_rel', 'line_id', 'group_id', string='Allowed Groups')
    state = fields.Boolean('Approved', default=False)
    approved_date = fields.Datetime(string='Approved Date')
    approved_id = fields.Many2one('res.users', string='Approved By')


class CrmCommercialQuotationReject(models.TransientModel):
    _name = 'crm.commercial.quotation.reject'
    _description = 'Quotation Reject Wizard'

    quotation_id = fields.Many2one('crm.commercial.quotation', required=True)
    reason = fields.Text(required=True)

    def action_reject(self):
        self.ensure_one()
        quotation = self.quotation_id
        if not quotation.is_approval_reject_button:
            raise UserError(_('You are not allowed to reject this quotation.'))
        quotation.with_context(approval_flow=True).write({
            'state': 'rejected',
            'is_rejected': True,
            'reject_date': fields.Datetime.now(),
            'rejected_user_id': self.env.user.id,
            'reject_reason': self.reason,
            'user_ids': [(5, 0, 0)],
            'group_ids': [(5, 0, 0)],
        })
        quotation._clear_approval_activities()
        quotation._log_audit('Quotation Rejected',
                             _('Rejected by %s. Reason: %s') % (self.env.user.name, self.reason))
        quotation._notify_salesman(_('Quotation %s was rejected by %s.<br/>Reason: %s')
                                   % (quotation.name, self.env.user.name, self.reason))
        return {'type': 'ir.actions.act_window_close'}
