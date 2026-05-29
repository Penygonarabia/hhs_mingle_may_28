# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from lxml import etree
import json

class ServiceSaleOrder(models.Model):
    _inherit = 'service.sale.order'

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        user = self.env.user
        # if not user._is_admin():
        if not user.user_has_groups('hr_saudi.group_sys_manager'):

            # Check if user is a CRM Team Leader (user_id)
            leader_teams = self.env['crm.team'].search([('user_id', '=', user.id)])
            if leader_teams:
                # Team leader → can see records from their teams OR own created records
                domain = expression.AND([
                    domain,
                    ['|',
                     ('create_uid', '=', user.id),
                     ('create_uid', 'in', leader_teams.member_ids.ids)
                     ]
                ])
            else:
                # Normal member → only see their own created records
                domain = expression.AND([
                    domain,
                    [('create_uid', '=', user.id)]
                ])
        return super(ServiceSaleOrder, self).search_fetch(domain, field_names, offset, limit, order)

    def read(self, fields=None, load='_classic_read'):
        if self.env.user.company_id.dynamic_approval:
            data = self.search([]).filtered(lambda l: l.is_approval_reject_button)
            data._compute_is_approval_reject_button()
        return super(ServiceSaleOrder, self).read(fields=fields, load=load)

    @api.model
    def default_get(self, fields):
        res = super(ServiceSaleOrder, self).default_get(fields)
        if self.env.user.company_id.dynamic_approval:
            model_approval_id = self.env['model.approval'].sudo().search([
                ('model_id', '=', 'service.sale.order'),
                ('active', '=', True)
            ])
            if model_approval_id and model_approval_id.mapped('approval_ids') and not res.get('suggested_ids'):
                res['suggested_ids'] = model_approval_id.mapped('approval_ids')
        return res

    is_approval = fields.Boolean(related='company_id.dynamic_approval', copy=False)
    # state = fields.Selection(selection_add=[('waiting', 'Waiting For Approval'), ('approve', 'Approved'), ('reject', 'Reject')])
    state = fields.Selection([('draft', 'Quotation'), ('waiting', 'Waiting For Approval'), ('approve', 'Approved'),
                              ('sent', 'Quotation Sent'),
                              ('sale', 'Confirmed'),
                              ('done', 'Locked'), ('reject', 'Reject'), ('cancel', 'Cancelled')], string='Status',
                              copy=True, tracking=3)
    service_sale_approval_id = fields.Many2one('approval.approval', string='Approval Level', copy=False)
    user_ids = fields.Many2many('res.users', string='Users', copy=False)
    group_ids = fields.Many2many('res.groups', string='Groups', copy=False)
    next_approval_level = fields.Char(string='Next Approval Level', copy=False)
    reject_date = fields.Datetime('Reject Date', copy=False)
    rejected_user_id = fields.Many2one('res.users', string='Reject By', copy=False)
    reject_reason = fields.Text('Reject Reason', copy=False)
    current_waiting_approval_line_id = fields.Many2one(
        'service.sale.order.approved', string='Current approval line', copy=False)
    service_sale_approved_ids = fields.One2many(
        'service.sale.order.approved', 'order_id', string='Service Sale Approval Details')
    current_approval_state = fields.Boolean('Current approval state', copy=False)
    is_saleperson_in_cc = fields.Boolean('Sales Person in CC', default=False)
    approved_user_ids = fields.Many2many(
        'res.users', 'approved_user_service_sale_order_rel', string='Approved Users', copy=False)
    is_approval_reject_button = fields.Boolean(
        'Approval Reject button', default=False, compute='_compute_is_approval_reject_button')
    is_rejected = fields.Boolean('Reject Order', default=False, copy=False)
    all_level_approved = fields.Boolean(
        'All Level Approved', default=False, compute='_compute_all_level_approved')
    is_display = fields.Boolean()
    suggested_ids = fields.Many2many('approval.approval', string='Suggested Approval', copy=False, compute="_compute_suggested_ids")

    @api.model_create_multi
    def create(self, values):
        result = super(ServiceSaleOrder, self).create(values)
        for res in result:
            if res.is_approval and not res.service_sale_approval_id and res.suggested_ids and res.state == 'draft' and res.company_id.approval_type:
                if res.company_id.approval_type == 'before_tax_amount':
                    data = res.suggested_ids.filtered(lambda l: l.minimum_amount <= res.untaxed_amount)
                    if data:
                        new_approval_id = data.sorted(key=lambda l: l.minimum_amount)[0].id
                        res.service_sale_approval_id = new_approval_id
                        res.approval_level_id = new_approval_id
                    # else:
                    #     raise ValidationError(_('You need to add approvals to create this service sale order!'))
                if res.company_id.approval_type == 'total':
                    data = res.suggested_ids.filtered(lambda l: l.minimum_amount <= res.grand_total_amount)
                    if data:
                        new_approval_id = data.sorted(key=lambda l: l.minimum_amount)[0].id
                        # res.service_sale_approval_id = new_approval_id
                        res.approval_level_id = new_approval_id
                    # else:
                    #     raise ValidationError(_('You need to add approvals to create this service sale order!'))
        return result

    def write(self, values):
        approval = False
        for record in self:
            approval = record.service_sale_approval_id
        result = super(ServiceSaleOrder, self).write(values)
        for record in self:
            if not record.service_sale_approval_id and approval:
                if record.is_approval and not record.service_sale_approval_id and record.suggested_ids and record.state == 'draft' and record.company_id.approval_type:
                    if record.company_id.approval_type == 'before_tax_amount':
                        data = record.suggested_ids.filtered(lambda l: l.minimum_amount <= record.untaxed_amount)
                        if data:
                            new_approval_id = data.sorted(key=lambda l: l.minimum_amount)[0].id
                            record.service_sale_approval_id = new_approval_id
                            record.approval_level_id = new_approval_id
                        # else:
                        #     raise ValidationError(_('You need to add approvals to create this service sale order!'))
                    if record.company_id.approval_type == 'total':
                        data = record.suggested_ids.filtered(lambda l: l.minimum_amount <= record.grand_total_amount)
                        if data:
                            new_approval_id = data.sorted(key=lambda l: l.minimum_amount)[0].id
                            record.service_sale_approval_id = new_approval_id
                            record.approval_level_id = new_approval_id

                        # else:
                        #     raise ValidationError(_('You need to add approvals to create this service sale order!'))
        return result

    # @api.depends('amount_total', 'amount_untaxed')
    @api.depends('grand_total_amount', 'untaxed_amount')
    def _compute_suggested_ids(self):
        for record in self:
            record.suggested_ids = False
            if record.is_approval:
                model_approval_id = self.env['model.approval'].sudo().search([
                    ('model_id', '=', 'service.sale.order'),
                    ('active', '=', True)
                ])
                if model_approval_id and model_approval_id.mapped('approval_ids'):
                    record.suggested_ids = model_approval_id.mapped('approval_ids')

                if record.service_sale_order_line_ids and record.suggested_ids and record.state == 'draft' and record.company_id.approval_type:
                    if record.company_id.approval_type == 'before_tax_amount':
                        data = record.suggested_ids.filtered(lambda l: l.minimum_amount <= record.untaxed_amount)
                        if data:
                            new_approval_id = data.sorted(key=lambda l: l.minimum_amount, reverse=True)[0].id
                            record.service_sale_approval_id = new_approval_id
                        else:
                            record.service_sale_approval_id = False
                    elif record.company_id.approval_type == 'total':
                        data = record.suggested_ids.filtered(lambda l: l.minimum_amount <= record.grand_total_amount)
                        if data:
                            new_approval_id = data.sorted(key=lambda l: l.minimum_amount, reverse=True)[0].id
                            record.service_sale_approval_id = new_approval_id
                        else:
                            record.service_sale_approval_id = False

    @api.depends('service_sale_approved_ids')
    def _compute_all_level_approved(self):
        for record in self:
            if record.service_sale_approved_ids and all(record.service_sale_approved_ids.mapped('state')):
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
            'name': _('Service Sale Order Reject'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'service.sale.order.reject',
            'target': 'new',
            'context': {'default_order_id': self.id}
        }

    # def action_approve(self):
    #     if self.current_waiting_approval_line_id and not self.current_waiting_approval_line_id.state and not self.current_approval_state:
    #         self.current_approval_state = True
    #         self.current_waiting_approval_line_id.state = True
    #         self.current_waiting_approval_line_id.approved_date = fields.Datetime.now()
    #         self.current_waiting_approval_line_id.approved_id = self.env.user.id
    #         self.approved_user_ids = [(4, self.env.user.id)]
    #         self.action_confirm_amc_quotation()
    #     return True

    def action_approve(self):
        if self.current_waiting_approval_line_id and not self.current_waiting_approval_line_id.state and not self.current_approval_state:
            # Approval values update
            self.current_approval_state = True
            self.current_waiting_approval_line_id.state = True
            self.current_waiting_approval_line_id.approved_date = fields.Datetime.now()
            self.current_waiting_approval_line_id.approved_id = self.env.user.id
            self.approved_user_ids = [(4, self.env.user.id)]

            # Call confirm
            self.action_confirm_amc_quotation()

            # Compute allowed minimum gross profit
            conf_gross_profit = float(
                self.env['ir.config_parameter'].sudo().get_param(
                    'machine_repair_management.gross_profit', default=0.0
                )
            )
            total_gross_profit = conf_gross_profit - self.env.user.discount_limit

            # ❗ Raise warning ONLY when below threshold
            if self.env.user.discount_limit != 0.0 and self.gross_profit < total_gross_profit:
                message = (
                    "You can only assign a maximum of "
                    f"{self.env.user.discount_limit}% Discount.\n"
                    "Contact your administrator for more details."
                )
                raise ValidationError(_(message))

            # If >= threshold → approval allowed normally (no raise)
            return True

    def _prepare_approved_line(self, line):
        if line:
            return {
                'approval_level': line.level,
                'user_ids': line.user_ids.ids if line.user_ids else [],
                'group_ids': line.group_ids.ids if line.group_ids else [],
            }

    def action_confirm_amc_quotation(self):
        for current in self:
            # check if there are no lines
            if not current.service_sale_order_line_ids or len(current.service_sale_order_line_ids) == 0:
                raise ValidationError(
                    "You must add at least one Service Sale Order Line before confirming the AMC Quotation.")
            if current.service_sale_approval_id:
                current.approval_level_id = current.service_sale_approval_id

            if current.is_approval and current.service_sale_approval_id:
                if current.service_sale_approval_id and not current.service_sale_approved_ids:
                    if not current.service_sale_approval_id.approval_line_ids:
                        raise ValidationError(_('No approval level found!'))
                    approval_lines = []
                    for record in current.service_sale_approval_id.approval_line_ids:
                        approval_lines.append((0, 0, current._prepare_approved_line(record)))
                    if approval_lines:
                        current.write({
                            'service_sale_approved_ids': approval_lines,
                            'is_saleperson_in_cc': current.service_sale_approval_id.is_sale_person
                        })
                        # template = self.env.ref('bi_all_in_one_dynamic_approval.request_approval_email_template')
                        # if template:
                        #     if current.is_saleperson_in_cc:
                        #         template.email_cc = current.user_id.email if current.user_id else False
                        #     mail = template.send_mail(int(current.id))
                        #     if mail:
                        #         mail_id = self.env['mail.mail'].browse(mail)
                        #         mail_id[0].sudo().send()
                if current.service_sale_approved_ids:
                    if not all(current.service_sale_approved_ids.mapped('state')):
                        approval_level = 0
                        for approval in current.service_sale_approved_ids.filtered(lambda l: not l.state):
                            if approval_level < approval.approval_level and (not current.current_waiting_approval_line_id or current.current_waiting_approval_line_id.state) and (current.current_approval_state or approval_level == 0):
                                approval_level = approval.approval_level
                                current.user_ids = False
                                current.group_ids = False
                                current.next_approval_level = str(approval.approval_level)
                                current.user_ids = approval.user_ids.ids
                                current.group_ids = approval.group_ids.ids
                                current.state = 'waiting'
                                current.current_waiting_approval_line_id = approval.id
                                current.current_approval_state = False
                        # submit_template = self.env.ref('bi_all_in_one_dynamic_approval.submit_for_approval_email_template')
                        # if submit_template:
                        #     mail = submit_template.send_mail(int(current.id))
                        #     if current.is_saleperson_in_cc:
                        #         submit_template.email_cc = current.user_id.email if current.user_id else False
                        #     if mail:
                        #         mail_id = self.env['mail.mail'].browse(mail)
                        #         mail_id[0].sudo().send()
                    else:
                        if current.all_level_approved:
                            current.write({'state': 'approve'})
                        return True
            else:
                # No approval → directly confirm
                current.write({'state': 'approve'})
            return True

    @api.onchange('service_sale_approval_id')
    def onchange_service_sale_approval_id(self):
        if self.service_sale_approval_id:
            if self.company_id.approval_type == 'total' and self.service_sale_approval_id.minimum_amount > self.grand_total_amount:
                raise ValidationError(_('Selected Approval is not proper as per your order!'))
            if self.company_id.approval_type == 'before_tax_amount' and self.service_sale_approval_id.minimum_amount > self.untaxed_amount:
                raise ValidationError(_('Selected Approval is not proper as per your order!'))

    def _can_be_confirmed(self):
        self.ensure_one()
        return self.state in {'draft', 'sent', 'waiting', 'approve'}

    show_approval_button = fields.Boolean(string="Show Approval Button", compute='compute_approval_button')

    def action_without_approval(self):
        if not self.service_sale_order_line_ids:
            raise ValidationError(_("Please enter at least one Product in the product lines"))
        return self.write({'state': 'approve'})

    def compute_approval_button(self):
        model_approval = self.env['model.approval'].search([('model_id.model', '=', 'service.sale.order')])
        for rec in self:
            rec.show_approval_button = False
            for line in model_approval.approval_ids:
                if rec.grand_total_amount > line.minimum_amount:
                    rec.show_approval_button = True

    # contract_id = fields.Many2one(
    #     'subscription.contract',
    #     string="Contract",
    #     readonly=True,
    #     copy=False
    # )
    #
    # def action_create_contract(self):
    #     for order in self:
    #         if order.contract_id:
    #             raise ValidationError(_("A contract already exists for this order."))
    #
    #         # Create subscription.contract record
    #         contract = self.env['subscription.contract'].create({
    #             'name': order.name or _("Contract for %s") % order.partner_id.name,
    #             'amc_quotation_id': order.id,
    #             # Add other fields if needed from service.sale.order
    #         })
    #
    #         order.contract_id = contract.id
    #
    #         # Open the new contract after creation
    #         # return {
    #         #     'type': 'ir.actions.act_window',
    #         #     'name': _('Subscription Contract'),
    #         #     'view_mode': 'form',
    #         #     'res_model': 'subscription.contract',
    #         #     'res_id': contract.id,
    #         #     'target': 'current',
    #         # }
    #     return True
    #
    # def show_contract(self):
    #     contract_search = self.env['subscription.contract'].search([('amc_quotation_id', '=', self.id)], limit=1)
    #     if contract_search:
    #         return {
    #             'name': 'Contract',
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'subscription.contract',
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'res_id': contract_search.id
    #
    #         }

