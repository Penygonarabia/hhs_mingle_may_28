from odoo import api, fields, models, _
from odoo.tools import float_round
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, time

class TerminationDetailsReport(models.TransientModel):
    
    _name = "termination.details.report"

    from_date = fields.Date(string='From Date', required=True,  default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    to_date = fields.Date(string='To Date', required=True,  default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id, required=True)
    employee_ids = fields.Many2many('hr.employee',string="Employee Name")

    
    def print_termination_details_excel(self):
        datas = {
            'model': 'termination.details.report',
            'form_data': self.read()[0],
        }
        return self.env.ref('termination_details_report.action_report_termination_details_report_xlsx').report_action(self,data=datas)

    def print_termination_details_report(self):
        selection_list = []
        employee_ids = False
        no_of_units = 0.00
        last_work_date = False
        if self.employee_ids:
            employee_ids = self.employee_ids
        else:
            employee_ids = self.env['hr.employee'].search(['|',('active', '=', True),  ('active','=',False)])
        for employee in employee_ids:
            eos_search = self.env['hr.end.service.benefit'].search([('employee_id', '=', employee.id), ('date', '>=', self.from_date), ('date', '<=', self.to_date)])
            termination_search = self.env['hr.exit'].search([('employee_id', '=', eos_search.employee_id.id)])
            for eos in eos_search:
                benefit_type = eos.end_service_benefit_type_id.name
                employee_name = eos.employee_id.name
                emp_no = eos.employee_id.employee_no
                gender = dict(employee._fields['gender'].selection).get(employee.gender)
                job_title = eos.employee_id.job_id.name
                location = eos.employee_id.work_location_id.name
                if eos.date:
                   eos_date = eos.date.strftime("%d-%m-%Y") or ''
                else:
                    eos_date = ''
                if employee.joining_date:
                   joining_date = employee.joining_date.strftime("%d-%m-%Y") or ''
                else:
                    joining_date = ''
                for term in termination_search:
                    if term.last_work_date:
                       last_work_date = term.last_work_date.strftime("%d-%m-%Y") or ''
                    else:
                        last_work_date = ''
                total_worked_days = float_round(eos.total_days, 2)
                amount = float_round(eos.available_amount, 2)
                selection_list.append({
                    'benefit_type': benefit_type,
                    'emp_no': emp_no,
                    'employee_name': employee_name,
                    'gender': gender,
                    'job_title': job_title,
                    'location': location,
                    'eos_date': eos_date,
                    'joining_date': joining_date,
                    'last_work_date': last_work_date,
                    'total_worked_days': total_worked_days,
                    'amount': amount,

                })
        if not selection_list:
            raise UserError("No data found for the selected Employees and date range.")
        from_date = self.from_date.strftime("%d-%m-%Y")
        to_date = self.to_date.strftime("%d-%m-%Y")
        data = {
            'form_data': self.read()[0],
            'from_date': from_date,
            'to_date': to_date,
            'selection': selection_list,
        }
        return self.env.ref('termination_details_report.action_termination_details_report_pdf').with_context(landscape=True).report_action(self, data=data)

