# -*- coding:utf-8 -*-

import babel
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from pytz import timezone
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
import calendar
import logging
from datetime import timedelta
# from datetimerange import DateTimeRange


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _description = 'Pay Slip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # @api.model
    # def _default_payroll_type(self):
    #     for rec in self:
    #         if rec.employee_id:
    #             if rec.employee_id.emp_on_vacation == True:
    #                 rec.payroll_type = 'leave'
    #             else:
    #                 rec.payroll_type = 'leave'

    struct_id = fields.Many2one('hr.payroll.structure', string='Structure',
        readonly=True,
        help='Defines the rules that have to be applied to this payslip, accordingly '
             'to the contract chosen. If you let empty the field contract, this field isn\'t '
             'mandatory anymore and thus the rules applied will be all the rules set on the '
             'structure of all contracts of the employee valid for the chosen period')
    name = fields.Char(string='Payslip Name', readonly=True,
        state={'draft': [('readonly', False)]})
    number = fields.Char(string='Reference', readonly=True, copy=False,
        state={'draft': [('readonly', False)]})
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True,
        state={'draft': [('readonly', False)]})
    date_from = fields.Date(string='Date From',  required=True,
        default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(string='Date To',  required=True,
        default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    # this is chaos: 4 states are defined, 3 are used ('verify' isn't) and 5 exist ('confirm' seems to have existed)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft',
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is under verification, the status is \'Waiting\'.
                \n* If the payslip is confirmed then status is set to \'Done\'.
                \n* When user cancel payslip the status is \'Rejected\'.""")
    line_ids = fields.One2many('hr.payslip.line', 'slip_id', string='Payslip Lines', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, copy=False,
                                 default=lambda self: self.env.company)
    worked_days_line_ids = fields.One2many('hr.payslip.worked_days', 'payslip_id',
        string='Payslip Worked Days', copy=True, readonly=True)
    input_line_ids = fields.One2many('hr.payslip.input', 'payslip_id', string='Payslip Inputs',
        readonly=True, copy=True)
    paid = fields.Boolean(string='Made Payment Order ? ', readonly=True, copy=False)
    note = fields.Text(string='Internal Note', readonly=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', readonly=True)
    details_by_salary_rule_category = fields.One2many('hr.payslip.line',
        compute='_compute_details_by_salary_rule_category', string='Details by Salary Rule Category')
    credit_note = fields.Boolean(string='Credit Note', readonly=True,
        help="Indicates this payslip has a refund of another")
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Payslip Batches', readonly=True,
        copy=False)
    payslip_count = fields.Integer(compute='_compute_payslip_count', string="Payslip Computation Details")
    is_terminated = fields.Boolean(string='Is Terminated', readonly=True,
                                   help="If the employee is terminated other than end date of the month, this field is enabled")
   
    
    employee_bool = fields.Boolean(string='Employee Present', compute='_compute_employee_bool', default=False)

    payroll_type = fields.Selection([('payroll', 'Payroll'), ('arrival', 'Payroll'), ('leave', 'Leave'), ('termination', 'Termination')],default='payroll',string="Payroll Type")
    

    line_ids_filtered = fields.One2many('hr.payslip.line',compute="_compute_line_ids" ,string="Payslip Lines" )

    leave_vacation_payslip_bool = fields.Boolean(string='Leave vacation Payslip', default=False)
    leave_id = fields.Many2one('hr.leave', string="Leave Reference", readonly=True)
    ## Full Accrued Leave base working this 'Future Loan deducted' Flag
    av_loan_bool = fields.Boolean(string='Future Loan deducted', readonly=True, default=False)
    same_month_vacation = fields.Boolean(string='Same month vacation', default=False)

    actual_arrival_date = fields.Date(
        string="Actual Arrival date",
    )


    employee_number = fields.Char(string='Employee No', store = True)

    # @api.model
    # def _default_payroll_type(self):
    #     print("Entering _default_payroll_type method.")
    #
    #     # Get employee_id from context
    #     employee_id = self.env.context.get('default_employee_id')  # Use 'default_' prefix
    #     print("Employee ID from context:", employee_id)
    #
    #     if employee_id:
    #         employee = self.env['hr.employee'].browse(employee_id)
    #         print("Fetched Employee Record:", employee)
    #
    #         # Check if the employee is on vacation
    #         if employee.emp_on_vacation:
    #             print("Employee is on vacation:", employee.emp_on_vacation)
    #             return 'leave'
    #         else:
    #             print("Employee is NOT on vacation.")
    #     else:
    #         print("No employee ID found in context.")
    #
    #     # Default to 'payroll'
    #     print("Returning default value: 'payroll'")
    #     return 'payroll'


    @api.onchange('employee_id')
    def _onchange_employee_number(self):
        for rec in self:
            rec.employee_number = False
            if rec.employee_id:
                rec.employee_number = rec.employee_id.employee_no
            ## newly added on Accrued annuval vacation monthly basis work flow.
            if rec.employee_id.emp_on_vacation:
                rec.leave_vacation_payslip_bool = True
                rec.payroll_type = 'leave'

    # Compute methods new Added date on - 07/5/2024
    
    
    @api.depends('line_ids.total')
    def _compute_line_ids(self):
        for rec in self:
            rec.line_ids_filtered = rec.line_ids.filtered(lambda l:l.total != 0)


    @api.depends('employee_id')
    def _compute_employee_bool(self):
        for payslip in self:
            payslip.employee_bool = bool(payslip.employee_id)
            payslip.update_input_lines()

    # logic methods new Added date on - 07/5/2024
    def update_input_lines(self):
        for payslip in self:
            if payslip.employee_bool:
                input_lines = [(5, 0, 0)]  # Initialize with a delete command
                payslip.input_line_ids = input_lines
                res = payslip.get_inputs(payslip.contract_id, payslip.date_from, payslip.date_to)
                payslip.employee_bool = True
                for data in res:
                    input_lines.append((0, 0, data))
                payslip.write({'input_line_ids': input_lines})

            else:
                payslip.input_line_ids = [(5, 0, 0)]
        self.compute_sheet()
        self.employee_bool = False

    # @api.constrains('employee_id', 'date_from', 'date_to')
    # def _check_unique_payslip(self):
    #     for payslip in self:
    #         domain = [
    #             ('employee_id', '=', payslip.employee_id.id),
    #             ('date_from', '<=', payslip.date_to),
    #             ('date_to', '>=', payslip.date_from),
    #             ('id', '!=', payslip.id)
    #         ]
    #         existing_payslips = self.search_count(domain)
    #         if existing_payslips > 0:
    #             raise ValidationError('Another payslip already exists for this employee within the same date range.')

    @api.constrains('employee_id', 'date_from', 'date_to')
    def _check_unique_payslip(self):
        for payslip in self:
            domain = [
                ('employee_id', '=', payslip.employee_id.id),
                ('date_from', '<=', payslip.date_to),
                ('date_to', '>=', payslip.date_from),
                ('id', '!=', payslip.id)
            ]
            existing_payslip = self.search(domain, limit=1)
            if existing_payslip:
                raise ValidationError(
                    'Another payslip (ID: {}) already exists for employee "{}" within the same date range.'.format(
                        existing_payslip.id, payslip.employee_id.name
                    )
                )

    def _compute_details_by_salary_rule_category(self):
        for payslip in self:
            payslip.details_by_salary_rule_category = payslip.mapped('line_ids').filtered(lambda line: line.category_id)

    def _compute_payslip_count(self):
        for payslip in self:
            payslip.payslip_count = len(payslip.line_ids)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if any(self.filtered(lambda payslip: payslip.date_from > payslip.date_to)):
            raise ValidationError(_("Payslip 'Date From' must be earlier 'Date To'."))

    def action_payslip_draft(self):
        return self.write({'state': 'draft'})

    def action_payslip_done(self):
        self.compute_sheet()
        return self.write({'state': 'done'})

    def action_payslip_cancel(self):
        # if self.filtered(lambda slip: slip.state == 'done'):
        #     raise UserError(_("Cannot cancel a payslip that is done."))
        return self.write({'state': 'cancel'})

    def refund_sheet(self):
        for payslip in self:
            copied_payslip = payslip.copy({'credit_note': True, 'name': _('Refund: ') + payslip.name})
            copied_payslip.compute_sheet()
            copied_payslip.action_payslip_done()
        form_view_ref = self.env.ref('om_om_hr_payroll.view_hr_payslip_form', False)
        tree_view_ref = self.env.ref('om_om_hr_payroll.view_hr_payslip_tree', False)
        return {
            'name': (_("Refund Payslip")),
            'view_mode': 'tree, form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
            'views': [(tree_view_ref and tree_view_ref.id or False, 'tree'), (form_view_ref and form_view_ref.id or False, 'form')],
            'context': {}
        }

    def action_send_email(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = self.env.ref('om_hr_payroll.mail_template_payslip').id
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[2]
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'hr.payslip',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
        }
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def check_done(self):
        return True

    def unlink(self):
        if any(self.filtered(lambda payslip: payslip.state not in ('draft', 'cancel'))):
            raise UserError(_('You cannot delete a payslip which is not draft or cancelled!'))
        return super(HrPayslip, self).unlink()

    # TODO move this function into hr_contract module, on hr.employee object
    @api.model
    def get_contract(self, employee, date_from, date_to):
        """
        @param employee: recordset of employee
        @param date_from: date field
        @param date_to: date field
        @return: returns the ids of all the contracts for the given employee that need to be considered for the given dates
        """
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id), ('state', '=', 'open'), '|', '|'] + clause_1 + clause_2 + clause_3
        return self.env['hr.contract'].search(clause_final).ids

    def compute_sheet(self):
        for payslip in self:
            number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
            # delete old payslip lines
            payslip.line_ids.unlink()
            # set the list of contract for which the rules have to be applied
            # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
            contract_ids = payslip.contract_id.ids or \
                self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)
            if not contract_ids:
                raise ValidationError(_("No running contract found for the employee: %s or no contract in the given period" % payslip.employee_id.name))
            lines = [(0, 0, line) for line in self._get_payslip_lines(contract_ids, payslip.id)]
            payslip.write({'line_ids': lines, 'number': number})

            # if not contract_ids:
            #     raise ValidationError(
            #         _("No running contract found for the employee: %s or no contract in the given period" % payslip.employee_id.name))
            #
            #     # Get payslip lines and filter out those with amount equal to zero
            # all_lines = self._get_payslip_lines(contract_ids, payslip.id)
            # filtered_lines = [line for line in all_lines if line.get('amount', 0) != 0]
            #
            # # Prepare lines for the payslip
            # lines = [(0, 0, line) for line in filtered_lines]
            #
            # # Update payslip with filtered lines and number
            # payslip.write({'line_ids': lines, 'number': number})
        return True

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), time.max)

            # compute leave days
            leaves = {}
            calendar = contract.resource_calendar_id
            tz = timezone(calendar.tz)
            day_leave_intervals = contract.employee_id.list_leaves(day_from, day_to, calendar=contract.resource_calendar_id)
            # for day, hours, leave in day_leave_intervals:
            #     holiday = leave.holiday_id
            #     current_leave_struct = leaves.setdefault(holiday.holiday_status_id, {
            #         'name': holiday.holiday_status_id.name or _('Global Leaves'),
            #         'sequence': 5,
            #         'code': holiday.holiday_status_id.code or 'GLOBAL',
            #         'number_of_days': 0.0,
            #         'number_of_hours': 0.0,
            #         'contract_id': contract.id,
            #     })
            #     current_leave_struct['number_of_hours'] -= hours
            #     work_hours = calendar.get_work_hours_count(
            #         tz.localize(datetime.combine(day, time.min)),
            #         tz.localize(datetime.combine(day, time.max)),
            #         compute_leaves=False,
            #     )
            #     if work_hours:
            #         current_leave_struct['number_of_days'] -= hours / work_hours

            # compute worked days
            work_data = contract.employee_id._get_work_days_data(
                day_from,
                day_to,
                calendar=contract.resource_calendar_id,
                compute_leaves=False,
            )


            # compute leave
            no_of_days = 0
            no_of_hours = 0
            leave_search = self.env['hr.leave'].search([('employee_ids', '=', self.employee_id.id), ('request_date_from', '>=', self.date_from), ('request_date_to', '<=', self.date_to), ('state', '=', 'validate')])
            for leave in leave_search:
                no_of_days += leave.number_of_days
                no_of_hours += no_of_days * self.contract_id.resource_calendar_id.hours_per_day

            attendances = {
                'name': _("Normal Working Days paid at 100%"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': work_data['days'],
                # 'number_of_days': '30',
                'number_of_hours': work_data['hours'],
                'contract_id': contract.id,
            }

            # Initialize a dictionary to store totals by holiday status code
            leave_totals = {}

            # Search for validated leave records for the employee
            leave_records = self.env['hr.leave'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'validate')
            ])

            # Iterate through each leave record
            for leave in leave_records:
                # First condition: if both request_date_from and request_date_to are within the date range
                if (leave.request_date_from >= self.date_from and leave.request_date_to <= self.date_to):
                    if leave.holiday_status_id.code != 'AV':
                        # print("Condition 1 (full leave period within range): Leave ID:", leave.id, "Holiday Code:",
                        #       leave.holiday_status_id.code, "Number of Days:", leave.unpaid_leave)

                        no_of_days = leave.unpaid_leave
                        no_of_hours = no_of_days * self.contract_id.resource_calendar_id.hours_per_day
                    if leave.holiday_status_id.code == 'AV':
                        no_of_days = leave.number_of_days
                        no_of_hours = no_of_days * self.contract_id.resource_calendar_id.hours_per_day


                # Second condition: if request_date_to is within the date range, calculate based on the difference between request_date_to and self.date_from
                elif leave.request_date_to >= self.date_from and leave.request_date_to <= self.date_to:
                    # print("Condition 2 (request_date_to within range): Leave ID:", leave.id, "Holiday Code:",
                    #       leave.holiday_status_id.code)

                    # Calculate the number of days as the difference between request_date_to and self.date_from
                    no_of_days = (leave.request_date_to - self.date_from).days
                    no_of_hours = no_of_days * self.contract_id.resource_calendar_id.hours_per_day

                # Ensure the holiday status is added to the totals dictionary
                holiday_code = leave.holiday_status_id.code
                if holiday_code not in leave_totals:
                    leave_totals[holiday_code] = {
                        'name': leave.holiday_status_id.name,
                        'sequence': 1,
                        'code': holiday_code,
                        'number_of_days': 0.0,
                        'number_of_hours': 0.0,
                        'contract_id': self.contract_id.id,
                    }

                # Accumulate the totals for the current holiday status
                leave_totals[holiday_code]['number_of_days'] += no_of_days
                leave_totals[holiday_code]['number_of_hours'] += no_of_hours


            # Final leave totals for each holiday status code
            for holiday_code, totals in leave_totals.items():
                # Append the summary to the result list
                if totals['number_of_days'] > 0:
                    res.append({
                        'name': totals['name'],
                        'code': holiday_code,
                        'number_of_days': - totals['number_of_days'],
                        'number_of_hours': totals['number_of_hours'],
                        'contract_id': totals['contract_id'],
                    })

            # # Example of how to print or use the result list
            # for item in res:
            #     print(
            #         f"Holiday Code: {item['code']}, Total Days: {item['number_of_days']}, Total Hours: {item['number_of_hours']}")

            leave = {
                'name': 'Unpaid Leave',
                'sequence': 2,
                'code': 'UNP',
                'number_of_days': -no_of_days,
                'number_of_hours': -no_of_days * self.contract_id.resource_calendar_id.hours_per_day,
                'contract_id': contract.id,

                }
            #
            ### for attendance search using attendance module
            attendance_search = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id),('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to)])
            no_of_attendance = 0
            for attendance in attendance_search:
                no_of_attendance += len(attendance)


            attend = {
                'name': _("Attendance"),
                'sequence': 3,
                'code': 'Attend100',
                'number_of_days': no_of_attendance,
                'number_of_hours': no_of_attendance * self.contract_id.resource_calendar_id.hours_per_day,
                'contract_id': contract.id,
            }

            res.append(attendances)
            # res.append(leave_records_list)
            res.extend(leaves.values())
            # res.append(attend)
            # res.append(leave)
        return res

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        res = []

        structure_ids = contracts.get_all_structures()
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]
        inputs = self.env['hr.salary.rule'].browse(sorted_rule_ids).mapped('input_ids')

        for contract in contracts:
            for input in inputs:
                input_data = {
                    'name': input.name,
                    'code': input.code,
                    'contract_id': contract.id,
                }
                         # else:
                #     time_range = DateTimeRange(holiday.date_from,holiday.date_to)
                #     ####This is also worked ,,,,,,,,,,,,,, because date is in range of two
                #     # for value in time_range.range(datetime.timedelta(days=1)):
                #     if previous_day_start in time_range:
                #         is_public_holiday = True
                #         break       res += [input_data]
        return res

    @api.model
    def _get_payslip_lines(self, contract_ids, payslip_id):
        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            localdict['categories'].dict[category.code] = category.code in localdict['categories'].dict and localdict['categories'].dict[category.code] + amount or amount
            return localdict

        class BrowsableObject(object):
            def __init__(self, employee_id, dict, env):
                self.employee_id = employee_id
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(amount) as sum
                    FROM hr_payslip as hp, hr_payslip_input as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours
                    FROM hr_payslip as hp, hr_payslip_worked_days as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
                            FROM hr_payslip as hp, hr_payslip_line as pl
                            WHERE hp.employee_id = %s AND hp.state = 'done'
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
                            (self.employee_id, from_date, to_date, code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        #we keep a dict with the result because a value can be overwritten by another rule with the same code
        result_dict = {}
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        blacklist = []
        payslip = self.env['hr.payslip'].browse(payslip_id)
        for worked_days_line in payslip.worked_days_line_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line
        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line

        categories = BrowsableObject(payslip.employee_id.id, {}, self.env)
        inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)
        worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict, self.env)
        payslips = Payslips(payslip.employee_id.id, payslip, self.env)
        rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)

        baselocaldict = {'categories': categories, 'rules': rules, 'payslip': payslips, 'worked_days': worked_days, 'inputs': inputs}
        #get the ids of the structures on the contracts and their parent id as well
        contracts = self.env['hr.contract'].browse(contract_ids)
        if len(contracts) == 1 and payslip.struct_id:
            structure_ids = list(set(payslip.struct_id._get_parent_structure().ids))
        else:
            structure_ids = contracts.get_all_structures()
        #get the rules of the structure and thier children
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        #run the rules by sequence
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]
        sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)

        for contract in contracts:
            employee = contract.employee_id
            localdict = dict(baselocaldict, employee=employee, contract=contract)
            for rule in sorted_rules:
                key = rule.code + '-' + str(contract.id)
                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100
                #check if the rule can be applied
                if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                    #compute the amount of the rule
                    amount, qty, rate = rule._compute_rule(localdict)
                    #check if there is already a rule computed with that code
                    previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                    #set/overwrite the amount computed for this rule in the localdict
                    tot_rule = contract.company_id.currency_id.round(amount * qty * rate / 100.0)
                    localdict[rule.code] = tot_rule
                    rules_dict[rule.code] = rule
                    #sum the amount for its salary category
                    localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                    #create/overwrite the rule in the temporary results
                    result_dict[key] = {
                        'salary_rule_id': rule.id,
                        'contract_id': contract.id,
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'appears_on_payslip': rule.appears_on_payslip,
                        'condition_select': rule.condition_select,
                        'condition_python': rule.condition_python,
                        'condition_range': rule.condition_range,
                        'condition_range_min': rule.condition_range_min,
                        'condition_range_max': rule.condition_range_max,
                        'amount_select': rule.amount_select,
                        'amount_fix': rule.amount_fix,
                        'amount_python_compute': rule.amount_python_compute,
                        'amount_percentage': rule.amount_percentage,
                        'amount_percentage_base': rule.amount_percentage_base,
                        'register_id': rule.register_id.id,
                        'amount': amount,
                        'employee_id': contract.employee_id.id,
                        'quantity': qty,
                        'rate': rate,
                    }
                else:
                    #blacklist this rule and its children
                    blacklist += [id for id, seq in rule._recursive_search_of_rules()]

        return list(result_dict.values())

    # YTI TODO To rename. This method is not really an onchange, as it is not in any view
    # employee_id and contract_id could be browse records
    def onchange_employee_id(self, date_from, date_to, employee_id=False, contract_id=False):
        #defaults
        res = {
            'value': {
                'line_ids': [],
                #delete old input lines
                'input_line_ids': [(2, x,) for x in self.input_line_ids.ids],
                #delete old worked days lines
                'worked_days_line_ids': [(2, x,) for x in self.worked_days_line_ids.ids],
                #'details_by_salary_head':[], TODO put me back
                'name': '',
                'contract_id': False,
                'struct_id': False,
            }
        }
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        employee = self.env['hr.employee'].browse(employee_id)
        locale = self.env.context.get('lang') or 'en_US'
        res['value'].update({
            'name': _('Salary Slip of %s for %s') % (employee.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale))),
            'company_id': employee.company_id.id,
        })

        if not self.env.context.get('contract'):
            #fill with the first contract of the employee
            contract_ids = self.get_contract(employee, date_from, date_to)
        else:
            if contract_id:
                #set the list of contract for which the input have to be filled
                contract_ids = [contract_id]
            else:
                #if we don't give the contract, then the input to fill should be for all current contracts of the employee
                contract_ids = self.get_contract(employee, date_from, date_to)

        if not contract_ids:
            return res
        contract = self.env['hr.contract'].browse(contract_ids[0])
        res['value'].update({
            'contract_id': contract.id
        })
        struct = contract.struct_id
        if not struct:
            return res
        res['value'].update({
            'struct_id': struct.id,
        })
        #computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        res['value'].update({
            'worked_days_line_ids': worked_days_line_ids,
            'input_line_ids': input_line_ids,
        })
        return res

    @api.onchange('employee_id', 'date_from', 'date_to', 'contract_id')
    def onchange_employee(self):
        self.ensure_one()
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return
        employee = self.employee_id
        date_from = self.date_from
        contract = self.contract_id
        # New Added in based on employee contract join date - 27/02/2024
        # # if employee.first_contract_date and employee.first_contract_date.month == date_from.month and employee.first_contract_date.year == date_from.year:
        #     self.date_from = employee.first_contract_date
        if contract.date_start and contract.date_start.month == date_from.month and contract.date_start.year == date_from.year:
            self.date_from = contract.date_start
        else:
            self.date_from = date_from
        # else:
        #     self.date_from = fields.Date.to_string(date.today().replace(day=1))
        #-----------------------------------------------------------#
        date_to = self.date_to
        contract_ids = []

        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        locale = self.env.context.get('lang') or 'en_US'
        self.name = _('Salary Slip of %s for %s') % (employee.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale)))
        self.company_id = employee.company_id

        if not self.env.context.get('contract') or not self.contract_id:
            contract_ids = self.get_contract(employee, date_from, date_to)
            if not contract_ids:
                return
            self.contract_id = self.env['hr.contract'].browse(contract_ids[0])

        if not self.contract_id.struct_id:
            return
        self.struct_id = self.contract_id.struct_id

        #computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        if contracts:
            worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
            worked_days_lines = self.worked_days_line_ids.browse([])
            for r in worked_days_line_ids:
                worked_days_lines += worked_days_lines.new(r)
            self.worked_days_line_ids = worked_days_lines

            input_line_ids = self.get_inputs(contracts, date_from, date_to)
            input_lines = self.input_line_ids.browse([])
            for r in input_line_ids:
                input_lines += input_lines.new(r)
            self.input_line_ids = input_lines
            return
        
    @api.onchange('contract_id')
    def onchange_contract(self):
        if not self.contract_id:
            self.struct_id = False
        self.with_context(contract=True).onchange_employee()
        return

    def get_salary_line_total(self, code):
        self.ensure_one()
        line = self.line_ids.filtered(lambda line: line.code == code)
        if line:
            return line[0].total
        else:
            return 0.0


    def automatically_attendance_update(self):
        # try:
        #     # Ensure that the user executing the method is linked to an employee record
        #     user_employee = self.env.user.employee_id
        #     if not user_employee:
        #         # If the user is not linked to an employee record, raise a ValidationError
        #         raise ValidationError("User is not linked to an employee record.")
        #

            # Proceed with leave request creation
        employee_search = self.env['hr.employee'].search([])
        for employee in employee_search:
            
            previous_day_start = (datetime.today() - timedelta(days=1)).replace(hour=0, minute=0, second=0)
            previous_day_end = (datetime.today() - timedelta(days=1)).replace(hour=23, minute=59, second=59)
            resource_calendar_id = employee.resource_calendar_id
            calendar = employee.resource_calendar_id
            tz = timezone(calendar.tz)
            yesterday_date_time = datetime.now(tz) - timedelta(days=1)

            # Extract the date and day
            yesterday_date = yesterday_date_time.date()
            yesterday_day = yesterday_date_time.strftime('%A')  # Get the full name of the day
            selection_day = ''
            is_calender_day = False 
            day=''
            for line in calendar.attendance_ids:
                selection_day = dict(line._fields['dayofweek'].selection).get(line.dayofweek)
                day = selection_day
                if day == yesterday_day:
                    is_calender_day = True
                    break
                   
           

            domain = [('calendar_id', '=', resource_calendar_id.id), ('display_type', '=', False)]
            attendances = self.env['resource.calendar.attendance'].read_group(domain, ['ids:array_agg(id)', 'hour_from:min(hour_from)', 'hour_to:max(hour_to)', 'week_type', 'dayofweek', 'day_period'], ['week_type', 'dayofweek', 'day_period'], lazy=False)
            is_public_holiday = False
            public_holidays = self.env['resource.calendar.leaves'].search([])
            for holiday in public_holidays:
                for holi in holiday.name:
                    yesterday = datetime.strftime(datetime.today() - timedelta(days=1),"%Y-%m-%d")
                    start_day = datetime.strftime(holiday.date_from, "%Y-%m-%d")
                    end_day = datetime.strftime(holiday.date_to, "%Y-%m-%d")
                    if start_day == end_day:
                        if start_day == yesterday:
                            is_public_holiday = True 
                            break
                    
                    else:
                        previous_day = datetime.strftime(datetime.today() - timedelta(days=1),"%Y-%m-%d")
                        start = datetime.strftime(holiday.date_from, "%Y-%m-%d")
                        end = datetime.strftime(holiday.date_to, "%Y-%m-%d")
                        if start <= previous_day <= end:
                            is_public_holiday = True
                            break    
                        else:
                            is_public_holiday = False
                            break
                 
                # This is worked when we install pip3 install in odoo-sever       
                # else:
                #     time_range = DateTimeRange(holiday.date_from,holiday.date_to)
                #     ####This is also worked ,,,,,,,,,,,,,, because date is in range of two
                #     # for value in time_range.range(datetime.timedelta(days=1)):
                #     if previous_day_start in time_range:
                #         is_public_holiday = True
                #         break
                

            # public_holidays = self.env['resource.calendar.leaves'].search([('date_from','>=',previous_day_start),('date_to','<=',previous_day_end)],limit=1)
           
            # if public_holidays:
            # # Check if yesterday falls within the public holiday range
            #     if previous_day_start.date() >= public_holidays.date_from.date() and previous_day_end.date() <= public_holidays.date_to.date():
            #         continue
              
            # Check if yesterday was a working day based on the company's working hours
            # is_working_day = False
            # for att in attendances:
            #
            #     if previous_day_start.weekday() == att['dayofweek'][0]:
            #         if att['hour_from'] or att['hour_to']:
            #             is_working_day = True
            #             break
            
            # If yesterday was a working day and the employee didn't have attendance records or leave requests
            if is_calender_day:
                attendance_search = self.env['hr.attendance'].search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', previous_day_start),
                    ('check_out', '<=', previous_day_end)
                ], limit=1)
    
                leave_type = self.env['hr.leave.type'].search([('code', '=', 'Unpaid')], limit=1)
    
                leave_search = self.env['hr.leave'].search([
                    ('employee_id', '=', employee.id),
                    ('request_date_from', '>=', previous_day_start),
                    ('request_date_to', '<=', previous_day_end)
                ], limit=1)
                # Assuming 'employee' is the correct holiday type
                holiday_type = 'employee'
                a = previous_day_start
                b = previous_day_end
                if not attendance_search:
                    if not leave_search:
                        if not is_public_holiday:
                        # if public_holidays.date_from and public_holidays.date_to:
                    
                            # if not ((public_holidays.date_from.date() == previous_day_start.date()) and (public_holidays.date_to.date() == previous_day_end.date())):
                            
                        # Get employee's department and company
                            department = employee.department_id.id
                            company = employee.company_id.id
        
                            # Create the leave request
                            vals = {
                                'holiday_status_id': leave_type.id,
                                'employee_id': employee.id,
                                'department_id': department,
                                'employee_company_id': company,
                                'request_date_from': a,
                                'request_date_to': b,
                                'number_of_days': 1,
                                'holiday_type': holiday_type,
                                # 'state':'validate'
                            }
                            leave_approve = self.env['hr.leave'].create(vals)
                            leave_approve.action_approve()
                            leave_approve.action_validate()
                            leave_approve.send_mail_leave_automatically()
    
        #
        # except ValidationError as e:
        #     # Log the error
        #     self.env['ir.logging'].create({
        #         'name': 'attendance_update Validation Error',
        #         'type': 'server',
        #         'level': 'ERROR',
        #         'message': str(e)
        #     })
        #
        #     # Inform the user about the error
        #     raise ValidationError("Validation Error: {}".format(str(e)))
    


