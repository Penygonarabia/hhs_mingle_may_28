from odoo import api, fields, models, _


class EmployeeCustodyReport(models.TransientModel):
    _name = "employee.custody.report"

    employee_ids = fields.Many2many('hr.employee', string="Employee Name")

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,
                                 required=True)
    
    
    department_ids = fields.Many2many('hr.department', string = "Department")
    
    job_title_ids = fields.Many2many('hr.job', string="Job Title")
    
    nationality_ids = fields.Many2many('res.country', string="Nationality")
    
    branch_location_ids = fields.Many2many('hr.work.location', string="Branch Location")
    
    from_request_date = fields.Date(string='From Request Date')
    
    to_request_date = fields.Date(string='To Request Date')
    
    from_return_date = fields.Date(string='From Return Date')
    
    to_return_date = fields.Date(string='To Return Date')
    #
    # from_contract_expiry_date = fields.Date(string='From Contract Expiry Date')
    #
    # to_contract_expiry_date = fields.Date(string='To Contract Expiry Date')
    #
    #
    asset_type_ids = fields.Many2many('account.asset.category',string="Property")
    
    approval_status = fields.Selection([('all','All'),('draft','Draft'),('waiting_for_approval','Waiting For Approval'),('approved','Approved'),('rejected','Rejected'),('returned','Returned')],string="Approval Status")

    sort_by = fields.Selection([('department','Department'),('job_title','Job Title'),('branch_location','Location'),('nationality','Nationality')],string='Sort By')
    
    employee_status = fields.Selection([('all','All'),('active','Active'),('terminated','Terminated')],string="Employee Status", default='all', required = True)
    
    
    

    def print_custody_report(self):
        datas = {
            'model': 'employee.custody.report',
            'form_data': self.read()[0],
        }
        return self.env.ref('hr_custody.action_report_employee_custody_report_xlsx').report_action(self, data=datas)

    def print_custody_pdf_report(self):
        selection_list = []
        employee_ids = False
        if self.employee_ids:
            employee_ids = self.employee_ids
        else:
            employee_ids = self.env['hr.employee'].search([])
        for employee in employee_ids:
            hr_custody = self.env['hr.custody'].search([('employee', '=', employee.id)])
            for custody in hr_custody:
                employee_name = custody.employee.display_name
                code = custody.name
                custody_name = custody.custody_name.display_name
                asset_type = custody.asset_types.display_name
                reason = custody.purpose
                if custody.date_request:
                    request_date = custody.date_request.strftime("%d-%m-%Y") or ''
                else:
                    request_date = ''
                if custody.return_date:
                    return_date = custody.return_date.strftime("%d-%m-%Y") or ''
                else:
                    return_date = ''
                Status = dict(custody._fields['state'].selection).get(
                    custody.state)

                selection_list.append({
                    'code': code,
                    'emp_name': employee_name,
                    'property': custody_name,
                    'asset_types': asset_type,
                    'reason': reason,
                    'request_date': request_date,
                    'return_date': return_date,
                    'Status': Status,

                })
        if not selection_list:
            raise UserError("No data found")

        data = {
            'form_data': self.read()[0],
            'selection': selection_list,
        }
        return self.env.ref('hr_custody.action_employee_custody_pdf').with_context(
            landscape=True).report_action(self, data=data)
        # return self.env.ref('hr_custody.action_employee_custody_pdf').report_action(self, data=data)

