# -*- coding: utf-8 -*-
import babel
from pytz import timezone

from odoo import models, fields, api, tools, _
from odoo.exceptions import warnings
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, time
import time
import calendar
import logging
from datetime import timedelta
from lxml import etree
import json


class hr_exit_checklist(models.Model):
    _name = 'hr.exit.checklist'
    _description = "HR Exit Checklist"
    
    name = fields.Char(string="Name", required=True, translate=True)
    responsible_user_id = fields.Many2one('res.users', string='Responsible User', required=True)
    notes = fields.Text(string="Notes")
    checklist_line_ids = fields.One2many('hr.exit.checklist.line','checklist_line_id', string='Checklist')

class hr_exit_checklist_line(models.Model):
    _name = 'hr.exit.checklist.line'
    _description = "HR Exit Checklist Lines"
    
    name = fields.Char(string="Name", required=True)
    checklist_line_id = fields.Many2one('hr.exit.checklist', invisible=True)

class hr_exit_line(models.Model):
    _name = 'hr.exit.line'
    _description = "Exit Lines"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'checklist_id'
    _order = 'id desc'
    
    
    checklist_id = fields.Many2one('hr.exit.checklist', string="Checklist", required=True)
    employee_id = fields.Many2one('hr.employee',string='Employee')
    notes = fields.Text(string="Remarks")
    state = fields.Selection(selection=[('draft', 'New'),\
                                        ('confirm', 'Confirmed'),\
                                        ('approved', 'Approved'),\
                                        ('reject', 'Rejected'),\
                                        ('cancel', 'Cancelled')],\
                                        string='State', default='draft', tracking=True)
    exit_id = fields.Many2one('hr.exit')
    responsible_user_id = fields.Many2one('res.users', string='Responsible User', required=True)
    user_id = fields.Many2one(related="exit_id.user_id",string="User", type='many2one', relation='res.users', \
                        readonly=True, store=True)
    checklist_line_ids = fields.Many2many('hr.exit.checklist.line',
        'rel_exit_checklist_line', 'exit_line_id', 'checklist_exit_line_id',
        string='Checklist Lines')
    
    employee_number = fields.Char(string='Employee No', store = True)
    
    @api.onchange('employee_id')
    def _onchange_employee(self):
        for rec in self:
            rec.employee_number = False
            if rec.employee_id:
                rec.employee_number = rec.employee_id.employee_no
    
    @api.onchange('checklist_id')
    def get_checklistline(self):
        self.checklist_line_ids = self.checklist_id.checklist_line_ids
    
    
    def checklist_confirm(self):
        self.state = 'confirm'
    
   
    def checklist_approved(self):
        self.state = 'approved'
    
    
    def checklist_cancel(self):
        self.state = 'cancel'
    
    
    def checklist_reject(self):
        self.state = 'reject'

    # def unlink(self):
    #     eos_obj = self.env['hr.end.service.benefit'].search(
    #         [('employee_id', '=', self.employee_id.id), ('termination_id', '=', self.exit_id.id), ('type', '=', 'ending_service')])
    #     for rec in self:
    #         if rec.state not in [('draft', 'confirm')] and eos_obj:
    #             raise ValidationError(('You cannot delete the approved or entries'))
    #     return super(hr_exit_line, self).unlink()
        
