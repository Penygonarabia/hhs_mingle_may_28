from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import ValidationError



class LeaveEncashReport(models.TransientModel):
    _name = 'leave.encash.report'
    _description = 'Leave Encash Report'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    employee_ids = fields.Many2many("hr.employee", string="Employees")
    leave_type_ids = fields.Many2many("hr.leave.type", string="Leave Type")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,required=True)

    
    @api.onchange('end_date')
    def validate_date(self):
        if self.start_date > self.end_date:
            raise ValidationError(_("End Date Must Be Greater Than Start Date"))
        
    def print_report_excel(self):
        datas = {
            'model': 'leave.encash.report',
            'form_data': self.read()[0],
        }
        return self.env.ref('leave_encash_hr.action_report_leave_encash_report_xlsx').report_action(self,data=datas)

    def print_report_pdf(self):
        leave_encash_lst = []
        start_date = self.start_date
        end_date = self.end_date
        employee_ids = False
        leave_type_ids = False
        
        if self.employee_ids:
            employee_ids = self.employee_ids
        else:
            employee_ids = self.env['hr.employee'].search([])
        
        if self.leave_type_ids:
            leave_type_ids = self.env['hr.leave.type'].search([])
            
            
        for employee in employee_ids:
            employee_leave_encash_search = self.env['leave.encash'].search([('employee_id','=',employee.id),('date','>=',start_date),('date','<=',end_date)])   
            for leave in employee_leave_encash_search:
                vals = {
                    'emp_name':leave.employee_id.name,
                    'emp_no':leave.employee_id.employee_no,
                    'country_name':leave.employee_id.country_id.name,
                    'department':leave.employee_id.department_id.name,
                    'job_position':leave.employee_id.job_id.name,
                    'work_location':leave.employee_id.work_location_id.name,
                    'contract':leave.contract_id.name,
                     'leave_type':leave.leave_type_id.name,
                     'total_leave_carry':leave.leave_carry,
                     'applied_leave_encash':leave.days_want,
                     'amount':round(leave.amount,2),
                     'status':leave.state,
                     'reference':leave.name,
                     'applied_date':leave.date
                    }
                leave_encash_lst.append(vals)
        if not leave_encash_lst:
            raise ValidationError("Encash Leave Data is not there in the specific date range")        
        
        datas={
            'form_data':self.read()[0],
            'leave_encash':leave_encash_lst
            
            }
        
        return self.env.ref('leave_encash_hr.action_report_leave_encash_report_pdf').report_action(self,data=datas)