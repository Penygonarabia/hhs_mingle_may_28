from odoo import api, fields, models, _
from odoo.tools import float_round
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, time

class PayrollTransactionReport(models.TransientModel):
    
    _name = "payroll.transaction.report"

    from_date = fields.Date(string='From Date', required=True,  default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    to_date = fields.Date(string='To Date', required=True,  default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id, required=True)
    employee_ids = fields.Many2many('hr.employee',string="Employee Name")
    job_title_ids = fields.Many2many('hr.job', string="Job Title")

    nationality_ids = fields.Many2many('res.country', string="Nationality")

    branch_location_ids = fields.Many2many('hr.work.location', string="Branch Location")
    department_ids = fields.Many2many('hr.department', string = "Department")


    sort_by = fields.Selection(
        [('department', 'Department'), ('job_title', 'Job Title'), ('branch_location', 'Location'),
         ('nationality', 'Nationality'),('employee_no','Employee No')], string='Sort By')

    group_by_transaction = fields.Boolean(string = "Group By Transaction", default = False)
    
    # @api.onchange('group_by_transaction')
    # def _onchange_group_by_transaction(self):
    #     for rec in self:
    #         rec.employee_ids = None
    #         rec.job_title_ids = None
    #         rec.nationality_ids = None
    #         rec.branch_location_ids = None
    #         rec.sort_by = None
                
    
    def print_payroll_transaction_excel(self):
        if self.group_by_transaction:
            self.employee_ids = None
            self.job_title_ids = None
            self.nationality_ids = None
            self.branch_location_ids = None
            self.sort_by = None
            
        datas = {
            'model': 'payroll.transaction.report',
            'form_data': self.read()[0],
        }
        return self.env.ref('payroll_transactions_report.action_report_payroll_transaction_report_xlsx').report_action(self,data=datas)

    def print_payroll_transaction_report(self):
        selection_list = []
        no_of_units = 0.00
        domain = []
        employee_lst = []
        
        employee_ids = self.employee_ids.ids if self.employee_ids else self.env['hr.employee'].search([]).ids
        domain.append(('employee_id', 'in', employee_ids))
    
        if self.department_ids:
            domain.append(('employee_id.department_id', 'in', self.department_ids.ids))
    
        if self.job_title_ids:
            domain.append(('employee_id.job_id', 'in', self.job_title_ids.ids))
    
        if self.nationality_ids:
            domain.append(('employee_id.country_of_birth', 'in', self.nationality_ids.ids))
    
        if self.branch_location_ids:
            domain.append(('employee_id.work_location_id', 'in', self.branch_location_ids.ids))
    
        if self.from_date:
            domain.append(('date', '>=', self.from_date))
    
        if self.to_date:
            domain.append(('date', '<=', self.to_date))
            
        transaction_search = self.env['salary.allowance.detection']
        transaction = transaction_search.search(domain)
        transaction = transaction.sorted(key=lambda d: d.date)
        
        if self.sort_by:
            if self.sort_by == 'department':
                transaction = transaction.filtered(lambda c : c.employee_id.department_id)
                transaction = transaction.sorted(key=lambda c:c.employee_id.department_id.name.lower())
            
            elif self.sort_by == 'job_title':
                transaction = transaction.filtered(lambda c : c.employee_id.job_id) 
                transaction = transaction.sorted(key = lambda c : c.employee_id.job_id.name.lower())
                
            elif self.sort_by == 'nationality':
                transaction = transaction.filtered(lambda c : c.employee_id.country_of_birth)
                transaction = transaction.sorted(key = lambda c:c.employee_id.country_of_birth.name.lower())
            
            elif self.sort_by == 'branch_location':
                transaction = transaction.filtered(lambda c : c.employee_id.work_location_id)
                transaction = transaction.sorted(key = lambda c:c.employee_id.work_location_id.name.lower())        
            
            elif self.sort_by == 'employee_no':
                transaction = transaction.sorted(key = lambda s: (
                    0 if s.employee_id.employee_no and isinstance(s.employee_id.employee_no,str) and s.employee_id.employee_no.isdigit() else 1,
                    int(s.employee_id.employee_no) if s.employee_id.employee_no and isinstance(s.employee_id.employee_no,str) and s.employee_id.employee_no.isdigit() else s.employee_id.employee_no or ''
                    ))
        
        if self.department_ids:
            transaction = transaction.sorted(key=lambda c:c.employee_id.department_id.name.lower())
            
        if self.job_title_ids:
            transaction = transaction.sorted(key = lambda c : c.employee_id.job_id.name.lower())
        
        if self.nationality_ids:
            transaction = transaction.sorted(key = lambda c:c.employee_id.country_of_birth.name.lower())
        
        if self.branch_location_ids:
            transaction = transaction.sorted(key = lambda c:c.employee_id.work_location_id.name.lower())        
                        
        
        for salary in transaction:
            employee_name = salary.employee_id.name
            emp_no = salary.employee_id.employee_no
            department = salary.employee_id.department_id.name
            job_title = salary.employee_id.job_id.name
            location = salary.employee_id.work_location_id.name
            code = salary.code
            description = salary.transaction_type_id.name
            reference = salary.name
            if salary.date:
               salary_allw_ded_date = salary.date.strftime("%d-%m-%Y") or ''
            else:
                salary_allw_ded_date = ''
            units = dict(salary._fields['units'].selection).get(salary.units)
            if salary.units == 'hours':
                no_of_units = round(salary.hours,2)
            elif salary.units == 'days':
                no_of_units = round(salary.days,2)
            amount = float_round(salary.amount, 2)
            remarks = salary.reason
            state = dict(salary._fields['state'].selection).get(salary.state)
            selection_list.append({
                 'emp_no': emp_no,
                'employee_name': salary.employee_id.name,
                 'department' : department,
                 'job_title': job_title,
                 'location': location,
                 'nationality': salary.employee_id.country_of_birth.name,
                 'code': code,
                 'description' : description,
                 'reference': reference,
                 'salary_allw_ded_date': salary_allw_ded_date,
                 'units': str(no_of_units) +' /' + str(units) ,
                 # 'no_of_units': no_of_units,
                 'amount': round(amount,2),
                 'remarks': remarks,
                 'state': state,

            })
        if not selection_list:
            raise ValidationError("No data found for the selected Employees and date range.")
        # from_date = self.from_date.strftime("%d-%m-%Y")
        # to_date = self.to_date.strftime("%d-%m-%Y")
        data = {
            'form_data': self.read()[0],
            'from_date': self.from_date.strftime("%d-%m-%Y"),
            'to_date': self.to_date.strftime("%d-%m-%Y"),
            'selection': selection_list,
        }
        return self.env.ref('payroll_transactions_report.action_payroll_transactions_detail_pdf').with_context(landscape=True).report_action(self, data=data)