class hr_exit(models.Model):
    _name = 'hr.exit'
    _description = "Exit"
    _rec_name = 'employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    employee_id = fields.Many2one('hr.employee', required=True, string="Employee")
    request_date = fields.Date('Request Date', readonly=True, \
                    default=fields.datetime.now())
    user_id = fields.Many2one('res.users', string='User', \
                        default=lambda self: self.env.user, \
                        readonly=True)
    confirm_date = fields.Date(string='Confirm Date(Employee)', \
                        readonly=True, copy=False)
    dept_approved_date = fields.Date(string='Approved Date(Department Manager)', \
                        readonly=True, copy=False)
    validate_date = fields.Date(string='Approved Date(HR Manager)', \
                        readonly=True, copy=False)
    general_validate_date = fields.Date(string='Approved Date(General Manager)', \
                        readonly=True, copy=False)
    
    confirm_by_id = fields.Many2one('res.users', string='Confirm By', readonly=True, copy=False)
    dept_manager_by_id = fields.Many2one('res.users', string='Approved By Department Manager', readonly=True, copy=False)
    hr_manager_by_id = fields.Many2one('res.users', string='Approved By HR Manager', readonly=True, copy=False)
    gen_man_by_id = fields.Many2one('res.users', string='Approved By General Manager', readonly=True, copy=False)
    reason_for_leaving = fields.Char(string='Reason For Leaving',required=True, copy=False, readonly=True)
    last_work_date = fields.Date(string='Last Day of Work', required=True)
    survey = fields.Many2one('survey.survey', string="Interview", readonly=True)
    response_id = fields.Many2one('survey.user_input', "Response", ondelete="set null", oldname="response")
    partner_id = fields.Many2one('res.partner', "Contact", readonly=True)
    
    
    state = fields.Selection(selection=[
                        ('draft', 'Draft'), \
                        ('confirm', 'Confirmed'), \
                        ('approved_dept_manager', 'Approved by Dept Manager'),\
                        ('approved_hr_manager', 'Approved by HR Manager'),\
                        ('approved_general_manager', 'Approved by General Manager'),\
                        ('done', 'Done'),\
                        ('cancel', 'Cancel'),\
                        ('reject', 'Rejected')],string='State', \
                        readonly=True, help='', default='draft', \
                        tracking=True)
    notes = fields.Text(string='Notes')
    
    manager_id = fields.Many2one('hr.employee', 'Department Manager', \
                        related='employee_id.parent_id', \
                        readonly=True, store=True,\
                        help='This area is automatically filled by the user who \
                        will confirm the exit', copy=False)
    # manager_id = fields.Many2one('hr.employee', 'Department Manager', \
    #                     related='employee_id.department_id.manager_id', \
    #                     states={'draft':[('readonly', False)]}, readonly=True, store=True,\
    #                     help='This area is automatically filled by the user who \
    #                     will confirm the exit', copy=False)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    department_id = fields.Many2one(related='employee_id.department_id', \
                        string='Department', type='many2one', relation='hr.department', \
                        readonly=True, store=True)
    job_id = fields.Many2one(related='employee_id.job_id', \
                        string='Job Title', type='many2one', relation='hr.department', \
                        readonly=True, store=True)
    checklist_ids = fields.One2many('hr.exit.line', 'exit_id', string="Checklist")
    contract_id = fields.Many2one('hr.contract', string='Contract', readonly=False)
    contract_ids = fields.Many2many('hr.contract', 'hr_contract_contract_tag')
    payslip_id = fields.Many2one('hr.payslip', string="Payslip")
    
    employee_number = fields.Char(string='Employee No', store = True)
    
    @api.onchange('employee_id')
    def _onchange_employeee(self):
        for rec in self:
            rec.employee_number = False
            if rec.employee_id:
                rec.employee_number = rec.employee_id.employee_no

    # def _unlink_payslip(self):
    #     # from_date = lambda self: fields.Date.to_string(date.today().replace(day=1))
    #     # print("from_date...........", from_date)
    #     # to_date = lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date())
    #     # print("to_date...........", to_date)
    #
    #     payslip_obj = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id),
    #             ('date_from', '<=', self.last_work_date),
    #             ('date_to', '>=', self.last_work_date), ('state', '=', 'done')])
    #     if payslip_obj:
    #         payslip_obj.unlink()


    
    def action_makeMeeting(self):
        """ This opens Meeting's calendar view to schedule meeting on current applicant
            @return: Dictionary value for created Meeting view
        """
#         self.ensure_one()
#         partners = self.partner_id | self.user_id.partner_id | self.department_id.manager_id.user_id.partner_id
        
#         category = self.env.ref('hr_recruitment.categ_meet_interview')
        res = self.env['ir.actions.act_window'].for_xml_id('calendar', 'action_calendar_event')
#         res['context'] = {
#             'search_default_partner_ids': self.partner_id.name,
#             'default_partner_ids': partners.ids,
#             'default_user_id': self.env.uid,
#             'default_name': self.name,
#             'default_categ_ids': category and [category.id] or False,
#         }
        return res
    
    #~ @api.multi
    #~ def action_start_survey(self):
        #~ self.ensure_one()
        #~ if not self.response_id:
            #~ response = self.env['survey.user_input'].create({'survey_id': self.survey.id, 'partner_id': self.partner_id.id})
            #~ self.response_id = response.id
        #~ else:
            #~ response = self.response_id
        #~ return self.survey.with_context(survey_token=response.token).action_start_survey()

    #~ @api.multi
    #~ def action_print_survey(self):
        #~ """ If response is available then print this response otherwise print survey form (print template of the survey) """
        #~ self.ensure_one()
        #~ if not self.response_id:
            #~ return self.survey.action_print_survey()
        #~ else:
            #~ response = self.response_id
            #~ return self.survey.with_context(survey_token=response.token).action_print_survey()


   
    def get_contract_latest(self, employee, date_from, date_to):
        """
        @param employee: browse record of employee                print("rec.....", rec)

        @param date_from: date field
        @param date_to: date field
        @return: returns the ids of all the contracts for the given employee that need to be considered for the given dates
        """
        contract_obj = self.env['hr.contract']
        clause = []
        #a contract is valid if it ends between the given dates
        clause_1 = ['&',('date_end', '<=', date_to),('date_end','>=', date_from)]
        #OR if it starts between the given dates
        clause_2 = ['&',('date_start', '<=', date_to),('date_start','>=', date_from)]
        #OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&',('date_start','<=', date_from),'|',('date_end', '=', False),('date_end','>=', date_to)]
        clause_final =  [('employee_id', '=', employee.id),'|','|'] + clause_1 + clause_2 + clause_3
        contract_ids = contract_obj.search(clause_final,limit=1)
        return contract_ids
    
    @api.onchange('employee_id', 'state')
    def get_contract(self):
        contract_obj = self.env['hr.contract']
        payslip_obj = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id), ('state', '=', 'draft'), ('date_from', '<=', self.last_work_date), ('date_to', '>=', self.last_work_date)])
