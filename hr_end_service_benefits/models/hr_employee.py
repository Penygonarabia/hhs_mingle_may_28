# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from dateutil import relativedelta
from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo import tools, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT


class Employee(models.Model):
    _name = 'hr.employee'
    _inherit = 'hr.employee'

    def _get_end_service_benefits_count(self):
        """compute number of rewords for employee"""
        for record in self:
            counter = self.env['hr.end.service.benefit'].search_count(
                [('employee_id', '=', record.id)])
            record.end_service_benefits_count = counter

    end_service_benefits_count = fields.Integer(string="Rewards Count", compute=_get_end_service_benefits_count)
    hiring_date = fields.Date(string="Hiring Date")
    joining_date = fields.Date(
        string='Joining Date',
        help="Employee joining date computed from the contract start date",
        compute='_compute_joining_date', store=True, readonly=False)
    address_home_id = fields.Many2one(
        'res.partner', 'Private Address',
        help='Enter here the private address of the employee, not the one linked to your company.',
        groups="base.group_user")

    @api.depends('contract_id')
    def _compute_joining_date(self):
        for rec in self:
            rec.joining_date = min(rec.contract_id.mapped('date_start')) \
                if rec.contract_id else False


class LeaveType(models.Model):
    _inherit = 'hr.leave.type'



    def get_days(self, employee_id):
        return self.get_employees_days([employee_id])[employee_id]