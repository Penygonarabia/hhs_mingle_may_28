# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def read(self, fields=None, load='_classic_read'):
        if self.env.user.company_id.dynamic_approval:
            data = self.search([]).filtered(
                lambda l: l.is_approval_reject_button)
            data._compute_is_approval_reject_button()
        return super(SaleOrder, self).read(fields=fields, load=load)
    
    @api.model
    def default_get(self, fields):
        res = super(SaleOrder, self).default_get(fields)
        if self.env.user.company_id.dynamic_approval:
            model_approval_id = self.env['model.approval'].sudo().search([('model_id', '=', 'sale.order'), ('active', '=', True)])
            if model_approval_id and model_approval_id.mapped('approval_ids') and not res.get('suggested_ids'):
                res['suggested_ids'] = model_approval_id.mapped('approval_ids')
        return res

    is_approval = fields.Boolean(related='company_id.dynamic_approval', copy=False)
    state = fields.Selection(
        selection_add=[('waiting', 'Waiting For Approval'), ('reject', 'Reject')])
    sale_approval_id = fields.Many2one(
        'approval.approval', string='Approval Level', copy=False)
    user_ids = fields.Many2many('res.users', string='Users', copy=False)
    group_ids = fields.Many2many('res.groups', string='Groups', copy=False)
    next_approval_level = fields.Char(string='Next Approval Level', copy=False)
    reject_date = fields.Datetime('Reject Date', copy=False)
    rejected_user_id = fields.Many2one(
        'res.users', string='Reject By', copy=False)
    reject_reason = fields.Text('Reject Reason', copy=False)
    current_waiting_approval_line_id = fields.Many2one(
        'sale.order.approved', string='Current approval line', copy=False)
    sale_approved_ids = fields.One2many(
        'sale.order.approved', 'order_id', string='Sale Approval Details')
    current_approval_state = fields.Boolean(
        'Current approval state', copy=False)
    is_saleperson_in_cc = fields.Boolean('Sales Person in CC', default=False)
    approved_user_ids = fields.Many2many(
        'res.users',  'approved_user_sale_order_rel', string='Approved Users', copy=False)
    is_approval_reject_button = fields.Boolean(
        'Approval Reject button', default=False, compute='_compute_is_approval_reject_button')
    is_rejected = fields.Boolean('Reject Order', default=False, copy=False)
    all_level_approved = fields.Boolean(
        'All Level Approved', default=False, compute='_compute_all_level_approved')
    is_display = fields.Boolean()
    suggested_ids = fields.Many2many('approval.approval', string='Suggested Approval', copy=False, compute="_compute_suggested_ids")

    @api.model_create_multi
    def create(self, values):
        result = super(SaleOrder, self).create(values)
        for res in result:
            if res.is_approval and not res.sale_approval_id and res.suggested_ids and res.state == 'draft' and res.company_id.approval_type:
                if res.company_id.approval_type == 'before_tax_amount':
                    data = res.suggested_ids.filtered(lambda l: l.minimum_amount <= res.amount_untaxed)
                    if data:
                        new_approval_id = data.sorted(key=lambda l: l.minimum_amount)[0].id
                        res.sale_approval_id = new_approval_id
                    else:
                        raise ValidationError('You need to add approvals for create this sale order!')
                if res.company_id.approval_type == 'total':
                    data = res.suggested_ids.filtered(lambda l: l.minimum_amount <= res.amount_total)
                    if data:
                        new_approval_id = data.sorted(key=lambda l: l.minimum_amount)[0].id
                        res.sale_approval_id = new_approval_id
                    else:
                        raise ValidationError('You need to add approvals for create this sale order!')
        return result

    def write(self, values):
        approval = False
        for record in self:
            approval = record.sale_approval_id
        result = super(SaleOrder, self).write(values)
        for record in self:
            if not record.sale_approval_id and approval:
                if record.is_approval and not record.sale_approval_id and record.suggested_ids and record.state == 'draft' and record.company_id.approval_type:
                    if record.company_id.approval_type == 'before_tax_amount':
                        data = record.suggested_ids.filtered(lambda l: l.minimum_amount <= record.amount_untaxed)
                        if data:
                            new_approval_id = data.sorted(key=lambda l: l.minimum_amount)[0].id
                            record.sale_approval_id = new_approval_id
                        else:
                            raise ValidationError('You need to add approvals for create this sale order!')
                    if record.company_id.approval_type == 'total':
                        data = record.suggested_ids.filtered(lambda l: l.minimum_amount <= record.amount_total)
                        if data:
                            new_approval_id = data.sorted(key=lambda l: l.minimum_amount)[0].id
                            record.sale_approval_id = new_approval_id
                        else:
                            raise ValidationError('You need to add approvals for create this sale order!')
        return result

    @api.depends('amount_total', 'amount_untaxed')
    def _compute_suggested_ids(self):
        for record in self:
            record.suggested_ids = False

            if record.is_approval:
                model_approval_id = self.env['model.approval'].sudo().search([
                    ('model_id', '=', 'sale.order'),
                    ('active', '=', True)
                ])
                if model_approval_id and model_approval_id.mapped('approval_ids'):
                    record.suggested_ids = model_approval_id.mapped('approval_ids')

                if record.order_line and record.suggested_ids and record.state == 'draft' and record.company_id.approval_type:
                    if record.company_id.approval_type == 'before_tax_amount':
                        data = record.suggested_ids.filtered(lambda l: l.minimum_amount <= record.amount_untaxed)
                        if data:
                            new_approval_id = data.sorted(key=lambda l: l.minimum_amount, reverse=True)[0].id
                            record.sale_approval_id = new_approval_id
                        else:
                            record.sale_approval_id = False

                    elif record.company_id.approval_type == 'total':
                        data = record.suggested_ids.filtered(lambda l: l.minimum_amount <= record.amount_total)
                        if data:
                            new_approval_id = data.sorted(key=lambda l: l.minimum_amount, reverse=True)[0].id
                            record.sale_approval_id = new_approval_id
                        else:
                            record.sale_approval_id = False


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

    @api.depends('sale_approved_ids')
    def _compute_all_level_approved(self):
        for record in self:
            if record.sale_approved_ids and all(record.sale_approved_ids.mapped('state')):
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
            raise ValidationError(_('Change approval Settings!'))
        return {
            'name': _('Sale Order Reject'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order.reject',
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
            self.action_confirm()
        return True

    def _prepare_approved_line(self, line):
        if line:
            return {
                'approval_level': line.level,
                'user_ids': line.user_ids.ids if line.user_ids else [],
                'group_ids': line.group_ids.ids if line.group_ids else [],
            }

    def action_confirm(self):
        for current in self:
            if current.is_approval and current.sale_approval_id:
                if current.sale_approval_id and not current.sale_approved_ids:
                    if not current.sale_approval_id.approval_line_ids:
                        raise ValidationError(_('No any approval level found!'))
                    approval_lines = []
                    for record in current.sale_approval_id.approval_line_ids:
                        approval_lines.append(
                            (0, 0, current._prepare_approved_line(record)))
                    if approval_lines:
                        current.write({'sale_approved_ids': approval_lines,
                                   'is_saleperson_in_cc': current.sale_approval_id.is_sale_person})
                        template = self.env.ref(
                            'bi_all_in_one_dynamic_approval.request_approval_email_template')
                        if template:
                            if current.is_saleperson_in_cc:
                                template.email_cc = current.user_id.email if current.user_id else False
                            mail = template.send_mail(int(current.id))
                            if mail:
                                mail_id = self.env['mail.mail'].browse(mail)
                                mail_id[0].sudo().send()
                if current.sale_approved_ids:
                    if not all(current.sale_approved_ids.mapped('state')):
                        approval_level = 0
                        for approval in current.sale_approved_ids.filtered(lambda l: not l.state):
                            if approval_level < approval.approval_level and (not current.current_waiting_approval_line_id or current.current_waiting_approval_line_id.state) and (current.current_approval_state or approval_level == 0):
                                approval_level = approval.approval_level
                                current.user_ids = False
                                current.group_ids = False
                                current.next_approval_level = str(
                                    approval.approval_level)
                                current.user_ids = approval.user_ids.ids
                                current.group_ids = approval.group_ids.ids
                                current.state = 'waiting'
                                current.current_waiting_approval_line_id = approval.id
                                current.current_approval_state = False
                        submit_template = self.env.ref(
                            'bi_all_in_one_dynamic_approval.submit_for_approval_email_template')
                        if submit_template:
                            mail = submit_template.send_mail(int(current.id))
                            if current.is_saleperson_in_cc:
                                submit_template.email_cc = current.user_id.email if current.user_id else False
                            if mail:
                                mail_id = self.env['mail.mail'].browse(mail)
                                mail_id[0].sudo().send()
                    else:
                        if current.all_level_approved:
                            template = self.env.ref(
                                'bi_all_in_one_dynamic_approval.approved_sale_order_email_template')
                            if template:
                                if current.is_saleperson_in_cc:
                                    template.email_cc = current.user_id.email if current.user_id else False
                                mail = template.send_mail(int(current.id))
                                if mail:
                                    mail_id = self.env['mail.mail'].browse(mail)
                                    mail_id[0].sudo().send()
                        return super(SaleOrder, self).action_confirm()
            else:
                return super(SaleOrder, self).action_confirm()

    @api.onchange('sale_approval_id')
    def onchange_sale_approval_id(self):
        if self.sale_approval_id:
            if self.company_id.approval_type and self.company_id.approval_type == 'total' and self.sale_approval_id.minimum_amount > self.amount_total:
                raise ValidationError(
                    _('Selected Approval is not proper as per your order!'))
            if self.company_id.approval_type and self.company_id.approval_type == 'before_tax_amount' and self.sale_approval_id.minimum_amount > self.amount_untaxed:
                raise ValidationError(
                    _('Selected Approval is not proper as per your order!'))
                    
                    
    def _can_be_confirmed(self):
        self.ensure_one()
        return self.state in {'draft', 'sent','waiting'}
