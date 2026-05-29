# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def read(self, fields=None, load='_classic_read'):
        if self.env.user.company_id.dynamic_approval:
            data = self.search([]).filtered(
                lambda l: l.is_approval_reject_button)
            data._compute_is_approval_reject_button()
        return super(AccountMove, self).read(fields=fields, load=load)

    @api.model
    def default_get(self, fields):
        res = super(AccountMove, self).default_get(fields)
        current_uid = self.env.user.company_id
        if current_uid.dynamic_approval:
            if (current_uid.group_access_for_bill and res.get('move_type') == 'in_invoice') or (current_uid.group_access_for_invoice and res.get('move_type') == 'out_invoice'):
                res['is_visible'] = True
                model_approval_id = self.env['model.approval'].sudo().search([('model_id', '=', 'account.move'), ('active', '=', True)])
                if model_approval_id and model_approval_id.mapped('approval_ids') and not res.get('suggested_ids'):
                    res['suggested_ids'] = model_approval_id.mapped('approval_ids')
        if res.get('move_type'):
            type = res.get('move_type')
            if current_uid.dynamic_approval:
                if type == 'in_invoice' and current_uid.group_access_for_bill == False:
                    res['is_approve_visible'] = True
                elif type == 'out_invoice' and current_uid.group_access_for_invoice == False:
                    res['is_approve_visible'] = True
                else:
                    res['is_approve_visible'] = False
            else:
                res['is_approve_visible'] = True
        else:
            if current_uid.dynamic_approval:
                if self.move_type == 'in_invoice' and current_uid.group_access_for_bill == False:
                    self.is_approve_visible = True
                elif self.move_type == 'out_invoice' and current_uid.group_access_for_invoice == False:
                    self.is_approve_visible = True
                else:
                    self.is_approve_visible = False
            else:
                self.is_approve_visible = True
        return res

    state = fields.Selection(selection_add=[('waiting', 'Waiting For Approval'),('reject', 'Reject')],ondelete={'waiting': 'cascade','reject': 'cascade'})
    
    is_approve_visible = fields.Boolean("Is Approve Info Visible", default=False,
                                        compute='_compute_approve_info_visible')
    group_access_for_bill = fields.Boolean(string='On Vendor Bill', related='company_id.group_access_for_bill',
                                           readonly=False)
    group_access_for_invoice = fields.Boolean(string='On Customer Invoice',
                                              related='company_id.group_access_for_invoice', readonly=False)
    is_approval = fields.Boolean(related='company_id.dynamic_approval', copy=False)
    invoice_approval_id = fields.Many2one('approval.approval', string='Approval Level ', copy=False, default=False)
    user_ids = fields.Many2many('res.users', 'approved_user_ids_rel', string='Users', copy=False)
    group_ids = fields.Many2many('res.groups', string='Groups', copy=False)
    next_approval_level = fields.Char(string='Next Approval Level', copy=False)
    reject_date = fields.Datetime('Reject Date', copy=False)
    rejected_user_id = fields.Many2one(
        'res.users', string='Reject By', copy=False)
    reject_reason = fields.Text('Reject Reason', copy=False)
    current_waiting_approval_line_id = fields.Many2one(
        'invoice.line.approval', string='Current approval line', copy=False)
    invoice_approved_ids = fields.One2many(
        'invoice.line.approval', 'order_id', string='Invoice  Approval Details')
    current_approval_state = fields.Boolean(
        'Current approval state', copy=False)
    is_saleperson_in_cc = fields.Boolean('Approval Person in CC', default=False)
    approved_user_ids = fields.Many2many(
        'res.users', 'approved_user_account_invoice_rel', string='Approved Users', copy=False)
    is_approval_reject_button = fields.Boolean(
        'Approval Reject button', default=False, compute='_compute_is_approval_reject_button')
    is_rejected = fields.Boolean('Reject Order', default=False, copy=False)
    all_level_approved = fields.Boolean(
        'All Level Approved', default=False, compute='_compute_all_level_approved')
    is_display = fields.Boolean()
    suggested_ids = fields.Many2many('approval.approval', string='Suggested Approval', copy=False, compute="_compute_suggested_ids")
    is_visible = fields.Boolean('Visible')

    @api.model_create_multi
    def create(self, values):
        result = super(AccountMove, self).create(values)
        for res in result:
            if (res.group_access_for_bill and res.move_type == 'in_invoice') or (res.group_access_for_invoice and res.move_type == 'out_invoice'):
                if res.is_approval and not res.invoice_approval_id and res.suggested_ids and res.state == 'draft' and res.company_id.approval_type:
                    if res.company_id.approval_type == 'before_tax_amount':
                        data = res.suggested_ids.filtered(lambda l: l.minimum_amount <= res.amount_untaxed)
                        if data:
                            new_approval_id = data.sorted(key=lambda l: l.minimum_amount, reverse=True)[0].id
                            res.invoice_approval_id = new_approval_id
                        else:
                            raise ValidationError('You need to add approvals for create this record!')
                    if res.company_id.approval_type == 'total':
                        data = res.suggested_ids.filtered(lambda l: l.minimum_amount <= res.amount_total)
                        if data:
                            new_approval_id = data.sorted(key=lambda l: l.minimum_amount, reverse=True)[0].id
                            res.invoice_approval_id = new_approval_id
                        else:
                            raise ValidationError('You need to add approvals for create this record!')
        return result

    def write(self, values):
        approval = False
        for record in self:
            approval = record.invoice_approval_id
        result = super(AccountMove, self).write(values)
        for record in self:
            if (record.group_access_for_bill and record.move_type == 'in_invoice') or (record.group_access_for_invoice and record.move_type == 'out_invoice'):
                if (not record.invoice_approval_id and values.get('invoice_line_ids')) or approval:
                    if record.is_approval and not record.invoice_approval_id and record.suggested_ids and record.state == 'draft':
                        if record.company_id.approval_type == 'before_tax_amount':
                            data = record.suggested_ids.filtered(lambda l: l.minimum_amount <= record.amount_untaxed)
                            if data:
                                new_approval_id = data.sorted(key=lambda l: l.minimum_amount, reverse=True)[0].id
                                record.invoice_approval_id = new_approval_id
                            else:
                                raise ValidationError('You need to add approvals for create this record!')
                        if record.company_id.approval_type == 'total':
                            data = record.suggested_ids.filtered(lambda l: l.minimum_amount <= record.amount_total)
                            if data:
                                new_approval_id = data.sorted(key=lambda l: l.minimum_amount, reverse=True)[0].id
                                record.invoice_approval_id = new_approval_id
                            else:
                                raise ValidationError('You need to add approvals for create this record!')
        return result

    @api.depends('amount_total', 'amount_untaxed')
    def _compute_suggested_ids(self):
        for record in self:
            record.suggested_ids = False

            if record.is_approval:
                model_approval_id = self.env['model.approval'].sudo().search([
                    ('model_id', '=', 'account.move'),
                    ('active', '=', True)
                ])
                if model_approval_id and model_approval_id.mapped('approval_ids'):
                    record.suggested_ids = model_approval_id.mapped('approval_ids')

                if record.invoice_line_ids and record.suggested_ids and record.state == 'draft' and record.company_id.approval_type:
                    if record.company_id.approval_type == 'before_tax_amount':
                        data = record.suggested_ids.filtered(lambda l: l.minimum_amount <= record.amount_untaxed)
                        if data:
                            new_approval_id = data.sorted(key=lambda l: l.minimum_amount, reverse=True)[0].id
                            record.invoice_approval_id = new_approval_id
                        else:
                            record.invoice_approval_id = False

                    elif record.company_id.approval_type == 'total':
                        data = record.suggested_ids.filtered(lambda l: l.minimum_amount <= record.amount_total)
                        if data:
                            new_approval_id = data.sorted(key=lambda l: l.minimum_amount, reverse=True)[0].id
                            record.invoice_approval_id = new_approval_id
                        else:
                            record.invoice_approval_id = False


    def _compute_approve_info_visible(self):
        for rec in self:
            if rec.is_approval:
                if rec.move_type == 'in_invoice' and rec.group_access_for_bill == False:
                    rec.is_approve_visible = True
                elif rec.move_type == 'out_invoice' and rec.group_access_for_invoice == False:
                    rec.is_approve_visible = True
                else:
                    rec.is_approve_visible = False
            else:
                rec.is_approve_visible = True

    def _get_user_emails(self):
        self.ensure_one()
        if self.user_ids and not self.group_ids:
            send_users = self.user_ids.mapped(
                'partner_id').filtered(lambda l: l.email)
            return ", ".join([e for e in send_users.mapped("email") if e])
        if not self.user_ids and self.group_ids:
            approval_users = []
            users = self.env['res.users'].search([])
            for user in users:
                if (set(self.group_ids.ids).issubset(set(user.groups_id.ids))):
                    approval_users.append(user.id)
            user_data = self.env['res.users'].browse(approval_users).mapped(
                'partner_id').filtered(lambda l: l.email)
            if user_data:
                return ",".join([e for e in user_data.mapped("email") if e])

    @api.depends('invoice_approved_ids')
    def _compute_all_level_approved(self):
        for record in self:
            if record.invoice_approved_ids and all(record.invoice_approved_ids.mapped('state')):
                record.all_level_approved = True
            else:
                record.all_level_approved = False

    @api.depends('approved_user_ids', 'user_ids')
    def _compute_is_approval_reject_button(self):
        for record in self:
            record.is_display = False
            record.is_approval_reject_button = False
            if record.user_ids:
                if self.env.user.id in record.user_ids.ids:
                    record.is_display = True
                    record.is_approval_reject_button = True
            elif record.group_ids:
                if (set(record.group_ids.ids).issubset(set(self.env.user.groups_id.ids))):
                    record.is_approval_reject_button = True
                    record.is_display = True

    def action_reject(self):
        if not self.is_approval:
            raise UserError('Change approval Settings!')
        return {
            'name': ('Invoice Reject'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'invoice.reject',
            'target': 'new',
            'context': {'default_order_id': self.id}
        }

    def action_approve(self):
        if self.current_waiting_approval_line_id and not self.current_waiting_approval_line_id.state and not self.current_approval_state:
            self.current_approval_state = True
            self.current_waiting_approval_line_id.state = True
            self.current_waiting_approval_line_id.approved_date = fields.Datetime.now()
            self.current_waiting_approval_line_id.approved_id = self.env.user.id
            self.approved_user_ids = [(4, self.env.user.id)]
            self.action_post()
        return True

    def _prepare_approved_line(self, line):
        if line:
            return {
                'approval_level': line.level,
                'user_ids': line.user_ids.ids if line.user_ids else [],
                'group_ids': line.group_ids.ids if line.group_ids else [],
            }

    def _compute_amount(self):
        rec = super(AccountMove, self)._compute_amount()
        for record in self:
            if record.is_approval and record.state == 'draft' and record.company_id.approval_type:
                if record.company_id.approval_type == 'before_tax_amount':
                    data = self.env['approval.approval'].search(
                        [('minimum_amount', '<=', record.amount_untaxed)])
                    if len(data) == 1:
                        record.invoice_approval_id = data.id
                if record.company_id.approval_type == 'total':
                    data = self.env['approval.approval'].search(
                        [('minimum_amount', '<=', record.amount_total)])
                    if len(data) == 1:
                        record.invoice_approval_id = data.id
        return rec

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for current in self:
            if not current.group_access_for_invoice and not current.group_access_for_bill:
                return res
            elif current.move_type == 'out_invoice' and current.group_access_for_invoice:
                current.set_action_post()
                return res
            elif current.move_type == 'out_invoice' and not current.group_access_for_invoice:
                return res
            elif current.move_type == 'in_invoice' and current.group_access_for_bill:
                current.set_action_post()
                return res
            elif current.move_type == 'in_invoice' and not current.group_access_for_bill:
                return res
            else:
                current.set_action_post()
                return res

    def set_action_post(self):
        if self.is_approval and self.invoice_approval_id:
            if self.invoice_approval_id and not self.invoice_approved_ids:
                if not self.invoice_approval_id.approval_line_ids:
                    raise UserError('No any approval level found!')
                approval_lines = []
                for record in self.invoice_approval_id.approval_line_ids:
                    approval_lines.append(
                        (0, 0, self._prepare_approved_line(record)))
                if approval_lines:
                    self.write({'invoice_approved_ids': approval_lines,
                                'is_saleperson_in_cc': self.invoice_approval_id.is_sale_person})
                    template = self.env.ref(
                        'bi_all_in_one_dynamic_approval.request_approval_email_template_invoice')
                    if template:
                        if self.is_saleperson_in_cc:
                            template.email_cc = self.user_id.email if self.user_id else False
                        mail = template.send_mail(int(self.id))
                        if mail:
                            mail_id = self.env['mail.mail'].browse(mail)
                            mail_id[0].sudo().send()
            if self.invoice_approved_ids:
                if not all(self.invoice_approved_ids.mapped('state')):
                    approval_level = 0
                    for approval in self.invoice_approved_ids.filtered(lambda l: not l.state):
                        if approval_level < approval.approval_level and (
                                not self.current_waiting_approval_line_id or self.current_waiting_approval_line_id.state) and (
                                self.current_approval_state or approval_level == 0):
                            approval_level = approval.approval_level
                            self.user_ids = False
                            self.group_ids = False
                            self.next_approval_level = str(
                                approval.approval_level)
                            self.user_ids = approval.user_ids.ids
                            self.group_ids = approval.group_ids.ids
                            self.state = 'waiting'
                            self.current_waiting_approval_line_id = approval.id
                            self.current_approval_state = False
                    submit_template = self.env.ref(
                        'bi_all_in_one_dynamic_approval.submit_for_approval_email_template_invoice')
                    if submit_template:
                        mail = submit_template.send_mail(int(self.id))
                        if self.is_saleperson_in_cc:
                            submit_template.email_cc = self.user_id.email if self.user_id else False
                        if mail:
                            mail_id = self.env['mail.mail'].browse(mail)
                            mail_id[0].sudo().send()
                else:
                    if self.all_level_approved:
                        template = self.env.ref(
                            'bi_all_in_one_dynamic_approval.approved_sale_order_email_template_invoice')
                        if template:
                            if self.is_saleperson_in_cc:
                                template.email_cc = self.user_id.email if self.user_id else False
                            mail = template.send_mail(int(self.id))
                            if mail:
                                mail_id = self.env['mail.mail'].browse(mail)
                                mail_id[0].sudo().send()
                    else:
                        return True
        else:
            return True
