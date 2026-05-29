from odoo import api,fields,models,_
from odoo.exceptions import ValidationError

class EmployeeLoanReport(models.TransientModel):
    
    _name = "employee.loan.report"
    
    
    employee_ids = fields.Many2many('hr.employee',string="Employee Name")
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,required=True)

    
    department_ids = fields.Many2many('hr.department', string = "Department")
    
    job_title_ids = fields.Many2many('hr.job', string="Job Title")
    
    nationality_ids = fields.Many2many('res.country', string="Nationality")
    
    branch_location_ids = fields.Many2many('hr.work.location', string="Branch Location")
    
    from_date = fields.Date(string='From Date')
    
    to_date = fields.Date(string='To Date')
    
    type = fields.Selection([('loan','Loan'),('advance','Advance')],default="loan",string="Type",required=True)
    
    payment_status = fields.Selection([('all','All'),('outstanding','Outstanding Only'),('fully_paid','Fully Paid')],string="Payment Status")
    
    approval_status = fields.Selection([('all','All'),('draft','Draft'),('waiting_for_approval','Waiting For Approval'),('approved','Approved'),('rejected','Rejected')],string="Approval Status")
    
    sort_by = fields.Selection([('department','Department'),('job_title','Job Title'),('branch_location','Location'),('nationality','Nationality'),('employee_no','Employee No')],string='Sort By')
    
    employee_status = fields.Selection([('all','All'),('active','Active'),('terminated','Terminated')],string="Employee Status", default='all', required = True)
    
    
    
    @api.constrains('from_date', 'to_date')
    def _check_from_date(self):
        if self.filtered(lambda c: c.to_date and c.from_date > c.to_date):
            raise ValidationError(_('From date Date must be less than Period To Date.'))
    
             
    @api.onchange('from_date')
    def _onchange_from_date(self):
        for rec in self:
            if rec.from_date:
                rec.to_date = rec.from_date  
                    
    
    def print_salary_report(self):
        datas = {
            'model': 'employee.loan.report',
            'form_data': self.read()[0],
        }
        return self.env.ref('employee_loan_report.action_report_employee_loan_report_xlsx').report_action(self, data=datas)

    def print_detail_report(self):
        selection_list = []
        employee_ids = False
        employee_ids = False
        if self.employee_ids:
            employee_ids = self.employee_ids
        else:
            employee_ids = self.env['hr.employee'].search([])

        for employee in employee_ids:
            contract_search = self.env['hr.employee.loan.ps'].search([('employee_id', '=', employee.id)])
            loan_start_date = ''
            ins_rate = 0.00
            ins_date = ''
            ins_remaining_amount = 0.00
            for contract in contract_search:
                emp_no = contract.employee_id.employee_no or ' '
                employee_name = contract.employee_id.display_name or ' '
                type_name = contract.type_id.display_name or ' '
                loan_name = contract.display_name or ' '
                if contract.loan_ins_start_date:
                    loan_start_date = contract.loan_ins_start_date.strftime("%d-%m-%Y") or ' '
                else:
                    loan_start_date = ''
                loan_amount = '{:.2f}'.format(float(contract.loan_amount)) or ' '
                for ins in contract.hr_employee_loan_line_ps:
                    ins_rate = ins.amount
                    if ins.state in ['deducted']:
                        ins_date = ins.installment_date.strftime("%d-%m-%Y")
                        ins_remaining_amount = ins.remaining_value
                ins_rate = '{:.2f}'.format(float(ins_rate)) or''
                ins_date = ins_date or ' '
                ins_remaining_amount = '{:.2f}'.format(float(ins_remaining_amount)) or ' '

                selection_list.append({
                    'employee_name': employee_name,
                    'emp_no': emp_no,
                    'type_name': type_name,
                    'loan_name': loan_name,
                    'loan_start_date': loan_start_date,
                    'loan_amount': loan_amount,
                    'ins_rate': ins_rate,
                    'ins_date': ins_date,
                    'ins_remaining_amount': ins_remaining_amount,
                })

        if not selection_list:
            raise UserError("No data found")

        data = {
            'form_data': self.read()[0],
            'selection': selection_list,
        }
        return self.env.ref('employee_loan_report.action_employee_loan_pdf').with_context(landscape=True).report_action(self, data=data)

