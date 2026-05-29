from datetime import timedelta

from odoo import models, fields, api, _


class BulkAllocationWizard(models.TransientModel):
    _name = "bulk.allocation.wizard"
    _description = "Bulk Allocation Wizard"
    _rec_name = 'shift_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    shift_id = fields.Many2one('employee.shift', string='Shift')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    employee_ids = fields.Many2many('hr.employee', 'rel_employee_wizard', 'wizard_id', 'employee_id', string='Employee')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,
                                 tracking=True)

    weekend_ids = fields.One2many('bulk.week.end', 'wizard_id', string='Weeks')

    def action_create_shift(self):
        for rec in self:
            start_date = rec.from_date
            end_date = rec.to_date
            delta = timedelta(days=rec.from_date.day)
            weekend_vals = []
            date = False
            for line_id in rec.weekend_ids:
                while start_date <= end_date:
                    if start_date.weekday() == line_id.week_off_id.day_no:
                        date = start_date
                    start_date += delta
                vals = {
                    'week_off_id': line_id.week_off_id.id,
                    'date': date,
                }
                weekend_vals.append((0, 0, vals))
            start_date1 = rec.from_date
            end_date1 = rec.to_date
            delta1 = timedelta(days=rec.from_date.day)
            workday_vals = []
            while start_date1 <= end_date1:
                if start_date1 != date:
                    vals = {
                        'shift_id': rec.shift_id.id,
                        'date': start_date1.strftime("%Y-%m-%d"),
                    }
                    workday_vals.append((0, 0, vals))
                start_date1 += delta1
            for employee_id in rec.employee_ids:
                vals = {
                    "employee_id": employee_id.id,
                    "shift_id": rec.shift_id.id,
                    "company_id": rec.company_id.id,
                    "shift_type_id": rec.shift_id.shift_type_id.id,
                    "from_date": rec.from_date,
                    "to_date": rec.to_date,
                    "weekend_ids": weekend_vals,
                    "workday_ids": workday_vals,
                    "state": 'draft',
                }
                self.env["employee.shift.allocation"].sudo().create(vals)


class EmployeeWeekEnd(models.TransientModel):
    _name = "bulk.week.end"
    _description = "Bulk Week End"
    _rec_name = 'wizard_id'

    wizard_id = fields.Many2one('bulk.allocation.wizard', string='Shift Allocation')
    week_off_id = fields.Many2one('employee.week.off', string='Day of Week')
    week_day_ids = fields.Many2many('employee.week.day', 'rel_wizard_week_day', 'wizard_line_id', 'week_day_id',
                                    string='Number of Week')
