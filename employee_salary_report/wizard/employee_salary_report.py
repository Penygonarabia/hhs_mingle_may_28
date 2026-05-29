from odoo import api,fields,models,_
from odoo.exceptions import ValidationError


class EmployeeSalaryReport(models.TransientModel):
    
    _name = "employee.salary.report"
    _description = "Employee Salary Report"
    
    employee_ids = fields.Many2many('hr.employee',string="Employee Name")
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,required=True)

    department_ids = fields.Many2many('hr.department', string = "Department")
    
    job_title_ids = fields.Many2many('hr.job', string="Job Title")
    
    nationality_ids = fields.Many2many('res.country', string="Nationality")
    
    branch_location_ids = fields.Many2many('hr.work.location', string="Branch Location")
    
    from_joining_date = fields.Date(string='From Joining Date')
    
    to_joining_date = fields.Date(string='To Joining Date')
    
    from_termination_date = fields.Date(string='From Termination Date')
    
    to_termination_date = fields.Date(string='To Termination Date')
    
    from_contract_expiry_date = fields.Date(string='From Contract Expiry Date')
    
    to_contract_expiry_date = fields.Date(string='To Contract Expiry Date')
    
    
    sort_by = fields.Selection([('department','Department'),('job_title','Job Title'),('branch_location','Location'),('nationality','Nationality'),('employee_no','Employee No')],string='Sort By')
    
    employee_status = fields.Selection([('all','All'),('active','Active'),('terminated','Terminated')],string="Employee Status", default='all', required = True)
    
    
    @api.constrains('from_joining_date', 'to_joining_date')
    def _check_salary_from_joining_date(self):
        if self.filtered(lambda c: c.to_joining_date and c.from_joining_date > c.to_joining_date):
            raise ValidationError(_('From Joining Date must be less than Period To Joining Date.'))
    
    @api.constrains('from_termination_date', 'to_termination_date')
    def _check_salary_from_termination_date(self):
        if self.filtered(lambda c: c.to_termination_date and c.from_termination_date > c.to_termination_date):
            raise ValidationError(_('from termination date must be less than to termination date.'))
  
    
    @api.constrains('from_contract_expiry_date', 'to_contract_expiry_date')
    def _check_salary_from_termination_date(self):
        if self.filtered(lambda c: c.to_contract_expiry_date and c.from_contract_expiry_date > c.to_contract_expiry_date):
            raise ValidationError(_('from contract expiry date must be less than to contract expiry date.'))
  
            
    @api.onchange('from_joining_date')
    def _onchange_salary_from_joining_date(self):
        for rec in self:
            if rec.from_joining_date:
                rec.to_joining_date = rec.from_joining_date  
                
                
    @api.onchange('from_termination_date')
    def _onchange_salary_from_termination_date(self):
        for rec in self:
            if rec.from_termination_date:
                rec.to_termination_date = rec.from_termination_date  
    
    
    @api.onchange('from_contract_expiry_date')
    def _onchange_salary_from_contract_expiry_date(self):
        for rec in self:
            if rec.from_contract_expiry_date:
                rec.to_contract_expiry_date = rec.from_contract_expiry_date   
    
    
    def print_salary_report(self):
        datas ={
            'model':'employee.salary.report',
            'form_data':self.read()[0],
            }
        return self.env.ref('employee_salary_report.action_employee_salary_report_xlsx').report_action(self,data=datas)
        
