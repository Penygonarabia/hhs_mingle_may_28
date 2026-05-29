from odoo import api,fields,models,_


class EmployeeSalaryReport(models.TransientModel):
    
    _name = "employee.salary.report"
    
    
    employee_ids = fields.Many2many('hr.employee',string="Employee Name")
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,required=True)

    
    def print_salary_report(self):
        datas ={
            'model':'employee.salary.report',
            'form_data':self.read()[0],
            }
        return self.env.ref('payroll_employee_report.action_report_employee_salary_report_xlsx').report_action(self,data=datas)
        
