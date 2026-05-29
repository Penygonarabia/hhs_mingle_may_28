# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import warnings, UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from lxml import etree
import json
import logging
from datetime import datetime, timedelta, time, date
import math


_logger = logging.getLogger(__name__)

def _get_employee(obj):
    ids = obj.env['hr.employee'].search([('user_id', '=', obj.env.uid)])
    if ids:
        return ids[0]
    else:
        raise ValidationError(_('The user is not an employee.'))
    return False

class hr_employee_loan_ps(models.Model):
    _name = 'hr.employee.loan.ps'
    _description = 'Loan'
    _inherit = ['mail.thread', 'resource.mixin']

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        # Check if the context has 'only_media'
        # if self.env.context.get('only_media'):
        #     # If context is 'only_media', filter records where 'name' is 'Media'
        #     domain += [('name', '=', 'Media')]

        if self.env.user.has_group('hr_saudi.group_sys_manager'):
            # Sys Manager can see all records, so no additional filtering on domain
            return super(hr_employee_loan_ps, self).search_fetch(domain, field_names, offset, limit, order)

        # Check for user group-based filtering logic (can be customized as needed)
        if self.env.user:
            if self.env.user.has_group('hr_saudi.group_normal_employee'):
                # For normal employees, filter records based on their own employee ID
                domain += [('employee_id.user_id', '=', self.env.user.id)]
            elif self.env.user.has_group('hr_saudi.group_dm'):
                # For DM group, filter records in 'request' state
                domain += [('state', '=', 'request')]
            elif self.env.user.has_group('hr_saudi.group_hrm'):
                # For HRM group, filter records in 'progress' state
                domain += [('state', '=', 'progress')]
            elif self.env.user.has_group('hr_saudi.group_finance_manager'):
                # For Finance Manager group, filter records in 'progress2' state
                domain += [('state', '=', 'progress2')]
            elif self.env.user.has_group('hr_saudi.group_admin_approval'):
                # For Admin Approval group, filter records in 'progress3' state
                domain += [('state', '=', 'progress3')]

        # Call the parent method to actually fetch the records
        return super(hr_employee_loan_ps, self).search_fetch(domain, field_names, offset, limit, order)

    # @api.model
    # def search(self, args, offset=0, limit=None, order=None):
    #     if self.env.user:
    #
    #         if self.env.user.has_group('hr_saudi.group_sys_manager'):
    #             print("Search in employee 1")
    #             return super(hr_employee_loan_ps, self).search(args, offset=offset, limit=limit, order=order)
    #         if self.env.user.has_group('hr_saudi.group_normal_employee'):
    #             print("Search in employee 2")
    #             args += [('employee_id.user_id', '=', self.env.user.id)]
    #             return super(hr_employee_loan_ps, self).search(args, offset=offset, limit=limit, order=order)
    #         if self.env.user.has_group('hr_saudi.group_dm'):
    #             print("Search in employee 3")
    #             args += [('state', '=', 'request')]
    #             return super(hr_employee_loan_ps, self).search(args, offset=offset, limit=limit, order=order)
    #
    #         if self.env.user.has_group('hr_saudi.group_hrm'):
    #             print("Search in employee 4")
    #             args += [('state', '=', 'progress')]
    #             return super(hr_employee_loan_ps, self).search(args, offset=offset, limit=limit, order=order)
    #         if self.env.user.has_group('hr_saudi.group_finance_manager'):
    #             print("Search in employee 5")
    #             args += [('state', '=', 'progress2')]
    #             return super(hr_employee_loan_ps, self).search(args, offset=offset, limit=limit, order=order)
    #         if self.env.user.has_group('hr_saudi.group_admin_approval'):
    #             print("Search in employee 6")
    #             args += [('state', '=', 'progress3')]
    #             return super(hr_employee_loan_ps, self).search(args, offset=offset, limit=limit, order=order)
    #
    #     return super(hr_employee_loan_ps, self).search(args, offset=offset, limit=limit, order=order)

    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     res = super(hr_employee_loan_ps, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
    #                                                            submenu=submenu)
    #     if view_type == 'form' and self.env.user.has_group('hr_saudi.group_normal_employee'):
    #         doc = etree.XML(res['arch'])
    #         fields_to_make_readonly = ['loan_month_ins', 'loan_amount', 'loan_ins_start_date']
    #
    #         for field_name in fields_to_make_readonly:
    #             for node in doc.xpath("//field[@name='%s']" % field_name):
    #                 print("node",node)
    #                 modifiers = json.loads(node.get("modifiers", "{}"))
    #                 modifiers['readonly'] = True
    #                 node.set("modifiers", json.dumps(modifiers))
    #         res['arch'] = etree.tostring(doc)
    #     return res

    # This code was commented on 29-05-2024.
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     res = super(hr_employee_loan_ps, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
    #                                                         submenu=submenu)
    #     if view_type == 'form' and self.env.user.has_group('hr_saudi.group_normal_employee'):
    #         try:
    #             doc = etree.XML(res['arch'])
    #             fields_to_make_readonly = ['loan_month_ins', 'loan_amount', 'loan_ins_start_date']
    #
    #             for field_name in fields_to_make_readonly:
    #                 for node in doc.xpath("//field[@name='%s']" % field_name):
    #                     modifiers = json.loads(node.get("modifiers", "{}"))
    #                     modifiers['readonly'] = True
    #                     node.set("modifiers", json.dumps(modifiers))
    #             res['arch'] = etree.tostring(doc)
    #         except Exception as e:
    #             _logger.error("Error while modifying field view: %s", e)
    #
    #     return res

    # This code was added on 29-05-2024.
    # def get_view(self, view_id=None, view_type='form', toolbar=False, submenu=False, **options):
    #     res = super(hr_employee_loan_ps, self).get_view(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu, **options)
    #     if view_type == 'form':
    #         try:
    #             doc = etree.XML(res['arch'])
    #             buttons_to_hide = ['action_request', 'action_progress', 'action_progress2', 'action_approve']
    #             button_to_show = 'action_progress3'
    #             approval_details = 'approval_details'
    #             payment_scheduler = 'payment_scheduler'
    #             if self.env.user.has_group('hr_saudi.group_normal_employee'):
    #                 fields_to_make_readonly = ['loan_month_ins', 'loan_amount', 'loan_ins_start_date', 'employee_id']
    #
    #                 for field_name in fields_to_make_readonly:
    #                     print("rajjjjjjjjjjjjjj")
    #                     for node in doc.xpath("//field[@name='%s']" % field_name):
    #                         modifiers = json.loads(node.get("modifiers", "{}"))
    #                         modifiers['readonly'] = True
    #                         node.set("modifiers", json.dumps(modifiers))
    #             if self.env.user.has_group('hr_saudi.group_sys_manager'):
    #                 for button_name in buttons_to_hide:
    #                     for node in doc.xpath("//button[@name='%s']" % button_name):
    #                         modifiers = json.loads(node.get("modifiers", "{}"))
    #                         modifiers['invisible'] = True
    #                         node.set("modifiers", json.dumps(modifiers))
    #                         node.set("invisible", "1")
    #
    #                 # Check if action_progress3 button has been clicked
    #                 for node in doc.xpath("//button[@name='%s']" % button_to_show):
    #                     modifiers = json.loads(node.get("modifiers", "{}"))
    #                     modifiers['invisible'] = [('is_progress3_clicked', '=', True)]
    #                     node.set("modifiers", json.dumps(modifiers))
    #                     node.set("invisible", "1")
    #
    #                 for node in doc.xpath("//page[@name='%s']" % approval_details):
    #                     modifiers = json.loads(node.get("modifiers", "{}"))
    #                     modifiers['invisible'] = False
    #                     node.set("modifiers", json.dumps(modifiers))
    #                     node.set("invisible", "0")
    #
    #                 for node in doc.xpath("//page[@name='%s']" % payment_scheduler):
    #                     modifiers = json.loads(node.get("modifiers", "{}"))
    #                     modifiers['invisible'] = False
    #                     node.set("modifiers", json.dumps(modifiers))
    #                     node.set("invisible", "0")
    #             # res['arch'] = etree.tostring(doc)
    #             res['arch'] = etree.tostring(doc, encoding='unicode')
    #
    #         except Exception as e:
    #             _logger.error("Error while modifying field view: %s", e)
    #
    #     return res

    def get_view(self, view_id=None, view_type='form', toolbar=False, submenu=False, **options):
        res = super(hr_employee_loan_ps, self).get_view(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                     submenu=submenu, **options)

        if view_type == 'form':
            try:
                doc = etree.XML(res['arch'])

                # Define elements to hide, show, or make readonly
                buttons_to_hide = ['action_request', 'action_progress', 'action_progress2', 'action_approve']
                button_to_show = 'action_progress3'
                approval_details = 'approval_details'
                payment_scheduler = 'payment_scheduler'

                # Custom behavior for employees in group 'hr_saudi.group_normal_employee'
                if self.env.user.has_group('hr_saudi.group_normal_employee'):
                    fields_to_make_readonly = ['loan_month_ins', 'loan_amount', 'loan_ins_start_date', 'employee_id']
                    for field_name in fields_to_make_readonly:
                        for node in doc.xpath(f"//field[@name='{field_name}']"):
                            modifiers = json.loads(node.get("modifiers", "{}"))
                            modifiers['readonly'] = True
                            node.set("modifiers", json.dumps(modifiers))
                            node.set("readonly", "1")

                # Custom behavior for users in group 'hr_saudi.group_sys_manager'
                if self.env.user.has_group('hr_saudi.group_sys_manager'):
                    # Hide specified buttons
                    for button_name in buttons_to_hide:
                        for node in doc.xpath(f"//button[@name='{button_name}']"):
                            # print(f"Hiding button '{button_name}'")
                            modifiers = json.loads(node.get("modifiers", "{}"))
                            modifiers['invisible'] = True
                            node.set("modifiers", json.dumps(modifiers))
                            node.set("invisible", "1")

                    # # Show button 'action_progress3' only if 'is_progress3_clicked' is not True
                    for node in doc.xpath(f"//button[@name='{button_to_show}']"):
                        # print(f"Configuring visibility for button '{button_to_show}' based on 'is_progress3_clicked'")
                        modifiers = json.loads(node.get("modifiers", "{}"))
                        modifiers['invisible'] = [('is_progress3_clicked', '=', True)]
                        node.set("modifiers", json.dumps(modifiers))
                        # node.set("invisible", "0")

                    # Check if action_progress3 button has been clicked
                    # for node in doc.xpath("//button[@name='%s']" % button_to_show):
                    #     modifiers = json.loads(node.get("modifiers", "{}"))
                    #     modifiers['invisible'] = [('is_progress3_clicked', '=', True)]
                    #     node.set("modifiers", json.dumps(modifiers))
                    #     node.set("invisible", "1")

                    # Make pages 'approval_details' and 'payment_scheduler' visible
                    for page_name in [approval_details, payment_scheduler]:
                        for node in doc.xpath(f"//page[@name='{page_name}']"):
                            # print(f"Making page '{page_name}' visible.")
                            modifiers = json.loads(node.get("modifiers", "{}"))
                            modifiers['invisible'] = False
                            node.set("modifiers", json.dumps(modifiers))
                            node.set("invisible", "0")

                # Convert XML tree back to string for Odoo to render
                res['arch'] = etree.tostring(doc, encoding='unicode')
                # print("Finished modifying the form view.")

            except Exception as e:
                print(f"Error while modifying field view: {e}")
                _logger.error("Error while modifying field view: %s", e)

        return res

    def action_response_mail(self):
        self.env.ref('hr_loan_advance.mail_template_loan_request').send_mail(self.id, force_send=True)
        return {'effect': {'fadeout': 'slow', 'message': 'Your email is send successfully', 'type': 'rainbow_man'}}

    def _get_currency(self):
        user = self.env['res.users'].browse([self.env.uid])[0]
        return user.company_id.currency_id.id

    def _old_loan_remaining(self):
        loan_obj = self.env['hr.employee.loan.ps']
        loan_line_obj = self.env['hr.employee.loan.line.ps']
        amount = 0
        if self.employee_id:
            loan_ids = loan_obj.search([('employee_id', '=', self.employee_id.id), ('state', '=', 'approve'), ('id', '!=', self.id if self.id else 0)])
            for loan in loan_ids:
                loan_line_ids = loan_line_obj.search(
                    [('hr_employee_loan_ps', '=', loan.id), ('state', '=', 'notdeducted')])
                for loan_line in loan_line_ids: amount += loan_line.amount
        self.old_loan_remaining = amount

    def _warning(self):
        self.warning = ''
        amount_to_ins, ins_per_month, remaining_value, loan_month_ins, y, installment_value = self.compute_installment_value(
            False)
        contract_ids = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)], limit=1,
                                                      order='date_start desc')
        if self.contract_id:
            if ins_per_month >= self.contract_id.wage: self.warning = 'Warning! Current Installment is greater or equal to employee contract wage.'

        else:
            self.warning = 'Warning! Please choose contract.'
        if not contract_ids: self.warning = 'Warning! There is no contract for this employee.'

    ##newly added list view calculation dated on april 16 2024
    def _get_ins_amount(self):
        for rec in self:
            total_amount = 0
            paid_amount = 0
            total_installment = 0
            paid_installment = 0
            for line in rec.hr_employee_loan_line_ps:
                if line.state == 'deducted' and line.confirm:
                    paid_amount += line.amount
                    paid_installment += 1
                if line.state == 'notdeducted':
                    if line.confirm:   
                        total_amount += line.amount
                        total_installment += 1
            rec.total_amount = total_amount
            rec.paid_amount = paid_amount
            rec.balance_amount = total_amount
            rec.paid_installment = paid_installment
            rec.unpaid_installment = total_installment

    # def _get_ins_amount(self):
    #     total_amount = paid_amount = total_installment = paid_installment = 0
    #     for line in self.hr_employee_loan_line_ps:
    #         if line.state == 'deducted':
    #             paid_amount += line.amount
    #             paid_installment += 1
    #         total_amount += line.amount
    #         total_installment += 1
    #     self.total_amount = total_amount
    #     self.paid_amount = paid_amount
    #     self.balance_amount = total_amount - paid_amount
    #     self.paid_installment = paid_installment
    #     self.unpaid_installment = total_installment - paid_installment

    # @api.depends('write_date', 'employee_id')
    # def _get_current_user(self):
    #     for case in self:
    #         current_user = False
    #         state = case.state
    #         is_direct_manager = False
    #         is_coach = False
    #         is_show_dm_approve = False
    #         is_show_hrm_approve = False
    #         is_show_fm_approve = False
    #         is_show_admin_approve = False
    #         employee = case.employee_id.sudo()
    #         parent = employee.parent_id.sudo()
    #         is_direct_manager = False
    #         group_hr_manager = case.env.user.has_group('hr.group_hr_manager')
    #         group_account_manager = case.env.user.has_group('account.group_account_manager')
    #         if (employee and parent and parent.user_id) and parent.user_id.id == case.env.uid:
    #             is_direct_manager = True
    #             if state == 'request':
    #                 is_show_dm_approve = True
    #         if (employee and employee.coach_id and employee.coach_id.user_id) \
    #                 and employee.coach_id.user_id.id == case.env.uid:
    #             is_coach = True
    #             if state == 'request':
    #                 is_show_dm_approve = True
    #         if state == 'request' and (is_coach or is_direct_manager):
    #             is_show_dm_approve = True
    #         # if state == 'request':
    #         #     if group_hr_manager:
    #         #         is_show_hrm_approve = True
    #         elif state == 'progress':
    #             if group_hr_manager:
    #                 is_show_hrm_approve = True
    #         elif state == 'progress2':
    #             if group_account_manager:
    #                 is_show_fm_approve = True
    #         elif state == 'progress3':
    #             if case.env.user.has_group('hr_loan_advance.group_admin_fd_user'):
    #                 is_show_admin_approve = True
    #         if current_user and ((current_user.guarantor_id) and (current_user.guarantor_id.user_id)) \
    #                 and current_user.guarantor_id.user_id.id == case.env.uid:
    #             current_user = True
    #         case.current_user = current_user
    #         case.is_direct_manager = is_direct_manager
    #         case.is_coach = is_coach
    #         case.is_show_dm_approve = is_show_dm_approve
    #         case.is_show_hrm_approve = is_show_hrm_approve
    #         case.is_show_fm_approve = is_show_fm_approve
    #         case.is_show_fm_approve = is_show_fm_approve
    #         case.is_show_admin_approve = is_show_admin_approve

    name = fields.Char(string='Loan Reference', default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, default=_get_employee)
    contract_id = fields.Many2one('hr.contract', string='Contract')
    type_id = fields.Many2one('hr.employee.loan.type.ps', string='Loan Type', required=True)
    request_date = fields.Date(string='Request Date')
    move_id = fields.Many2one('account.move', string='Journal Entry')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env['res.company']._company_default_get(
                                     'hr.employee.loan.ps'))
    loan_amount_required = fields.Monetary(string='Loan Amount Required', required=True,
                                           digits='Account', copy=False)
    loan_amount = fields.Float(string='Loan Amount Approved')
    loan_month_ins = fields.Integer(string='Number of Installments')
    loan_ins_start_date = fields.Date(string='Installment Start Date')
    loan_open = fields.Boolean(string='Loan Open')
    hr_employee_loan_line_ps = fields.One2many('hr.employee.loan.line.ps', 'hr_employee_loan_ps', string='Loan Line')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=_get_currency)
    employee_comment = fields.Text(string='User Comments')
    dm_comment = fields.Text(string='Department Manager')
    hr_comment = fields.Text(string='HR manager')
    account_comment = fields.Text(string='Finance Manager')
    warning = fields.Text(string='Warning', compute='_warning')
    old_loan_remaining = fields.Float(string='Old Loan Remaining Amount', compute='_old_loan_remaining')
    total_amount = fields.Float(string='Total Amount', compute='_get_ins_amount')
    paid_amount = fields.Float(string='Paid Amount', compute='_get_ins_amount')
    balance_amount = fields.Float(string='Balance Amount', compute='_get_ins_amount')
    paid_installment = fields.Integer(string='Paid Installment', compute='_get_ins_amount')
    unpaid_installment = fields.Integer(string='Unpaid Installment', compute='_get_ins_amount')
    # current_user = fields.Boolean(string='Current User')
    allow_another_loan = fields.Boolean(string='Allow Another Loan')
    guarantor_id = fields.Many2one('hr.employee', string='Guarantor')
    guarantor_user_id = fields.Many2one('res.users', string='Guarantor User', readonly=True)
    guarantor_date = fields.Datetime(string='Confirmed Date', readonly=True)
    direct_manager_id = fields.Many2one('res.users', string='Direct Manager', readonly=True)
    direct_manager_date = fields.Datetime(string='Confirmed Date', readonly=True)
    hr_manager_id = fields.Many2one('res.users', string='HR Manager', readonly=True)
    hr_manager_date = fields.Datetime(string='Confirmed Date', readonly=True)
    account_manager_id = fields.Many2one('res.users', string='Account Manager', readonly=True)
    account_manager_date = fields.Datetime(string='Confirmed Date', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('request', 'Waiting for Direct Manager approval'),
        ('progress', 'Waiting for HR Manager approval'),
        ('progress2', 'Waiting for Finance Manager approval'),
        ('progress3', 'Waiting for Admin & Financial Director approval'),
        ('approve', 'Approved'),
        ('refused', 'Refused'),
    ], 'Status', readonly=True, tracking=True, default="draft",
        help='Status : User in 1.Draft(default) state Requesting to 2.DM Approval and processed by 3.HRM and Finalized by 4.FM')
    is_direct_manager = fields.Boolean(string='Is Direct Manager', compute='_get_current_user')
    is_coach = fields.Boolean(string='Is Coach', default=False, compute='_get_current_user')
    is_show_dm_approve = fields.Boolean(string='Is Show DM Button', compute='_get_current_user')
    is_show_hrm_approve = fields.Boolean(string='Is Show HR-Manager Approval Button', compute='_get_current_user')
    is_show_fm_approve = fields.Boolean(string='Is Show FM Approval Button', compute='_get_current_user')
    is_show_admin_approve = fields.Boolean(string='Is Show Admin & Financial Director Approval Button',
                                           compute='_get_current_user')

    # ==============================================================================================
    d_manager = fields.Many2one('res.users', string="Direct Manager", readonly=True)
    hr_manage_id = fields.Many2one('res.users', string='HR Manager', readonly=True)
    account_manage_id = fields.Many2one('res.users', string='Accounting Manager', readonly=True)
    admin_manager_id = fields.Many2one('res.users', string='Admin & Finance Manager', readonly=True)
    # ==============================================================================================
    #       Responsible Notes
    d_manager_note = fields.Text(string="Direct Manager Note", )
    hr_manage_note = fields.Text(string="HR Manager Note", )
    account_manage_note = fields.Text(string="Accounting Manager Note", )
    admin_manager_note = fields.Text(string="Admin & Finance Manager Note", )

    # Add a Boolean field to indicate if the action_progress3 button has been clicked
    is_progress3_clicked = fields.Boolean(string="Action Progress3 Clicked", default=False)
    
    employee_number = fields.Char(string='Employee No', store = True)

    amount_based_loan = fields.Boolean(string="Amount Based(Y/N)", default=False)

    monthly_based_amount = fields.Float(string="Monthly Based Amount")

    amount_enterable = fields.Boolean(string="Amount entered or not", default=False,
                                      compute="_compute_amount_enterable")

    @api.depends('loan_amount')
    def _compute_amount_enterable(self):
        for rec in self:
            rec.amount_enterable = False
            if rec.amount_based_loan:
                if rec.monthly_based_amount > 0:
                    rec.amount_enterable = True
                    if rec.amount_enterable and rec.amount_based_loan:
                        rec.loan_month_ins = math.ceil(rec.loan_amount / rec.monthly_based_amount)
                    else:
                        if not rec.amount_based_loan:
                            rec.amount_enterable = False
                            rec.monthly_based_amount = False


    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for rec in self:
            rec.employee_number = False
            if rec.employee_id:
                rec.employee_number = rec.employee_id.employee_no
    
    @api.constrains('guarantor_id')
    def _guarantor_constrains(self):
        if (self.guarantor_id):
            guarantor_ids = self.env['hr.employee.loan.ps'].search(
                [('employee_id', '=', self.guarantor_id.id), ('balance_amount', '>', 0)])
            if guarantor_ids: raise ValidationError(_('The Guarantor has already unpaid loan, So he cannot be a Gaurantor'))

    @api.onchange('employee_id')
    def _onchange_employee(self):
        self.contract_id = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)], limit=1,
                                                          order='date_start desc').id

    @api.model
    def create(self, values):
        if values.get('name', 'New') == 'New':
            values['name'] = self.env['ir.sequence'].next_by_code('hr.employee.loan.ps') or 'New'
        result = super(hr_employee_loan_ps, self).create(values)
        return result

    ## Important code validation perpose comd on 11/09/2024
    # @api.constrains('loan_ins_start_date')
    # def _check_loan_ins_start_date(self):
    #     for rec in self:
    #         current_date = fields.Date.context_today(rec)
    #         if rec.loan_ins_start_date:
    #
    #             # Get the start of the current and previous months
    #             current_month_start = current_date.replace(day=1)
    #             previous_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    #
    #             # Find draft payslip from the previous month
    #             previous_month_payslip = self.env['hr.payslip'].search([
    #                 ('employee_id', '=', rec.employee_id.id),
    #                 ('date_from', '>=', previous_month_start),
    #                 ('date_to', '<', current_month_start),
    #                 ('state', '=', 'draft')
    #             ], limit=1)
    #
    #             # Conditions based on the payslip state
    #             if previous_month_payslip:
    #                 # Allow only current or previous month dates if a draft payslip exists for previous month
    #                 if rec.loan_ins_start_date < previous_month_start:
    #                     raise ValidationError(
    #                         _('Loan requests can only be created for the current or previous month. '
    #                           'Please select dates within the current or previous months.')
    #                     )
    #             else:
    #                 # Allow only current or future month dates if no draft payslip exists for the previous month
    #                 if rec.loan_ins_start_date < current_month_start:
    #                     raise ValidationError(
    #                         _('Loan requests can only be created for the current month or future months. '
    #                           'Please select dates within the current or future months.')
    #                     )


    # @api.constrains('loan_ins_start_date')
    # def _check_loan_ins_start_date(self):
    #     for record in self:
    #         current_date = fields.Date.today()
    #         if record.loan_ins_start_date:
    #             if record.loan_ins_start_date < current_date:
    #                 raise ValidationError("Installment start date must be present date or future date. Please change the date")
    #
    # def unlink(self):0.00
    #     if self.state not in ('draft', False):
    #         raise Warning(_('You cannot delete record which is not in Draft.'))
    #     return models.Model.unlink(self)

    def action_request(self):
        if self.loan_amount_required <= 0: raise ValidationError(_('Loan Amount Required must be greater than Zero!'))
        config = self.env['hr.config.settings']._get_limit_of_loan_advance()
        if self.type_id.is_annual:
            year_bef = datetime.now() - relativedelta(years=1)

            if self.employee_id.aj_date and self.employee_id.aj_date > year_bef.date():
                raise ValidationError(_('You are not eligible to apply for Annual Loan!'))
            if not self.employee_id.aj_date:
                raise ValidationError(_('You are not eligible to apply for Annual Loan!'))
        if config:
            if config.limit_of_loan == 'amount':
                if self.loan_amount_required > config.loan_amount:
                    raise ValidationError(_('Over limit loan amount required!'))
            elif config.limit_of_loan == 'basic':
                if not self.contract_id: raise ValidationError(_('There is no contract.Please contact administrator!'))
                amount = self.contract_id.wage * config.loan_months
                if self.loan_amount_required > amount: raise ValidationError(_('Over limit loan amount required!'))
        self.write({'state': 'request', 'loan_amount': self.loan_amount_required, 'request_date': fields.date.today()})
        self.action_response_mail()
        # Send Notification To Direct Manager
        # self.sending_notification(self._description, self._name, self.id, self.name, 'direct_manager')

    # def action_guarantor_approve(self):
    #     return self.write(
    #         {'state': 'guarantor_approve', 'guarantor_user_id': self.env.uid
    #             , 'guarantor_date': fields.date.today()})

    # # DM, HRM, FM

    def action_progress(self):
        # Here Update the status and assign and direct manager approval to current user
        self.write({'state': 'progress'})


    def action_progress2(self):
        self.write({'state': 'progress2', 'hr_manager_id': self.env.uid,
                    'hr_manage_id': self.env.uid})
        # self.write({'state': 'progress2', 'hr_manager_id': self.env.uid
        #                , 'hr_manager_date': fields.date.today(), 'hr_manage_id': self.env.uid})


    def action_approve(self):
        if not self.allow_another_loan and self.old_loan_remaining > 0: raise ValidationError(
            _('The Employee has already loan with balance.Please allow another loan or refuse!'))
        self.compute_installment_board()
        # self.write({'state': 'progress3', 'account_manager_id': self.env.uid
        #                , 'account_manager_date': fields.date.today(), 'account_manage_id': self.env.uid})
        #

        self.write({'state': 'progress3', 'account_manager_id': self.env.uid
                       , 'account_manage_id': self.env.uid})


    def action_progress3(self):
        if self.env.user.has_group('hr_saudi.group_sys_manager'):
            if self.loan_amount_required <= 0: raise ValidationError(_('Loan Amount Required must be greater than Zero!'))
            config = self.env['hr.config.settings']._get_limit_of_loan_advance()
            if self.type_id.is_annual:
                year_bef = datetime.now() - relativedelta(years=1)

                if self.employee_id.aj_date and self.employee_id.aj_date > year_bef.date():
                    raise ValidationError(_('You are not eligible to apply for Annual Loan!'))
                if not self.employee_id.aj_date:
                    raise ValidationError(_('You are not eligible to apply for Annual Loan!'))
            if config:
                if config.limit_of_loan == 'amount':
                    if self.loan_amount_required > config.loan_amount:
                        raise ValidationError(_('Over limit loan amount required!'))
                elif config.limit_of_loan == 'basic':
                    if not self.contract_id: raise ValidationError(_('There is no contract.Please contact administrator!'))
                    amount = self.contract_id.wage * config.loan_months
                    if self.loan_amount_required > amount: raise ValidationError(_('Over limit loan amount required!'))
            if not self.allow_another_loan and self.old_loan_remaining > 0: raise ValidationError(
                _('The Employee has already loan with balance.Please allow another loan or refuse!'))
            if self.loan_amount <= 0:
                raise ValidationError(_('Loan Amount must be greater than Zero!'))

            self.compute_installment_board()
        self.is_progress3_clicked = True
        move_id = self.sudo().generate_entry()
        self.write({'state': 'approve', 'move_id': move_id, 'account_manager_id': self.env.uid,
                    'admin_manager_id': self.env.uid})

        # self.write({'state': 'approve', 'move_id': move_id, 'account_manager_id': self.env.uid,
        #             'admin_manager_id': self.env.uid, 'account_manager_date': fields.date.today(), 'request_date': fields.date.today()})
        self.action_response_mail()


    def action_refuse(self):
        self.write({'state': 'refused'})

    def check_detucted(self):
        result = False
        for record in self.hr_employee_loan_line_ps:
            if record.state == 'deducted': result = True
        return result

    def update_detucted(self, update):
        installment_value = tot_current_value = rem_value = t = 0
        for installment_lin_deducted in self.hr_employee_loan_line_ps:
            if installment_lin_deducted.state == 'deducted':
                tot_current_value = tot_current_value + installment_lin_deducted.amount
                rem_value = self.loan_amount - tot_current_value
                t += 1
                name_temp = str(self.name) + ' - ' + str(t) + '/' + str(self.loan_month_ins)
                if update: self.env.cr.execute(
                    "update hr_employee_loan_line_ps set installment_value = %s,remaining_value = %s,name = '%s' where id = %s" % (
                        installment_value, rem_value, name_temp, installment_lin_deducted.id))
                installment_value = installment_value + installment_lin_deducted.amount
        return tot_current_value, t, installment_value

    def compute_installment_value(self, update):
        amount_to_ins = ins_per_month = installment_value = remaining_value = loan_month_ins = t = 0
        if self.check_detucted():
            tot_current_value, t, installment_value = self.update_detucted(update)
            amount_to_ins = self.loan_amount - tot_current_value
            if (self.loan_month_ins - t) > 0: ins_per_month = amount_to_ins / (self.loan_month_ins - t)
            remaining_value = amount_to_ins - ins_per_month
            loan_month_ins = (self.loan_month_ins - t)
        else:
            if not self.amount_enterable:
                amount_to_ins = self.loan_amount
                if self.loan_month_ins > 0: ins_per_month = amount_to_ins / self.loan_month_ins
                remaining_value = amount_to_ins - ins_per_month
                loan_month_ins = self.loan_month_ins
            # if self.amount_enterable:
            #     amount_to_ins = self.loan_amount
            #     if self.loan_month_ins > 0: ins_per_month = amount_to_ins / self.loan_month_ins
            #     remaining_value = amount_to_ins - ins_per_month
            #     loan_month_ins = self.loan_month_ins

            if self.amount_enterable:
                amount_to_ins = self.loan_amount  # Total loan amount, e.g., 1150
                ins_per_month = self.monthly_based_amount  # Monthly installment, e.g., 100

                # Calculate the initial number of installments
                loan_month_ins = amount_to_ins // ins_per_month  # Integer division for initial months, e.g., 1150 // 100 = 11
                remaining_value = amount_to_ins % ins_per_month  # Remaining value, e.g., 1150 % 100 = 50
                loan_month_ins = int(loan_month_ins)  # e.g., 11 + 1 = 12
                # Check if there's a remaining value that requires an extra installment
                if remaining_value > 0:
                    loan_month_ins += 1  # Add an extra installment

        return amount_to_ins, ins_per_month, remaining_value, loan_month_ins, t, installment_value

    # def compute_installment_board(self):
    #     if self.loan_amount_required <= 0:
    #         raise ValidationError(_('Loan Amount must be greater than Zero!'))
    #     if self.loan_month_ins <= 0:
    #         raise ValidationError(_('Number of Installments must be greater than Zero!'))
    #     if not self.loan_ins_start_date:
    #         raise ValidationError(_('Choose Installment Start Date'))
    #
    #     loan_ins_start_date = self.loan_ins_start_date
    #     skipped_installments = []  # To track skipped installment details
    #
    #     # Unlink 'notdeducted' lines and store their details in skipped_installments
    #     for record in self.hr_employee_loan_line_ps:
    #         if record.state == 'notdeducted':
    #             skipped_installments.append({
    #                 'amount': record.amount,
    #                 'installment_date': record.installment_date,
    #             })
    #             record.unlink()
    #         else:
    #             loan_ins_start_date = (record.installment_date + relativedelta(months=+1))
    #
    #     # Calculate the installments
    #     amount_to_ins, ins_per_month, remaining_value, loan_month_ins, t, installment_value = self.compute_installment_value(True)
    #
    #     # Add regular installments
    #     for x in range(0, loan_month_ins):
    #         installment_date = (loan_ins_start_date + relativedelta(months=+x))
    #         i = x + 1 + t
    #         vals = {
    #             'amount': ins_per_month,
    #             'hr_employee_loan_ps': self.id,
    #             'sequence': i,
    #             'name': str(self.name) + ' - ' + str(i) + '/' + str(self.loan_month_ins),
    #             'remaining_value': remaining_value,
    #             'installment_value': installment_value,
    #             'installment_date': installment_date.strftime('%Y-%m-%d'),
    #             'confirm': True,
    #         }
    #         self.env['hr.employee.loan.line.ps'].create(vals)
    #         installment_value += ins_per_month
    #         remaining_value -= ins_per_month
    #
    #     # Add skipped installments as extra loan lines at the end
    #     if skipped_installments:
    #         for skipped_installment in skipped_installments:
    #             last_installment_date = (loan_ins_start_date + relativedelta(months=+loan_month_ins))
    #             vals = {
    #                 'amount': skipped_installment['amount'],
    #                 'hr_employee_loan_ps': self.id,
    #                 'sequence': loan_month_ins + 1 + t,  # Adjust sequence for skipped installments
    #                 'name': str(self.name) + ' - Extra/' + str(loan_month_ins + 1),
    #                 'remaining_value': remaining_value,
    #                 'installment_value': installment_value,
    #                 'installment_date': last_installment_date.strftime('%Y-%m-%d'),
    #                 'confirm': True,
    #             }
    #             self.env['hr.employee.loan.line.ps'].create(vals)
    #             loan_month_ins += 1  # Increase the loan month for each extra line
    #             installment_value += skipped_installment['amount']
    #             remaining_value -= skipped_installment['amount']
    #
    #     return True

    
    # def compute_installment_board(self):
    #     if self.loan_amount_required <= 0:
    #         raise ValidationError(_('Loan Amount must be greater than Zero!'))
    #     if self.loan_month_ins <= 0:
    #         raise ValidationError(_('Number of Installments must be greater than Zero!'))
    #     if not self.loan_ins_start_date: raise ValidationError(_('Choose Installment Start Date'))
    #     loan_ins_start_date = self.loan_ins_start_date
    #     for record in self.hr_employee_loan_line_ps:
    #         if record.state == 'notdeducted':
    #             record.unlink()
    #         else:
    #             loan_ins_start_date = (record.installment_date + relativedelta(months=+1))
    #     amount_to_ins, ins_per_month, remaining_value, loan_month_ins, t, installment_value = self.compute_installment_value(
    #         True)
    #     for x in range(0, loan_month_ins):
    #         installment_date = (loan_ins_start_date + relativedelta(months=+x))
    #         i = x + 1 + t
    #         vals = {
    #             'amount': ins_per_month,
    #             'hr_employee_loan_ps': self.id,
    #             'sequence': i,
    #             'name': str(self.name) + ' - ' + str(i) + '/' + str(self.loan_month_ins),
    #             'remaining_value': remaining_value,
    #             'installment_value': installment_value,
    #             'installment_date': installment_date.strftime('%Y-%m-%d'),
    #             'confirm': True,
    #         }
    #         self.env['hr.employee.loan.line.ps'].create(vals)
    #         installment_value = installment_value + ins_per_month
    #         remaining_value = remaining_value - ins_per_month
    #     return True

    def compute_installment_board(self):
        if self.loan_amount_required <= 0:
            raise ValidationError(_('Loan Amount must be greater than Zero!'))
        if self.loan_month_ins <= 0:
            raise ValidationError(_('Number of Installments must be greater than Zero!'))
        if not self.loan_ins_start_date: raise ValidationError(_('Choose Installment Start Date'))
        loan_ins_start_date = self.loan_ins_start_date
        for record in self.hr_employee_loan_line_ps:
            if record.state == 'notdeducted':
                record.unlink()
            else:
                loan_ins_start_date = (record.installment_date + relativedelta(months=+1))
        amount_to_ins, ins_per_month, remaining_value, loan_month_ins, t, installment_value = self.compute_installment_value(
            True)
        total_loan_amount = False
        for x in range(0, loan_month_ins):
            installment_date = (loan_ins_start_date + relativedelta(months=+x))
            i = x + 1 + t
            total_loan_amount += ins_per_month
            vals = {
                # 'amount': ins_per_month,
                'hr_employee_loan_ps': self.id,
                'sequence': i,
                'name': str(self.name) + ' - ' + str(i) + '/' + str(self.loan_month_ins),
                'remaining_value': remaining_value,
                'installment_value': installment_value,
                'installment_date': installment_date.strftime('%Y-%m-%d'),
                'confirm': True,
            }
            '''currently working'''

            transaction = self.env['hr.employee.loan.line.ps']

            if total_loan_amount <= amount_to_ins:
                vals.update({'amount': ins_per_month})
            else:
                vals.update({'amount': amount_to_ins - installment_value})

            transaction = transaction.create(vals)
            installment_value = installment_value + ins_per_month
            remaining_value = remaining_value - ins_per_month

        return True

    def generate_entry(self):
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        company_currency = self.company_id.currency_id.id
        diff_currency_p = self.currency_id.id != company_currency
        if not self.employee_id.address_id: raise ValidationError(_('Please set the home address for employee'))
        ref = self.employee_id.name + '/' + self.name
        # config = self.env['hr.accounting.config']._get_hr_accounting_config()
        if not self.company_id.loan_journal_id:
            raise ValidationError(_('Journal is not configured. Select Journal in Company Configuration'))
        journal_id = self.company_id.loan_journal_id
        if not journal_id.default_account_id or not journal_id.default_account_id:
            raise ValidationError(
                _('Missing credit or debit account for journal. Please set credit and debit account for journal.'))
        # move_id = move_obj.create(nazar_obj.account_move_get(self, journal_id, date=fields.datetime.today(), ref=ref,
        #                                                      company_id=self.company_id.id))

        vals = {
            'journal_id': journal_id.id,
            'date': fields.datetime.today(),
            # 'period_id': period_obj.find(date)[0],
            'ref': '',
            'company_id': self.company_id.id,
        }

        line1 = [(0, 0, {
            # 'move_id': move_id.id,
            'journal_id': journal_id.id,
            'partner_id': self.employee_id.address_id.id,
            'credit': 0,
            'debit': self.loan_amount,
            # 'centralisation': 'normal',
            'company_id': self.company_id.id,
            # 'state': 'valid',
            'blocked': False,
            'account_id': journal_id.default_account_id.id,
            # 'period_id': move_id.period_id.id,
            'name': 'Loan',
            'amount_currency': diff_currency_p and self.currency_id.id or False,
            'quantity': 1,

        })]
        line1.append((0, 0, {
            # 'move_id': move_id.id,
            'journal_id': journal_id.id,
            'partner_id': self.employee_id.address_id.id,
            'credit': self.loan_amount,
            'debit': 0,
            # 'centralisation': 'normal',
            'company_id': self.company_id.id,
            # 'state': 'valid',
            'blocked': False,
            'account_id': self.employee_id.address_id.property_account_payable_id.id,
            # 'period_id': move_id.period_id.id,
            'name': '/',
            'amount_currency': diff_currency_p and self.currency_id.id or False,
            'quantity': 1,

        }))

        vals.update({'line_ids': line1})

        move_id = move_obj.create(vals)
        return move_id.id

    def action_draft(self):
        return self.write({'state': 'draft'})

    # This code was added on 29-05-2024.
    def unlink(self):
        for rec in self:
            if rec.state == 'approve':
                raise ValidationError(_("You cannot delete approved records."))
        return super(hr_employee_loan_ps, self).unlink()

    # Sending Notification with to users has "group_name"
    # def sending_notification(self, description, model, res_id, res_name, group_name):
    #     mail_channel = self.env['mail.channel']
    #     mail_channel.sudo().send_message_without_refresh(description, model, res_id, res_name, group_name)