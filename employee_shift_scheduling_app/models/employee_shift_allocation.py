# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HREmployeeInherited(models.Model):
    _inherit = "hr.employee"

    allocation_ids = fields.One2many('employee.shift.allocation', 'employee_id', string='Allocation')
    workday_ids = fields.One2many('employee.work.day', 'employee_id', string='Work Days')
    weekend_ids = fields.One2many('employee.week.end', 'employee_id', string='Week Ends')


class EmployeeShiftAllocation(models.Model):
    _name = "employee.shift.allocation"
    _description = "Employee Shift Allocation"
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')
    shift_id = fields.Many2one('employee.shift', string='Shift', tracking=True)
    user_id = fields.Many2one('res.users', string='Responsible', store=True, related='shift_id.user_id')
    shift_type_id = fields.Many2one('shift.type', string='Shift Type', tracking=True)
    from_date = fields.Date(string='From Date', tracking=True)
    to_date = fields.Date(string='To Date', tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,
                                 tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'), ('cancel', 'Cancel')], default='draft',
                             tracking=True)

    workday_ids = fields.One2many('employee.work.day', 'allocation_id', string='Work Days')
    weekend_ids = fields.One2many('employee.week.end', 'allocation_id', string='Week Ends')

    @api.model
    def create(self, vals):
        res = super(EmployeeShiftAllocation, self).create(vals)
        res['name'] = self.env['ir.sequence'].next_by_code('employee.shift.allocation') or 'New'
        template_id = self.env.ref('employee_shift_scheduling_app.employee_shift_allocation_mail_template').id
        template = self.env['mail.template'].browse(template_id)
        # template.subject = vals['name']
        template.sudo().send_mail(res.id, force_send=True)
        return res

    @api.onchange('shift_id')
    def onchange_shift_id(self):
        for rec in self:
            rec.shift_type_id = rec.shift_id.shift_type_id

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'


class EmployeeWorkDay(models.Model):
    _name = "employee.work.day"
    _description = "Employee Shift Allocation"
    _rec_name = 'employee_id'

    allocation_id = fields.Many2one('employee.shift.allocation', string='Shift Allocation')
    shift_id = fields.Many2one('employee.shift', string='Shift')
    date = fields.Date(string='Date of Week')
    employee_id = fields.Many2one('hr.employee', string='Employee', related='allocation_id.employee_id', store=True)
    user_id = fields.Many2one('res.users', string='Responsible', related='allocation_id.shift_id.user_id', store=True)

    def name_get(self):
        res = []
        for rec in self:
            name = str(rec.employee_id.name) + " " + str(rec.date)
            res.append((rec.id, name))
        return res


class EmployeeWeekEnd(models.Model):
    _name = "employee.week.end"
    _description = "Employee Week End"
    _rec_name = 'allocation_id'

    allocation_id = fields.Many2one('employee.shift.allocation', string='Shift Allocation')
    week_off_id = fields.Many2one('employee.week.off', string='Day of Week')
    shift_id = fields.Many2one('employee.shift', string='Shift', related='allocation_id.shift_id', store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', related='allocation_id.employee_id', store=True)
    user_id = fields.Many2one('res.users', string='Responsible', related='allocation_id.shift_id.user_id', store=True)
    date = fields.Date(string='Date of Week')

    def name_get(self):
        res = []
        for rec in self:
            name = str(rec.employee_id.name) + " " + str(rec.date)
            res.append((rec.id, name))
        return res
