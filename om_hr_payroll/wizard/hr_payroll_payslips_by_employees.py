# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import babel
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from pytz import timezone
import calendar
import logging
from datetime import timedelta
# from datetimerange import DateTimeRange


class HrPayslipEmployees(models.TransientModel):
    _name = 'hr.payslip.employees'
    _description = 'Generate payslips for all selected employees'
    
    
    @api.model
    def _default_payslip_run(self):
        active_id = self.env.context.get('active_id')
        payslip_search = self.env['hr.payslip.run'].browse(active_id)
        return payslip_search

    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employees', )

    payslip_run_id = fields.Many2one('hr.payslip.run', string="Payslip Run", default=_default_payslip_run)

    update_employee_ids = fields.Boolean(
        string="Update Employee IDs", default=False, compute='_compute_employee_ids',
        help="If set to True, only mid-joined employees will be included in the payslip.")
    
        
    
    @api.onchange('payslip_run_id')
    def _onchange_payslip_run(self):
        for rec in self:
            employee_ids = [(5, 0, 0)]
            if rec.payslip_run_id:
                for slip in rec.payslip_run_id.slip_ids:
                    if slip.state not in ['done', 'cancel', 'verify'] and slip.payroll_type not in ['leave', 'arrival']:
                        employee_ids.append((4, slip.employee_id.id))
            rec.employee_ids = employee_ids

    @api.onchange('payslip_run_id')
    def _onchange_payslip_run_id(self):
        if self.payslip_run_id:
            employee_ids = [slip.employee_id.id for slip in self.payslip_run_id.slip_ids]
            return {
                'domain': {
                    'employee_ids': [('id', 'not in', employee_ids), ('exit_date', '=', False), ('contract_warning', '=', False)]
                }
            }



    ## Newly added this code based on mid-join employee is update in employee_ids -- created on 30/09/2024
    @api.depends('payslip_run_id', 'employee_ids')
    def _compute_employee_ids(self):
        for record in self:
            # Ensure that payslip_run_id exists
            if record.payslip_run_id:
                # Check if start and end dates are present
                if record.payslip_run_id.date_start and record.payslip_run_id.date_end:
                    start_date = record.payslip_run_id.date_start
                    end_date = record.payslip_run_id.date_end

                    # Search for mid-joined employees
                    mid_joined_employees = self.env['hr.employee'].search([
                        ('contract_id.date_start', '>', start_date),
                        ('contract_id.date_start', '<=', end_date),
                    ])

                    # If mid_joined_employees exist, process each employee
                    if mid_joined_employees:
                        record.update_employee_ids = True

                        # Iterate through each mid-joined employee
                        for mid in mid_joined_employees:
                            # Append each mid employee ID to employee_ids
                            if mid.id not in record.employee_ids.ids:
                                # record.employee_ids = [(4, mid.id)]
                                # print(record.employee_ids, record.employee_ids)
                                existing_ids = record.employee_ids.ids
                                # Add mid.id to the end of the list
                                updated_ids = existing_ids + [mid.id]
                                # Update the employee_ids field with the new list (using (6, _, ids) to replace the entire list)
                                record.employee_ids = [(6, 0, updated_ids)]
                                # print("Updated employee_ids:", updated_ids)
                    else:
                        record.update_employee_ids = False
                else:
                    record.update_employee_ids = False
            else:
                record.update_employee_ids = False

    ## already working code
    # def compute_sheet(self):
    #     payslips = self.env['hr.payslip']
    #     [data] = self.read()
    #     active_id = self.env.context.get('active_id')
    #     if active_id:
    #         [run_data] = self.env['hr.payslip.run'].browse(active_id).read(['date_start', 'date_end', 'credit_note'])
    #     from_date = run_data.get('date_start')
    #     to_date = run_data.get('date_end')
    #     if not data['employee_ids']:
    #         raise UserError(_("You must select employee(s) to generate payslip(s)."))
    #     for employee in self.env['hr.employee'].browse(data['employee_ids']):
    #
    #         domain = [
    #             ('employee_id', '=', employee.id),
    #             ('date_from', '>=', from_date),
    #             ('date_to', '<=', to_date),
    #             ('state','in',['draft', 'verify'])
    #         ]
    #         payslip_search = payslips.search(domain)
    #         print("payslip_search", payslip_search)
    #         if not payslip_search:
    #             slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, employee.id, contract_id=False)
    #
    #             res = {
    #                 'employee_id': employee.id,
    #                 'name': slip_data['value'].get('name'),
    #                 'struct_id': slip_data['value'].get('struct_id'),
    #                 'contract_id': slip_data['value'].get('contract_id'),
    #                 'payslip_run_id': active_id,
    #                 'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
    #                 'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
    #                 'date_from': from_date,
    #                 'date_to': to_date,
    #                 'credit_note': run_data.get('credit_note'),
    #                 'company_id': employee.company_id.id,
    #             }
    #             payslips += self.env['hr.payslip'].create(res)
    #         if payslip_search:
    #             if payslip_search.state == 'draft':
    #                 payslip_search.unlink()
    #             if payslip_search.state == 'verify':
    #
    #             slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, employee.id, contract_id=False)
    #
    #             res = {
    #                 'employee_id': employee.id,
    #                 'name': slip_data['value'].get('name'),
    #                 'struct_id': slip_data['value'].get('struct_id'),
    #                 'contract_id': slip_data['value'].get('contract_id'),
    #                 'payslip_run_id': active_id,
    #                 'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
    #                 'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
    #                 'date_from': from_date,
    #                 'date_to': to_date,
    #                 'credit_note': run_data.get('credit_note'),
    #                 'company_id': employee.company_id.id,
    #             }
    #             payslips += self.env['hr.payslip'].create(res)
    #
    #     payslips.compute_sheet()
    #     return {'type': 'ir.actions.act_window_close'}

    #

    ## Newly added on already created vacation payslip is update in Payslips Batches -- created on 19/09/2024
    def compute_sheet(self):
        payslips = self.env['hr.payslip']
        [data] = self.read()
        active_id = self.env.context.get('active_id')

        if active_id:
            [run_data] = self.env['hr.payslip.run'].browse(active_id).read(['date_start', 'date_end', 'credit_note'])

        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')

        if not data['employee_ids']:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        for employee in self.env['hr.employee'].browse(data['employee_ids']):
            old_payslips = self.env['hr.payslip'].search(
                [('employee_id', '=', employee.id), ('date_from', '>=', from_date),
                 ('date_to', '<=', to_date), ('payroll_type', '=', 'payroll'), ('state', '=', 'draft')])
            if old_payslips:
                for payslip in old_payslips:
                    payslip.unlink()

        for employee in self.env['hr.employee'].browse(data['employee_ids']):
            domain = [
                ('employee_id', '=', employee.id),
                ('date_from', '>=', from_date),
                ('date_to', '<=', to_date),
                ('state', 'in', ['draft', 'verify']),
                ('payroll_type', 'in', ['leave', 'arrival'])
            ]

            payslip_search = payslips.search(domain)
            if payslip_search:
                for pay in payslip_search:
                    if pay:
                        # Proceed to create a new payslip
                        slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, employee.id,
                                                                                contract_id=False)
                        if employee.contract_id.date_start.month == from_date.month and employee.contract_id.date_start.year == to_date.year:
                            from_date = employee.contract_id.date_start
                        else:
                            from_date = from_date

                        res = {
                            'employee_id': employee.id,
                            'name': slip_data['value'].get('name'),
                            'struct_id': slip_data['value'].get('struct_id'),
                            'contract_id': slip_data['value'].get('contract_id'),
                            'payslip_run_id': active_id,
                            'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                            'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
                            'date_from': from_date,
                            'date_to': to_date,
                            'credit_note': run_data.get('credit_note'),
                            'company_id': employee.company_id.id,
                        }
                        payslips += self.env['hr.payslip'].create(res)
                    # elif pay.state == 'verify':
                    #     # If the state is 'verify', just append the existing payslip
                    #     payslips += pay
            else:
                # # No existing payslip found, delete old ones and create a new payslip
                # print("Employee without payslip:", employee.name)
                # old_payslips = self.env['hr.payslip'].search(
                #     [('employee_id', '=', employee.id), ('date_from', '>=', from_date),
                #      ('date_to', '<=', to_date)])
                # if old_payslips:
                #     for payslip in old_payslips:
                #         print("Deleting old payslip:", payslip.name)
                #         payslip.unlink()

                # Proceed to create a new payslip
                slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, employee.id,
                                                                        contract_id=employee.contract_id)

                if slip_data['value'].get('contract_id') == employee.contract_id.id:
                    from_start_date = run_data.get('date_start')
                    to_end_date = run_data.get('date_end')

                    if from_start_date and employee.contract_id.date_start and employee.contract_id.employee_id == employee:
                        if (employee.contract_id.date_start.month == from_start_date.month) and (
                                employee.contract_id.date_start.year == from_start_date.year):
                            from_date = employee.contract_id.date_start
                        else:
                            from_date = from_start_date

                    res = {
                        'employee_id': employee.id,
                        'name': slip_data['value'].get('name'),
                        'struct_id': slip_data['value'].get('struct_id'),
                        'contract_id': slip_data['value'].get('contract_id'),
                        'payslip_run_id': active_id,
                        'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                        'worked_days_line_ids': [(0, 0, x) for x in
                                                 slip_data['value'].get('worked_days_line_ids')],
                        'date_from': from_date,
                        'date_to': to_date,
                        'credit_note': run_data.get('credit_note'),
                        'company_id': employee.company_id.id,
                    }
                    payslips += self.env['hr.payslip'].create(res)
                    payslips._onchange_employee_number()

        payslips.compute_sheet()
        return {'type': 'ir.actions.act_window_close'}

