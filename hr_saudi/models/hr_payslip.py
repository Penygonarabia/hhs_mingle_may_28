# -*- coding: utf-8 -*-
import babel
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from pytz import timezone
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    attendance_ids = fields.One2many('hr.attendance', 'employee_id', string='Attendances',help='Attendances represented by payslip.')
    total_hours = fields.Float(string="Hours")
    contract_start_date = fields.Date('Contract Date')

    # @api.onchange('employee_id','contract_start_date', 'date_from', 'date_to')
    # def onchange_employee_attendance(self):
    #     for rec in self:
    #         rec.contract_start_date = rec.employee_id.contract_id.date_start
    #     if rec.contract_start_date == rec.employee_id.contract_id.date_start:
    #         rec.date_from = rec.employee_id.contract_id.date_start