#        if not self.employee_id.address_home_id:
#            raise Warning(_('The employee must have a home address.'))
        self.partner_id = self.employee_id.address_id.id
        all_contract_ids = contract_obj.search([('employee_id', '=', self.employee_id.id)])
        contract_ids = self.get_contract_latest(self.employee_id, self.request_date, self.request_date)
        if contract_ids:
            self.contract_id = contract_ids[0].id
            self.payslip_id = payslip_obj.id
            self.contract_ids = all_contract_ids.ids
            self.manager_id = self.employee_id.parent_id.id
    
    def exit_approved_by_department(self):
        obj_emp = self.env['hr.employee']
        self.state = 'confirm'
        self.dept_approved_date = time.strftime('%Y-%m-%d')

    
    def request_set(self):
        self.state = 'draft'
    
    
    def exit_cancel(self):
        self.state = 'cancel'

    
    def get_confirm(self):
        self.state = 'confirm'
        self.confirm_date = time.strftime('%Y-%m-%d')
        self.confirm_by_id = self.env.user.id
        employee_id = False

        payslip_obj = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id),  ('state', '=', 'draft'), ('date_from', '<=', self.last_work_date), ('date_to', '>=', self.last_work_date)])
        if not payslip_obj:
            new_payslip_obj = self.env['hr.payslip']
            contract_obj = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id), ('state', '=', 'open')])
            employee = self.env['hr.employee'].browse(employee_id)
            for contract in contract_obj:
                for rec in self:
                    new_payslip = {
                        'employee_id': rec.employee_id.id,
                        'date_from': datetime.now().strftime('%Y-%m-01'),
                        'date_to': rec.last_work_date,
                        'contract_id': contract[0].id,
                        'is_terminated': True,
                        'company_id': employee.company_id.id,
                        'payroll_type':'termination',
                }

                    new_obj = new_payslip_obj.create(new_payslip)
                    new_obj.onchange_employee()
                    new_obj.compute_sheet()
                    '''As per Siva sir instruction on sept.10.2024 no need to payslip done for exit employee.because we need to calculate the end of service reward using the  payslip.so done state is removed '''
                    # new_obj.action_payslip_done()
        done_payslip = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id),  ('state', '=', 'done'), ('date_from', '<=', self.last_work_date), ('date_to', '=', self.last_work_date)])
        if done_payslip:
            self.payslip_id = done_payslip.id





    def get_apprv_dept_manager(self):
        self.state = 'approved_dept_manager'
        self.dept_approved_date = time.strftime('%Y-%m-%d')
        self.dept_manager_by_id = self.env.user.id
        checklist_data = self.env['hr.exit.checklist'].search([])
        for checklist in checklist_data:
            vals= {'checklist_id': checklist.id,
                   'exit_id':self.id,
                   'employee_id':self.employee_id.id,
                   'state': 'confirm',
                   'responsible_user_id': checklist.responsible_user_id.id,
                   'checklist_line_ids': [(6, 0, checklist.checklist_line_ids.ids)]}
            self.env['hr.exit.line'].create(vals)
        
    
    def get_apprv_hr_manager(self):
        self.state = 'approved_hr_manager'
        self.validate_date = time.strftime('%Y-%m-%d')
        self.hr_manager_by_id = self.env.user.id
        for record in self.checklist_ids:
            if not record.state in ['approved']:
                raise ValidationError(_('You can not approved this request since there are some checklist to be approved by respected department'))
        
    
    def get_apprv_general_manager(self):
        self.state = 'approved_general_manager'
        self.general_validate_date = time.strftime('%Y-%m-%d')
        self.gen_man_by_id = self.env.user.id
        
    
    def get_done(self):
        for record in self:
            record.state = 'done'
            record.employee_id.write({'state': 'exit', "exit_date":record.last_work_date,"active":True,'accrued_leave_end_of_service':record.last_work_date})
            record.employee_id.contract_id.write({'state':'exit'})

        no_of_days = 0
        payslip_obj = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id),
                                                     ('date_from', '<=', self.last_work_date),
                                                     ('date_to', '>=', self.last_work_date),
                                                     ('state', '=', 'draft')])
        for rec in payslip_obj:
            for line in rec.worked_days_line_ids:
                payslip_obj.write({'date_to': self.last_work_date,
                                   'is_terminated': True,
                                   'payroll_type':'termination',
                                   })
                '''As per Siva sir instruction on sept.10.2024 no need to payslip done for exit employee.because we need to calculate the end of service reward using the  payslip.so done state is removed '''
                # payslip_obj.action_payslip_done()
                
                # no_of_days = (rec.date_to - rec.date_from).days + 1
                # line.update({'number_of_days': no_of_days})

   
    def get_reject(self):
        self.state = 'reject'



    def unlink(self):
        eos_obj = self.env['hr.end.service.benefit'].search(
            [('employee_id', '=', self.employee_id.id), ('termination_id', '=', self.id), ('type', '=', 'ending_service')])
        for rec in self:
            for line in self.checklist_ids:
                if rec.state not in [('draft', 'confirm')] or line.state not in [('draft', 'confirm')] or eos_obj:
                    raise ValidationError(('You cannot delete the approved or done entries'))
        return super(hr_exit, self).unlink()

