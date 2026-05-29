from odoo import api, fields, models,_
from collections import defaultdict
import logging

from datetime import datetime, time, date, timedelta
from dateutil.relativedelta import relativedelta

from odoo.addons.resource.models.utils import HOURS_PER_DAY
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round
from odoo.tools.date_utils import get_timedelta
from odoo.osv import expression



class HolidaysType(models.Model):
    _inherit = "hr.leave.type"
    
    is_leave_encash = fields.Boolean('Leave Encash or not',default=False)
    
    maximum_allowed_days = fields.Float('Maximum Allowed Days')
    
    
    @api.constrains('maximum_allowed_days')
    def _check_maximum_allowed_days(self):
        if self.is_leave_encash==True:
            if self.maximum_allowed_days == 0.00:
                raise ValidationError("Please enter a number greater than zero in Maximum allowed days.")

            
class HolidaysAllocation(models.Model):
    """ Allocation Requests Access specifications: similar to leave requests """
    _inherit = "hr.leave.allocation"
    _description = "Leave Allocation"

    def _default_holiday_status_id(self):
        if self.user_has_groups('hr_holidays.group_hr_holidays_user'):
            domain = [('has_valid_allocation', '=', True), ('requires_allocation', '=', 'yes')]
        else:
            domain = [('has_valid_allocation', '=', True), ('requires_allocation', '=', 'yes'), ('employee_requests', '=', 'yes')]
        return self.env['hr.leave.type'].search(domain, limit=1)

    def _domain_holiday_status_id(self):
        if self.user_has_groups('hr_holidays.group_hr_holidays_user'):
            return [('requires_allocation', '=', 'yes')]
        return [('employee_requests', '=', 'yes')]

    holiday_status_id = fields.Many2one(
        "hr.leave.type", compute='_compute_holiday_status_id', store=True, string="Leave Type", required=True,
        readonly=False,
        domain=_domain_holiday_status_id,
        default=_default_holiday_status_id)
    
    
    
    # @api.constrains('holiday_status_id','employee_id','allocation_type')
    # def _check_allowed_leave_allocation(self):
    #     current_date = fields.Date.today()
    #     current_year_start = current_date.replace(month=1, day=1)
    #     current_year_end = current_date.replace(month=12, day=31)
    #     for rec in self:
    #         leave_allocation = self.env['hr.leave.allocation'].search([
    #             ('employee_id', '=', rec.employee_id.id),
    #             ('holiday_status_id', '=', rec.holiday_status_id.id),
    #             ('state', '=', 'validate'),
    #             ('allocation_type', '=', rec.allocation_type),
    #             ('date_from', '>=', current_year_start),
    #             ('date_to', '<=', current_year_end)
    #         ])
    #
    #         if leave_allocation:
    #             raise ValidationError("Already Leave allocation is alloted for this Employee of current year")

    # @api.constrains('holiday_status_id', 'employee_ids', 'allocation_type', 'state', 'date_from', 'date_to')
    # def _check_allowed_leave_allocation(self):
    #     current_date = fields.Date.today()
    #     current_year_start = current_date.replace(month=1, day=1)
    #     current_year_end = current_date.replace(month=12, day=31)
    #     for rec in self:
    #         leave_allocation = self.env['hr.leave.allocation'].search([
    #             ('employee_ids', 'in', rec.employee_ids.ids),
    #             ('holiday_status_id', '=', rec.holiday_status_id.id),
    #             ('state', '=', 'validate'),
    #             ('allocation_type', '=', rec.allocation_type),
    #             ('date_from', '<=', current_year_start),
    #             ('date_to', '>=', current_year_end)
    #         ])
    #         if len(leave_allocation) > 1:
    #             raise ValidationError("Already Leave allocation is alloted for this Employee of current year")

    @api.constrains('holiday_status_id', 'employee_ids', 'allocation_type', 'state', 'date_from', 'date_to')
    def _check_allowed_leave_allocation(self):
        current_date = fields.Date.today()
        current_year_start = current_date.replace(month=1, day=1)
        current_year_end = current_date.replace(month=12, day=31)

        for rec in self:
            leave_allocation = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('holiday_status_id', '=', rec.holiday_status_id.id),
                ('state', '=', 'validate'),
                ('allocation_type', '=', rec.allocation_type),
                ('id', '!=', rec.id),
                '|', '|',
                '&', ('date_from', '<=', current_year_end), ('date_to', '>=', current_year_start),
                # Overlapping current year
                ('date_from', '>=', current_year_start),
                ('date_to', '<=', current_year_end)
            ])

            if leave_allocation:
                print("leave_allocation 1111111111", leave_allocation)
                raise ValidationError("Leave allocation for this employee already exists for the current year.")


    @api.model
    def create(self, values):
        '''If mid join employee have the allocation and it will automatically created using company policy when we create the alloction for the particular employee'''
        allocation = super(HolidaysAllocation, self).create(values)
        cron_job = self.env.ref('hr_holidays.hr_leave_allocation_cron_accrual')
        if cron_job:
            cron_job.method_direct_trigger()
        # current_date = fields.Date.today()
        # current_year_start = current_date.replace(month=1, day=1)
        # current_year_end = current_date.replace(month=12, day=31)
        # print("current_year_end",current_year_end)
        #
        # # for rec in self:
        # leave_allocation = self.env['hr.leave.allocation'].search([
        #     ('employee_ids', 'in', allocation.employee_ids.ids),
        #     ('holiday_status_id', '=', allocation.holiday_status_id.id),
        #     ('state', '=', 'validate'),
        #     ('allocation_type', '=', allocation.allocation_type),
        #     ('date_from', '<=', current_year_start),
        #     ('date_to', '>=', current_year_end)
        # ])
        # print("leave_allocation", leave_allocation)
        # if len(leave_allocation) > 1:
        #     raise ValidationError("Already Leave allocation is alloted for this Employee of current year")
        return allocation

    @api.constrains('employee_ids', 'date_from')
    def _check_joining_date_allocation(self):
        for rec in self.employee_ids:
            if rec:
                current_year = datetime.now().year
                
                if rec.joining_date:
                    if rec.joining_date.year == current_year and rec.joining_date and self.date_from:
                        # if rec.joining_date and self.date_from:
                        if rec.joining_date > self.date_from:
                            raise ValidationError(
                                f"The joining date ({rec.joining_date}) cannot be later than the start date ({self.date_from}) for employee {rec.name}. Please ensure the joining date is earlier than the start date."
                            )
                # if rec.joining_date.year == current_year and rec.joining_date and self.date_from:
                #     # if rec.joining_date and self.date_from:
                #     if rec.joining_date > self.date_from:
                #         raise ValidationError(
                #             f"The joining date ({rec.joining_date}) cannot be later than the start date ({self.date_from}) for employee {rec.name}. Please ensure the joining date is earlier than the start date."
                #         )

    
    @api.onchange('employee_ids')
    def _onchange_employee_id(self):
        for rec in self.employee_ids:
            if rec:
                current_year = datetime.now().year
                if rec.joining_date:
                    if rec.joining_date.year == current_year:
                        self.date_from = rec.joining_date
                else:
                    self.date_from = fields.Date.context_today(self)
            else:
                self.date_from = fields.Date.context_today(self)
    
    
    def _process_accrual_plan_level(self, level, start_period, start_date, end_period, end_date):
        """
        Returns the added days for that level
        """
        self.ensure_one()
        if level.accrual_plan_id.is_based_on_worked_time:
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.min.time())
            worked = \
            self.employee_id._get_work_days_data_batch(start_dt, end_dt, calendar=self.employee_id.resource_calendar_id) \
                [self.employee_id.id]['hours']
            if start_period != start_date or end_period != end_date:
                start_dt = datetime.combine(start_period, datetime.min.time())
                end_dt = datetime.combine(end_period, datetime.min.time())
                planned_worked = self.employee_id._get_work_days_data_batch(start_dt, end_dt,
                                                                            calendar=self.employee_id.resource_calendar_id) \
                    [self.employee_id.id]['hours']
            else:
                planned_worked = worked
            left = self.employee_id.sudo()._get_leave_days_data_batch(start_dt, end_dt,
                                                                      domain=[('time_type', '=', 'leave')])[
                self.employee_id.id]['hours']
            work_entry_prorata = worked / (left + planned_worked) if (left + planned_worked) else 0
            added_value = work_entry_prorata * level.added_value
        else:
            added_value = level.added_value
        # Convert time in hours to time in days in case the level is encoded in hours
        if level.added_value_type == 'hours':
            added_value = added_value / (self.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)
        period_prorata = 1
        if (start_period != start_date or end_period != end_date) and not level.accrual_plan_id.is_based_on_worked_time:
            period_days = (end_period - start_period)
            call_days = (end_date - start_date) + timedelta(days=1)
            period_prorata = min(1, call_days / period_days) if period_days else 1
        return added_value * period_prorata

    # def _process_accrual_plans(self, date_to=False, force_period=False, log=True):
    #     """
    #     This method is part of the cron's process.
    #     The goal of this method is to retroactively apply accrual plan levels and progress from nextcall to today
    #     """
    #     today = fields.Date.today()
    #     first_allocation = _(
    #         """This allocation have already ran once, any modification won't be effective to the days allocated to the employee. If you need to change the configuration of the allocation, cancel and create a new one.""")
    #     for allocation in self:
    #         level_ids = allocation.accrual_plan_id.level_ids.sorted('sequence')
    #         if not level_ids:
    #             continue
    #         if not allocation.nextcall:
    #             first_level = level_ids[0]
    #             first_level_start_date = allocation.date_from + get_timedelta(first_level.start_count,
    #                                                                           first_level.start_type) - timedelta(days=1)
    #             if today < first_level_start_date:
    #                 # Accrual plan is not configured properly or has not started
    #                 continue
    #             allocation.lastcall = max(allocation.lastcall, first_level_start_date)
    #             allocation.nextcall = first_level._get_next_date(allocation.lastcall)
    #             if len(level_ids) > 1:
    #                 second_level_start_date = allocation.date_from + get_timedelta(level_ids[1].start_count,
    #                                                                                level_ids[1].start_type)
    #                 allocation.nextcall = min(second_level_start_date, allocation.nextcall)
    #             allocation._message_log(body=first_allocation)
    #         days_added_per_level = defaultdict(lambda: 0)
    #         while allocation.nextcall <= today:
    #             (current_level, current_level_idx) = allocation._get_current_accrual_plan_level_id(allocation.nextcall)
    #             current_level_maximum_leave = current_level.maximum_leave if current_level.added_value_type == "days" else current_level.maximum_leave / (
    #                         allocation.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)
    #             nextcall = current_level._get_next_date(allocation.nextcall)
    #             # Since _get_previous_date returns the given date if it corresponds to a call date
    #             # this will always return lastcall except possibly on the first call
    #             # this is used to prorate the first number of days given to the employee
    #             period_start = current_level._get_previous_date(allocation.lastcall)
    #             period_end = current_level._get_next_date(allocation.lastcall)
    #             # Also prorate this accrual in the event that we are passing from one level to another
    #             if current_level_idx < (
    #                     len(level_ids) - 1) and allocation.accrual_plan_id.transition_mode == 'immediately':
    #                 next_level = level_ids[current_level_idx + 1]
    #                 current_level_last_date = allocation.date_from + get_timedelta(next_level.start_count,
    #                                                                                next_level.start_type)
    #                 if allocation.nextcall != current_level_last_date:
    #                     nextcall = min(nextcall, current_level_last_date)
    #             days_added_per_level[current_level] += allocation._process_accrual_plan_level(
    #                 current_level, period_start, allocation.lastcall, period_end, allocation.nextcall)
    #             if current_level_maximum_leave > 0 and sum(days_added_per_level.values()) > current_level_maximum_leave:
    #                 days_added_per_level[current_level] -= sum(
    #                     days_added_per_level.values()) - current_level_maximum_leave
    #             allocation.lastcall = allocation.nextcall
    #             allocation.nextcall = nextcall
    #         if days_added_per_level:
    #             number_of_days_to_add = allocation.number_of_days + sum(days_added_per_level.values())
    #             max_allocation_days = current_level_maximum_leave + (
    #                 allocation.leaves_taken if allocation.type_request_unit != "hour" else allocation.leaves_taken / (
    #                             allocation.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY))
    #             # Let's assume the limit of the last level is the correct one
    #             allocation.number_of_days = min(number_of_days_to_add,
    #                                             max_allocation_days) if current_level_maximum_leave > 0 else number_of_days_to_add


    # def _process_accrual_plans(self, date_to=False, force_period=False, log=True):
    #     """
    #     This method is part of the cron's process.
    #     The goal of this method is to retroactively apply accrual plan levels and progress from nextcall to date_to or today.
    #     If force_period is set, the accrual will run until date_to in a prorated way (used for end of year accrual actions).
    #     """
    #     date_to = date_to or fields.Date.today()
    #     first_allocation = _("""This allocation have already ran once, any modification won't be effective to the days allocated to the employee. If you need to change the configuration of the allocation, delete and create a new one.""")
    #     for allocation in self:
    #         level_ids = allocation.accrual_plan_id.level_ids.sorted('sequence')
    #         if not level_ids:
    #             continue
    #         # "cache" leaves taken, as it gets recomputed every time allocation.number_of_days is assigned to. Without this,
    #         # every loop will take 1+ second. It can be removed if computes don't chain in a way to always reassign accrual plan
    #         # even if the value doesn't change. This is the best performance atm.
    #         first_level = level_ids[0]
    #         first_level_start_date = allocation.date_from + get_timedelta(first_level.start_count, first_level.start_type)
    #         leaves_taken = allocation.leaves_taken if first_level.added_value_type == "day" else allocation.leaves_taken / (allocation.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)
    #         # first time the plan is run, initialize nextcall and take carryover / level transition into account
    #         if not allocation.nextcall:
    #             # Accrual plan is not configured properly or has not started
    #             if date_to < first_level_start_date:
    #                 continue
    #             allocation.lastcall = max(allocation.lastcall, first_level_start_date)
    #             allocation.nextcall = first_level._get_next_date(allocation.lastcall)
    #             # adjust nextcall for carryover
    #             carryover_date = allocation._get_carryover_date(allocation.nextcall)
    #             allocation.nextcall = min(carryover_date, allocation.nextcall)
    #             # adjust nextcall for level_transition
    #             if len(level_ids) > 1:
    #                 second_level_start_date = allocation.date_from + get_timedelta(level_ids[1].start_count, level_ids[1].start_type)
    #                 allocation.nextcall = min(second_level_start_date, allocation.nextcall)
    #             if log:
    #                 allocation._message_log(body=first_allocation)
    #         (current_level, current_level_idx) = (False, 0)
    #         current_level_maximum_leave = 0.0
    #         # all subsequent runs, at every loop:
    #         # get current level and normal period boundaries, then set nextcall, adjusted for level transition and carryover
    #         # add days, trimmed if there is a maximum_leave
    #         while allocation.nextcall <= date_to:
    #             (current_level, current_level_idx) = allocation._get_current_accrual_plan_level_id(allocation.nextcall)
    #             if not current_level:
    #                 break
    #             if current_level.cap_accrued_time:
    #                 current_level_maximum_leave = current_level.maximum_leave if current_level.added_value_type == "day" else current_level.maximum_leave / (allocation.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)
    #             nextcall = current_level._get_next_date(allocation.nextcall)
    #             # Since _get_previous_date returns the given date if it corresponds to a call date
    #             # this will always return lastcall except possibly on the first call
    #             # this is used to prorate the first number of days given to the employee
    #             period_start = current_level._get_previous_date(allocation.lastcall)
    #             period_end = current_level._get_next_date(allocation.lastcall)
    #             # There are 2 cases where nextcall could be closer than the normal period:
    #             # 1. Passing from one level to another, if mode is set to 'immediately'
    #             if current_level_idx < (len(level_ids) - 1) and allocation.accrual_plan_id.transition_mode == 'immediately':
    #                 next_level = level_ids[current_level_idx + 1]
    #                 current_level_last_date = allocation.date_from + get_timedelta(next_level.start_count, next_level.start_type)
    #                 if allocation.nextcall != current_level_last_date:
    #                     nextcall = min(nextcall, current_level_last_date)
    #             # 2. On carry-over date
    #             carryover_date = allocation._get_carryover_date(allocation.nextcall)
    #             if allocation.nextcall < carryover_date < nextcall:
    #                 nextcall = min(nextcall, carryover_date)
    #             if not allocation.already_accrued:
    #                 allocation._add_days_to_allocation(current_level, current_level_maximum_leave, leaves_taken, period_start, period_end)
    #             # if it's the carry-over date, adjust days using current level's carry-over policy, then continue
    #             if allocation.nextcall == carryover_date:
    #                 if current_level.action_with_unused_accruals in ['lost', 'maximum']:
    #                     allocation_days = allocation.number_of_days + leaves_taken
    #                     allocation_max_days = current_level.postpone_max_days + leaves_taken
    #                     allocation.number_of_days = min(allocation_days, allocation_max_days)
    #
    #             allocation.lastcall = allocation.nextcall
    #             allocation.nextcall = nextcall
    #             allocation.already_accrued = False
    #             if force_period and allocation.nextcall > date_to:
    #                 allocation.nextcall = date_to
    #                 force_period = False
    #
    #         # if plan.accrued_gain_time == 'start', process next period and set flag 'already_accrued', this will skip adding days
    #         # once, preventing double allocation.
    #         if allocation.accrual_plan_id.accrued_gain_time == 'start':
    #             # check that we are at the start of a period, not on a carry-over or level transition date
    #             current_level = current_level or allocation.accrual_plan_id.level_ids[0]
    #             period_start = current_level._get_previous_date(allocation.lastcall)
    #             if allocation.lastcall != period_start:
    #                 continue
    #             if current_level.cap_accrued_time:
    #                 current_level_maximum_leave = current_level.maximum_leave if current_level.added_value_type == "day" else current_level.maximum_leave / (allocation.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)
    #             allocation._add_days_to_allocation(current_level, current_level_maximum_leave, leaves_taken, allocation.lastcall, allocation.nextcall)
    #             allocation.already_accrued = True

    def _process_accrual_plans(self, date_to=False, force_period=False, log=True):
        """
        This method is part of the cron's process.
        The goal of this method is to retroactively apply accrual plan levels and progress from nextcall to date_to or today.
        If force_period is set, the accrual will run until date_to in a prorated way (used for end of year accrual actions).
        """
        date_to = date_to or fields.Date.today()
        first_allocation = _(
            """This allocation has already run once, any modification won't be effective to the days allocated to the employee. If you need to change the configuration of the allocation, delete and create a new one.""")
        for allocation in self:
            level_ids = allocation.accrual_plan_id.level_ids.sorted('sequence')
            if not level_ids:
                continue
            first_level = level_ids[0]
            first_level_start_date = allocation.date_from + get_timedelta(first_level.start_count,
                                                                          first_level.start_type)
            leaves_taken = allocation.leaves_taken if first_level.added_value_type == "day" else allocation.leaves_taken / (
                        allocation.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)

            # Initialize lastcall correctly
            if not allocation.lastcall:
                allocation.lastcall = first_level_start_date
            else:
                allocation.lastcall = max(allocation.lastcall or first_level_start_date, first_level_start_date)

            # First time the plan is run
            if not allocation.nextcall:
                if date_to < first_level_start_date:
                    continue
                allocation.nextcall = first_level._get_next_date(allocation.lastcall)
                carryover_date = allocation._get_carryover_date(allocation.nextcall)
                allocation.nextcall = min(carryover_date, allocation.nextcall)
                if len(level_ids) > 1:
                    second_level_start_date = allocation.date_from + get_timedelta(level_ids[1].start_count,
                                                                                   level_ids[1].start_type)
                    allocation.nextcall = min(second_level_start_date, allocation.nextcall)
                if log:
                    allocation._message_log(body=first_allocation)

            current_level, current_level_idx = None, 0
            current_level_maximum_leave = 0.0

            while allocation.nextcall <= date_to:
                current_level, current_level_idx = allocation._get_current_accrual_plan_level_id(allocation.nextcall)
                if not current_level:
                    break
                if current_level.cap_accrued_time:
                    current_level_maximum_leave = current_level.maximum_leave if current_level.added_value_type == "day" else current_level.maximum_leave / (
                                allocation.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)

                nextcall = current_level._get_next_date(allocation.nextcall)
                period_start = current_level._get_previous_date(allocation.lastcall)
                period_end = current_level._get_next_date(allocation.lastcall)

                if current_level_idx < (
                        len(level_ids) - 1) and allocation.accrual_plan_id.transition_mode == 'immediately':
                    next_level = level_ids[current_level_idx + 1]
                    current_level_last_date = allocation.date_from + get_timedelta(next_level.start_count,
                                                                                   next_level.start_type)
                    nextcall = min(nextcall, current_level_last_date)

                carryover_date = allocation._get_carryover_date(allocation.nextcall)
                if allocation.nextcall < carryover_date < nextcall:
                    nextcall = carryover_date

                if not allocation.already_accrued:
                    allocation._add_days_to_allocation(current_level, current_level_maximum_leave, leaves_taken,
                                                       period_start, period_end)

                if allocation.nextcall == carryover_date:
                    if current_level.action_with_unused_accruals in ['lost', 'maximum']:
                        allocation_days = allocation.number_of_days + leaves_taken
                        allocation_max_days = current_level.postpone_max_days + leaves_taken
                        allocation.number_of_days = min(allocation_days, allocation_max_days)

                allocation.lastcall = allocation.nextcall
                allocation.nextcall = nextcall
                allocation.already_accrued = False

                if force_period and allocation.nextcall > date_to:
                    allocation.nextcall = date_to
                    force_period = False

            if allocation.accrual_plan_id.accrued_gain_time == 'start':
                current_level = current_level or allocation.accrual_plan_id.level_ids[0]
                period_start = current_level._get_previous_date(allocation.lastcall)
                if allocation.lastcall != period_start:
                    continue
                if current_level.cap_accrued_time:
                    current_level_maximum_leave = current_level.maximum_leave if current_level.added_value_type == "day" else current_level.maximum_leave / (
                                allocation.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)
                allocation._add_days_to_allocation(current_level, current_level_maximum_leave, leaves_taken,
                                                   allocation.lastcall, allocation.nextcall)
                allocation.already_accrued = True

    # def _prepare_holiday_values(self, employees):
    #     self.ensure_one()
    #     current_year = datetime.now().year
    #
    #     holiday_values = []
    #     for employee in employees:
    #         date_from = self.date_from
    #         if employee.joining_date and employee.joining_date.year == current_year:
    #             date_from = employee.joining_date
    #
    #         if employee.joining_date:
    #             if not employee.joining_date >= self.date_to:
    #                 values = {
    #                     'name': self.name,
    #                     'holiday_type': 'employee',
    #                     'holiday_status_id': self.holiday_status_id.id,
    #                     'notes': self.notes,
    #                     'number_of_days': self.number_of_days,
    #                     'parent_id': self.id,
    #                     'employee_id': employee.id,
    #                     'employee_ids': [(6, 0, [employee.id])],
    #                     'state': 'confirm',
    #                     'allocation_type': self.allocation_type,
    #                     'date_from': date_from,
    #                     'date_to': self.date_to,
    #                     'accrual_plan_id': self.accrual_plan_id.id,
    #                 }
    #                 holiday_values.append(values)
    #
    #     return holiday_values        
    #

     
    # def _action_validate_create_childs(self):
    #     childs = self.env['hr.leave.allocation']
    #     # In the case we are in holiday_type `employee` and there is only one employee we can keep the same allocation
    #     # Otherwise we do need to create an allocation for all employees to have a behaviour that is in line
    #     # with the other holiday_type
    #     if self.state == 'validate' and (self.holiday_type in ['category', 'department', 'company'] or
    #                                      (self.holiday_type == 'employee' and len(self.employee_ids) > 1)):
    #         if self.holiday_type == 'employee':
    #             employees = self.employee_ids
    #         elif self.holiday_type == 'category':
    #             employees = self.category_id.employee_ids
    #         elif self.holiday_type == 'department':
    #             employees = self.department_id.member_ids
    #         else:
    #             employees = self.env['hr.employee'].search([('company_id', '=', self.mode_company_id.id)])
    #
    #
    #         allocation_create_vals = self._prepare_holiday_values(employees)
    #         childs += self.with_context(
    #             mail_notify_force_send=False,
    #             mail_activity_automation_skip=True
    #         ).create(allocation_create_vals)
    #         if childs:
    #             childs.action_validate()
    #     return childs       
    #
    #
    #
