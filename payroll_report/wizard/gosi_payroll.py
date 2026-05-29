from odoo import fields, models, api, _
from datetime import datetime
from odoo.exceptions import warnings
import time
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, time

class GosiPayroll(models.TransientModel):
    
    _name = 'gosi.payroll'

    _description ="gosi payroll report"
    
    
    
    employ_ids = fields.Many2many('hr.employee',string="Employee")
    from_date =fields.Date(string="From date",required=True,default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    to_date = fields.Date(string="To date",required=True,default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    department_ids = fields.Many2many('hr.department', string= "Department")
    company_id = fields.Many2one('res.company',string='Company',default=lambda self:self.env.user.company_id)
    job_ids = fields.Many2many('hr.job',string="Job Title")
    nationality_ids=fields.Many2many('res.country',string="Nationality")
    branch_ids = fields.Many2many('hr.branch',string="Branch Location")
    structure_id = fields.Many2one('hr.payroll.structure',string="Structure", required=True)
    group_wise = fields.Selection([('department','Department'),('jobtitle','Job Title'),('location','Location'),('nationality','Nationality')],string="Group By")

    
    # branch_ids=fields.Many2many('hr.branch',string="Branch Location")
  
   
    # @api.constrains('from_date','to_date')
    # def check_date(self):
    #     for rec in self:
    #         start = self.env['hr.payslip'].search([('date_from','=',rec.from_date),('date_to','=',rec.to_date)])
    #         if not start:
    #             raise Warning(_("Period Date %s - %s is not Available. Please Change the Different Date" % (rec.from_date, rec.to_date)))                             

    
    @api.onchange('from_date','to_date')
    def get_two_date(self):
        if self.from_date and self.to_date:
            d1=datetime.strptime(str(self.from_date),'%Y-%m-%d') 
            d2=datetime.strptime(str(self.to_date),'%Y-%m-%d')
            if d1>d2:
                warning = {
                        'title': _("Warning"),
                        'message':"Invalid.Because End Date is Always greater than From Date "
                        }
                res = {}
                if warning:
                    res['warning'] = warning
                self.to_date=False
                return res
   
   
    @api.model
    def _get_payslips(self):
        department_ids = False
        if self.department_ids:
            department_ids = self.department_ids
        else:
            department_ids = self.env['hr.department'].search([])
        department_wise_payslip = {}
        for department in department_ids:
            domain = []
            employees = self.env['hr.employee'].search([('department_id','=', department.id)])
            domain.append(('date_from', '>=', self.from_date))
            domain.append(('date_from', '<=', self.to_date))
            domain.append(('employee_id', 'in', employees.ids))
            if self.company_id:
                domain.append(('company_id', '=', self.company_id.id))
            domain.append(('state', 'in', ['draft','verify','done']))
            payslips = self.env['hr.payslip'].search(domain, order = 'date_from')
            payslips_dict = {}
            for payslip in payslips:
                if payslip.date_from not in payslips_dict:
                    payslips_dict[payslip.date_from] = payslip
                else:
                    payslips_dict[payslip.date_from] += payslip
                if not payslips:
                    raise Warning(_('Payslips are not found!'))
            department_wise_payslip[department.name] = payslips_dict
        for res in self:
            if not res.department_ids:
                domain = []
                employees = res.env['hr.employee'].search([('department_id','=',False)])
                domain.append(('date_from', '>=', res.from_date))
                domain.append(('date_from', '<=', res.to_date))
                if employees.ids:
                    domain.append(('employee_id', 'in', employees.ids))
                if res.company_id:
                    domain.append(('company_id', '=', res.company_id.id))
                domain.append(('state', 'in', ['draft','verify','done']))
                payslips = res.env['hr.payslip'].search(domain, order = 'date_from')
                payslips_dict = {}
                for payslip in payslips:
                    if payslip.date_from not in payslips_dict:
                        payslips_dict[payslip.date_from] = payslip
                    else:
                        payslips_dict[payslip.date_from] += payslip
                    if not payslips:
                        raise Warning(_('Payslips are not found!'))
                    department_wise_payslip['Unknown'] = payslips_dict
        return department_wise_payslip
   
    
    # @api.onchange('group_wise')
    # def change_groupwise(self):  
    #     for rec in self:
    #         if self.group_wise =='department':
    #             rec.department_ids=self.env['hr.department'].search([])  
    #             rec.job_ids=None
    #             rec.nationality_ids=None
    #             rec.branch_ids=None
    #             rec.employ_ids=None                               
    #         if self.group_wise =='jobtitle':
    #             rec.job_ids=self.env['hr.job'].search([])  
    #             rec.department_ids=None
    #             rec.nationality_ids=None
    #             rec.branch_ids=None
    #             rec.employ_ids=None     
    #         if self.group_wise =='location':
    #             rec.branch_ids =self.env['hr.branch'].search([])  
    #             rec.department_ids=None
    #             rec.nationality_ids=None
    #             rec.job_ids=None
    #             rec.employ_ids=None      
    #         if self.group_wise =='nationality':
    #             rec.nationality_ids =self.env['res.country'].search([])  
    #             rec.department_ids=None
    #             rec.branch_ids=None
    #             rec.job_ids=None 
    #             rec.employ_ids=None   
    #

    # @api.constrains('from_date','to_date') 
    # def check_date(self): 
    #     for rec in self:
    #         date_one=rec.env["hr.payslip"].search(['date_from','=',rec.from_date])
    #         if date_one!=rec.from_date:
    #             raise Warning(_('From date is not found! please Enter correct From date'))
    

            # elif rec.to_date=='To date':
            #     raise Warning(_('To date is not found! please Enter correct To date'))
            #

        
   
   
    # @api.model
    # def get_payslip(self):
    #    department_ids = False
    #    if self.department_ids:
    #        department_ids = self.department_ids
    #    else:
    #         department_ids = self.env['hr.department'].search([])
    #    department_wise_payslip = {}
    #    for department in department_ids:
    #        department.id
    #        print("Department.id in python",department.id)
    #        department.name
    #        print("department name in python",department.name)
    #        domain = []
    #        employees = self.env['hr.employee'].search([('department_id', '=',department.id)])
    #        # for employee in  employees:
    #        domain = []
    #        print("employee name in python",employee.name,employee.department_id.name)
    #             # domain.append(('date_from','>=',self.from_date))
    #
    #        # domain.append(('date_from','<=',self.to_date))
    #        domain.append(('employee_id','=',employee.id))
    #        # if self.company_id:
    #        #     domain.append(('company_id','=',self.company_id.id))
    #        domain.append(('state','=','draft'))
    #        payslips = self.env['hr.payslip'].search(domain)
    #
    #
    #             # payslips = self.env['hr.payslip'].search(domain,order='date_from')
    #             # for payslip in  payslips: 
    #             #     for line in payslip.line_ids:
    #                     # print("line.amount",line.amount)
    #                     # print("line.code",line.code)
    #        payslips_dict = {}
    #        for payslip in payslips:
    #
    #        #         if payslip.date_from not in payslips_dict:
    #        #             payslips_dict[payslip.date_from] = payslip
    #        #         else:
    #        #            payslips_dict[payslip.date_from] += payslip
    #        #         if not payslips:
    #        #             raise Warning(('Payslips are not found'))
    #             department_wise_payslip[department.name] = payslips_dict
    #
    #        return department_wise_payslip
    #
    #      # return department.id

           
               
           
   
    
    def cancel(self):
        print("*************pdf cancel")
    
    def print_excel(self):
        # print("...........print Excel............")
        for rec in self:
            return {
                'type': 'ir.actions.act_url',
                 'url': '/om_hr_payroll/excel_report/%s' % (rec.id),
                 'target': 'new',
                 }
    
    
    # @api.onchange('department_ids')
    # def change_department(self):
    #     # if self.group_wise == 'department':
    #     for rec in self:
    #         rec.employ_ids=self.env['hr.employee'].search([('department_id', '=',rec.department_ids.ids)])
    #

    # @api.onchange('job_ids')
    # def change_job_title(self):
    #     for rec in self:
    #         rec.employ_ids = self.env['hr.employee'].search([('job_id','=',rec.job_ids.ids)])    
    #
    # @api.onchange('branch_ids')
    # def change_branch(self):
    #     for rec in self:
    #         rec.employ_ids = self.env['hr.employee'].search([('branch_id','=',rec.job_ids.ids)])    
  
    
    
    #
    # @api.onchange('from_date','to_date')
    # def get_two_date(self):
    #     if self.from_date and self.to_date:
    #         d1=datetime.strptime(str(self.from_date),'%Y-%m-%d') 
    #         d2=datetime.strptime(str(self.to_date),'%Y-%m-%d')
    #         if d1 > d2:
    #             warning = {
    #                     'title': _("Warning"),
    #                     'message':"Invalid Because From Date is always lesser than to Date"
    #                     }
    #             res = {}
    #             if warning:
    #                 res['warning'] = warning
    #             self.to_daten=False
    #             return res
        
        #
        # data={}
        # return self.env.ref('payroll_report.payroll_report_details1').report_action(self,data=data)
        # context = self._context

        # return {
        #     'type': 'ir.actions.report',
        #     'data': {'model': 'gosi.payroll',
        #              # 'options': json.dumps(data, default=date_utils.json_default),
        #              'output_format': 'xlsx',
        #              'report_name': 'payroll_report_details_xlsx',
        #              },
        #     'report_type': 'xlsx'
        # }  
        #