class HrPayslipLine(models.Model):
    _name = 'hr.payslip.line'
    _inherit = 'hr.salary.rule'
    _description = 'Payslip Line'
    _order = 'contract_id, sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade')
    salary_rule_id = fields.Many2one('hr.salary.rule', string='Rule', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True, index=True)
    rate = fields.Float(string='Rate (%)', default=100.0)
    amount = fields.Float( string='Regular Amount')
    quantity = fields.Float(default=1.0)
    total = fields.Float(compute='_compute_total', string='Actual Amount')


    
    # @api.depends('quantity', 'amount', 'rate')
    # def _compute_total(self):
    #     for line in self:
    #         line.total = float(line.quantity) * line.amount * line.rate / 100

    # Newly added in 26/02/2024 employee salary calculation
    # @api.depends('quantity', 'amount', 'rate', 'slip_id.date_from', 'slip_id.date_to')
    # def _compute_total(self):
    #
    #     #### Total allowance declaration on april 1 2024
    #     total_allowance = 0
    #     total_deduction = 0
    #     total_transaction_addition = 0
    #     total_transction_deduction = 0
    #     total_gross = 0
    #     total_add = 0
    #     total_net = 0
    #     temp_total_addition_amount = 0
    #     temp_total_deduction_amount = 0
    #     leave_days = 0
    #     total_leave_days = 0
    #     for line in self:
    #         try:
    #             days = 0
    #             num_days = 0
    #             total_amount = 0
    #             line.total = 0
    #             net_amount = 0
    #
    #             for lin in line.slip_id.worked_days_line_ids:
    #                 # if lin.code=='GLOBAL' or 'UNP':
    #                 if lin.code == 'UNP':
    #                     leave_days += lin.number_of_days
    #             # total_allowance =0
    #             total_leave_days = leave_days
    #
    #             if line.slip_id.date_from and line.slip_id.date_to:
    #                 date_from = fields.Date.to_date(line.slip_id.date_from)
    #                 date_to = fields.Date.to_date(line.slip_id.date_to)
    #                 # days = (date_to - date_from).days + 1
    #                 # num_days = calendar.monthrange(date_from.year, date_from.month)[1]
    #                 # if calendar.isleap(date_from.year):
    #                 #     num_days += 1
    #                 if date_from.month == 2:
    #                     if calendar.isleap(date_from.year):
    #                         num_days = 30
    #                         days = (date_to - date_from).days + 2
    #                         # print("isleap - ", num_days, days)
    #                     else:
    #                         num_days = 30
    #                         days = (date_to - date_from).days + 3
    #                         # print("not isleap - ", num_days, days)
    #                 else:
    #                     num_days = calendar.monthrange(date_from.year, date_from.month)[1]
    #                     # if num_days > 30:
    #                     #     num_days = 30
    #                     days = (date_to - date_from).days + 1
    #             if not line.code == 'Loan':
    #                 total_amount = float(line.quantity) * ((line.amount / num_days) * days)
    #                 line.total = total_amount
    #             if line.code == 'Loan':
    #                 total_amount = line.amount
    #                 line.total = total_amount
    #
    #             # if line.category_id.code=="BASIC" or line.category_id.code=="ALW":
    #             #
    #             #     total_amount = float(line.quantity)*((line.amount / num_days) * days)
    #             #     line.total = total_amount
    #             #     total_allowance += total_amount
    #             #
    #             # if  line.category_id.code=="DED":
    #             #     total_amount = float(line.quantity)*((line.amount / num_days) * days)
    #             #     line.total = total_amount
    #             #     total_deduction += total_amount
    #             #
    #             # if  line.category_id.code=="COMP":
    #             #     total_amount = float(line.quantity)*((line.amount / num_days) * days)
    #             #     line.total = total_amount
    #             #
    #             # if  line.category_id.code=="PTADD" :
    #             #     total_amount = line.amount
    #             #     line.total = total_amount
    #             #     total_transaction_addition += total_amount
    #             #
    #             #
    #             # if  line.category_id.code=="PTDED" :
    #             #     total_amount = line.amount
    #             #     line.total = total_amount
    #             #     total_transction_deduction += total_amount
    #             #
    #             #
    #             # if line.category_id.code == "GROSS":
    #             #     # line.amount = 0
    #             #     total_gross =   total_allowance+total_transaction_addition
    #             #     line.amount = total_gross
    #             #     line.total = total_gross
    #             #
    #             # if line.category_id.code == "NET":
    #             #     # line.amount = 0
    #             #     total_net =  (total_allowance + total_transaction_addition) + total_deduction + total_transction_deduction
    #             #     line.amount = total_net
    #             #     line.total = total_net
    #             #     print("line.total",line.total,total_deduction,total_transction_deduction )
    #
    #             # newly added 28/03/2023
    #             # Newly added on 28/03/2023
    #             allowance_amount = self.env['salary.allowance.detection'].search([
    #                 ('employee_contract_id', '=', line.slip_id.contract_id.id),
    #                 ('type', '=', 'transaction_allowance'),
    #                 ('code', '=', line.code),
    #                 ('date', '>=', line.slip_id.date_from),
    #                 ('date', '<=', line.slip_id.date_to),
    #                 ('state', '=', 'approve')
    #             ])
    #             temp_total_addition_amount = 0
    #             for allowance in allowance_amount:
    #                 temp_total_addition_amount += allowance.amount
    #                 line.amount = temp_total_addition_amount
    #                 line.total = temp_total_addition_amount
    #
    #                 for li in line.slip_id.input_line_ids.filtered(lambda li: li.code == allowance.code):
    #                     li.amount = 0.00
    #                     if li:
    #                         li.amount = temp_total_addition_amount
    #
    #             deduction_amount = self.env['salary.allowance.detection'].search([
    #                 ('employee_contract_id', '=', line.slip_id.contract_id.id),
    #                 ('type', '=', 'transaction_detection'),
    #                 ('code', '=', line.code),
    #                 ('date', '>=', line.slip_id.date_from),
    #                 ('date', '<=', line.slip_id.date_to),
    #                 ('state', '=', 'approve')
    #             ])
    #
    #             for deduction in deduction_amount:
    #                 temp_total_deduction_amount += deduction.amount
    #                 line.amount = -temp_total_deduction_amount
    #                 line.total = -temp_total_deduction_amount
    #
    #                 for dec in line.slip_id.input_line_ids.filtered(lambda dec: dec.code == deduction.code):
    #                     dec.amount = 0.00
    #                     if dec:
    #                         dec.amount = temp_total_deduction_amount
    #                 # amount = allowance.amount
    #             #### for encash leave newly added may 20  because encash leave is added with accured leave category
    #             if line.code == 'ACL':
    #                 for li in line.slip_id.input_line_ids:
    #                     if li.code == 'ACL':
    #                         total_amount = line.amount + line.slip_id.encash_amt
    #                         line.amount = total_amount
    #                         line.total = total_amount
    #                     else:
    #
    #                         total_amount = line.slip_id.encash_amt
    #
    #
    #
    #         except Exception as e:
    #             # _logger.error(f"Error in compute_total: {e}")
    #             line.total = 0

    @api.depends('quantity', 'amount', 'rate', 'slip_id.date_from', 'slip_id.date_to')
    def _compute_total(self):
        for line in self:
            try:
                days = 0
                num_days = 0
                total_amount = 0
                line.total = 0

                # Calculate leave days
                leave_days = sum(lin.number_of_days for lin in line.slip_id.worked_days_line_ids if lin.code == 'UNP')

                # Calculate number of days in payroll period
                if line.slip_id.date_from and line.slip_id.date_to:
                    date_from = fields.Date.to_date(line.slip_id.date_from)
                    date_to = fields.Date.to_date(line.slip_id.date_to)
                    print("normal payslip")

                    # Calculate the actual days between the two dates
                    days = (date_to - date_from).days + 1
                    num_days = 30
                    leave_records = self.env['hr.leave'].search([('request_date_from', '>=', line.slip_id.date_from),
                                                                 ('request_date_to', '<=', line.slip_id.date_to),
                                                                 ('employee_id', '=', line.slip_id.employee_id.id),
                                                                 ('state', '=', 'validate'),
                                                                 ('holiday_status_id.code', '!=', 'AV')]).mapped(
                        'unpaid_leave')

                    num_of_leave_days = sum(leave_records) if leave_records else 0.00
                    print("num_of_leave_days", num_of_leave_days)


                    # Check if the month is February
                    if date_from.month == 2 and date_to.month == 2:
                        days = 30
                        # print("day1111", days)
                    if days > 30:
                        days = 30

                    #Newly added this code 08/10/2024
                    days = days - num_of_leave_days
                    print("days final ", days)



                    # if date_from.month == 2:  # February handling
                    #     if calendar.isleap(date_from.year):
                    #         num_days = 29
                    #         days = (date_to - date_from).days + 2
                    #     else:
                    #         num_days = 28
                    #         days = (date_to - date_from).days + 1
                    # else:
                    #     num_days = calendar.monthrange(date_from.year, date_from.month)[1]
                    #     days = (date_to - date_from).days + 1

                if line.code not in ['Loan', 'GOSI', 'GOSI_COMP']:
                    
                    total_amount = float(line.quantity) * ((line.amount / num_days) * days)
                    line.total = total_amount
                    
                if line.code in ['Loan']:
                    
                    line.total = line.amount
                 
                if line.code in ['GOSI', 'GOSI_COMP']:
                    # Check if hiring_date and date_from are set
                    hiring_date = line.slip_id.employee_id.joining_date
                    exit_date = line.slip_id.employee_id.exit_date
                    date_from = line.slip_id.date_from
                
                    if hiring_date and date_from:
                       
                        # Calculate the month and year for comparison
                        hiring_month_year = hiring_date.strftime("%m-%Y")
                        exit_month_year = exit_date.strftime("%m-%Y") if exit_date else None
                        payslip_month_year = date_from.strftime("%m-%Y")
                        ''' If employee is mid join then Gosi and gosi comp will be caluclated based on the days of hiring date or exit employee in a month then the payslip is mid exit which is done on nov 19 2024'''
                        if (hiring_month_year == payslip_month_year) or (exit_month_year == payslip_month_year):
                            # Mid-join or mid-exit calculation
                            # num_days = (date_from + relativedelta(day=31)).day  # Total days in the month
                            # if hiring_month_year == payslip_month_year:
                            #     days = (date_from + relativedelta(day=31)).day - hiring_date.day + 1  # Days worked after joining
                            # else:
                            #     days = exit_date.day  # Days worked until exiting
                            #
                            # print(f"Total days in month: {num_days}, Days worked: {days}")
                            total_amount = float(line.quantity) * ((line.amount / num_days) * days)
                            line.total = total_amount
                        else:
                            # Normal calculation for full month
                            line.total = line.amount
                
                    else:
                        # Fallback if dates are missing
                        line.total = line.amount
                        

                # if line.code in ['GOSI', 'GOSI_COMP']:
                #     print("..........goisiiiiiiiiiiiiiiiiiiiiiiiiiiiii",line.code)
                #     ''' If employee is mid join then Gosi and gosi comp will be caluclated based on the days of hiring date or exit employee in a month then the payslip is mid exit which is done on nov 19 2024'''
                #     if line.slip_id.employee_id.hiring_date and line.slip_id.date_from:
                #         print(".....................firstttttttttttttttt",line.slip_id.employee_id.hiring_date)
                #         if (line.slip_id.employee_id.hiring_date.strftime("%m-%Y") == line.slip_id.date_from.strftime("%m-%Y")) or (line.slip_id.employee_id.exit_date.strftime("%m-%Y") == line.slip_id.date_from.strftime("%m-%Y")) :
                #             total_amount = float(line.quantity) * ((line.amount / num_days) * days)
                #             line.total = total_amount
                #         else:    
                #             line.total = line.amount
                #             print("..........line.total",line.total)
                        

                # Handling encashed leave (ACL)
                if line.code == 'ACL':
                    for li in line.slip_id.input_line_ids:
                        if li.code == 'ACL':
                            total_amount = line.amount + line.slip_id.encash_amt
                            line.amount = total_amount
                            line.total = total_amount
                if line.code == 'EOSEXIT':
                    line.total = line.slip_id.terminal_amount
                    # line.amount = line.slip_id.terminal_amount
                if line.code == 'EOSACCL':
                    line.total = line.slip_id.eos_accured_leave
                   
                    # line.amount = line.slip_id.eos_accured_leave    
                if line.code == 'EOSLoan':
                    line.total = - line.slip_id.eos_outstanding_loan
                    # line.amount = line.slip_id.terminal_amount
                if line.code == 'EOSAdvance':
                    line.total = - line.slip_id.eos_outstanding_advance
                    
            except Exception as e:
                line.total = 0
                print(f"Error in _compute_total: {str(e)}")

        # Calculate the GROSS amount based on BASIC and ALW categories
        gro_total = 0.0
        basic_alw = 0.0
        alw_total = 0.0
        total_ded = 0.0
        ded_total = 0.0
        total_deduction = 0.00

        for li in self.slip_id.line_ids:
            # if li.slip_id.payroll_type in ['leave', 'termination']:
            #     previous_payslips = self.env['hr.payslip'].search([
            #         ('employee_id', '=', li.slip_id.employee_id.id),
            #         ('date_from', '>=', li.slip_id.date_from.replace(day=1)),
            #         ('date_to', '<=', li.slip_id.date_to),
            #         ('id', '!=', li.slip_id.id),
            #         ('payroll_type', '=', 'leave')
            #     ])
            #     if not previous_payslips:
            #         if li.slip_id.contract_id:
            #             if li.slip_id.contract_id.house_allowance_bool and li.code == 'HRA':
            #                 li.total = li.amount
            #             if li.slip_id.contract_id.transport_allowance_bool and li.code == 'TRANSPORT':
            #                 li.total = li.amount
            #             if li.slip_id.contract_id.school_allowance_bool and li.code == 'SCHOOL':
            #                 li.total = li.amount
            #             if li.slip_id.contract_id.food_allowance_bool and li.code == 'FOOD':
            #                 li.total = li.amount
            #             if li.slip_id.contract_id.fuel_allowance_bool and li.code == 'FUEL':
            #                 li.total = li.amount
            #             if li.slip_id.contract_id.ticket_allowance_bool and li.code == 'TICKET':
            #                 li.total = li.amount
            #             if li.slip_id.contract_id.fixed_allowance_bool and li.code == 'FIXED':
            #                 li.total = li.amount
            #             if li.slip_id.contract_id.work_allowance_bool and li.code == 'MEDICAL':
            #                 li.total = li.amount
            #             if li.slip_id.contract_id.mobile_allowance_bool and li.code == 'MOBILE':
            #                 li.total = li.amount
            #             if li.slip_id.contract_id.housing_allowance_bool and li.code == 'OTA':
            #                 li.total = li.amount
            #     else:
            #         if li.slip_id.contract_id:
            #             if li.slip_id.contract_id.house_allowance_bool and li.code == 'HRA':
            #                 li.total = 0.0
            #             if li.slip_id.contract_id.transport_allowance_bool and li.code == 'TRANSPORT':
            #                 li.total = 0.0
            #             if li.slip_id.contract_id.school_allowance_bool and li.code == 'SCHOOL':
            #                 li.total = 0.0
            #             if li.slip_id.contract_id.food_allowance_bool and li.code == 'FOOD':
            #                 li.total = 0.0
            #             if li.slip_id.contract_id.fuel_allowance_bool and li.code == 'FUEL':
            #                 li.total = 0.0
            #             if li.slip_id.contract_id.ticket_allowance_bool and li.code == 'TICKET':
            #                 li.total = 0.0
            #             if li.slip_id.contract_id.fixed_allowance_bool and li.code == 'FIXED':
            #                 li.total = 0.0
            #             if li.slip_id.contract_id.work_allowance_bool and li.code == 'MEDICAL':
            #                 li.total = 0.0
            #             if li.slip_id.contract_id.mobile_allowance_bool and li.code == 'MOBILE':
            #                 li.total = 0.0
            #             if li.slip_id.contract_id.housing_allowance_bool and li.code == 'OTA':
            #                 li.total = 0.0
            #             if li.code == 'GOSI_COMP':
            #                 li.total = 0.0
            #             if li.code == 'GOSI':
            #                 li.total = 0.0

            # if li.slip_id.payroll_type in ['leave', 'termination']:
            #     previous_payslips = self.env['hr.payslip'].search([
            #         ('employee_id', '=', li.slip_id.employee_id.id),
            #         ('date_from', '>=', li.slip_id.date_from.replace(day=2)),
            #         ('date_to', '<=', li.slip_id.date_to),
            #         ('id', '!=', li.slip_id.id),
            #         ('payroll_type', '=', 'leave')
            #     ])
            #     ''' this check is used to when the employee goes to leave from 1 st day of the month then the company wants to produced payslip only one day with gosi alone to produced to the employee for respective month.'''
            #     if li.slip_id.date_from.day == 1 and li.slip_id.date_to.day == 1:
            #         if li.slip_id.contract_id:
            #             if not li.code in ['GOSI_COMP', 'GOSI']:
            #                 li.total = 0.0
            #
            #             if li.code == 'GOSI_COMP':
            #                 li.total = line.amount
            #             if li.code == 'GOSI':
            #                 li.total = line.amount
            #
            #
            #     else:
            #         if not previous_payslips:
            #             if li.slip_id.contract_id:
            #                 if li.slip_id.contract_id.house_allowance_bool and li.code == 'HRA':
            #                     li.total = li.amount
            #                 if li.slip_id.contract_id.transport_allowance_bool and li.code == 'TRANSPORT':
            #                     li.total = li.amount
            #                 if li.slip_id.contract_id.school_allowance_bool and li.code == 'SCHOOL':
            #                     li.total = li.amount
            #                 if li.slip_id.contract_id.food_allowance_bool and li.code == 'FOOD':
            #                     li.total = li.amount
            #                 if li.slip_id.contract_id.fuel_allowance_bool and li.code == 'FUEL':
            #                     li.total = li.amount
            #                 if li.slip_id.contract_id.ticket_allowance_bool and li.code == 'TICKET':
            #                     li.total = li.amount
            #                 if li.slip_id.contract_id.fixed_allowance_bool and li.code == 'FIXED':
            #                     li.total = li.amount
            #                 if li.slip_id.contract_id.work_allowance_bool and li.code == 'MEDICAL':
            #                     li.total = li.amount
            #                 if li.slip_id.contract_id.mobile_allowance_bool and li.code == 'MOBILE':
            #                     li.total = li.amount
            #                 if li.slip_id.contract_id.housing_allowance_bool and li.code == 'OTA':
            #                     li.total = li.amount
            #                 if not (li.slip_id.date_from.day == 1 and li.slip_id.date_to.day == 1):
            #                     if li.code == 'GOSI_COMP':
            #                         li.total = 0.0
            #                     if li.code == 'GOSI':
            #                         li.total = 0.0
            #
            #
            #
            #         else:
            #             if li.slip_id.contract_id:
            #                 if li.slip_id.contract_id.house_allowance_bool and li.code == 'HRA':
            #                     li.total = 0.0
            #                 if li.slip_id.contract_id.transport_allowance_bool and li.code == 'TRANSPORT':
            #                     li.total = 0.0
            #                 if li.slip_id.contract_id.school_allowance_bool and li.code == 'SCHOOL':
            #                     li.total = 0.0
            #                 if li.slip_id.contract_id.food_allowance_bool and li.code == 'FOOD':
            #                     li.total = 0.0
            #                 if li.slip_id.contract_id.fuel_allowance_bool and li.code == 'FUEL':
            #                     li.total = 0.0
            #                 if li.slip_id.contract_id.ticket_allowance_bool and li.code == 'TICKET':
            #                     li.total = 0.0
            #                 if li.slip_id.contract_id.fixed_allowance_bool and li.code == 'FIXED':
            #                     li.total = 0.0
            #                 if li.slip_id.contract_id.work_allowance_bool and li.code == 'MEDICAL':
            #                     li.total = 0.0
            #                 if li.slip_id.contract_id.mobile_allowance_bool and li.code == 'MOBILE':
            #                     li.total = 0.0
            #                 if li.slip_id.contract_id.housing_allowance_bool and li.code == 'OTA':
            #                     li.total = 0.0
            #                 if li.code == 'GOSI_COMP':
            #                     li.total = 0.0
            #                 if li.code == 'GOSI':
            #                     li.total = 0.0
            if li.slip_id.payroll_type in ['leave', 'arrival']:
                if not li.slip_id.leave_vacation_payslip_bool:
                    print("00000000000000000000000000000000000")

                    # Fetch previous payslips of type 'leave'
                    previous_payslips = self.env['hr.payslip'].search([
                        ('employee_id', '=', li.slip_id.employee_id.id),
                        ('date_from', '>=', li.slip_id.date_from.replace(day=1)),
                        ('date_to', '<=', li.slip_id.date_to),
                        ('id', '!=', li.slip_id.id),
                        ('payroll_type', '=', 'leave')
                    ])
                    emp_loan_amount = 0.00
                    emp_advance_amount = 0.00
                    # loan_added_payslips = self.env['hr.employee.loan.ps'].search([
                    #     ('employee_id', '=', li.slip_id.employee_id.id)
                    # ])
                    # for emp_loan in loan_added_payslips.hr_employee_loan_line_ps:
                    #     if emp_loan and emp_loan.installment_date:
                    #         if (emp_loan.installment_date.year == li.slip_id.date_from.year and
                    #                 emp_loan.installment_date.month == li.slip_id.date_from.month) and (emp_loan.confirm == True) and (emp_loan.state == 'notdeducted'):
                    #             emp_loan_amount = emp_loan.amount
                    #
                    # advance_added_payslips = self.env['hr.employee.advance.ps'].search([
                    #     ('employee_id', '=', li.slip_id.employee_id.id)
                    # ])
                    # for emp_advance in advance_added_payslips.hr_employee_advance_line_ps:
                    #     if emp_advance and emp_advance.installment_date:
                    #         if (emp_advance.installment_date.year == li.slip_id.date_from.year and
                    #                 emp_advance.installment_date.month == li.slip_id.date_from.month) and (emp_advance.confirm == True) and (emp_advance.state == 'notdeducted'):
                    #             emp_advance_amount = emp_advance.amount

                    if li.slip_id.av_loan_bool:
                        if li.slip_id.date_from and li.slip_id.leave_id.request_date_to:
                            start_date = li.slip_id.date_from
                            end_date = li.slip_id.leave_id.request_date_to
                            # print("end_date, start_date", end_date, start_date)

                            current_date = start_date

                            while current_date <= end_date:
                                loan_added_payslips = self.env['hr.employee.loan.ps'].search([
                                    ('employee_id', '=', li.slip_id.employee_id.id)
                                ])
                                for emp_loan in loan_added_payslips.hr_employee_loan_line_ps:
                                    if emp_loan and emp_loan.installment_date:
                                        if (emp_loan.installment_date.year == current_date.year and
                                            emp_loan.installment_date.month == current_date.month)and (
                                                emp_loan.confirm == True) and (emp_loan.state in ['notdeducted', 'deducted']):
                                            emp_loan_amount += emp_loan.amount  # Add loan amount to total

                                advance_added_payslips = self.env['hr.employee.advance.ps'].search([
                                    ('employee_id', '=', li.slip_id.employee_id.id)
                                ])
                                for emp_advance in advance_added_payslips.hr_employee_advance_line_ps:
                                    if emp_advance and emp_advance.installment_date:
                                        if (emp_advance.installment_date.year == current_date.year and
                                            emp_advance.installment_date.month == current_date.month) and (
                                                emp_advance.confirm == True) and (emp_advance.state in ['notdeducted', 'deducted']):
                                            emp_advance_amount += emp_advance.amount  # Add advance amount to total

                                current_date = current_date + relativedelta(months=1)
                                # print("current_date", current_date)



                    else:
                        loan_added_payslips = self.env['hr.employee.loan.ps'].search([
                            ('employee_id', '=', li.slip_id.employee_id.id)
                        ])
                        for emp_loan in loan_added_payslips.hr_employee_loan_line_ps:
                            if emp_loan and emp_loan.installment_date:
                                if (emp_loan.installment_date.year == li.slip_id.date_from.year and
                                    emp_loan.installment_date.month == li.slip_id.date_from.month) and (
                                        emp_loan.confirm == True) and (emp_loan.state in ['notdeducted', 'deducted']):
                                    emp_loan_amount = emp_loan.amount

                        advance_added_payslips = self.env['hr.employee.advance.ps'].search([
                            ('employee_id', '=', li.slip_id.employee_id.id)
                        ])
                        for emp_advance in advance_added_payslips.hr_employee_advance_line_ps:
                            if emp_advance and emp_advance.installment_date:
                                if (emp_advance.installment_date.year == li.slip_id.date_from.year and
                                    emp_advance.installment_date.month == li.slip_id.date_from.month) and (
                                        emp_advance.confirm == True) and (emp_advance.state in ['notdeducted', 'deducted']):
                                    emp_advance_amount = emp_advance.amount


                    if li.slip_id.date_from.day == 1 and li.slip_id.date_to.day == 1:
                        if li.slip_id.contract_id:
                            # if li.code not in ['GOSI_COMP', 'GOSI']:
                            #     li.total = 0.0

                            allowances = {
                                'HRA': li.slip_id.contract_id.house_allowance_bool,
                                'TRANSPORT': li.slip_id.contract_id.transport_allowance_bool,
                                'SCHOOL': li.slip_id.contract_id.school_allowance_bool,
                                'FOOD': li.slip_id.contract_id.food_allowance_bool,
                                'FUEL': li.slip_id.contract_id.fuel_allowance_bool,
                                'TICKET': li.slip_id.contract_id.ticket_allowance_bool,
                                'FIXED': li.slip_id.contract_id.fixed_allowance_bool,
                                'MEDICAL': li.slip_id.contract_id.work_allowance_bool,
                                'MOBILE': li.slip_id.contract_id.mobile_allowance_bool,
                                'OTA': li.slip_id.contract_id.housing_allowance_bool,
                                'GOSI_COMP': True,
                                'GOSI': True
                            }
                            li.total = li.amount if allowances.get(li.code, False) else 0.00
                            # li.total = li.amount
                            if li.code == 'loan':
                                li.total = -emp_loan_amount
                                li.amount = -emp_loan_amount
                            if li.code == 'Advance':
                                li.total = -emp_advance_amount
                                li.amount = -emp_advance_amount

                            # if li.code in ['GOSI_COMP', 'GOSI']:
                            #     li.total = li.amount
                    else:
                        if not previous_payslips and li.slip_id.contract_id:
                            allowances = {
                                'HRA': li.slip_id.contract_id.house_allowance_bool,
                                'TRANSPORT': li.slip_id.contract_id.transport_allowance_bool,
                                'SCHOOL': li.slip_id.contract_id.school_allowance_bool,
                                'FOOD': li.slip_id.contract_id.food_allowance_bool,
                                'FUEL': li.slip_id.contract_id.fuel_allowance_bool,
                                'TICKET': li.slip_id.contract_id.ticket_allowance_bool,
                                'FIXED': li.slip_id.contract_id.fixed_allowance_bool,
                                'MEDICAL': li.slip_id.contract_id.work_allowance_bool,
                                'MOBILE': li.slip_id.contract_id.mobile_allowance_bool,
                                'OTA': li.slip_id.contract_id.housing_allowance_bool
                            }
                            if allowances.get(li.code, False):
                                li.total = li.amount
                            if li.code == 'Loan':
                                li.total = -emp_loan_amount
                                li.amount = -emp_loan_amount
                            if li.code == 'Advance':
                                li.total = -emp_advance_amount
                                li.amount = -emp_advance_amount


                        else:
                            allowances = {
                                'HRA': li.slip_id.contract_id.house_allowance_bool,
                                'TRANSPORT': li.slip_id.contract_id.transport_allowance_bool,
                                'SCHOOL': li.slip_id.contract_id.school_allowance_bool,
                                'FOOD': li.slip_id.contract_id.food_allowance_bool,
                                'FUEL': li.slip_id.contract_id.fuel_allowance_bool,
                                'TICKET': li.slip_id.contract_id.ticket_allowance_bool,
                                'FIXED': li.slip_id.contract_id.fixed_allowance_bool,
                                'MEDICAL': li.slip_id.contract_id.work_allowance_bool,
                                'MOBILE': li.slip_id.contract_id.mobile_allowance_bool,
                                'OTA': li.slip_id.contract_id.housing_allowance_bool
                            }
                            if allowances.get(li.code, False):
                                li.total = 0.00

                            if li.code in ['GOSI_COMP', 'GOSI']:
                                li.total = 0.0
                            if li.code == 'Loan':
                                li.total = 0.00
                            if li.code == 'Advance':
                                li.total = 0.00

                            # if li.code in ['GOSI_COMP', 'GOSI']:
                            #     li.total = li.amount



                ## Already working code
                # elif li.slip_id.leave_vacation_payslip_bool:
                #     loan_added_payslips = self.env['hr.employee.loan.ps'].search([
                #         ('employee_id', '=', li.slip_id.employee_id.id)
                #     ])
                #     emp_loan_amount = 0.00
                #     emp_advance_amount = 0.00
                #
                #     for emp_loan in loan_added_payslips.hr_employee_loan_line_ps:
                #         if emp_loan and emp_loan.installment_date:
                #             if (emp_loan.installment_date.year == li.slip_id.date_from.year and
                #                     emp_loan.installment_date.month == li.slip_id.date_from.month) and (emp_loan.confirm == True) and (emp_loan.state in ['notdeducted', 'deducted']):
                #                 emp_loan_amount = emp_loan.amount
                #
                #     advance_added_payslips = self.env['hr.employee.advance.ps'].search([
                #         ('employee_id', '=', li.slip_id.employee_id.id)
                #     ])
                #     for emp_advance in advance_added_payslips.hr_employee_advance_line_ps:
                #         if emp_advance and emp_advance.installment_date:
                #             if (emp_advance.installment_date.year == li.slip_id.date_from.year and
                #                     emp_advance.installment_date.month == li.slip_id.date_from.month) and (emp_advance.confirm == True) and (emp_advance.state in ['notdeducted', 'deducted']):
                #                 emp_advance_amount = emp_advance.amount
                #
                #     if li.slip_id.contract_id:
                #         allowances = {
                #             'HRA': li.slip_id.contract_id.house_allowance_bool,
                #             'TRANSPORT': li.slip_id.contract_id.transport_allowance_bool,
                #             'SCHOOL': li.slip_id.contract_id.school_allowance_bool,
                #             'FOOD': li.slip_id.contract_id.food_allowance_bool,
                #             'FUEL': li.slip_id.contract_id.fuel_allowance_bool,
                #             'TICKET': li.slip_id.contract_id.ticket_allowance_bool,
                #             'FIXED': li.slip_id.contract_id.fixed_allowance_bool,
                #             'MEDICAL': li.slip_id.contract_id.work_allowance_bool,
                #             'MOBILE': li.slip_id.contract_id.mobile_allowance_bool,
                #             'OTA': li.slip_id.contract_id.housing_allowance_bool,
                #             'GOSI_COMP': True,
                #             'GOSI': True,
                #             # 'Loan': True,
                #             # 'Advance': True
                #         }
                #         li.total = li.amount if allowances.get(li.code, False) else 0.00
                #         if li.code == 'Loan':
                #             li.total = -emp_loan_amount
                #             li.amount = -emp_loan_amount
                #         if li.code == 'Advance':
                #             li.total = -emp_advance_amount
                #             li.amount = -emp_advance_amount

                # Process the payslip line based on leave and arrival conditions

                if li.slip_id.leave_vacation_payslip_bool and li.slip_id.same_month_vacation:
                    print("1111111111111111111111111111")

                    emp_loan_amount = 0.00
                    emp_advance_amount = 0.00

                    # Search for loans for the employee
                    loan_added_payslips = self.env['hr.employee.loan.ps'].search([
                        ('employee_id', '=', li.slip_id.employee_id.id)
                    ])
                    # Calculate loan amount for the current month
                    for emp_loan in loan_added_payslips.hr_employee_loan_line_ps:
                        if emp_loan and emp_loan.installment_date:
                            if (emp_loan.installment_date.year == li.slip_id.date_from.year and
                                    emp_loan.installment_date.month == li.slip_id.date_from.month and
                                    emp_loan.confirm and emp_loan.state in ['notdeducted', 'deducted']):
                                emp_loan_amount = emp_loan.amount

                    # Search for advances for the employee
                    advance_added_payslips = self.env['hr.employee.advance.ps'].search([
                        ('employee_id', '=', li.slip_id.employee_id.id)
                    ])
                    # Calculate advance amount for the current month
                    for emp_advance in advance_added_payslips.hr_employee_advance_line_ps:
                        if emp_advance and emp_advance.installment_date:
                            if (emp_advance.installment_date.year == li.slip_id.date_from.year and
                                    emp_advance.installment_date.month == li.slip_id.date_from.month and
                                    emp_advance.confirm and emp_advance.state in ['notdeducted', 'deducted']):
                                emp_advance_amount = emp_advance.amount

                    paid_leave = 0.00
                    unpaid_leave = 0.00
                    leave_days = 0.00

                    leave_allocation = self.env['hr.leave'].search([
                        ('request_date_from', '>=', li.slip_id.date_from),
                        ('request_date_to', '<=', li.slip_id.date_to),
                        ('employee_id', '=', li.slip_id.employee_id.id),
                        ('state', '=', 'validate')
                    ])

                    # Summing up paid and unpaid leave days
                    leave_days = 0.00
                    arrival_leave_days = 0.00
                    leave_days_return = 0.00
                    for leave in leave_allocation:
                        arrival_leave_days += leave.number_of_days_display
                        if leave.actual_return_date:
                            leave_days_return = (leave.actual_return_date - leave.request_date_from).days
                        # paid_leave += leave.paid_leave
                        # unpaid_leave += leave.unpaid_leave
                            leave_days += leave_days_return
                            print("leave_days ifff ", leave_days, leave.id)
                        else:
                            leave_days = arrival_leave_days
                            print("leave_days else", leave_days)

                    # leave_days = paid_leave + unpaid_leave
                    # leave_days = leave_days

                    days = 0
                    num_days = 30

                    # Calculate the number of actual days in the payroll period
                    if li.slip_id.date_from and li.slip_id.date_to:
                        days = num_days - leave_days
                        ### Newly added on 08/10/2024
                        leave_records = self.env['hr.leave'].search(
                            [('request_date_from', '>=', line.slip_id.date_from),
                             ('request_date_to', '<=', line.slip_id.date_to),
                             ('employee_id', '=', line.slip_id.employee_id.id),
                             ('state', '=', 'validate'),
                             ('holiday_status_id.code', '!=', 'AV')]).mapped(
                            'unpaid_leave')

                        num_of_leave_days = sum(leave_records) if leave_records else 0.00
                        days = days - num_of_leave_days
                        ############################
                        print(f"days: {days}, leave_days: {leave_days}")

                    if li.slip_id.contract_id:
                        allowances = {
                            'HRA': li.slip_id.contract_id.house_allowance_bool,
                            'TRANSPORT': li.slip_id.contract_id.transport_allowance_bool,
                            'SCHOOL': li.slip_id.contract_id.school_allowance_bool,
                            'FOOD': li.slip_id.contract_id.food_allowance_bool,
                            'FUEL': li.slip_id.contract_id.fuel_allowance_bool,
                            'TICKET': li.slip_id.contract_id.ticket_allowance_bool,
                            'FIXED': li.slip_id.contract_id.fixed_allowance_bool,
                            'MEDICAL': li.slip_id.contract_id.work_allowance_bool,
                            'MOBILE': li.slip_id.contract_id.mobile_allowance_bool,
                            'OTA': li.slip_id.contract_id.housing_allowance_bool,
                            'GOSI_COMP': True,
                            'GOSI': True,
                        }

                        # Check if the line code is not an allowance
                        if li.code not in allowances or not allowances[li.code]:
                            total_amount = float(li.quantity) * ((li.amount / num_days) * days)
                            li.total = total_amount

                        # Adjust totals for Loan and Advance
                        if li.code == 'Loan':
                            li.total = -emp_loan_amount
                            li.amount = -emp_loan_amount
                        elif li.code == 'Advance':
                            li.total = -emp_advance_amount
                            li.amount = -emp_advance_amount


                elif li.slip_id.leave_vacation_payslip_bool:
                    print("2222222222222222222222222222222")
                    # print(f"Processing payslip for employee {li.slip_id.employee_id.name}")
                    # Initialize loan and advance amounts
                    emp_loan_amount = 0.00
                    emp_advance_amount = 0.00
                    # Search for loans for the employee
                    loan_added_payslips = self.env['hr.employee.loan.ps'].search([
                        ('employee_id', '=', li.slip_id.employee_id.id)
                    ])
                    # Calculate loan amount for the current month
                    for emp_loan in loan_added_payslips.hr_employee_loan_line_ps:
                        if emp_loan and emp_loan.installment_date:
                            if (emp_loan.installment_date.year == li.slip_id.date_from.year and
                                    emp_loan.installment_date.month == li.slip_id.date_from.month and
                                    emp_loan.confirm and emp_loan.state in ['notdeducted', 'deducted']):
                                emp_loan_amount = emp_loan.amount

                    # Search for advances for the employee
                    advance_added_payslips = self.env['hr.employee.advance.ps'].search([
                        ('employee_id', '=', li.slip_id.employee_id.id)
                    ])
                    # Calculate advance amount for the current month
                    for emp_advance in advance_added_payslips.hr_employee_advance_line_ps:
                        if emp_advance and emp_advance.installment_date:
                            if (emp_advance.installment_date.year == li.slip_id.date_from.year and
                                    emp_advance.installment_date.month == li.slip_id.date_from.month and
                                    emp_advance.confirm and emp_advance.state in ['notdeducted', 'deducted']):
                                emp_advance_amount = emp_advance.amount

                    # Set allowances based on the employee's contract
                    if li.slip_id.contract_id:
                        allowances = {
                            'HRA': li.slip_id.contract_id.house_allowance_bool,
                            'TRANSPORT': li.slip_id.contract_id.transport_allowance_bool,
                            'SCHOOL': li.slip_id.contract_id.school_allowance_bool,
                            'FOOD': li.slip_id.contract_id.food_allowance_bool,
                            'FUEL': li.slip_id.contract_id.fuel_allowance_bool,
                            'TICKET': li.slip_id.contract_id.ticket_allowance_bool,
                            'FIXED': li.slip_id.contract_id.fixed_allowance_bool,
                            'MEDICAL': li.slip_id.contract_id.work_allowance_bool,
                            'MOBILE': li.slip_id.contract_id.mobile_allowance_bool,
                            'OTA': li.slip_id.contract_id.housing_allowance_bool,
                            'GOSI_COMP': True,
                            'GOSI': True,
                        }

                        # Set total based on allowances
                        li.total = li.amount if allowances.get(li.code, False) else 0.00
                        # Adjust totals for Loan and Advance
                        if li.code == 'Loan':
                            li.total = -emp_loan_amount
                            li.amount = -emp_loan_amount
                        elif li.code == 'Advance':
                            li.total = -emp_advance_amount
                            li.amount = -emp_advance_amount

                    # Handle actual arrival date logic
                    if li.slip_id.actual_arrival_date:
                        print("33333333333333333333333333333333")
                        days = 0
                        num_days = 0
                        total_amount = 0
                        # Calculate the number of days in the payroll period
                        if li.slip_id.date_from and li.slip_id.date_to:
                            date_from = fields.Date.to_date(li.slip_id.date_from)
                            date_to = fields.Date.to_date(li.slip_id.date_to)
                            actual_arrival_date = fields.Date.to_date(li.slip_id.actual_arrival_date)
                            date_to_30_days = date_from + timedelta(days=29)
                            days = (date_to_30_days - actual_arrival_date).days + 1


                            # Calculate actual days between the two dates
                            # days = (date_to - actual_arrival_date).days + 1
                            # days =  30 - (actual_arrival_date).days + 1
                            ### Newly added on 08/10/2024
                            leave_records = self.env['hr.leave'].search(
                                [('request_date_from', '>=', line.slip_id.date_from),
                                 ('request_date_to', '<=', line.slip_id.date_to),
                                 ('employee_id', '=', line.slip_id.employee_id.id),
                                 ('state', '=', 'validate'),
                                 ('holiday_status_id.code', '!=', 'AV')]).mapped(
                                'unpaid_leave')

                            num_of_leave_days = sum(leave_records) if leave_records else 0.00
                            days = days - num_of_leave_days
                            ###############################

                            print("days", days)
                            num_days = 30

                        # Calculate total amount for payslip line
                        if li.slip_id.contract_id:
                            allowances = {
                                'HRA': li.slip_id.contract_id.house_allowance_bool,
                                'TRANSPORT': li.slip_id.contract_id.transport_allowance_bool,
                                'SCHOOL': li.slip_id.contract_id.school_allowance_bool,
                                'FOOD': li.slip_id.contract_id.food_allowance_bool,
                                'FUEL': li.slip_id.contract_id.fuel_allowance_bool,
                                'TICKET': li.slip_id.contract_id.ticket_allowance_bool,
                                'FIXED': li.slip_id.contract_id.fixed_allowance_bool,
                                'MEDICAL': li.slip_id.contract_id.work_allowance_bool,
                                'MOBILE': li.slip_id.contract_id.mobile_allowance_bool,
                                'OTA': li.slip_id.contract_id.housing_allowance_bool,
                                'GOSI_COMP': True,
                                'GOSI': True,
                            }

                            # Check if the line code is not an allowance
                            if li.code not in allowances or not allowances[li.code]:
                                total_amount = float(li.quantity) * ((li.amount / num_days) * days)
                                li.total = total_amount

                            # Adjust totals for Loan and Advance
                            if li.code == 'Loan':
                                li.total = -emp_loan_amount
                                li.amount = -emp_loan_amount
                            elif li.code == 'Advance':
                                li.total = -emp_advance_amount
                                li.amount = -emp_advance_amount

            if li.slip_id.payroll_type == 'termination' and li.slip_id.contract_id:
                allowances = {
                    'HRA': li.slip_id.contract_id.house_allowance_bool,
                    'TRANSPORT': li.slip_id.contract_id.transport_allowance_bool,
                    'SCHOOL': li.slip_id.contract_id.school_allowance_bool,
                    'FOOD': li.slip_id.contract_id.food_allowance_bool,
                    'FUEL': li.slip_id.contract_id.fuel_allowance_bool,
                    'TICKET': li.slip_id.contract_id.ticket_allowance_bool,
                    'FIXED': li.slip_id.contract_id.fixed_allowance_bool,
                    'MEDICAL': li.slip_id.contract_id.work_allowance_bool,
                    'MOBILE': li.slip_id.contract_id.mobile_allowance_bool,
                    'OTA': li.slip_id.contract_id.housing_allowance_bool
                }
                if allowances.get(li.code, False):
                    li.total = li.amount
                if li.code in ['Loan', 'Advance']:
                    li.total = 0.00

            # Handling additional allowances
            allowance_amount = self.env['salary.allowance.detection'].search([
                ('employee_contract_id', '=', li.slip_id.contract_id.id),
                ('type', '=', 'transaction_allowance'),
                ('code', '=', li.code),
                # ('date', '>=', li.slip_id.date_from),
                # ('date', '>=', li.slip_id.date_to),
                ('state', '=', 'approve')
            ])
            if allowance_amount:
                # if allowance_amount.date.month == li.slip_id.date_from.month and allowance_amount.date.year == li.slip_id.date_from.year:
                    # print("allowance_amount 111111111111111111", allowance_amount,allowance_amount.date.month, li.slip_id.date_from.month )
                filtered_allowances = allowance_amount.filtered(
                    lambda allowance: allowance.date.month == li.slip_id.date_from.month
                                      and allowance.date.year == li.slip_id.date_from.year
                )
                temp_total_addition_amount = sum(allowance.amount for allowance in filtered_allowances)
                if temp_total_addition_amount:
                    # li.amount = temp_total_addition_amount
                    li.total = temp_total_addition_amount
                # for li in line.slip_id.input_line_ids.filtered(lambda li: li.code == line.code):
                #     li.amount = temp_total_addition_amount

            # Handling deductions
            deduction_amount = self.env['salary.allowance.detection'].search([
                ('employee_contract_id', '=', li.slip_id.contract_id.id),
                ('type', '=', 'transaction_detection'),
                ('code', '=', li.code),
                # ('date', '>=', li.slip_id.date_from),
                # ('date', '<=', li.slip_id.date_to),
                ('state', '=', 'approve')
            ])

            if deduction_amount:
                filtered_deduction = deduction_amount.filtered(
                    lambda deduction: deduction.date.month == li.slip_id.date_from.month
                                      and deduction.date.year == li.slip_id.date_from.year
                )
                # if deduction_amount.date.month == li.slip_id.date_from.month and deduction_amount.date.year == li.slip_id.date_from.year:
                    # print("allowance_amount 111111111111111111", allowance_amount,allowance_amount.date.month, li.slip_id.date_from.month )

                temp_total_deduction_amount = sum(deduction.amount for deduction in filtered_deduction)
                if temp_total_deduction_amount:
                    # li.amount = -temp_total_deduction_amount
                    li.total = -temp_total_deduction_amount
                    # for dec in line.slip_id.input_line_ids.filtered(lambda dec: dec.code == line.code):
                    #     dec.amount = temp_total_deduction_amount

            # if li.category_id.code in ["BASIC", "ALW"] and li.code not in ['ACL', 'OVT']:
            if li.category_id.code in ["BASIC", "ALW"]:
                total_amount = li.total
                basic_alw += total_amount

            if li.category_id.code == "DED":
                total_amount = li.total
                total_ded += total_amount

        gro_total = basic_alw + alw_total

        ded_total = basic_alw + alw_total + total_ded
        total_deduction = total_ded

        # Assign the calculated GROSS amount
        for li in self.slip_id.line_ids:
            if li.code == "GROSS":
                li.total = gro_total
            if li.code == "NET":
                li.total = ded_total
                # print("li.total", li.code,li.total)
            if li.code == "TOTAL_DED":
                li.total = total_deduction



    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if 'employee_id' not in values or 'contract_id' not in values:
                payslip = self.env['hr.payslip'].browse(values.get('slip_id'))
                values['employee_id'] = values.get('employee_id') or payslip.employee_id.id
                values['contract_id'] = values.get('contract_id') or payslip.contract_id and payslip.contract_id.id
                if not values['contract_id']:
                    raise UserError(_('You must set a contract to create a payslip line.'))
        return super(HrPayslipLine, self).create(vals_list)


