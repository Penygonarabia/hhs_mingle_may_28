from odoo import api,fields,models,_
from odoo.exceptions import ValidationError

class EmployeeDocumentsRenewalReport(models.TransientModel):
    
    _name = "employee.renewal.report"
    _description = "Employee Renewal Report"
    
    
    employee_ids = fields.Many2many('hr.employee',string="Employee Name")
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,required=True)

    
    department_ids = fields.Many2many('hr.department', string = "Department")
    
    job_title_ids = fields.Many2many('hr.job', string="Job Title")
    
    nationality_ids = fields.Many2many('res.country', string="Nationality")
    
    branch_location_ids = fields.Many2many('hr.work.location', string="Branch Location")
    
    from_expiry_date = fields.Date(string='From Expiry Date')
    
    to_expiry_date = fields.Date(string='To Expiry Date')
    
    # document_type = fields.Selection([('all','All'),('passport','Passport'),('iqama','Iqama')],string="Document Type")
    
    document_type_ids = fields.Many2many('employee.checklist',string="Document Type")

   
    sort_by = fields.Selection([('department','Department'),('job_title','Job Title'),('branch_location','Location'),('nationality','Nationality'),('employee_no','Employee No')],string='Sort By')
    
    employee_status = fields.Selection([('all','All'),('active','Active'),('terminated','Terminated')],string="Employee Status", default='all', required = True)
    
    
    
    @api.constrains('from_expiry_date', 'to_expiry_date')
    def _check_from_expiry_date(self):
        if self.filtered(lambda c: c.to_expiry_date and c.from_expiry_date > c.to_expiry_date):
            raise ValidationError(_('From Expiry date Date must be less than Period To Expiry Date.'))
    
             
    @api.onchange('from_expiry_date')
    def _onchangefrom_expiry_date(self):
        for rec in self:
            if rec.from_expiry_date:
                rec.to_expiry_date = rec.from_expiry_date  
                    
    
    def print_renewal_report(self):
        datas = {
            'model': 'employee.renewal.report',
            'form_data': self.read()[0],
        }
        return self.env.ref('employee_document_renewal_report.action_employee_renewal_report_xlsx').report_action(self, data=datas)
    
    
    def print_renewal_report_pdf(self):
        
        selection_lst = []
        
        domain = []
        
        
        domain = [('employee_ref', 'in', self.employee_ids.ids if self.employee_ids else self.env['hr.employee'].search([]).ids)]

        if self.from_expiry_date and self.to_expiry_date:
            domain += [('expiry_date', '<=', self.to_expiry_date), ('expiry_date', '>=', self.from_expiry_date)]

        if self.employee_status:
            if self.employee_status == 'all':
                domain += ['|', ('employee_ref.contract_warning', '=', False),
                           ('employee_ref.contract_warning', '=', True)]
            elif self.employee_status == 'active':
                domain += [('employee_ref.state', '=', 'draft'), ('employee_ref.contract_warning', '=', False)]
            elif self.employee_status == 'terminated':
                domain += ['|', ('employee_ref.state', '=', 'exit'), ('employee_ref.contract_warning', '=', True)]

        
        if self.document_type_ids:
            domain += [('document_name','in',self.document_type_ids.ids)]
      
        if self.department_ids:
            domain += [('employee_ref.department_id', 'in', self.department_ids.ids)]

        if self.job_title_ids:
            domain += [('employee_ref.job_id', 'in', self.job_title_ids.ids)]

        if self.nationality_ids:
            domain += [('employee_ref.country_of_birth', 'in', self.nationality_ids.ids)]

        if self.branch_location_ids:
            domain += [('employee_ref.work_location_id', 'in', self.branch_location_ids.ids)]

        renewal_search = self.env['hr.employee.document'].search(domain)
        renewal_search = renewal_search.sorted(key=lambda c:c.employee_ref.name.lower())

      
        if self.sort_by:
            if self.sort_by == 'department':
                renewal_search = renewal_search.filtered(lambda c: c.employee_ref.department_id)
                renewal_search = renewal_search.sorted(key=lambda c: c.employee_ref.department_id.name.lower())

            elif self.sort_by == 'job_title':
                renewal_search = renewal_search.filtered(lambda c: c.employee_ref.job_id)
                renewal_search = renewal_search.sorted(key=lambda c: c.employee_ref.job_id.name.lower())

            elif self.sort_by == 'nationality':
                renewal_search = renewal_search.filtered(lambda c: c.employee_ref.country_of_birth)
                renewal_search = renewal_search.sorted(key=lambda c: c.employee_ref.country_of_birth.name.lower())

            elif self.sort_by == 'branch_location':
                renewal_search = renewal_search.filtered(lambda c: c.employee_ref.work_location_id)
                renewal_search = renewal_search.sorted(key=lambda c: c.employee_ref.work_location_id.name.lower())

            elif self.sort_by == 'employee_no':
                renewal_search = renewal_search.sorted(key = lambda c:(
                    0 if c.employee_ref.employee_no and isinstance(c.employee_ref.employee_no,str) and c.employee_ref.employee_no.isdigit() else 1,
                    int(c.employee_ref.employee_no) if c.employee_ref.employee_no and isinstance(c.employee_ref.employee_no,str) and c.employee_ref.employee_no.isdigit() else c.employee_ref.employee_no or ' '
                    ))
        
        
        if self.department_ids:
            renewal_search = renewal_search.sorted(key=lambda c: c.employee_ref.department_id.name.lower())

        if self.job_title_ids:
            renewal_search = renewal_search.sorted(key=lambda c: c.employee_ref.job_id.name.lower())

        if self.nationality_ids:
            renewal_search = renewal_search.sorted(key=lambda c: c.employee_ref.country_of_birth.name.lower())

        
        if self.branch_location_ids:
            renewal_search = renewal_search.sorted(key=lambda c: c.employee_ref.work_location_id.name.lower())
        
       
        renewal_lst = []
        for renewal in renewal_search:
            selection_lst.append({
                
                'emp_no':renewal.employee_ref.employee_no or ' ',
                'emp_name':renewal.employee_ref.display_name,
                'dept_name':renewal.employee_ref.department_id.name or ' ',
                'job_name':renewal.employee_ref.job_id.name or ' ',
                'nation_name':renewal.employee_ref.country_of_birth.name or ' ',
                'work_location':renewal.employee_ref.work_location_id.name or ' ',
                'document_name':renewal.document_name.name or ' ',
                'document_number':renewal.display_name or ' ',
                'place_of_issue':renewal.place_city_id.display_name or ' ',
                'issue_date':renewal.issue_date.strftime("%d-%m-%Y") if renewal.issue_date else ' ',
                'expiry_date':renewal.expiry_date.strftime("%d-%m-%Y") if renewal.expiry_date else ' ',
            
                })
            
        
            renewal_lst.append(renewal.employee_ref.display_name)
        
        if len(renewal_lst) == 0:
            raise ValidationError("No Renewal documents for the Employees is not there in this range")
    
        data = {
            'form_data':self.read()[0],
            'selection':selection_lst,
            'from_expiry_date':self.from_expiry_date.strftime("%d-%m-%Y") if self.from_expiry_date else ' ',
            'to_expiry_date':self.to_expiry_date.strftime('%d-%m-%Y') if self.to_expiry_date else ' ',
                        
            }
    
        return self.env.ref('employee_document_renewal_report.action_employee_renewal_report_pdf').with_context(landscape=True).report_action(self,data=data)
    
    
    
    
    
