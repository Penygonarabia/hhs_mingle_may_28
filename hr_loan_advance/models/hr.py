# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import warnings, RedirectWarning


class hr_employee(models.Model):
    _inherit = 'hr.employee'


    def _get_loan_Advance_count(self):
        self.loan_count = self.env['hr.employee.loan.ps'].search_count([('employee_id', '=', self.id)])
        self.advance_count = self.env['hr.employee.advance.ps'].search_count([('employee_id', '=', self.id)])

    loan_count = fields.Integer(string='Loan', compute='_get_loan_Advance_count')
    advance_count = fields.Integer(string='Advance', compute='_get_loan_Advance_count')

    @api.model
    def loan_advance_payslip(self, employee, date_from, date_to, cate):
        result = 0
        rec = False
        if cate not in ('loan', 'advance'): return result
        domain = [('installment_date', '>=', date_from), ('installment_date', '<=', date_to), ('confirm', '=', True)]
        if cate == 'loan':
            line_obj = self.env['hr.employee.loan.line.ps']
        if cate == 'advance':
            line_obj = self.env['hr.employee.advance.line.ps']
        line_obj_ids = line_obj.search(domain)
        for record in line_obj_ids:
            if cate == 'loan':
                if record.hr_employee_loan_ps.employee_id.id == employee and record.hr_employee_loan_ps.state == 'approve':
                    result += record.amount
            if cate == 'advance':
                if record.hr_employee_advance_ps.employee_id.id == employee and record.hr_employee_advance_ps.state == 'approve':
                    result += record.amount

        return result
