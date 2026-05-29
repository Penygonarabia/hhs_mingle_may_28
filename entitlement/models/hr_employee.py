# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import re
import calendar
from odoo.exceptions import AccessError





class HrEmployee(models.Model):

    _inherit = 'hr.employee'

    leave_entitle_days = fields.Float(string='Leave Entitlement', store=True, required=True)
    leave_entitle_period = fields.Selection([('days', 'Days'), ('months', 'Months'), ('years', 'Years')],string='Period', default='days', required=True)
    air_ticket_entitle_days = fields.Float(string='Air Ticket Entitlement', store=True, required=True)
    air_ticket_entitle_period = fields.Selection([('days', 'Days'), ('months', 'Months'), ('years', 'Years')],string='Period', default='days', required=True)
    air_ticket_unit_price = fields.Float(string='Air Ticket Unit Price', required=True)
    # entitlement = fields.Float(string='Entitlement', readonly=True)
    entitlement = fields.Float(string='Entitlement', readonly=True, compute='_compute_entitlement')
    bfwd_previous_year = fields.Float(string='B/Fwd - Previous Years', readonly=True)
    adjustments = fields.Float(string='Adjustments', readonly=True)
    utilised_this_year = fields.Float(string='Utilised This Year', readonly=True, compute='_compute_leave_details')
    balance = fields.Float(string='Accrued Leave Up to End of the Year',  readonly=True, compute='_compute_balance_leave')
    entitlement_ticket = fields.Float(string='Entitlement',  readonly=True)
    bfwd_previous_year_ticket = fields.Float(string='B/Fwd - Previous Years', readonly=True)
    adjustments_ticket = fields.Float(string='Adjustments', readonly=True)
    utilised_this_year_ticket = fields.Float(string='Utilised This Year', readonly=True)
    balance_ticket = fields.Float(string='Accrued Ticket Up to End of the Year',  readonly=True, compute='_compute_balance_ticket')
    status = fields.Selection([('new', 'New'), ('in_progress', 'In Progress'), ('done', 'Done')],string='Status', default='new', readonly=True)
    last_leave_date = fields.Date(string='Last Leave Date', readonly=True, compute='_compute_leave_details')
    last_return_date = fields.Date(string='Last Return Date', readonly=True)
    # accrued_leave = fields.Date(string='Accrued Leave',)
    accrued_leave = fields.Date(string='Accrued Leave')
    total_paid_leave = fields.Float(string='Total Paid Leave', readonly=True, compute='_compute_leave_details')
    total_unpaid_leave = fields.Float(string='Total Unpaid Leave', readonly=True, compute='_compute_leave_details')
    leave_days = fields.Integer(string="Days")
    air_tkt_days = fields.Integer(string="Days")
    eos_start_date = fields.Date(string='End of Service Start Date')
    accrued_leave_num_of_days = fields.Float(string="Accrued Leave Days as of Today", compute='_compute_accrued_leave_days', readonly=True)
    accrued_ticket_num_of_days = fields.Float(string="Accrued Ticket Days as of Today", readonly=True)

    accrued_leave_num_of_days_end_of_service = fields.Float(string="Accrued Leave Days as of Today End of service ", compute='_compute_accrued_leave_days_end_of_service', readonly=True)
    accrued_leave_end_of_service = fields.Date(string='Accrued Leave End of Service', compute="_compute_today")
    accrued_leave_boolean = fields.Boolean(string="accrued_leave_boolean", compute='_compute_default_today_accrued_leave', default=False)
    emp_on_vacation = fields.Boolean(string="On Vacation", readonly=True, default=False)

    #end of service calculation in Accrued Leave
    @api.depends('accrued_leave_end_of_service', 'bfwd_previous_year', 'utilised_this_year', 'adjustments')
    def _compute_accrued_leave_days_end_of_service(self):
        for record in self:
            if record.accrued_leave_end_of_service:
                current_year = datetime.now().year
                accrued_leave_date = record.accrued_leave_end_of_service
                accrued_leave_month = accrued_leave_date.month
                accrued_leave_year = accrued_leave_date.year
                bfwd_previous_year = record.bfwd_previous_year
                utilised_this_year = record.utilised_this_year
                adjustments = record.adjustments

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

                num_of_days = record.accrued_leave_end_of_service.day or 0.00
                record.accrued_leave_num_of_days_end_of_service = 0.00

                # Search for hr.leave.accrual.plan records
                leave_allocation = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', record.id),
                    ('state', '=', 'validate'),
                    ('holiday_status_id.code', '=', 'AV')

                ])
                if leave_allocation:
                    for leave in leave_allocation:
                        accrual_plans = self.env['hr.leave.accrual.plan'].search(
                            [('time_off_type_id.code', '=', 'AV'), ('name', '=', leave.accrual_plan_id.name)])

                        for plan in accrual_plans:
                            for leave in plan.level_ids[0]:
                                # Calculate accrued_leave_num_of_days based on the number of months and leave.added_value
                                added_value = leave.added_value
                                if accrued_leave_year == current_year:
                                    accrued_leave_num_of_days = (previous_month * added_value) + (
                                            added_value * num_of_days) / month_num_of_days
                                else:
                                    accrued_leave_num_of_days = 0.00
                                record.accrued_leave_num_of_days_end_of_service = accrued_leave_num_of_days + bfwd_previous_year + adjustments - utilised_this_year
                                if record.accrued_leave_num_of_days_end_of_service >= 1:
                                    record.accrued_leave_num_of_days_end_of_service = record.accrued_leave_num_of_days_end_of_service
                                else:
                                    record.accrued_leave_num_of_days_end_of_service = 0.00
                                break
            else:
                record.accrued_leave_num_of_days_end_of_service = 0.00
    
    def _compute_today(self):
        for rec in self:
            rec.accrued_leave_end_of_service = False
            if rec.state == 'draft':
                rec.accrued_leave_end_of_service = fields.Date.today()
            if rec.state == 'exit':
                rec.accrued_leave_end_of_service = rec.exit_date

    def _compute_default_today_accrued_leave(self):
        for rec in self:
            rec.accrued_leave = False
            if not rec.accrued_leave_boolean:
                if rec.state == 'draft':
                    rec.accrued_leave_boolean = True
                    if rec.accrued_leave_boolean:
                        rec.accrued_leave = fields.Date.today()
                if rec.state == 'exit':
                    rec.accrued_leave = rec.exit_date
                    
    
    # def write(self, vals):
    #     for record in self:
    #         if record.state == 'exit' and any(field in vals for field in self.fields_get()):
    #             raise AccessError("Cannot modify records when the state is 'exit'.")
    #     return super(HrEmployee, self).write(vals)

    def _compute_entitlement(self):
        for record in self:
            record.entitlement = 0.00
            if record:

                leave_allocation = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', record.id),
                    ('state', '=', 'validate'),
                    ('holiday_status_id.code', '=', 'AV')

                ])
                if leave_allocation:
                    for leave in leave_allocation:
                        accrual_plans = self.env['hr.leave.accrual.plan'].search([('time_off_type_id.code', '=', 'AV'), ('name', '=', leave.accrual_plan_id.name)])
                        for plan in accrual_plans:
                            for leave in plan.level_ids:
                                record.entitlement = leave.maximum_leave if leave.maximum_leave else 0.00

    # @api.onchange('accrued_leave')
    # def _onchange_accrued_leave_days(self):
    #     for record in self:
    #         if record.accrued_leave:
    #             accrued_leave_date = record.accrued_leave
    #             accrued_leave_month = accrued_leave_date.month
    #             accrued_leave_year = accrued_leave_date.year
    #             bfwd_previous_year = record.bfwd_previous_year
    #             utilised_this_year = record.utilised_this_year
    #             adjustments = record.adjustments
    #             # bfwd_previous_year_ticket = record.bfwd_previous_year_ticket
    #             # adjustments_ticket = record.adjustments_ticket
    #             # utilised_this_year_ticket = record.utilised_this_year_ticket
    #             # balance_ticket = record.balance_ticket
    #
    #
    #
    #             # Calculate the number of days in the selected month
    #             month_num_of_days = calendar.monthrange(accrued_leave_year, accrued_leave_month)[1]
    #
    #             # Calculate the previous month and adjust the year if needed
    #             if accrued_leave_month > 1:
    #                 previous_month = accrued_leave_month - 1
    #                 previous_year = accrued_leave_year
    #             else:
    #                 previous_month = 0
    #                 previous_year = accrued_leave_year - 1
    #
    #             num_of_days = record.accrued_leave.day or 0.00
    #             record.accrued_leave_num_of_days = 0.00
    #
    #             # Search for hr.leave.accrual.plan records
    #             accrual_plans = self.env['hr.leave.accrual.plan'].search([])
    #
    #             for plan in accrual_plans:
    #                 for leave in plan.level_ids[0]:
    #                     # Calculate accrued_leave_num_of_days based on the number of months and leave.added_value
    #                     added_value = leave.added_value
    #                     accrued_leave_num_of_days = (previous_month * added_value) + (
    #                                 added_value * num_of_days) / month_num_of_days
    #                     record.accrued_leave_num_of_days = accrued_leave_num_of_days + bfwd_previous_year + adjustments - utilised_this_year
    #                     break
    #
    #         else:
    #             record.accrued_leave_num_of_days = 0.00
    
    

    @api.depends('accrued_leave', 'bfwd_previous_year', 'utilised_this_year', 'adjustments')
    def _compute_accrued_leave_days(self):
        for record in self:
            if record.accrued_leave:
                #accrued Leave calculation:
                current_year = datetime.now().year
                accrued_leave_date = record.accrued_leave
                accrued_leave_month = accrued_leave_date.month
                accrued_leave_year = accrued_leave_date.year
                bfwd_previous_year = record.bfwd_previous_year
                utilised_this_year = record.utilised_this_year
                adjustments = record.adjustments

                # Calculate the number of days in the selected month
                month_num_of_days = calendar.monthrange(accrued_leave_year, accrued_leave_month)[1]
                print(month_num_of_days, month_num_of_days)

                # Calculate the previous month and adjust the year if needed
                # if accrued_leave_year == current_year:
                if accrued_leave_month > 1:
                    previous_month = accrued_leave_month - 1
                    previous_year = accrued_leave_year
                else:
                    previous_month = 0
                    previous_year = accrued_leave_year - 1

                num_of_days = record.accrued_leave.day or 0.00
                record.accrued_leave_num_of_days = 0.00

                ## Accured Ticket Calculation
                record.accrued_ticket_num_of_days = 0.00
                entitlement_ticket = record.entitlement_ticket
                bfwd_previous_year_ticket = record.bfwd_previous_year_ticket
                adjustments_ticket = record.adjustments_ticket
                utilised_this_year_ticket = record.utilised_this_year_ticket
                monthly_ticket_entitlement = entitlement_ticket / 12
                accrued_ticket_days = (previous_month * monthly_ticket_entitlement) + (monthly_ticket_entitlement * num_of_days)/month_num_of_days
                record.accrued_ticket_num_of_days = accrued_ticket_days + bfwd_previous_year_ticket + adjustments_ticket - utilised_this_year_ticket

                # Search for hr.leave.accrual.plan records
                # accrual_plans = self.env['hr.leave.accrual.plan'].search([])
                leave_allocation = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', record.id),
                    ('state', '=', 'validate'),
                    ('holiday_status_id.code', '=', 'AV')

                ])
                if leave_allocation:
                    for leave in leave_allocation:
                        accrual_plans = self.env['hr.leave.accrual.plan'].search(
                            [('time_off_type_id.code', '=', 'AV'), ('name', '=', leave.accrual_plan_id.name)])

                        for plan in accrual_plans:
                            for leave in plan.level_ids[0]:
                                # Calculate accrued_leave_num_of_days based on the number of months and leave.added_value
                                added_value = leave.added_value
                                # if accrued_leave_year == current_year:
                                #     accrued_leave_num_of_days = (previous_month * added_value) + (
                                #             added_value * num_of_days) / month_num_of_days
                                # else:
                                #     accrued_leave_num_of_days = 0.00
                                if accrued_leave_year == current_year and accrued_leave_year > record.joining_date.year:
                                    accrued_leave_num_of_days = (previous_month * added_value) + (
                                            added_value * num_of_days) / month_num_of_days
                                else:
                                    accrued_leave_num_of_days = 0.00
                                    if accrued_leave_year == current_year and accrued_leave_year == record.joining_date.year:
                                        mid_employee_month = record.joining_date.month
                                        pre_month = accrued_leave_month
                                        acc_month = pre_month - mid_employee_month
                                        accrued_leave_num_of_days = (acc_month * added_value) + (
                                                added_value * num_of_days) / month_num_of_days
                                record.accrued_leave_num_of_days = accrued_leave_num_of_days + bfwd_previous_year + adjustments - utilised_this_year
                                if record.accrued_leave_num_of_days >= 1:
                                    record.accrued_leave_num_of_days = record.accrued_leave_num_of_days
                                if record.accrued_leave_num_of_days < 0:
                                    record.accrued_leave_num_of_days = 0.00
                                # else:
                                #     record.accrued_leave_num_of_days = 0.00
                                break
            else:
                record.accrued_leave_num_of_days = 0.00
                record.accrued_ticket_num_of_days = 0.00

    # @api.onchange('accrued_leave')
    # def _onchange_accrued_leave_Days(self):
    #     for record in self:
    #         # Extract the numeric part of the record's ID
    #         employee_id = int(''.join(filter(str.isdigit, str(record.id))))
    #
    #         # Check if there are any validated leave allocations for the employee
    #         validated_allocations = self.env['hr.leave.allocation'].search([
    #             ('employee_id', '=', employee_id),
    #             ('state', '=', 'validate')
    #         ])
    #
    #         if validated_allocations:
    #             if record.accrued_leave:
    #                 # Convert accrued_leave to datetime.date object
    #                 # accrued_leave_date = fields.Date.from_string(record.accrued_leave)
    #                 # accrued_leave_month = accrued_leave_date.month
    #                 accrued_leave_date = record.accrued_leave.month
    #                 record.accrued_leave_num_of_days = 0.00
    #
    #
    #                 # accrual_plans = self.env['hr.leave.accrual.plan'].search([('time_off_type_id.name', '=', 'Annual Vacation')])
    #                 accrual_plans = self.env['hr.leave.accrual.plan'].search([])
    #
    #                 for plan in accrual_plans:
    #                     for leave in plan.level_ids:
    #                         record.accrued_leave_num_of_days = accrued_leave_date * leave.added_value
    #         else:
    #             record.accrued_leave_num_of_days = 0.00





    @api.onchange('leave_entitle_days', 'air_ticket_entitle_days')
    def change_entitlement(self):
        # if self.leave_entitle_days:
        #     self.write({'entitlement' : self.leave_entitle_days})
        if self.air_ticket_entitle_days:
            self.write({'entitlement_ticket': self.air_ticket_entitle_days})

    @api.depends('entitlement', 'bfwd_previous_year', 'adjustments', 'utilised_this_year')
    def _compute_balance_leave(self):
        self.balance = (self.entitlement + self.bfwd_previous_year + self.adjustments) - self.utilised_this_year

    @api.depends('entitlement_ticket', 'bfwd_previous_year_ticket', 'adjustments_ticket', 'utilised_this_year_ticket')
    def _compute_balance_ticket(self):
        self.balance_ticket = (self.entitlement_ticket + self.bfwd_previous_year_ticket + self.adjustments_ticket) - self.utilised_this_year_ticket

    @api.constrains('leave_entitle_days')
    def _check_leave_entitle_days(self):
        for record in self:
            try:
                float(record.leave_entitle_days)
            except (TypeError, ValueError):
                raise ValidationError("The value for Leave Entitlement must be a valid float number.")

    @api.constrains('air_ticket_entitle_days')
    def _check_air_ticket_entitle_days(self):
        for record in self:
            try:
                float(record.air_ticket_entitle_days)
            except (TypeError, ValueError):
                raise ValidationError("The value for Air Ticket Entitlement must be a valid float number.")

    @api.depends('utilised_this_year', 'total_paid_leave', 'total_unpaid_leave', 'last_leave_date')
    def _compute_leave_details(self):
        leave_obj = self.env['hr.leave']
        for rec in self:
            validated_leaves = leave_obj.search([
                ('employee_id', '=', rec.id),
                ('state', '=', 'validate')
            ])

            total_paid_leave = sum(validated_leaves.mapped('paid_leave'))
            total_unpaid_leave = sum(validated_leaves.mapped('unpaid_leave'))
            ## Already working code
            # total_vacation_entitle = sum(validated_leaves.mapped('vacation_utilised'))

            ##Added on Annuval vacation leave based this calculation
            total_vacation_entitle = 0.00
            for leave in validated_leaves:
                if leave.holiday_status_id.code == 'AV':
                    total_vacation_entitle += leave.vacation_utilised

            rec.last_leave_date = validated_leaves and max(validated_leaves.mapped('date_from')).date() or False
            rec.total_paid_leave = total_paid_leave
            rec.total_unpaid_leave = total_unpaid_leave
            rec.utilised_this_year = total_vacation_entitle
            
            leave_encash = self.env['leave.encash'].search([('employee_id', '=', rec.id), ('state', 'in', ['approved', 'paid'])])
            if leave_encash:
                for leave in leave_encash:
                    rec.utilised_this_year -= leave.days_want
                    rec.utilised_this_year = abs(rec.utilised_this_year)
                
            
            