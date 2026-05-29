from datetime import datetime
import time
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.tools.misc import xlsxwriter
from odoo.exceptions import ValidationError, AccessError
from stdnum.exceptions import ValidationError
from odoo.osv import expression
from odoo import api, fields, models
from datetime import date, datetime, time



class PayrollPaymentAdviceBankTwo(models.Model):    
    _name = "payroll.advice.two"    
    _description = "Payroll Payment Advice - Saudi Investment bank"

    name = fields.Char(string = "Period Name")
    from_date = fields.Date(string = "Date",required=True,default=lambda self: fields.Date.to_string(date.today().replace(day=1)))    
    payroll_two_line_ids = fields.One2many('payroll.advice.two.line','payroll_two_id',string = "Bank Format one")
    
    @api.onchange('from_date')
    def _change_date_function(self):
        domain = [(5,0,0)]
        if self.from_date:
            date_wise = datetime.strptime(str(self.from_date), "%Y-%m-%d").strftime('%b - %Y')
            self.name=str(date_wise)
            
        payslip_date_wise = self.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('date_from','<=',self.from_date),('date_to','>=', self.from_date)],order="name asc")
        for slip in payslip_date_wise:
            if slip.contract_id:
                iqam_no = slip.employee_id.is_saudi            
                if iqam_no == True:
                    employee = slip.employee_id.identification_id
                else:               
                    employee = slip.employee_id.iqama_no                
                if slip.employee_id:
                    deduction = 0.0
                    total_emp_all = 0.0
                    value = 0.0                               
                    for line in slip.line_ids:                  
                        if line.code == "BASIC":
                            salary_basic = ('{:,.2f}'.format(abs(line.amount)))
                        if line.code == "NET":          
                            total_salary = ('{:,.2f}'.format(abs(line.total)))
                        if line.code == "HRA":          
                            housing_amount = ('{:,.2f}'.format(abs(line.amount)))
                        if line.category_id.code == 'DED':
                            deduction += line.amount
                            ded = ('{:,.2f}'.format(abs(deduction)))                      
                        if line.category_id.code == 'ALW':
                            value += line.amount
                            if line.code == "HRA":
                                total = line.amount
                            total_emp_all = value - total                      
                vals={                                
                    'employee_id' : slip.employee_id.id ,                
                    'basic_salary': salary_basic ,
                    'housing_allowance' : housing_amount ,
                    'net_salary' : total_salary,
                    'bank_account_id' : slip.employee_id.bank_account_id.id ,
                    'bank_name' : slip.employee_id.bank_account_id.bank_id.name ,
                    'other_earning' : total_emp_all ,
                    'deduction' : ded ,
                    'beneficiary_id' : employee ,        
                    'payroll_two_id' : self.id
                    }
                domain.append((0,0,vals))         
            self.payroll_two_line_ids = domain
            
        
        
    @api.constrains('name')
    def check_name(self):
        for rec in self:
            name = self.env['payroll.advice.two'].search([('name',"=",rec.name),('id',"!=",rec.id)])
            if name:
                raise ValidationError(("Period Name %s is Already Exist " % rec.name))

class PayrollPaymentAdviceBankTwoLine(models.Model):    

    _name = "payroll.advice.two.line"
    _description = "Payroll Payment Advice Bank Line Format Two"

    payroll_two_id = fields.Many2one('payroll.advice.two', string = "payroll")        
    employee_id  = fields.Many2one('hr.employee', string = "Beneficiary Name 1")
    employee_beneficiary = fields.Char(string = "Beneficiary Name 2")
    employee_benefi = fields.Char(string = "Beneficiary Name 3")
    bank_name = fields.Char(string = "Beneficiary Bank")
    payment_description = fields.Char(string = "Payment Description (optional)")                      
    bank_account_id = fields.Many2one('res.partner.bank', string = "Beneficiary Account")
    net_salary = fields.Char(string = "Net Salary")    
    basic_salary = fields.Char(string = "Basic Salary")
    housing_allowance = fields.Char(string = "Housing Allowance")
    other_earning = fields.Char(string = "Other Earnings")
    deduction = fields.Char(string = "Deductions")
    beneficiary_id = fields.Char(string="Beneficiary ID")
    
    
     
    
    
    
    
    
    
    