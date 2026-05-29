from odoo import api,fields,models,_
from odoo.exceptions import ValidationError
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, time

class EmployeePayrollReport(models.TransientModel):
    
    _name = "employee.payroll.report"
    
    _description = "Employee Payroll Report"
    
    
    def _default_structure_id(self):
       structure_search = self.env['hr.payroll.structure'].search([],limit=1)
       return structure_search.id
           
    
    employee_ids = fields.Many2many('hr.employee',string="Employee Name")
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,required=True)

    department_ids = fields.Many2many('hr.department', string = "Department")
    
    job_title_ids = fields.Many2many('hr.job', string="Job Title")
    
    nationality_ids = fields.Many2many('res.country', string="Nationality")
    
    branch_location_ids = fields.Many2many('hr.work.location', string="Branch Location")
    
    from_date = fields.Date(string='From Date', required = True, default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    
    to_date = fields.Date(string='To Date',required = True, default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    
    structure_id = fields.Many2one('hr.payroll.structure',string="Structure", required = True, default=_default_structure_id)
    
    sort_by = fields.Selection([('department','Department'),('job_title','Job Title'),('branch_location','Location'),('nationality','Nationality'),('employee_no','Employee No')],string='Sort By')
    
    
    
    @api.constrains('from_date', 'to_date')
    def _check_from_date(self):
        if self.filtered(lambda c: c.to_date and c.from_date > c.to_date):
            raise ValidationError(_('From date Date must be less than Period To Date.'))
    
    
    def print_payroll_report(self):
        
        data = {
            
            'model':'employee.payroll.report',
             'form_data':self.read()[0]
            
            }
        
        return self.env.ref('employee_payroll_report.action_employee_payroll_report_xlsx').report_action(self,data=data)
        
        
        
    
    