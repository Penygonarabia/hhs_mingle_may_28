# -*- coding:utf-8 -*-

from odoo import api, fields, models, tools, _
import logging
import pytz

from collections import namedtuple, defaultdict
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, time, date
from pytz import timezone, UTC
from odoo.addons.base.models.res_partner import _tz_get
# from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare, format_date
from odoo.tools.float_utils import float_round
from odoo.tools.translate import _
from odoo.osv import expression
import calendar
_logger = logging.getLogger(__name__)
from odoo.addons.resource.models.utils import float_to_time, HOURS_PER_DAY


class LeaveReport(models.Model):
    _inherit = "hr.leave.report"

    leave_type = fields.Selection([
        ('allocation', 'Allocation'),
        ('request', 'Leave')
    ], string='Request Type', readonly=True)

    @api.model
    def action_time_off_analysis(self):
        domain = [('holiday_type', '=', 'employee')]

        # if self.env.context.get('active_ids'):
        #     domain = expression.AND([
        #         domain,
        #         [('employee_id', 'in', self.env.context.get('active_ids', []))]
        #     ])


        if self.env.user.has_group('hr_saudi.group_sys_manager'):
            # Admin can view all employees, no need to modify the domain
            if self.env.context.get('active_ids'):
                domain = expression.AND([
                    domain,
                    [('employee_id', 'in', self.env.context.get('active_ids', []))]
                ])
        if self.env.user.has_group('hr_saudi.group_normal_employee'):
            # For non-admin users, restrict to their own employee record
            domain = expression.AND([
                domain,
                [('employee_id', '=', self.env.user.employee_id.id)]
            ])

        return {
            'name': _('Leave Analysis'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.report',
            'view_mode': 'tree,pivot,form',
            'search_view_id': [self.env.ref('hr_holidays.view_hr_holidays_filter_report').id],
            'domain': domain,
            'context': {
                'search_default_group_type': True,
                'search_default_year': True,
                'search_default_validated': True,
                'search_default_active_employee': True,
            }
        }


class LeaveType(models.Model):
    _inherit = 'hr.leave.type'

    code = fields.Char(string='Code')
    name = fields.Char('Leave Type', required=True, translate=True)

    leave_validation_type = fields.Selection([
        ('no_validation', 'No Validation'),
        ('hr', 'By Leave Officer'),
        ('manager', "By Employee's Approver"),
        ('both', "By Employee's Approver and Leave Officer")], default='hr', string='Leave Validation')

    allocation_validation_type = fields.Selection([
        ('no', 'No validation needed'),
        ('officer', 'Approved by Leave Officer'),
        ('set', "Set by Leave Officer")], default='officer', string='Approval')

    time_type = fields.Selection([('leave', 'Leave'), ('other', 'Other')], default='leave', string="Kind of Leave",
                                 help="Whether this should be computed as a holiday or as work time (eg: formation)")

    leave_notif_subtype_id = fields.Many2one('mail.message.subtype', string='Leave Notification Subtype', default=lambda self: self.env.ref('hr_holidays.mt_leave', raise_if_not_found=False))

    request_unit = fields.Selection([
        ('day', 'Day'),
        ('half_day', 'Half Day'),
        ('hour', 'Hours')], default='day', string='Take Leave in', required=True)

    responsible_id = fields.Many2one(
        'res.users', 'Responsible Leave Officer',
        domain=lambda self: [('groups_id', 'in', self.env.ref('hr_holidays.group_hr_holidays_user').id)],
        help="Choose the Time Off Officer who will be notified to approve allocation or Time Off request")

    virtual_remaining_leaves = fields.Float(
        compute='_compute_leaves', search='_search_virtual_remaining_leaves', string='Virtual Remaining Leave',
        help='Maximum Leave Allowed - Leave Already Taken - Leave Waiting Approval')
    virtual_leaves_taken = fields.Float(
        compute='_compute_leaves', string='Virtual Leave Already Taken',
        help='Sum of validated and non validated Leave requests.')


class AccrualPlan(models.Model):
    _inherit = "hr.leave.accrual.plan"
    _description = "Accrual Plan"

    time_off_type_id = fields.Many2one('hr.leave.type', string="Leave Type",
        help="""Specify if this accrual plan can only be used with this Time Off Type.
                Leave empty if this accrual plan can be used with any Time Off Type.""")

    # time_off_type_id = fields.Many2one('hr.leave.type', string='Leave Type',
    #                                    domain=lambda self: self._get_time_off_domain())

    # @api.model
    # def _get_time_off_domain(self):
    #     if self.env.user.has_group('base.group_multi_company'):
    #         return ['|', ('company_id', '=', False), ('company_id', '=', self.env.user.company_id.id)]
    #     return [('company_id', '=', False)]




class Leave(models.Model):

    _inherit = "hr.leave"
    _description = "Leave"

    holiday_status_id = fields.Many2one(
        "hr.leave.type", compute='_compute_from_employee_id', store=True, string="Leave Type", required=True,
        readonly=False)

    vacation_entitle = fields.Float(
        # string="Vacation Entitlement",
        string="Leave  Entitlement",
        required=False,
        readonly=True,
    )

    paid_leave = fields.Float(
        string="Paid Leave",
        required=False,
        readonly=True,
    )

    unpaid_leave = fields.Float(
        string="Unpaid Leave",
        required=False,
        readonly=True,
    )
    national_holiday = fields.Float(
        string="National Holiday",
        required=False,
        readonly=True,
    )
    # vacation_utilised = fields.Float(
    #     string="Vacation Utilised",
    #     required=False,
    #     readonly=True,
    # )
    vacation_utilised = fields.Float(
        # string="Vacation Utilised",
        string="Leave Utilised",
        required=False,
        readonly=True,
    )

    # Boolean field to control visibility
    show_leave_fields = fields.Boolean(
        string="Show Leave Fields",
        compute='_compute_show_leave_fields'
    )

    actual_return_date = fields.Date(
        string="Actual Return Date",
        readonly=True,

    )
    
    date_from = fields.Datetime(
        'Leave Date From', compute='_compute_date_from_to', store=True, readonly=False, index=True, copy=False, required=True, tracking=True)
    date_to = fields.Datetime(
        'Expected Return Date', compute='_compute_date_from_to', store=True, readonly=False, copy=False, required=True, tracking=True)

    employee_number = fields.Char(string='Employee No', store=True)

    @api.onchange('employee_ids')
    def _onchange_employe(self):
        for rec in self:
            rec.employee_number = False
            if rec.employee_ids:
                rec.employee_number = rec.employee_ids.employee_no

    # @api.constrains('date_from', 'date_to', 'employee_id')
    # def _check_date(self):
    #     if self.env.context.get('leave_skip_date_check', False):
    #         return
    #     for holiday in self.filtered('employee_id'):
    #         print("holiday", holiday.employee_id.name, holiday.request_date_from, holiday.request_date_to)
    #         holiday_date_from = holiday.date_to + timedelta(days=1)
    #         # domain = [
    #         #     ('date_from', '<', holiday.date_to),
    #         #     ('actual_return_date', '>', holiday_date_from),
    #         #     ('employee_id', '=', holiday.employee_id.id),
    #         #     ('id', '!=', holiday.id),
    #         #     ('state', 'not in', ['cancel', 'refuse']),
    #         # ]
    #
    #         domain = [
    #             ('date_from', '<', holiday.date_to),
    #             ('actual_return_date', '>', holiday_date_from),
    #             ('employee_id', '=', holiday.employee_id.id),
    #             ('id', '!=', holiday.id),
    #             ('state', 'not in', ['cancel', 'refuse']),
    #         ]
    #         nholidays = self.search_count(domain)
    #         if nholidays:
    #             raise ValidationError(
    #                 _('You can not set 2 time off that overlaps on the same day for the same employee.') + '\n- %s' % (
    #                     holiday.display_name))

    def _check_validity(self):
        pass
        # sorted_leaves = defaultdict(lambda: self.env['hr.leave'])
        # for leave in self:
        #     sorted_leaves[(leave.holiday_status_id, leave.date_from.date())] |= leave
        # for (leave_type, date_from), leaves in sorted_leaves.items():
        #     if leave_type.requires_allocation == 'no':
        #         continue
        #     employees = self.env['hr.employee']
        #     for leave in leaves:
        #         employees |= leave._get_employees_from_holiday_type()
        #     leave_data = leave_type.get_allocation_data(employees, date_from)
            # if leave_type.allows_negative:
            #     max_excess = leave_type.max_allowed_negative
            #     for employee in employees:
            #         if leave_data[employee] and leave_data[employee][0][1]['virtual_remaining_leaves'] < -max_excess:
            #             raise ValidationError(_("There is no valid allocation to cover that request."))
            #     continue

            # previous_leave_data = leave_type.with_context(
            #     ignored_leave_ids=leaves.ids
            # ).get_allocation_data(employees, date_from)
            # for employee in employees:
            #     previous_emp_data = previous_leave_data[employee] and previous_leave_data[employee][0][1][
            #         'virtual_excess_data']
            #     emp_data = leave_data[employee] and leave_data[employee][0][1]['virtual_excess_data']
            #     if not previous_emp_data and not emp_data:
            #         continue
            #     if previous_emp_data != emp_data and len(emp_data) >= len(previous_emp_data):
            #         raise ValidationError(_("There is no valid allocation to cover that request."))

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_date(self):
        # Skip the check if context has 'leave_skip_date_check'
        if self.env.context.get('leave_skip_date_check', False):
            return

        for holiday in self.filtered('employee_id'):
            # Add one day to holiday date_to for comparison
            # holiday_date_from = holiday.date_from.date() + timedelta(days=1)

            # Define domain for checking overlapping leaves with the same employee
            domain = [
                ('date_from', '<', holiday.date_to),  # Conflicting if any leave starts before this leave ends
                ('employee_id', '=', holiday.employee_id.id),  # Same employee
                ('id', '!=', holiday.id),  # Exclude current record
                ('state', 'not in', ['cancel', 'refuse']),  # Only validate relevant states
            ]

            # Search for records that match the domain criteria
            conflicting_holidays = self.search(domain)

            # Check for missing actual_return_date in conflicting records
            missing_return_date = conflicting_holidays.filtered(lambda leave: not leave.actual_return_date)

            # If any conflicting record does not have actual_return_date set
            if missing_return_date:
                missing_ids = ', '.join([str(leave.id) for leave in missing_return_date])
                conflict_employee_name = holiday.employee_id.name

                raise ValidationError(
                    _('The following leave records are missing the actual return date for the employee.') +
                    '\nEmployee: %s\nRecord IDs Missing Actual Return Date: %s' % (conflict_employee_name, missing_ids)
                )

            if conflicting_holidays:
                overlapping_holidays = conflicting_holidays.filtered(
                    lambda leave: leave.actual_return_date > holiday.date_from.date())

                # If there are any conflicting holidays that overlap based on the actual_return_date check
                if overlapping_holidays:
                    conflict_ids = ', '.join([str(leave.id) for leave in overlapping_holidays])
                    conflict_employee_name = holiday.employee_id.name

                    raise ValidationError(
                        _('You cannot set two leave that overlap for the same employee.') +
                        '\nEmployee: %s\nConflicting Record IDs: %s' % (conflict_employee_name, conflict_ids)
                    )

            # If there are any other conflicting holidays with overlapping dates
            # if conflicting_holidays:
            #     conflict_ids = ', '.join([str(leave.id) for leave in conflicting_holidays])
            #     conflict_employee_name = holiday.employee_id.name
            #
            #     raise ValidationError(
            #         _('You cannot set two time offs that overlap for the same employee.') +
            #         '\nEmployee: %s\nConflicting Record IDs: %s' % (conflict_employee_name, conflict_ids)
            #     )

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(Leave, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                   submenu=submenu)
        domain = []

        if self.env.user.has_group('hr_saudi.group_sys_manager'):
            if self.env.context.get('active_ids'):
                domain = expression.AND([
                    domain,
                    [('employee_id', 'in', self.env.context.get('active_ids', []))]
                ])
                print("domainm", domain)
        if self.env.user.has_group('hr_saudi.group_normal_employee'):
            employee_id = self.env.user.sudo().employee_id.id
            domain = expression.AND([
                domain,
                [('employee_id', '=', employee_id)]
            ])

        action = self.env.ref('hr_holidays.action_hr_available_holidays_report').sudo()
        action.write({'domain': domain})

        return res

    '''Also it will also worked'''
    @api.onchange('employee_ids')
    def _onchange_employeee(self):
        for rec in self:
            leave_lst = []
            res = {}
            leave_search = self.env['hr.leave.type'].search([])
            if rec.employee_ids.is_saudi:
                leave_lst = leave_search.ids
            else:
                leave_lst = leave_search.filtered(lambda s: s.code != 'ML').ids
            res['domain'] = {'holiday_status_id': [('id', 'in', leave_lst)]}
            return res

    @api.depends('holiday_status_id')
    def _compute_show_leave_fields(self):
        for rec in self:
            rec.show_leave_fields = bool(rec.holiday_status_id)

    def send_mail_leave_automatically(self):
        self.env.ref('om_hr_payroll.mail_automatic_send_to_manager_template').send_mail(self.id,force_send=True)
        return {'effect': {'fadeout': 'slow', 'message': 'Your email is send successfully', 'type': 'rainbow_man'}}

    # @api.constrains('request_date_from', 'request_date_to')
    # def _check_leave_dates(self):
    #     for rec in self:
    #         current_date = fields.Date.context_today(rec)
    #         current_month_start = current_date.replace(day=1)
    #         if rec.request_date_from < current_month_start or rec.request_date_to < current_month_start:
    #             raise ValidationError(
    #                 _('Leave requests can only be created for the current month or future months. '
    #                   'Please select dates within the current or future months.')
    #             )

    # @api.constrains('request_date_from', 'request_date_to')
    # def _check_leave_dates(self):
    #     for rec in self:
    #         current_date = fields.Date.context_today(rec)
    #         # Get the first day of the current month
    #         current_month_start = current_date.replace(day=1)
    #         # Get the first day of the previous month
    #         previous_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    #
    #         # Search for the previous month's payslip in 'draft' state
    #         previous_month_payslip = self.env['hr.payslip'].search([
    #             ('employee_id', '=', rec.employee_id.id),
    #             ('date_from', '>=', previous_month_start),
    #             ('date_to', '<', current_month_start),
    #             ('state', '=', 'draft')
    #         ], limit=1)
    #
    #         # Apply different conditions based on the payslip state
    #         if previous_month_payslip:
    #             # Condition for current and previous month if previous month's payslip is in draft state
    #             if rec.request_date_from < previous_month_start or rec.request_date_to < previous_month_start:
    #                 raise ValidationError(
    #                     _('Leave requests can only be created for the current or previous month. '
    #                       'Please select dates within the current or previous months.')
    #                 )
    #         else:
    #             # Condition for current month only if no draft payslip for the previous month
    #             if rec.request_date_from < current_month_start or rec.request_date_to < current_month_start:
    #                 raise ValidationError(
    #                     _('Leave requests can only be created for the current month or future months. '
    #                       'Please select dates within the current or future months.')
    #                 )

    @api.onchange("holiday_status_id", 'request_date_from', 'request_date_to', 'employee_ids')
    def _onchange_vacation_entitle(self):
        for rec in self:
            if rec.holiday_status_id and rec.employee_id:
                allocation_obj = self.env['hr.leave.allocation']
                leave_obj = self.env['hr.leave']

                # Get the allocation for the employee and leave type
                allocation = allocation_obj.search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('holiday_status_id', '=', rec.holiday_status_id.id),
                    ('state', '=', 'validate'),
                    ('holiday_status_id.code', '=', 'AV')
                ]).mapped('number_of_days_display')
                total_allocation = 0.00
                if allocation:
                    if rec.request_date_from:
                        current_year = datetime.now().year
                        accrued_leave_date = rec.request_date_from
                        accrued_leave_month = accrued_leave_date.month
                        accrued_leave_year = accrued_leave_date.year
                        bfwd_previous_year = rec.employee_id.bfwd_previous_year
                        utilised_this_year = rec.employee_id.utilised_this_year
                        adjustments = rec.employee_id.adjustments

                        # Calculate the number of days in the selected month
                        month_num_of_days = calendar.monthrange(accrued_leave_year, accrued_leave_month)[1]

                        # Calculate the previous month and adjust the year if needed
                        # if accrued_leave_year == current_year:
                        if accrued_leave_month > 1:
                            previous_month = accrued_leave_month - 1
                            previous_year = accrued_leave_year
                        else:
                            previous_month = 0
                            previous_year = accrued_leave_year - 1

                        num_of_days = rec.request_date_from.day or 0.00
                        total_allocation = 0.00

                        # Search for hr.leave.accrual.plan recs
                        # accrual_plans = self.env['hr.leave.accrual.plan'].search([])
                        allocation_value = allocation_obj.search([
                            ('employee_id', '=', rec.employee_id.id),
                            ('holiday_status_id', '=', rec.holiday_status_id.id),
                            ('state', '=', 'validate'),
                            ('holiday_status_id.code', '=', 'AV')
                        ])
                        accrual_plans = self.env['hr.leave.accrual.plan'].search(
                            [('time_off_type_id.code', '=', 'AV'), ('name', '=', allocation_value.accrual_plan_id.name)])

                        for plan in accrual_plans:
                            for leave in plan.level_ids[0]:
                                # Calculate accrued_leave_num_of_days based on the number of months and leave.added_value
                                added_value = leave.added_value
                                # print("added_value", added_value)
                                # if accrued_leave_year == current_year:
                                if accrued_leave_year == current_year and accrued_leave_year > rec.employee_id.joining_date.year:
                                    accrued_leave_num_of_days = (previous_month * added_value) + (
                                            added_value * num_of_days) / month_num_of_days
                                else:
                                    accrued_leave_num_of_days = 0.00
                                    if accrued_leave_year == current_year and accrued_leave_year == rec.employee_id.joining_date.year:
                                        mid_employee_month = rec.employee_id.joining_date.month
                                        pre_month = accrued_leave_month
                                        acc_month = pre_month - mid_employee_month
                                        accrued_leave_num_of_days = (acc_month * added_value) + (
                                                added_value * num_of_days) / month_num_of_days
                                total_allocation = accrued_leave_num_of_days + bfwd_previous_year + adjustments - utilised_this_year
                                if total_allocation >= 1:
                                    total_allocation = total_allocation
                                else:
                                    total_allocation = 0.00
                                break

                    # Calculate the total validated leave days already taken
                    validated_leave_days = leave_obj.search([
                        ('employee_id', '=', rec.employee_id.id),
                        ('holiday_status_id', '=', rec.holiday_status_id.id),
                        ('state', '=', 'validate'),
                        ('holiday_status_id.code', '=', 'AV')
                    ]).mapped('number_of_days')

                    public_holiday_model = self.env['resource.calendar.leaves']
                    public_holidays = public_holiday_model.search([
                        ('resource_id', '=', False)  # Global public holidays
                    ])

                    # Loop through each public holiday and check overlap with leave dates
                    num_of_days = 0.00
                    for holiday in public_holidays:
                        # Find the overlapping range between the public holiday and leave request
                        holiday_start = max(holiday.date_from.date(), rec.request_date_from)
                        holiday_end = min(holiday.date_to.date(), rec.request_date_to)

                        # Calculate number of days of overlap if within the range
                        if holiday_start <= holiday_end:  # Only count if there's an overlap
                            num_of_days += (holiday_end - holiday_start).days + 1

                    # Add 1 extra day if needed
                    num_of_days = int(num_of_days)
                    # Update the national_holiday field in the record
                    if num_of_days > 0:
                        rec.write({'national_holiday': num_of_days})
                    else:
                        rec.write({'national_holiday': 0.00})


                    total_validated_days = sum(validated_leave_days)
                    # total_allocation = sum(allocation)
                    # total_allocation = sum(allocation)

                    # bfwd_previous_year_leave = rec.employee_id.bfwd_previous_year
                    # adjustment_leave = rec.employee_id.adjustments
                    # Subtract the validated leave days from the allocation
                    # remaining_days = round(total_allocation - total_validated_days + bfwd_previous_year_leave + adjustment_leave ,
                    #                        2) if allocation else 0.00
                    remaining_days = round(total_allocation, 2) if allocation else 0.00

                    # Set the remaining vacation entitlement
                    if remaining_days > 0:
                        rec.vacation_entitle = int(remaining_days)
                    else:
                        rec.vacation_entitle = 0.00


                    if rec.vacation_entitle < rec.number_of_days_display:
                        rec.paid_leave = round(rec.vacation_entitle + rec.national_holiday, 2)
                        # rec.unpaid_leave = round(rec.number_of_days_display - rec.vacation_entitle, 2)
                        ## working code unpaid leave
                        # rec.unpaid_leave = round(rec.number_of_days_display - rec.paid_leave, 2)
                        unpaid_leave = round(rec.number_of_days_display - rec.paid_leave, 2)
                        rec.unpaid_leave = unpaid_leave if unpaid_leave > 0 else 0.00
                        rec.vacation_utilised = round(rec.vacation_entitle, 2)

                    else:
                        rec.paid_leave = round(rec.number_of_days_display, 2)
                        rec.unpaid_leave = 0
                        rec.vacation_utilised = round(rec.paid_leave - rec.national_holiday, 2)
                        # rec.vacation_utilised = round(rec.vacation_entitle, 2)

                else:
                    if rec.holiday_status_id.code != 'AV':
                        rec.paid_leave = 0.00
                        rec.unpaid_leave = 0.00
                        rec.vacation_utilised = 0.00
                        rec.national_holiday = 0.00
                        rec.vacation_entitle = 0.00

                        validated_leave_days = leave_obj.search([
                            ('employee_id', '=', rec.employee_id.id),
                            ('holiday_status_id', '=', rec.holiday_status_id.id),
                            ('state', '=', 'validate'),
                            ('holiday_status_id.code', '!=', 'AV')
                        ])
                        leave_allocation = allocation_obj.search([
                            ('employee_id', '=', rec.employee_id.id),
                            ('holiday_status_id', '=', rec.holiday_status_id.id),
                            ('state', '=', 'validate'),
                            ('holiday_status_id.code', '!=', 'AV')
                        ])
                        allovation_total = 0.00
                        remaining_days_leave = 0.00
                        unpaid_leave = 0.00
                        paid_leave = 0.00
                        for leave_allo in leave_allocation:
                            if leave_allo.holiday_status_id.code == rec.holiday_status_id.code:
                                allovation_total = leave_allocation.number_of_days_display

                        for leave in validated_leave_days:
                            if leave.holiday_status_id.code == rec.holiday_status_id.code:
                                unpaid_leave += leave.unpaid_leave
                                paid_leave += leave.paid_leave
                        remaining_days_leave = (allovation_total - unpaid_leave - paid_leave)
                                # rec.vacation_entitle = allovation_total - leave.unpaid_leave - leave.paid_leave
                        public_holiday_model = self.env['resource.calendar.leaves']
                        public_holidays = public_holiday_model.search([
                            ('resource_id', '=', False)  # Global public holidays
                        ])

                        # Loop through each public holiday and check overlap with leave dates
                        num_of_days = 0.00
                        for holiday in public_holidays:
                            # Find the overlapping range between the public holiday and leave request
                            holiday_start = max(holiday.date_from.date(), rec.request_date_from)
                            holiday_end = min(holiday.date_to.date(), rec.request_date_to)

                            # Calculate number of days of overlap if within the range
                            if holiday_start <= holiday_end:  # Only count if there's an overlap
                                num_of_days += (holiday_end - holiday_start).days + 1

                        # Add 1 extra day if needed
                        num_of_days = num_of_days
                        # Update the national_holiday field in the record
                        if num_of_days > 0:
                            rec.write({'national_holiday': num_of_days})
                        else:
                            rec.write({'national_holiday': 0.00})

                        # total_validated_days = sum(validated_leave_days)
                        # total_allocation = sum(allocation)
                        # total_allocation = sum(allocation)

                        # bfwd_previous_year_leave = rec.employee_id.bfwd_previous_year
                        # adjustment_leave = rec.employee_id.adjustments
                        # Subtract the validated leave days from the allocation
                        # remaining_days = round(total_allocation - total_validated_days + bfwd_previous_year_leave + adjustment_leave ,
                        #                        2) if allocation else 0.00
                        remaining_days = round(remaining_days_leave, 2) if allovation_total else 0.00

                        # Set the remaining vacation entitlement
                        if remaining_days > 0:
                            rec.vacation_entitle = remaining_days
                        else:
                            rec.vacation_entitle = 0.00

                        if rec.vacation_entitle < rec.number_of_days_display:
                            rec.paid_leave = round(rec.vacation_entitle + rec.national_holiday, 2)
                            # rec.unpaid_leave = round(rec.number_of_days_display - rec.vacation_entitle, 2)
                            ## working code unpaid leave
                            # rec.unpaid_leave = round(rec.number_of_days_display - rec.paid_leave, 2)
                            unpaid_leave = round(rec.number_of_days_display - rec.paid_leave, 2)
                            rec.unpaid_leave = unpaid_leave if unpaid_leave > 0 else 0.00
                            rec.vacation_utilised = round(rec.vacation_entitle, 2)

                        else:
                            rec.paid_leave = round(rec.number_of_days_display, 2)
                            rec.unpaid_leave = 0
                            rec.vacation_utilised = round(rec.paid_leave - rec.national_holiday, 2)
                        # print("leave", leave, leave.holiday_status_id.code, leave.number_of_days)

    def action_approve(self):
        for rec in self:
            # Ensure the leave is confirmed before approval
            if any(holiday.state != 'confirm' for holiday in self):
                raise UserError(_('Leave request must be confirmed ("To Approve") in order to approve it.'))

            current_employee = self.env.user.employee_id
            self.filtered(lambda hol: hol.validation_type == 'both').write(
                {'state': 'validate1', 'first_approver_id': current_employee.id})

            # Post a second message
            for holiday in self.filtered(lambda holiday: holiday.employee_id.user_id):
                user_tz = timezone(holiday.tz)
                utc_tz = pytz.utc.localize(holiday.date_from).astimezone(user_tz)
                holiday.message_post(
                    body=_(
                        'Your %(leave_type)s planned on %(date)s has been accepted',
                        leave_type=holiday.holiday_status_id.display_name,
                        date=utc_tz.replace(tzinfo=None)
                    ),
                    partner_ids=holiday.employee_id.user_id.partner_id.ids)

            self.filtered(lambda hol: not hol.validation_type == 'both').action_validate()

            if not self.env.context.get('leave_fast_create'):
                self.activity_update()

            ## Monthly Carry for Accrued Leave in hr.leave.tpe code = 'AV'
            if rec.holiday_status_id.monthly_carry_accrued_leave:
                ## Prepare Transaction:
                if rec.holiday_status_id.prepare_payslip == True:
                    if rec.request_date_from.month == rec.request_date_to.month:
                        check_date = False
                        if rec.date_from.date().day == 1:
                            # Set check_date to the start date of the month plus 1 day
                            check_date = rec.date_from.date()
                        else:
                            # Set check_date to rec.date_from.date() - 1 day
                            check_date = rec.date_from.date() - timedelta(days=1)
                        if rec.holiday_status_id and rec.holiday_status_id.transact_code_accrd_leave:
                            payroll_transaction = self.env['salary.allowance.detection']
                            vals = {
                                'employee_id': rec.employee_ids.id,
                                'employee_number': rec.employee_ids.employee_no,
                                'department': rec.employee_ids.department_id.id or False,
                                'employee_contract_id': rec.employee_ids.contract_id.id or False,
                                # 'date': rec.date_from.date() - timedelta(days=1),
                                'date': check_date,
                                'hr_transaction_id': rec.holiday_status_id.transact_code_accrd_leave.id or False,
                                'transaction_type_id': rec.holiday_status_id.transact_code_accrd_leave.transaction_type_id.id or False,
                                'days': rec.paid_leave or 0.00,
                                'type': rec.holiday_status_id.transact_code_accrd_leave.rule_type,
                                'reason': 'Annual Vacation Leave for the day',
                                'leave_id': rec.id
                            }
                            transaction = payroll_transaction.create(vals)
                            transaction.onchange_transaction_type()
                            transaction.action_progress3()
                    else:

                        if rec.holiday_status_id.prepare_payslip:
                            payroll_transaction = self.env['salary.allowance.detection']

                            # Step 1: Initialize current_start_date based on rec.request_date_from
                            if rec.request_date_from.day == 1:
                                current_start_date = rec.request_date_from
                            else:
                                current_start_date = rec.request_date_from - timedelta(
                                    days=1)  # First time only, subtract 1 day

                            remaining_leave = rec.paid_leave

                            # Loop through each month between rec.request_date_from and rec.request_date_to
                            while current_start_date <= rec.request_date_to and remaining_leave > 0:
                                # Calculate the last day of the current month
                                next_month = current_start_date.replace(day=28) + timedelta(days=4)  # Move to next month
                                last_day_of_month = next_month - timedelta(
                                    days=next_month.day)  # Get last day of the current month

                                num_of_days = 0.00
                                days_in_current_month = 0.00
                                if rec.holiday_status_id.thirty_days_flag:
                                    num_of_days = last_day_of_month.day
                                    if num_of_days >= 28:
                                        num_of_days = 30

                                    if rec.request_date_to < last_day_of_month:
                                        days_in_current_month = (rec.request_date_to - current_start_date).days + 1
                                    else:

                                        if current_start_date.day > 1:
                                            current_start_date_days = current_start_date.day
                                            days_in_current_month = num_of_days - current_start_date_days
                                        else:
                                            current_start_date_days = current_start_date.day
                                            days_in_current_month = num_of_days - current_start_date_days + 1

                                if rec.holiday_status_id.calendar_days_flag:
                                    if rec.request_date_to < last_day_of_month:
                                        days_in_current_month = (rec.request_date_to - current_start_date).days + 1
                                    else:
                                        if current_start_date.day > 1:
                                            days_in_current_month = (last_day_of_month - current_start_date).days
                                        else:
                                            days_in_current_month = (last_day_of_month - current_start_date).days + 1

                                # Determine the leave days to allocate for this month
                                leave_days_in_month = min(days_in_current_month, remaining_leave)

                                # Prepare the transaction values for the current month
                                vals = {
                                    'employee_id': rec.employee_ids.id,
                                    'employee_number': rec.employee_ids.employee_no,
                                    'department': rec.employee_ids.department_id.id or False,
                                    'employee_contract_id': rec.employee_ids.contract_id.id or False,
                                    'date': current_start_date,  # Set the current start date for the transaction
                                    'hr_transaction_id': rec.holiday_status_id.transact_code_accrd_leave.id or False,
                                    'transaction_type_id': rec.holiday_status_id.transact_code_accrd_leave.transaction_type_id.id or False,
                                    'days': leave_days_in_month,
                                    'type': rec.holiday_status_id.transact_code_accrd_leave.rule_type,
                                    'reason': 'Annual Vacation Leave for the month',
                                    'leave_id': rec.id
                                }

                                # Create the payroll transaction
                                transaction = payroll_transaction.create(vals)
                                transaction.onchange_transaction_type()
                                transaction.action_progress3()

                                # Update the remaining leave
                                remaining_leave -= leave_days_in_month

                                # Move to the next month
                                current_start_date = last_day_of_month + timedelta(
                                    days=1)  # Move to the first day of the next month
                                if current_start_date.day != 1:  # Ensure that the current_start_date is set to the first day of the month
                                    current_start_date = current_start_date.replace(day=1)

                ## Payslip preparation
                if rec.holiday_status_id.prepare_payslip:
                    rec.employee_id.emp_on_vacation = True
                    if rec.request_date_from.month == rec.request_date_to.month:
                        # if rec.employee_id.slip_ids:
                        #     check_date = False
                        #     if rec.date_from.date().day == 1:
                        #         # Set check_date to the start date of the month plus 1 day
                        #         check_date = rec.date_from.date()
                        #     else:
                        #         # Set check_date to rec.date_from.date() - 1 day
                        #         check_date = rec.date_from.date() - timedelta(days=1)
                        #
                        #     # check_date = rec.date_from.date() - timedelta(days=1)
                        #     relevant_slip = rec.employee_id.slip_ids.filtered(
                        #         lambda slip: slip.date_from <= check_date <= slip.date_to and slip.state == 'draft'
                        #     )
                        #
                        #     if relevant_slip:
                        #         relevant_slip.write({'date_to': check_date, 'date_from': check_date,  'payroll_type': 'leave', 'leave_id': rec.id})
                        #         relevant_slip.onchange_employee()
                        #         relevant_slip.compute_sheet()
                        #
                        #     else:
                        #         # If no relevant payslip exists, create a new payslip
                        #         payslip_vals = {
                        #             'employee_id': rec.employee_id.id,
                        #             'date_to': check_date,
                        #             'date_from':  check_date.replace(day=1),
                        #             'state': 'draft',
                        #             'payroll_type': 'leave',
                        #             'journal_id': rec.employee_id.contract_id.journal_id.id,
                        #             'leave_id': rec.id
                        #         }
                        #         new_payslip = self.env['hr.payslip'].create(payslip_vals)
                        #         new_payslip.onchange_employee()
                        #         new_payslip.compute_sheet()
                        # else:
                        #
                        #     check_date = False
                        #     if rec.date_from.date().day == 1:
                        #         # Set check_date to the start date of the month plus 1 day
                        #         check_date = rec.date_from.date()
                        #     else:
                        #         # Set check_date to rec.date_from.date() - 1 day
                        #         check_date = rec.date_from.date() - timedelta(days=1)
                        #
                        #     # If no relevant payslip exists, create a new payslip
                        #     # check_date = rec.date_from.date() - timedelta(days=1)
                        #     payslip_vals = {
                        #         'employee_id': rec.employee_id.id,
                        #         'date_from': check_date.replace(day=1),
                        #         'date_to': check_date,
                        #         'state': 'draft',
                        #         'payroll_type': 'leave',
                        #         'journal_id': rec.employee_id.contract_id.journal_id.id,
                        #         'leave_id': rec.id
                        #     }
                        #     new_payslip = self.env['hr.payslip'].create(payslip_vals)
                        #     new_payslip.onchange_employee()
                        #     new_payslip.compute_sheet()

                        if rec.employee_id.slip_ids:
                            check_date = False
                            if rec.date_from.date().day == 1:
                                # Set check_date to the start date of the month plus 1 day
                                check_date = rec.date_from.date()
                            else:
                                # Set check_date to rec.date_from.date() - 1 day
                                check_date = rec.date_from.date() - timedelta(days=1)

                            # check_date = rec.date_from.date() - timedelta(days=1)
                            relevant_slip = rec.employee_id.slip_ids.filtered(
                                lambda slip: slip.date_from <= check_date <= slip.date_to and slip.state == 'draft'
                            )

                            if relevant_slip:
                                # relevant_slip.write({'date_to': check_date, 'date_from': check_date,  'payroll_type': 'leave', 'leave_id': rec.id})
                                relevant_slip.write({'payroll_type': 'leave', 'leave_id': rec.id, 'same_month_vacation': True, 'leave_vacation_payslip_bool': True })
                                relevant_slip.onchange_employee()
                                relevant_slip.compute_sheet()
                    else:
                        # if rec.holiday_status_id.prepare_payslip:
                        #     # Extract request dates
                        #     request_start_date = rec.request_date_from
                        #     request_end_date = rec.request_date_to
                        #
                        #     # Initialize the start date for the payslip period
                        #     # First payslip period: from the start of the month to one day before request_start_date
                        #     first_payslip_start_date = date(request_start_date.year, request_start_date.month, 1)
                        #     if request_start_date.day == 1:
                        #         first_payslip_end_date = request_start_date
                        #     else:
                        #         first_payslip_end_date = request_start_date - timedelta(days=1)
                        #
                        #     # Create the first payslip if it covers a valid period
                        #     if first_payslip_end_date >= first_payslip_start_date:
                        #         payslip_vals = {
                        #             'employee_id': rec.employee_id.id,
                        #             'date_from': first_payslip_start_date,
                        #             'date_to': first_payslip_end_date,
                        #             'state': 'draft',
                        #             'payroll_type': 'leave',
                        #             'journal_id': rec.employee_id.contract_id.journal_id.id,
                        #         }
                        #
                        #         # Create the new payslip
                        #         new_payslip = self.env['hr.payslip'].create(payslip_vals)
                        #         new_payslip.onchange_employee()
                        #         new_payslip.compute_sheet()
                        #
                        #     # Initialize the start date for the next payslips
                        #
                        #     current_start_date = (request_start_date + relativedelta(months=1)).replace(day=1)
                        #
                        #     # Loop through each month after the first payslip
                        #     while current_start_date <= request_end_date:
                        #         # Determine the end date for the current payslip period
                        #         next_month = current_start_date.replace(day=28) + timedelta(days=4)  # Move to the next month
                        #         period_end_date = next_month - timedelta(days=next_month.day)  # Last day of the current month
                        #
                        #         # Adjust the end date if it's beyond the leave request end date
                        #         if period_end_date > request_end_date:
                        #             period_end_date = request_end_date
                        #
                        #         # Create payslip if the period is within the request range
                        #         if period_end_date >= current_start_date:
                        #             payslip_vals = {
                        #                 'employee_id': rec.employee_id.id,
                        #                 'date_from': current_start_date,
                        #                 'date_to': period_end_date,
                        #                 'state': 'draft',
                        #                 'payroll_type': 'leave',
                        #                 'journal_id': rec.employee_id.contract_id.journal_id.id,
                        #             }
                        #
                        #             # Create the new payslip
                        #             new_payslip = self.env['hr.payslip'].create(payslip_vals)
                        #             new_payslip.onchange_employee()
                        #             new_payslip.compute_sheet()
                        #
                        #         # Move to the next month
                        #         current_start_date = period_end_date + timedelta(days=1)

                        if rec.holiday_status_id.prepare_payslip:
                            # Extract request dates
                            request_start_date = rec.request_date_from
                            # request_end_date = rec.request_date_to
                            paid_leave = rec.paid_leave
                            request_end_date = request_start_date + timedelta(days=paid_leave)
                            print("request_end_date", request_end_date)

                            # Initialize the start date for the payslip period
                            # First payslip period: from the start of the month to one day before request_start_date
                            first_payslip_start_date = date(request_start_date.year, request_start_date.month, 1)
                            if request_start_date.day == 1:
                                first_payslip_end_date = request_start_date
                            else:
                                first_payslip_end_date = request_start_date - timedelta(days=1)

                            # Create the first payslip if it covers a valid period
                            if first_payslip_end_date >= first_payslip_start_date:
                                if rec.employee_id.slip_ids:
                                    check_date = False
                                    if rec.date_from.date().day == 1:
                                        # Set check_date to the start date of the month plus 1 day
                                        check_date = rec.date_from.date()
                                    else:
                                        # Set check_date to rec.date_from.date() - 1 day
                                        check_date = rec.date_from.date() - timedelta(days=1)

                                    # check_date = rec.date_from.date() - timedelta(days=1)
                                    relevant_slip = rec.employee_id.slip_ids.filtered(
                                        lambda slip: slip.date_from <= check_date <= slip.date_to and slip.state in ['draft', 'verify']
                                    )

                                    if relevant_slip:
                                        relevant_slip.write(
                                            {'date_to': first_payslip_end_date, 'date_from': first_payslip_start_date, 'payroll_type': 'leave', 'leave_id': rec.id, 'state': 'verify'})
                                        relevant_slip.onchange_employee()
                                        relevant_slip.compute_sheet()
                                        # relevant_slip.action_payslip_done()

                                    else:
                                        payslip_vals = {
                                            'employee_id': rec.employee_id.id,
                                            'date_from': first_payslip_start_date,
                                            'date_to': first_payslip_end_date,
                                            # 'state': 'draft',
                                            'state': 'verify',
                                            'payroll_type': 'leave',
                                            'journal_id': rec.employee_id.contract_id.journal_id.id,
                                            'leave_id': rec.id
                                        }

                                        # Create the new payslip
                                        new_payslip = self.env['hr.payslip'].create(payslip_vals)
                                        new_payslip.onchange_employee()
                                        new_payslip.compute_sheet()
                                        # new_payslip.action_payslip_done()


                                else:
                                    payslip_vals = {
                                        'employee_id': rec.employee_id.id,
                                        'date_from': first_payslip_start_date,
                                        'date_to': first_payslip_end_date,
                                        # 'state': 'draft',
                                        'state': 'verify',
                                        'payroll_type': 'leave',
                                        'journal_id': rec.employee_id.contract_id.journal_id.id,
                                        'leave_id': rec.id
                                    }

                                    # Create the new payslip
                                    new_payslip = self.env['hr.payslip'].create(payslip_vals)
                                    new_payslip.onchange_employee()
                                    new_payslip.compute_sheet()
                                    # new_payslip.action_payslip_done()

                            # Initialize the start date for the next payslips

                            current_start_date = (request_start_date + relativedelta(months=1)).replace(day=1)

                            # #Generate up coming month paid leave based run this code commanded an 29/09/2024

                            # # Loop through each month after the first payslip
                            # while current_start_date <= request_end_date:
                            #     # Determine the end date for the current payslip period
                            #     next_month = current_start_date.replace(day=28) + timedelta(days=4)  # Move to the next month
                            #     period_end_date = next_month - timedelta(days=next_month.day)  # Last day of the current month
                            #
                            #     # Adjust the end date if it's beyond the leave request end date
                            #     if period_end_date > request_end_date:
                            #         period_end_date = request_end_date
                            #
                            #     # Create payslip if the period is within the request range
                            #     if period_end_date >= current_start_date:
                            #         payslip_vals = {
                            #             'employee_id': rec.employee_id.id,
                            #             'date_from': current_start_date,
                            #             'date_to': period_end_date,
                            #             # 'state': 'draft',
                            #             'state': 'verify',
                            #             'payroll_type': 'leave',
                            #             'journal_id': rec.employee_id.contract_id.journal_id.id,
                            #             'leave_vacation_payslip_bool': True,
                            #             'leave_id': rec.id
                            #         }
                            #
                            #         # Create the new payslip
                            #         new_payslip = self.env['hr.payslip'].create(payslip_vals)
                            #         new_payslip.onchange_employee()
                            #         new_payslip.compute_sheet()
                            #
                            #     # Move to the next month
                            #     current_start_date = period_end_date + timedelta(days=1)

            ## Full accrued leave transaction in prepare the single month
            if rec.holiday_status_id.full_accrued_leave:
                ##### Already working code commaned on 17/09/2024
                #### if rec.holiday_status_id and rec.holiday_status_id.transact_code_accrd_leave and rec.paid_leave > 0:
                if rec.holiday_status_id.prepare_payslip == True:
                    if rec.holiday_status_id and rec.holiday_status_id.transact_code_accrd_leave:
                        payroll_transaction = self.env['salary.allowance.detection']
                        vals = {
                            'employee_id': rec.employee_ids.id,
                            'employee_number': rec.employee_ids.employee_no,
                            'department': rec.employee_ids.department_id.id or False,
                            'employee_contract_id': rec.employee_ids.contract_id.id or False,
                            'date': rec.date_from.date() - timedelta(days=1),
                            'hr_transaction_id': rec.holiday_status_id.transact_code_accrd_leave.id or False,
                            'transaction_type_id': rec.holiday_status_id.transact_code_accrd_leave.transaction_type_id.id or False,
                            'days': rec.paid_leave or 0.00,
                            'type': rec.holiday_status_id.transact_code_accrd_leave.rule_type,
                            'reason': 'Annual Vacation Leave for the day',
                            'leave_id': rec.id,
                        }
                        transaction = payroll_transaction.create(vals)
                        transaction.onchange_transaction_type()
                        transaction.action_progress3()

                # Check payslip date range and update slip.date_to
                # if rec.employee_id.slip_ids and rec.paid_leave > 0:
                if rec.holiday_status_id.prepare_payslip == True:
                    rec.employee_id.emp_on_vacation = True
                    if rec.employee_id.slip_ids:
                        check_date = rec.date_from.date() - timedelta(days=1)
                        relevant_slip = rec.employee_id.slip_ids.filtered(
                            lambda slip: slip.date_from <= check_date <= slip.date_to and slip.state == 'draft'
                        )

                        if relevant_slip:
                            relevant_slip.write({'date_to': check_date, 'payroll_type': 'leave', 'leave_id': rec.id, 'av_loan_bool': True})
                            relevant_slip.onchange_employee()
                            relevant_slip.compute_sheet()
                            relevant_slip.action_payslip_done()


                        else:
                            # If no relevant payslip exists, create a new payslip
                            payslip_vals = {
                                'employee_id': rec.employee_id.id,
                                'date_to': check_date,
                                'state': 'draft',
                                'payroll_type': 'leave',
                                'journal_id': rec.employee_id.contract_id.journal_id.id,
                                'leave_id': rec.id,
                                'av_loan_bool': True
                            }
                            new_payslip = self.env['hr.payslip'].create(payslip_vals)
                            new_payslip.onchange_employee()
                            new_payslip.compute_sheet()
                            new_payslip.action_payslip_done()

                    else:
                        # If no relevant payslip exists, create a new payslip
                        check_date = rec.date_from.date() - timedelta(days=1)
                        payslip_vals = {
                            'employee_id': rec.employee_id.id,
                            'date_from': check_date.replace(day=1),
                            'date_to': check_date,
                            'state': 'draft',
                            'payroll_type': 'leave',
                            'journal_id': rec.employee_id.contract_id.journal_id.id,
                            'leave_id': rec.id,
                            'av_loan_bool': True
                        }
                        new_payslip = self.env['hr.payslip'].create(payslip_vals)
                        new_payslip.onchange_employee()
                        new_payslip.compute_sheet()
                        new_payslip.action_payslip_done()

        return True

    ###This code is com on 07/11/2024 - functionality checking
    # @api.constrains('state', 'number_of_days', 'holiday_status_id')
    # def _check_holidays(self):
    #     mapped_days = self.holiday_status_id.get_employees_days((self.employee_id | self.employee_ids).ids)
    #     for holiday in self:
    #         if holiday.holiday_type != 'employee' \
    #                 or not holiday.employee_id and not holiday.employee_ids \
    #                 or holiday.holiday_status_id.requires_allocation == 'no':
    #             continue
    #         if holiday.employee_id:
    #             leave_days = mapped_days[holiday.employee_id.id][holiday.holiday_status_id.id]
    #             if float_compare(leave_days['remaining_leaves'], 0, precision_digits=2) == -1 \
    #                     or float_compare(leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
    #                 # raise ValidationError(
    #                 #     _('The number of remaining time off is not sufficient for this time off type.\n'
    #                 #       'Please also check the time off waiting for validation.'))
    #                 pass
    #         else:
    #             unallocated_employees = []
    #             for employee in holiday.employee_ids:
    #                 leave_days = mapped_days[employee.id][holiday.holiday_status_id.id]
    #                 if float_compare(leave_days['remaining_leaves'], self.number_of_days, precision_digits=2) == -1 \
    #                         or float_compare(leave_days['virtual_remaining_leaves'], self.number_of_days,
    #                                          precision_digits=2) == -1:
    #                     unallocated_employees.append(employee.name)
    #             if unallocated_employees:
    #                 raise ValidationError(
    #                     _('The number of remaining time off is not sufficient for this time off type.\n'
    #                       'Please also check the time off waiting for validation.')
    #                     + _('\nThe employees that lack allocation days are:\n%s',
    #                         (', '.join(unallocated_employees))))

    def action_refuse(self):
        current_employee = self.env.user.employee_id
        if any(holiday.state not in ['draft', 'confirm', 'validate', 'validate1'] for holiday in self):
            raise UserError(_('Time off request must be confirmed or validated in order to refuse it.'))

        validated_holidays = self.filtered(lambda hol: hol.state == 'validate1')
        validated_holidays.write({'state': 'refuse', 'first_approver_id': current_employee.id})
        (self - validated_holidays).write({'state': 'refuse', 'second_approver_id': current_employee.id})
        # Delete the meeting
        self.mapped('meeting_id').write({'active': False})
        # If a category that created several holidays, cancel all related
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_refuse()

        # Post a second message, more verbose than the tracking message
        for holiday in self:
            holiday.employee_id.emp_on_vacation = False
            if holiday.employee_id.user_id:
                holiday.message_post(
                    body=_('Your %(leave_type)s planned on %(date)s has been refused', leave_type=holiday.holiday_status_id.display_name, date=holiday.date_from),
                    partner_ids=holiday.employee_id.user_id.partner_id.ids)

            check_date = holiday.date_from.date() - timedelta(days=1)
            # Delete the relevant payslip using a SQL query
            # if holiday.employee_id and check_date and holiday.holiday_status_id.prepare_payslip:
            #     self.env.cr.execute("""
            #                DELETE FROM hr_payslip
            #                WHERE employee_id = %s
            #                AND state = 'draft'
            #                AND date_from <= %s
            #                AND date_to >= %s
            #                AND leave_id = %s
            #            """, (holiday.employee_id.id, check_date, check_date, holiday.id))

                # self.env.cr.execute("""
                #            DELETE FROM hr_payslip
                #            WHERE employee_id = %s
                #            AND state in ['draft', 'verify', 'done']
                #            AND leave_id = %s
                #        """, (holiday.employee_id.id, holiday.id))

            # Delete the transaction record using a SQL query
            if holiday.employee_id and check_date and holiday.holiday_status_id.transact_code_accrd_leave.transaction_type_id:
                self.env.cr.execute("""
                           DELETE FROM salary_allowance_detection
                           WHERE employee_id = %s
                           AND date = %s
                           AND transaction_type_id = %s
                           AND leave_id = %s
                       """, (
                holiday.employee_id.id,
                check_date,
                holiday.holiday_status_id.transact_code_accrd_leave.transaction_type_id.id,
                holiday.id
            ))

            #     self.env.cr.execute("""
            #                DELETE FROM salary_allowance_detection
            #                WHERE employee_id = %s
            #                AND state = 'approve'
            #                AND transaction_type_id = %s
            #                AND leave_id = %s
            #            """, (
            #     holiday.employee_id.id,
            #     holiday.holiday_status_id.transact_code_accrd_leave.transaction_type_id.id,
            #     holiday.id
            # ))

        self.activity_update()

        return True
