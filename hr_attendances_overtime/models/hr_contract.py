# See LICENSE file for full copyright and licensing details

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta


class HrContract(models.Model):
    """Inherit Hr Contract ."""

    _inherit = 'hr.contract'

    attend_police_id = fields.Many2one(
        'hr.attendance.policies', string='Policy')

    attendance_required_bool = fields.Boolean(string="Attendance required", default=False)
    # attendance_grace_time = fields.Float('Grace Time')

    mail_required_bool = fields.Boolean(string = "Mail required (Y/N)", default = False,help = "Absence,Late in,Early out Mail is send to executive or not")

class HrEmployee(models.Model):
    """Inherit Hr Employee to add Attendance Sheet Many2one."""

    _inherit = 'hr.employee'
    _description = 'Description'

    attendance_sheet_id = fields.Many2one(
        'hr.attendance.sheet', string='Attendance Sheet')
    
    '''Absence email send to Employee  '''
    #currently working but commented by Vijaya bhaskar on July 29 -2025 because mail is directly taken from attendance sheet
    # @api.model
    # def _email_for_absence_employee(self):
    #     yesterday = fields.Date.today() - relativedelta(days = 1)
    #     today = fields.Date.today()
    #     yesterday_str = yesterday.strftime('%d-%m-%Y')
    #
    #
    #     # employee_search = self.env['hr.employee'].search([
    #     #                 ('state','!=','exit'),('contract_warning','=', False),
    #     #                 ('contract_id.attendance_required_bool','=',True),
    #     #                 ('id','in',('7457','7344','7300','7385'))
    #     #                 ])
    #
    #     employee_search = self.env['hr.employee'].search([
    #                     ('state','!=','exit'),('contract_warning','=', False),
    #                     ('contract_id.attendance_required_bool','=',True),
    #                     ('contract_id.mail_required_bool','=',True),
    #                     ('contract_id.state','=','open')
    #                     ])
    #
    #     for employee in employee_search:
    #         holiday_records_search = self.env['resource.calendar.leaves'].search([
    #                                     ('resource_id', '=', False),
    #                                     ('date_from', '<=', yesterday),
    #                                     ('date_to', '>=', yesterday),
    #                                 ],limit=1)
    #
    #         if not holiday_records_search: 
    #             calendar_search = employee.resource_calendar_id
    #             if calendar_search:
    #                 weekday = yesterday.weekday()
    #                 attendance_line = calendar_search.attendance_ids.filtered(lambda a: int(a.dayofweek)==weekday)
    #                 # if not attendance_line:
    #                 #     continue
    #                 if attendance_line:
    #                     attendance_search = self.env['hr.attendance'].search([
    #                                         ('employee_id','=', employee.id),
    #                                         ('check_in','>=',  yesterday),
    #                                         ('check_in','<', today)
    #                                         ], limit=1)
    #
    #                     if not attendance_search:
    #
    #                             leave_search = self.env['hr.leave'].search([
    #                                                     ('employee_id', '=', employee.id),
    #                                                     ('state', '=', 'validate'),
    #                                                     ('request_date_from', '<', today),
    #                                                     ('request_date_to', '>=', yesterday)
    #                                                 ], limit=1)
    #
    #                             if not leave_search:
    #                                 # yesterday = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")
    #                                 template = self.env.ref('hr_attendances_overtime.email_template_for_absent_employee')
    #                                 if template :
    #                                     template.with_context(yesterday_str=yesterday_str).send_mail(employee.id, force_send=True)
    #                                     # template.send_mail(employee.id,force_send = True)
    #
    #                                     # template.with_context(yesterday_str=yesterday).send_mail(employee.id,force_send = True)
    #
    #

                


class HrPayslip(models.Model):
    """Inherit Hr Payslip."""

    _inherit = 'hr.payslip'
    _description = 'Pay Slip'

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """Method is overriden to add worked days line in Payslip."""
        res = super(HrPayslip, self).get_worked_day_lines(
            contracts, date_from, date_to)
        sheet_id = self.env['hr.attendance.sheet'].search(
            [('employee_id', '=', self.employee_id.id),
             ('request_date_from', '>=', self.date_from),
             ('request_date_to', '<=', self.date_to),
             ('state','in',['approved','export'])
             ])

        if sheet_id:
            if sheet_id.no_overtime:
                res.append({
                    'name': 'Overtime',
                    'code': 'OVT',
                    'number_of_days': sheet_id.no_overtime or False,
                    'number_of_hours': sheet_id.total_overtime or False,
                    'contract_id': self.contract_id.id or False
                })
            if sheet_id.no_latein:
                res.append({
                    'name': 'Late in',
                    'code': 'LATE',
                    'number_of_days': sheet_id.no_latein or False,
                    'number_of_hours': sheet_id.total_latein or False,
                    'contract_id': self.contract_id.id or False
                })
            if sheet_id.no_absence:
                res.append({
                    'name': 'Absence',
                    'code': 'ABS',
                    'number_of_days': sheet_id.no_absence or False,
                    'number_of_hours': sheet_id.total_absence or False,
                    'contract_id': self.contract_id.id or False
                })
            if sheet_id.no_difftime:
                res.append({
                    'name': 'DIFFRENCE TIME',
                    'code': 'DIFFT',
                    'number_of_days': sheet_id.no_difftime or False,
                    'number_of_hours': sheet_id.total_difftime or False,
                    'contract_id': self.contract_id.id or False
                })

            if sheet_id.no_early_checkout:
                res.append({
                    'name' : 'Early Check Out',
                    'code':'EARLYOUT',
                    'number_of_days':sheet_id.no_early_checkout or False,
                    'number_of_hours':sheet_id.total_early_checkout or False,
                    'contract_id':self.contract_id.id or False
                    
                    })
        return res