class HrPayslipWorkedDays(models.Model):
    _name = 'hr.payslip.worked_days'
    _description = 'Payslip Worked Days'
    _order = 'payslip_id, sequence'

    name = fields.Char(string='Description', required=True)
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(required=True, help="The code that can be used in the salary rules")
    number_of_days = fields.Float(string='Number of Days')
    number_of_hours = fields.Float(string='Number of Hours')
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True,
        help="The contract for which applied this input")


class HrPayslipInput(models.Model):
    _name = 'hr.payslip.input'
    _description = 'Payslip Input'
    _order = 'payslip_id, sequence'

    name = fields.Char(string='Description')
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(required=True, help="The code that can be used in the salary rules")
    amount = fields.Float(help="It is used in computation. For e.g. A rule for sales having "
                               "1% commission of basic salary for per product can defined in expression "
                               "like result = inputs.SALEURO.amount * contract.wage*0.01.")
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True,
        help="The contract for which applied this input")
    date = fields.Date(string='Date', readonly=True)
    reference = fields.Char(string='Reference', readonly=True)
    units = fields.Char(string='Units', readonly=True)




class HrPayslipRun(models.Model):
    _name = 'hr.payslip.run'
    _description = 'Payslip Batches'

    name = fields.Char(required=True)
    slip_ids = fields.One2many('hr.payslip', 'payslip_run_id', string='Payslips', readonly=True, compute='_compute_slip_ids', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('close', 'Close'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')
    date_start = fields.Date(string='Date From', required=True, default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_end = fields.Date(string='Date To', required=True,
                           default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    credit_note = fields.Boolean(string='Credit Note',
                                 help="If its checked, indicates that all payslips generated from here are refund payslips.")

    # @api.constrains('date_start', 'date_end')
    # def _check_previous_month_payslip(self):
    #     for rec in self:
    #         # Get the first day of the previous month
    #         current_month_start = date.today().replace(day=1)
    #         previous_month_start = (current_month_start - relativedelta(months=1)).replace(day=1)
    #         previous_month_end = current_month_start - relativedelta(days=1)
    #
    #         # Check for the payslip batch of the previous month
    #         previous_month_payslip_run = self.env['hr.payslip.run'].search([
    #             ('date_start', '=', previous_month_start),
    #             ('date_end', '=', previous_month_end)
    #         ], limit=1)
    #
    #         if previous_month_payslip_run and previous_month_payslip_run.state == 'draft':
    #             # If the previous month's payslip batch is still in draft, raise a validation error
    #             raise ValidationError(
    #                 _('You cannot create the current month\'s payslip because the previous month\'s payslip batch is still in draft state. '
    #                   'Please finalize the previous month\'s payslip batch first.')
    #             )

    # @api.model
    # def create(self, vals):
    #     # Get the first day and last day of the current month
    #     current_month_start = date.today().replace(day=1)
    #     current_month_end = (current_month_start + relativedelta(months=1, days=-1))
    #
    #     # Check if the provided date range falls within the current month
    #     if vals.get('date_start') and vals.get('date_end'):
    #         date_start = fields.Date.from_string(vals['date_start'])
    #         date_end = fields.Date.from_string(vals['date_end'])
    #
    #         # Check if the date range is within the current month
    #         if date_start < current_month_start or date_end > current_month_end:
    #             raise ValidationError(
    #                 _('You can only create a payslip batch for the current month. '
    #                   'Please ensure the dates are within the current month.')
    #             )
    #
    #         # Check if a payslip batch already exists for the same or overlapping date range
    #         overlapping_payslip_run = self.env['hr.payslip.run'].search([
    #             ('date_start', '<=', date_end),
    #             ('date_end', '>=', date_start)
    #         ], limit=1)
    #
    #         if overlapping_payslip_run:
    #             raise ValidationError(
    #                 _('A payslip batch already exists for the selected date range: '
    #                   '%s to %s.') % (overlapping_payslip_run.date_start, overlapping_payslip_run.date_end)
    #             )
    #
    #     # Proceed with creating the current month's payslip batch
    #     return super(HrPayslipRun, self).create(vals)

    # @api.onchange('date_start', 'date_end')
    # def _onchange_date_range(self):
    #     if self.date_start and self.date_end:
    #         start_date = self.date_start.replace(day=1)
    #         end_date = datetime(self.date_end.year, self.date_end.month + 1, 1) - timedelta(days=1)
    #
    #         payslips = self.env['hr.payslip'].search([
    #             ('date_from', '>=', start_date),
    #             ('date_to', '<=', end_date),
    #             ('state', 'in', ['verify', 'draft']),
    #             ('payroll_type', '=', 'leave')
    #         ])
    #         print("payslips", payslips)
    #
    #         if payslips:
    #             self.slip_ids = [(6, 0, payslips.ids)]
    #         else:
    #             self.slip_ids = [(5, 0, 0)]

    ## Newly added on already created vacation payslip is update in Payslips Batches -- created on 19/09/2024
    # @api.depends('date_start', 'date_end')
    # def _compute_slip_ids(self):
    #     for record in self:
    #         if record.date_start and record.date_end:
    #             # Ensure start_date is the first day of the start month
    #             start_date = record.date_start.replace(day=1)
    #             # Calculate end_date to be the last day of the end month
    #             next_month = record.date_end.replace(day=28) + timedelta(days=4)
    #             end_date = next_month - timedelta(days=next_month.day)
    #
    #             payslips = self.env['hr.payslip'].search([
    #                 ('date_from', '>=', start_date),
    #                 ('date_to', '<=', end_date),
    #                 ('state', 'in', ['verify', 'draft', 'done']),
    #                 ('payroll_type', 'in', ['leave', 'arrivel'])
    #             ])
    #
    #             if payslips:
    #                 record.slip_ids = [(6, 0, payslips.ids)]
    #             else:
    #                 record.slip_ids = [(5, 0, 0)]
    #         else:
    #             record.slip_ids = [(5, 0, 0)]

    @api.depends('date_start', 'date_end')
    def _compute_slip_ids(self):
        for record in self:
            if record.date_start and record.date_end:
                # Ensure start_date is the first day of the start month
                start_date = record.date_start.replace(day=1)
                # Calculate end_date to be the last day of the end month
                next_month = record.date_end.replace(day=28) + timedelta(days=4)
                end_date = next_month - timedelta(days=next_month.day)

                # Search for payslips with 'verify', 'draft', 'done' state and payroll type 'leave' or 'arrival'
                payslips = self.env['hr.payslip'].search([
                    ('date_from', '>=', start_date),
                    ('date_to', '<=', end_date),
                    ('state', 'in', ['verify', 'draft', 'done']),
                    ('payroll_type', 'in', ['leave', 'arrival'])
                ])

                # Also fetch payslips that are in the 'done' state separately
                done_payslips = self.env['hr.payslip'].search([
                    ('date_from', '>=', start_date),
                    ('date_to', '<=', end_date),
                    ('state', '=', 'done'),
                ])

                # Combine the ids of both sets of payslips
                all_payslips = payslips | done_payslips
                print("all_payslips", all_payslips)

                if all_payslips:
                    record.slip_ids = [(6, 0, all_payslips.ids)]
                else:
                    record.slip_ids = [(5, 0, 0)]
            else:
                record.slip_ids = [(5, 0, 0)]

    def draft_payslip_run(self):
        return self.write({'state': 'draft'})

    def close_payslip_run(self):
        return self.write({'state': 'close'})

    def done_payslip_run(self):
        for line in self.slip_ids:
            line.action_payslip_done()
        return self.write({'state': 'done'})

    def unlink(self):
        # self.mapped('slip_ids').unlink()
        for rec in self:
            if rec.state == 'draft':
                rec.mapped('slip_ids').unlink()
            if rec.state == 'done':
                raise ValidationError(_('You Cannot Delete Done Pay-slips Batches'))
        return super(HrPayslipRun, self).unlink()
