# -*- coding: utf-8 -*-
import time
from datetime import datetime
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from lxml import etree
import json
import logging

_logger = logging.getLogger(__name__)

def _get_employee(obj):
    if obj.env.user.has_group('hr_saudi.group_sys_manager'):
        return True
    else:
        ids = obj.env['hr.employee'].search([('user_id', '=', obj.env.uid)])
        if ids:
            return ids[0]
        else:
            raise ValidationError(_('The user is not an employee.'))

class SalaryAllowanceDetection(models.Model):
    _name = "salary.allowance.detection"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, help="Employee", default=_get_employee)
    date = fields.Date(string='Date', required=True, default=lambda self: fields.Date.today(), help="Submit date")
    reason = fields.Text(string='Reason', help="Reason")
    code = fields.Char(string='Code')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    units = fields.Selection([('days', 'Days'), ('hours', 'Hours'), ('amount', 'Amount')], string='Type', store=True, default='amount')
    days = fields.Float(string='Days', required=True)
    hours = fields.Float(string='Hours')
    amount = fields.Float(string='Amount', store=True,compute='compute_hr_allowance_days_hours')
    fixed_amount = fields.Float(string="Fixed Amount")
    department = fields.Many2one('hr.department', string='Department')
    basic = fields.Float(string='Basic')
    transaction_type_id = fields.Many2one('hr.transaction.rule', string='Transaction Type', required=True,
                                          domain="[('rule_type', 'in', ['transaction_allowance','transaction_detection'])]")
    hr_transaction_id = fields.Many2one('hr.transaction.entry', 'Transaction Entry')


    type = fields.Selection([('transaction_allowance', 'Transaction Allowance'),
                              ('transaction_detection', 'Transaction Deduction')
                             ], string='Type')
    reference = fields.Char(string='Reference')
    # state = fields.Selection([('draft', 'Draft'),
    #                           ('submit', 'Submitted'),
    #                           ('waiting_approval', 'Waiting Approval'),
    #                           ('approve', 'Approved'),
    #                           ('cancel', 'Cancelled'),
    #                           ('reject', 'Rejected')], string='Status', default='draft', track_visibility='onchange')
    employee_contract_id = fields.Many2one('hr.contract', string='Contract')
    calculate_based_on_allowance = fields.Selection(string="Calculate Based On",
                                                    selection=[('wage', 'Wage'),
                                                               ('hra', 'HRA'),
                                                               ('wage_trv', 'Basic + Transport'),
                                                               ('wage_tr_fd','Basic + Transport + Food'),
                                                               ('hra_trv', 'HRA + Transport'),
                                                               ('hr_tr_sch', 'HRA + Transport + School'),
                                                               ('hr_tr_fd', 'HRA + Transport + Food'),
                                                               ('hr_tr_fl', 'HRA + Transport + Fuel'),
                                                               ('hr_tr_tk', 'HRA + Transport + Ticket'),
                                                               ('hr_tr_fx', 'HRA + Transport + Fixed'),
                                                               ('hr_tr_mb', 'HRA + Transport + Mobile'),
                                                               ('hr_tr_oth', 'HRA + Transport + Other'),
                                                               ('hr_tr_wk', 'HRA + Transport + Work'), ('all', 'All')], default='hra', required=True)

    state = fields.Selection([
        ('draft', 'Pending'),
        ('request', 'Waiting for Direct Manager approval'),
        ('progress', 'Waiting for HR Manager approval'),
        ('progress2', 'Waiting for Finance Manager approval'),
        ('progress3', 'Waiting for Admin & Financial Director approval'),
        ('approve', 'Approved'),
        ('refused', 'Refused'),
        ('cancel','Cancel'),
    ], 'Status', readonly=True, tracking=True, default="draft",
        help='Status : User in 1.Draft(default) state Requesting to 2.DM Approval and processed by 3.HRM and Finalized by 4.FM')

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

    slip_id = fields.Many2one('hr.payslip', string='Payslip', readonly=True)
    slip_bool = fields.Boolean(string='Payslip Present', compute='_compute_slip_bool', default=False)
    # Add a Boolean field to indicate if the action_progress3 button has been clicked
    is_progress3_clicked = fields.Boolean(string="Action Progress3 Clicked", default=False)

    attendance_sheet_id = fields.Many2one('hr.attendance.sheet',string="Attendance Sheet Id")

    leave_id = fields.Many2one('hr.leave', string="Leave Reference", ondelete='cascade')

    employee_number = fields.Char(string='Employee No', store=True)

    payroll_transaction_batch_id = fields.Many2one('payroll.transaction.batch', string="Payroll Transaction Batch")

    export = fields.Selection(
        [('no', 'No'), ('yes', 'Yes')],
        string="Export",
        default='no'
    )
    
    @api.onchange('employee_id')
    def _onchange_employ(self):
        for rec in self:
            rec.employee_number = False
            if rec.employee_id:
                rec.employee_number = rec.employee_id.employee_no
    
    @api.model
    # def search(self, args, offset=0, limit=None, order=None):
    def search_fetch(self, args, field_names, offset=0, limit=None, order=None):
        if self.env.user:
            if self.env.user.has_group('hr_saudi.group_sys_manager'):
                return super(SalaryAllowanceDetection, self).search_fetch(args, field_names, offset, limit, order)
            if self.env.user.has_group('hr_saudi.group_normal_employee'):
                args += [('employee_id.user_id', '=', self.env.user.id)]
                print("args", args)
                return super(SalaryAllowanceDetection, self).search_fetch(args, field_names, offset, limit, order)
            if self.env.user.has_group('hr_saudi.group_dm'):
                args += [('state', '=', 'request')]
                return super(SalaryAllowanceDetection, self).search_fetch(args, field_names, offset, limit, order)

            if self.env.user.has_group('hr_saudi.group_hrm'):
                args += [('state', '=', 'progress')]
                return super(SalaryAllowanceDetection, self).search_fetch(args, field_names, offset, limit, order)
            if self.env.user.has_group('hr_saudi.group_finance_manager'):
                args += [('state', '=', 'progress2')]
                return super(SalaryAllowanceDetection, self).search_fetch(args, field_names, offset, limit, order)
            if self.env.user.has_group('hr_saudi.group_admin_approval'):
                args += [('state', '=', 'progress3')]
                return super(SalaryAllowanceDetection, self).search_fetch(args, field_names, offset, limit, order)

        return super(SalaryAllowanceDetection, self).search_fetch(args, field_names, offset, limit, order)

    # Compute methods new Added date on - 08/5/2024
    @api.depends('employee_id', 'date', 'state')
    def _compute_slip_bool(self):
        for rec in self:
            rec.slip_bool = False
            if rec.state == 'approve' and rec.employee_id:
                payslip = self.env['hr.payslip'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('state', '=', 'done'),
                    ('date_from', '<=', rec.date),
                    ('date_to', '>=', rec.date)
                ], limit=1)
                if payslip:
                    rec.slip_bool = True
                    rec.slip_id = payslip.id
                else:
                    rec.slip_bool = False


                payslip_draft = self.env['hr.payslip'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('state', '=', 'draft'),
                    ('date_from', '<=', rec.date),
                    ('date_to', '>=', rec.date)
                ], limit=1)
                if payslip_draft:
                    rec.slip_bool = True
                    rec.slip_id.unlink()
                    rec.slip_bool = False

    @api.model
    def create(self, vals):
        if vals.get('type') == 'transaction_allowance':
            vals['name'] = self.env['ir.sequence'].next_by_code('salary.allowance.seq')
            vals['reference'] = vals['name']
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('salary.detection.seq')
            vals['reference'] = vals['name']
        return super(SalaryAllowanceDetection, self).create(vals)


    # @api.constrains('employee_id')
    # def dupl_transaction(self):
    #     if self.employee_id:
    #         existing_employee = self.env['salary.allowance.detection'].search(
    #             [('id', '!=', self.id), ('employee_id', '=', self.employee_id.id), ('employee_contract_id', '=', self.employee_contract_id.id),
    #              ('transaction_type_id', '=', self.transaction_type_id.id),
    #              ('date', '=', self.date)])
    #         if existing_employee:
    #             raise ValidationError(('Already Employee %s is existing on today' % self.employee_id.name))

    ''' it will modified because the attendance sheet same late in transaction and earlyout transaction have same trasanction type id.so it will create the error.so the constraint is changed'''

    @api.constrains('employee_id', 'hr_transaction_id', 'date')
    def dupl_transaction(self):
        for record in self:
            if record.employee_id:
                # Search for existing records with the same employee, contract, transaction, and date
                existing_employee = self.env['salary.allowance.detection'].search([
                    ('id', '!=', record.id),
                    ('employee_id', '=', record.employee_id.id),
                    ('hr_transaction_id', '=', record.hr_transaction_id.id),
                    # ('transaction_type_id', '=', record.transaction_type_id.id),
                    ('date', '=', record.date)
                ])

                if existing_employee:
                    '''This is for when manager click compute sheet the already payroll detection will be deleted. on november 11 2024'''
                    if existing_employee.attendance_sheet_id:
                        # if existing_employee.state=='approve':
                        #     existing_employee.cancelled()
                        #     existing_employee.unlink()
                        #
                        # else:
                        existing_employee.cancelled()
                        existing_employee.unlink()
                    else:
                        raise ValidationError(
                            _('Duplicate entry detected: Employee %s already has a transaction on %s.')
                            % (record.employee_id.name, record.date)
                        )


    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.department = self.employee_id.department_id.id
        self.employee_contract_id = self.employee_id.contract_id.id

    # def set_to_draft(self):
    #     self.state = 'draft'
    # def submit_to_manager(self):
    #     self.state = 'submit'

    def action_request(self):
        """This Approves the employee allowance/detection advance request.
                           """
        emp_obj = self.env['hr.employee']
        # address = emp_obj.browse([self.employee_id.id]).address_home_id
        # if not address.id:
        #     raise except_orm('Error!', 'Define home address for the employee. i.e address under private information of the employee.')
        allowance_detection_search = self.search([('employee_id', '=', self.employee_id.id),
                                                  ('id', '!=', self.id),
                                                  ('type', '=', self.type),
                                                  ('state', '=', 'approve')])
        current_month = datetime.strptime(str(self.date), '%Y-%m-%d').date().month
        # for each_advance in allowance_detection_search:
        #     existing_month = datetime.strptime(str(each_advance.date), '%Y-%m-%d').date().month
        #     if current_month == existing_month:
        #         raise except_orm('Error!', '%s can be requested once in a month' %(self.type))

        if not self.employee_contract_id:
            raise ValidationError(_('Define a contract for the employee'))

        struct_id = self.employee_contract_id.struct_id

        payslip_obj = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id),
                                                     ('state', '=', 'done'), ('date_from', '<=', self.date),
                                                     ('date_to', '>=', self.date)])
        if payslip_obj:
            raise ValidationError(_('This month salary already calculated'))

        for slip in self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id)]):
            slip_moth = datetime.strptime(str(slip.date_from), '%Y-%m-%d').date().month
            if current_month == slip_moth + 1:
                slip_day = datetime.strptime(str(slip.date_from), '%Y-%m-%d').date().day
                current_day = datetime.strptime(str(self.date), '%Y-%m-%d').date().day

                # print("....struct",type(struct_id.advance_date))
        #         if (current_day - slip_day) < struct_id.advance_date:
        #             raise exceptions.Warning(
        #                 _('Request can be done after "%s" Days From prevoius month salary') % struct_id.advance_date)
        # self.state = 'waiting_approval'
        self.write({'state': 'request'})

    def action_progress(self):
        self.write({'state': 'progress', 'd_manager': self.env.uid})

    def action_progress2(self):
        self.write({'state': 'progress2', 'hr_manage_id': self.env.uid})

    def action_approve(self):
        self.write({'state': 'progress3', 'account_manage_id': self.env.uid})

    def action_progress3(self):
        for rec in self:
            if not rec.employee_contract_id:
                raise ValidationError(_('Define a contract for the employee'))

            payslip_obj = self.env['hr.payslip'].search([('employee_id', '=', rec.employee_id.id),
                                                         ('state', '=', 'done'), ('date_from', '<=', rec.date),
                                                         ('date_to', '>=', rec.date)])
            if payslip_obj:
                raise ValidationError(_('This month salary already calculated'))
            rec.is_progress3_clicked = True
            rec.write({'state': 'approve', 'admin_manager_id': rec.env.uid})

    def action_draft(self):
        return self.write({'state': 'draft'})

    def cancelled(self):
        return self.write({'state': 'cancel'})

    def reject(self):
        self.state = 'reject'

    # def approve_request_acc_dept(self):
    #     """This Approves the employee salary advance request from accounting department.
    #                """
    #     self.state = 'approve'
    #     return True

    # @api.constrains('fixed_amount', 'amount')
    # def check_fixed_amount(self):
    #     for rec in self:
    #         if rec.units in ['days', 'hours']:
    #             if rec.amount < 1:
    #                 raise ValidationError("'Amount' must be greater than 0.")

    @api.onchange('hr_transaction_id')
    def onchange_transaction_type(self):
        # transact_entry = self.env['hr.transaction.entry'].search([('transaction_type_id', '=', self.transaction_type_id.id)],limit=1)
       
        for rec in self:
            if rec.hr_transaction_id:
                rec.type = rec.hr_transaction_id.rule_type
                rec.units = rec.hr_transaction_id.unit_type
                rec.code = rec.hr_transaction_id.code
                rec.transaction_type_id = rec.hr_transaction_id.transaction_type_id.id
                rec.calculate_based_on_allowance = rec.hr_transaction_id.calculate_based_on_allowance
                if rec.units == 'amount':
                    rec.fixed_amount = rec.hr_transaction_id.fixed_amount
                    rec.amount = rec.fixed_amount

    @api.onchange('employee_contract_id')
    def onchange_contract_id(self):
        if self.employee_contract_id:
            self.basic = self.employee_contract_id.wage

    @api.depends('days', 'units', 'employee_contract_id', 'hours', 'calculate_based_on_allowance')
    def compute_hr_allowance_days_hours(self):
        """
            Method to compute the hr payroll amount with days and hours.
        """
        for salary in self:
            salary.amount = 0.00
            for rec in salary.employee_contract_id:
                if salary.employee_id:
                    # worked_days = self.env['hr.payslip.worked_days'].search(
                    #     [('contract_id', '=', salary.employee_contract_id.id)])
                    # days_list = []
                    # for payslip in worked_days:
                        # number_of_days = payslip.number_of_days
                    no_of_days = 30
                    hours_per_day = 8
                    # days_list.append(number_of_days)
                    # no_of_days = days_list[0]
                    if salary.calculate_based_on_allowance == 'wage':
                        if salary.units == 'days':
                            salary.amount = (rec.wage * salary.days / no_of_days * (salary.hr_transaction_id.rate/100))
                        if salary.units == 'hours':
                            salary.amount = (rec.wage / no_of_days / hours_per_day * (salary.hr_transaction_id.rate/100)) * salary.hours
                    #Newly Added on 19/09/2024 Basic + Transport
                    if salary.calculate_based_on_allowance == 'wage_trv':
                        if salary.units == 'days':
                            salary.amount = ((rec.wage + rec.transport_allowance) * salary.days / no_of_days * (salary.hr_transaction_id.rate/100))
                        elif salary.units == 'hours':
                            salary.amount = ((rec.wage + rec.transport_allowance) / no_of_days / hours_per_day * (salary.hr_transaction_id.rate/100)) * salary.hours
                        elif salary.units == 'amount':
                            salary.amount = salary.fixed_amount
                    
                    if salary.calculate_based_on_allowance == 'wage_tr_fd':
                        if salary.units == 'days':
                            salary.amount = ((rec.wage + rec.food_allowance + rec.transport_allowance) * salary.days / no_of_days * (salary.hr_transaction_id.rate/100))
                        elif salary.units == 'hours':
                            salary.amount = ((rec.wage + rec.food_allowance + rec.transport_allowance) / no_of_days / hours_per_day * (salary.hr_transaction_id.rate/100)) * salary.hours
                        elif salary.units == 'amount':
                            salary.amount = salary.fixed_amount
                            

                    if salary.calculate_based_on_allowance == 'hra':
                        if salary.units == 'days':
                            salary.amount = ((rec.wage + rec.house_allowance) * salary.days / no_of_days * (salary.hr_transaction_id.rate/100))
                        elif salary.units == 'hours':
                            salary.amount = ((rec.wage + rec.house_allowance) / no_of_days / hours_per_day * (salary.hr_transaction_id.rate/100)) * salary.hours
                        elif salary.units == 'amount':
                            salary.amount = salary.fixed_amount

                    if salary.calculate_based_on_allowance == 'hra_trv':
                        if salary.units == 'days':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance) * salary.days / no_of_days * (salary.hr_transaction_id.rate/100))
                        elif salary.units == 'hours':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance) /no_of_days /hours_per_day * (salary.hr_transaction_id.rate/100))* salary.hours
                    if salary.calculate_based_on_allowance == 'hr_tr_sch':
                        if salary.units == 'days':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.school_allowance) * salary.days / no_of_days * (salary.hr_transaction_id.rate/100))
    
                        elif salary.units == 'hours':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.school_allowance) / no_of_days / hours_per_day * (salary.hr_transaction_id.rate/100)) * salary.hours
                    if salary.calculate_based_on_allowance == 'hr_tr_fd':
                        if salary.units == 'days':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.food_allowance) * salary.days / no_of_days * (salary.hr_transaction_id.rate/100))
                        elif salary.units == 'hours':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.food_allowance)/ no_of_days / hours_per_day * (salary.hr_transaction_id.rate/100)) * salary.hours
                    if salary.calculate_based_on_allowance == 'hr_tr_fl':
                        if salary.units == 'days':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.fuel_allowance) * salary.days / no_of_days * (salary.hr_transaction_id.rate/100))
                        elif salary.units == 'hours':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.fuel_allowance)/ no_of_days / hours_per_day * (salary.hr_transaction_id.rate/100)) * salary.hours
                    if salary.calculate_based_on_allowance == 'hr_tr_tk':
                        if salary.units == 'days':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.ticket_allowance) * salary.days / no_of_days * (salary.hr_transaction_id.rate/100))
                        elif salary.units == 'hours':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.ticket_allowance)/ no_of_days/hours_per_day * (salary.hr_transaction_id.rate/100)) * salary.hours
                    if salary.calculate_based_on_allowance == 'hr_tr_fx':
                        if salary.units == 'days':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.fixed_allowance) * salary.days / no_of_days * (salary.hr_transaction_id.rate/100))
                        elif salary.units == 'hours':
                            salary.amount = salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.fixed_allowance)/ no_of_days/hours_per_day * (salary.hr_transaction_id.rate/100)) * salary.hours
                    if salary.calculate_based_on_allowance == 'hr_tr_mb':
                        if salary.units == 'days':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.mobile_allowance) * salary.days / no_of_days * (salary.hr_transaction_id.rate/100))
                        elif salary.units == 'hours':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.mobile_allowance)/ no_of_days/hours_per_day * (salary.hr_transaction_id.rate/100)) * salary.hours
    
                    if salary.calculate_based_on_allowance == 'hr_tr_wk':
                        if salary.units == 'days':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.work_allowance) * salary.days / no_of_days * (salary.hr_transaction_id.rate/100))
                        elif salary.units == 'hours':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.work_allowance) / no_of_days/hours_per_day * (salary.hr_transaction_id.rate/100)) * salary.hours
    
                    if salary.calculate_based_on_allowance == 'hr_tr_oth':
                        if salary.units == 'days':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.housing_allowance) * salary.days / no_of_days * (salary.hr_transaction_id.rate/100))
                        elif salary.units == 'hours':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.housing_allowance) / no_of_days/hours_per_day * (salary.hr_transaction_id.rate/100)) * salary.hours
                    if salary.calculate_based_on_allowance == 'all':
                        if salary.units == 'days':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance +
                                              rec.school_allowance + rec.food_allowance + rec.fuel_allowance + rec.ticket_allowance
                                              + rec.fixed_allowance + rec.mobile_allowance + rec.work_allowance +rec.housing_allowance) * salary.days / no_of_days * (salary.hr_transaction_id.rate/100))
                        elif salary.units == 'hours':
                            salary.amount = ((rec.wage + rec.house_allowance + rec.transport_allowance +
                                              rec.school_allowance + rec.food_allowance + rec.fuel_allowance + rec.ticket_allowance
                                              + rec.fixed_allowance + rec.mobile_allowance + rec.work_allowance +rec.housing_allowance) / no_of_days / hours_per_day * (salary.hr_transaction_id.rate/100)) * salary.hours
                
                        
            if salary.units == 'amount':
                salary.amount = salary.fixed_amount
                


        # return self.amount
    # def approve_request(self):
    #     """This Approves the employee allowance/detection advance request.
    #                """
    #     emp_obj = self.env['hr.employee']
    #     # address = emp_obj.browse([self.employee_id.id]).address_home_id
    #     # if not address.id:
    #     #     raise except_orm('Error!', 'Define home address for the employee. i.e address under private information of the employee.')
    #     allowance_detection_search = self.search([('employee_id', '=', self.employee_id.id),
    #                                               ('id', '!=', self.id),
    #                                               ('type', '=', self.type),
    #                                               ('state', '=', 'approve')])
    #     current_month = datetime.strptime(str(self.date), '%Y-%m-%d').date().month
    #     # for each_advance in allowance_detection_search:
    #     #     existing_month = datetime.strptime(str(each_advance.date), '%Y-%m-%d').date().month
    #     #     if current_month == existing_month:
    #     #         raise except_orm('Error!', '%s can be requested once in a month' %(self.type))
    #
    #     if not self.employee_contract_id:
    #         raise ValidationError(_('Define a contract for the employee'))
    #
    #     struct_id = self.employee_contract_id.struct_id
    #
    #     payslip_obj = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id),
    #                                                  ('state', '=', 'done'), ('date_from', '<=', self.date),
    #                                                  ('date_to', '>=', self.date)])
    #     if payslip_obj:
    #         raise ValidationError(_('This month salary already calculated'))
    #
    #     for slip in self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id)]):
    #         slip_moth = datetime.strptime(str(slip.date_from), '%Y-%m-%d').date().month
    #         if current_month == slip_moth + 1:
    #             slip_day = datetime.strptime(str(slip.date_from), '%Y-%m-%d').date().day
    #             current_day = datetime.strptime(str(self.date), '%Y-%m-%d').date().day
    #
    #             # print("....struct",type(struct_id.advance_date))
    #     #         if (current_day - slip_day) < struct_id.advance_date:
    #     #             raise exceptions.Warning(
    #     #                 _('Request can be done after "%s" Days From prevoius month salary') % struct_id.advance_date)
    #     self.state = 'waiting_approval'

    @api.model
    # def search(self, args, offset=0, limit=None, order=None, count=False):
    def search_fetch(self, args, field_names, offset=0, limit=None, order=None):
        if self.env.user:
            if self.env.user.has_group('hr_saudi.group_sys_manager'):
                return super(SalaryAllowanceDetection, self).search_fetch(args, field_names, offset, limit, order)

            if self.env.user.has_group('hr_saudi.group_normal_employee'):
                args += [('employee_id.user_id', '=', self.env.user.id)]
                return super(SalaryAllowanceDetection, self).search_fetch(args, field_names, offset, limit, order)

            if self.env.user.has_group('hr_saudi.group_dm'):
                args += ['|', ('state', '=', 'request'), ('employee_id.user_id', '=', self.env.user.id)]
                return super(SalaryAllowanceDetection, self).search_fetch(args, field_names, offset, limit, order)

            if self.env.user.has_group('hr_saudi.group_hrm'):
                args += ['|', ('state', '=', 'progress'), ('employee_id.user_id', '=', self.env.user.id)]
                return super(SalaryAllowanceDetection, self).search_fetch(args, field_names, offset, limit, order)

            if self.env.user.has_group('hr_saudi.group_finance_manager'):
                args += ['|', ('state', '=', 'progress2'), ('employee_id.user_id', '=', self.env.user.id)]
                return super(SalaryAllowanceDetection, self).search_fetch(args, field_names, offset, limit, order)

            if self.env.user.has_group('hr_saudi.group_admin_approval'):
                args += ['|', ('state', '=', 'progress3'), ('employee_id.user_id', '=', self.env.user.id)]
                return super(SalaryAllowanceDetection, self).search_fetch(args, field_names, offset, limit, order)

        return super(SalaryAllowanceDetection, self).search_fetch(args, field_names, offset, limit, order)

    # This code was added on 30-05-2024.
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     res = super(SalaryAllowanceDetection, self).fields_view_get(view_id=view_id, view_type=view_type,
    #                                                               toolbar=toolbar,
    #                                                               submenu=submenu)
    def get_view(self, view_id=None, view_type='form', toolbar=False, submenu=False, **options):
        res = super(SalaryAllowanceDetection, self).get_view(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                        submenu=submenu, **options)

        if view_type == 'form':
            try:
                doc = etree.XML(res['arch'])
                buttons_to_hide = ['action_request', 'action_progress', 'action_progress2', 'action_approve']
                button_to_show = 'action_progress3'

                if self.env.user.has_group('hr_saudi.group_sys_manager'):
                    for button_name in buttons_to_hide:
                        for node in doc.xpath("//button[@name='%s']" % button_name):
                            modifiers = json.loads(node.get("modifiers", "{}"))
                            modifiers['invisible'] = True
                            node.set("modifiers", json.dumps(modifiers))
                            node.set("invisible", "1")

                    # Check if action_progress3 button has been clicked
                    for node in doc.xpath("//button[@name='%s']" % button_to_show):
                        modifiers = json.loads(node.get("modifiers", "{}"))
                        modifiers['invisible'] = ['|', ('is_progress3_clicked', '=', True), ('state', '=', 'cancel')]
                        node.set("modifiers", json.dumps(modifiers))
                        # node.set("invisible", "1")

                res['arch'] = etree.tostring(doc, encoding='unicode')

            except Exception as e:
                _logger.error("Error while modifying field view: %s", e)

        return res

    # def write(self, vals):
    #     for record in self:
    #         print("raj111111111111111111")
    #         res = super(SalaryAllowanceDetection, self).write(vals)
    #         if self.env.user.has_group('hr_saudi.group_sys_manager'):
    #             if 'employee_contract_id' in vals or not record.employee_contract_id:
    #                 if not vals.get('employee_contract_id', record.employee_contract_id):
    #                     raise ValidationError(_('Define a contract for the employee'))
    #
    #             # if 'employee_id' in vals or 'date' in vals:
    #             #     employee_id = vals.get('employee_id', record.employee_id.id)
    #             #     print("employee_id", employee_id)
    #             #
    #             date = vals.get('date', record.date)
    #             employee_id = vals.get('employee_id', record.employee_id.id)
    #             print("employee_id",employee_id)
    #             if employee_id and date:
    #                 payslip_obj = self.env['hr.payslip'].search([
    #                     ('employee_id', '=', employee_id),
    #                     ('state', '=', 'done'),
    #                     ('date_from', '<=', date),
    #                     ('date_to', '>=', date)
    #                 ])
    #                 if payslip_obj:
    #                     raise ValidationError(_('This month salary already calculated'))
    #                 else:
    #                     # Ensure state is set to 'approve'
    #                     vals['state'] = 'approve'
    #                     print("state", vals['state'])
    #                     vals['admin_manager_id'] = self.env.uid
    #
    #             if 'state' in vals and vals['state'] == 'approve':
    #                 print("state", vals['state'])
    #                 vals['is_progress3_clicked'] = True
    #     return res

    def unlink(self):
        for rec in self:
            if rec.state == 'approve':
                raise ValidationError(_('Approved Records cannot be deleted'))
        return super(SalaryAllowanceDetection, self).unlink()





