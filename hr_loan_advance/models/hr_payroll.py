from odoo import models, fields, api, _
from odoo.exceptions import warnings, RedirectWarning, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, time


class HrPayslip(models.Model):
    _inherit = "hr.payslip"


    # def action_payslip_done(self):
    #     if not self.employee_id.address_home_id:
    #         raise ValidationError(_('You must add the home adress of employee!'))
    #     loan_ids = self.env['hr.employee.loan.ps'].search([('employee_id', '=', self.employee_id.id), ('state', '=', 'approve')])
    #     for record in loan_ids:
    #         for line in record.hr_employee_loan_line_ps:
    #             # if line.installment_date >= self.date_from and line.installment_date <= self.date_to and line.confirm == True and line.state == 'notdeducted':
    #             if (line.installment_date.year == self.date_from.year) and (line.installment_date.month == self.date_from.month) and (line.confirm == True) and (line.state == 'notdeducted'):
    #                 line.state = 'deducted'
    #                 record.loan_open = True
    #
    #     advance_ids = self.env['hr.employee.advance.ps'].search([('employee_id', '=', self.employee_id.id)])
    #     for record in advance_ids:
    #         for line in record.hr_employee_advance_line_ps:
    #             # if line.installment_date >= self.date_from and line.installment_date <= self.date_to and line.confirm == True and line.state == 'notdeducted':
    #             if (line.installment_date.year == self.date_from.year) and (line.installment_date.month == self.date_from.month) and (line.confirm == True) and (line.state == 'notdeducted'):
    #                 line.state = 'deducted'
    #                 record.advance_open = True
    #     return super(HrPayslip, self).action_payslip_done()

    def action_payslip_done(self):
        if not self.employee_id.address_id:
            raise ValidationError(_('You must add the home adress of employee!'))
        if self.av_loan_bool:
            if self.date_from and self.leave_id.request_date_to:
                start_date = self.date_from
                end_date = self.leave_id.request_date_to
                print("end_date, start_date", end_date, start_date)

                current_date = start_date

                while current_date <= end_date:
                    loan_added_payslips = self.env['hr.employee.loan.ps'].search([
                        ('employee_id', '=', self.employee_id.id)
                    ])
                    for emp_loan_line in loan_added_payslips:
                        for emp_loan in emp_loan_line.hr_employee_loan_line_ps:
                            if emp_loan and emp_loan.installment_date:
                                if (emp_loan.installment_date.year == current_date.year and
                                    emp_loan.installment_date.month == current_date.month) and (
                                        emp_loan.confirm == True) and (emp_loan.state == 'notdeducted'):
                                    emp_loan.state = 'deducted'
                                    emp_loan_line.loan_open = True

                    advance_added_payslips = self.env['hr.employee.advance.ps'].search([
                        ('employee_id', '=', self.employee_id.id)
                    ])
                    for emp_advance_line in advance_added_payslips.hr_employee_advance_line_ps:
                        for emp_advance in emp_advance_line.hr_employee_advance_line_ps:
                            if emp_advance and emp_advance.installment_date:
                                if (emp_advance.installment_date.year == current_date.year and
                                    emp_advance.installment_date.month == current_date.month) and (
                                        emp_advance.confirm == True) and (emp_advance.state == 'notdeducted'):
                                    emp_advance.state = 'deducted'
                                    emp_advance_line.advance_open = True

                    current_date = current_date + relativedelta(months=1)
                    print("current_date", current_date)

        else:
            loan_ids = self.env['hr.employee.loan.ps'].search(
                [('employee_id', '=', self.employee_id.id), ('state', '=', 'approve')])
            for record in loan_ids:
                for line in record.hr_employee_loan_line_ps:
                    # if line.installment_date >= self.date_from and line.installment_date <= self.date_to and line.confirm == True and line.state == 'notdeducted':
                    if (line.installment_date.year == self.date_from.year) and (
                            line.installment_date.month == self.date_from.month) and (line.confirm == True) and (
                            line.state == 'notdeducted'):
                        line.state = 'deducted'
                        record.loan_open = True

            advance_ids = self.env['hr.employee.advance.ps'].search([('employee_id', '=', self.employee_id.id)])
            for record in advance_ids:
                for line in record.hr_employee_advance_line_ps:
                    # if line.installment_date >= self.date_from and line.installment_date <= self.date_to and line.confirm == True and line.state == 'notdeducted':
                    if (line.installment_date.year == self.date_from.year) and (
                            line.installment_date.month == self.date_from.month) and (line.confirm == True) and (
                            line.state == 'notdeducted'):
                        line.state = 'deducted'
                        record.advance_open = True
        return super(HrPayslip, self).action_payslip_done()