# class Employee(models.Model):
#     _inherit = 'hr.employee'
#
#     state = fields.Selection(selection=[
#                         ('draft', 'Enroll'), \
#                         ('exit', 'Exit')],string='State', \
#                         readonly=True, help='', default='draft', \
#                         tracking=True)
#
#     exit_date = fields.Date(string="Exit Date")
#     allocation_used_display = fields.Char(string="Allocation Used Display")

    # @api.depends('exit_date')
    # def _compute_hide_edit_button(self):
    #     for record in self:
    #         record.hide_edit_button = bool(record.exit_date)

    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     res = super(Employee, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
    #                                                 submenu=submenu)
    #     # employee_id = self._context.get('active_id') or self._context.get('params', {}).get('id')
    #     # print("Context: ", self._context)
    #     # print("Employee ID: ", employee_id)
    #
    #     if view_type == 'form':
    #         doc = etree.XML(res['arch'])
    #         # List of fields to exclude from being read-only
    #         exclude_fields = ['last_activity', 'first_contract_date', 'allocation_display', 'allocation_remaining_display', 'hours_last_month_display', 'exit_date']
    #         for node in doc.xpath("//field"):
    #             field_name = node.get("name")
    #             # print("field_name", field_name)
    #             # print("field_name", field_name)
    #             if field_name not in exclude_fields:
    #                 modifiers = json.loads(node.get("modifiers", "{}"))
    #                 # modifiers['readonly'] = [('exit_date', '!=', False)]
    #                 modifiers['readonly'] = [('state', '=', 'exit')]
    #                 node.set("modifiers", json.dumps(modifiers))
    #                 node.set("readonly", "1")
    #         res['arch'] = etree.tostring(doc, encoding='unicode')
    #     return res


class Contract(models.Model):
    _inherit = 'hr.contract'
    
    state = fields.Selection([
        ('draft', 'New'),
        ('open', 'Running'),
        ('close', 'Expired'),
        ('exit','Exit'),
        ('cancel', 'Cancelled')
    ], string='Status', group_expand='_expand_states', copy=False,
       tracking=True, help='Status of the contract', default='draft')
    



class ContractHistory(models.Model):
    _inherit = 'hr.contract.history'
    _description = 'Contract history'
    _auto = False
    _order = 'is_under_contract'

    # Even though it would have been obvious to use the reference contract's id as the id of the
    # hr.contract.history model, it turned out it was a bad idea as this id could change (for instance if a
    # new contract is created with a later start date). The hr.contract.history is instead closely linked
    # to the employee. That's why we will use this id (employee_id) as the id of the hr.contract.history.
   
    state = fields.Selection([
        ('draft', 'New'),
        ('open', 'Running'),
        ('close', 'Expired'),
        ('exit', 'Exit'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True)

    # employee_no = fields.Char('Employee No')

class HrDepartureReason(models.Model):

    _inherit = "hr.departure.reason"

    name = fields.Char(translate=True)






