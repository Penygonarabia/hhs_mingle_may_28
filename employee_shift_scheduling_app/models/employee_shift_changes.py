# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class EmployeeShiftChanges(models.Model):
    _name = "employee.shift.changes"
    _description = "Employee Shift Changes"
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')
    shift_id = fields.Many2one('employee.shift', string='Shift', tracking=True)
    allocation_id = fields.Many2one('employee.shift.allocation', string='Allocation', tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,
                                 tracking=True)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('process', 'Process'), ('approve', 'Approve'), ('cancel', 'Cancel')],
                             default='draft',
                             tracking=True)
    note = fields.Text(string='Note')
    workday_ids = fields.Many2many('employee.work.day', 'rel_shift_change_work_day', 'shift_change_id', 'workday_id',
                                   string='Work Days')

    @api.model
    def create(self, vals):
        res = super(EmployeeShiftChanges, self).create(vals)
        res['name'] = self.env['ir.sequence'].next_by_code('employee.shift.changes') or 'New'
        return res
        # return super(EmployeeShiftAllocation, self).create(vals)

    def action_process(self):
        for rec in self:
            rec.state = 'process'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def action_approve(self):
        for rec in self:
            template_id = self.env.ref('employee_shift_scheduling_app.employee_shift_changes_mail_template').id
            template = self.env['mail.template'].browse(template_id)
            template.sudo().send_mail(rec.id, force_send=True)
            rec.state = 'approve'
