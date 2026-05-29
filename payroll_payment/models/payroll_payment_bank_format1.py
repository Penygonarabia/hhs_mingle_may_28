from odoo import fields,models,api,_
from datetime import datetime
import time
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.tools.misc import xlsxwriter
from odoo.exceptions import ValidationError, AccessError
from stdnum.exceptions import ValidationError
from odoo.osv import expression
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, datetime, time



class PayrollPaymentAdviceBank(models.Model):    
    _name = "payroll.payment.advice"    
    _description = "Payroll Payment Advice Bank --- SABB Format"    
    name = fields.Char(string = "Period Name")
    from_date = fields.Date(string = "Date",required=True,default=lambda self: fields.Date.to_string(date.today().replace(day=1)))    
    payroll_line_ids = fields.One2many('payroll.payment.advice.line','payroll_id',string = "Bank Format one")
    
    @api.onchange('from_date')
    def _change_date_function(self):
        domain = [(5,0,0)]
        if self.from_date:
            date_wise = datetime.strptime(str(self.from_date), "%Y-%m-%d").strftime('%b - %Y')
            self.name = str(date_wise)            
        payslip_date_wise = self.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('date_from','<=',self.from_date),('date_to','>=', self.from_date)],order="name asc")
        for slip in payslip_date_wise:
            if slip.employee_id:
                deduction = 0.0
                total_emp_all = 0.0
                value = 0.0
                for line in slip.line_ids:                  
                    if line.code == "NET":          
                        total_salary = ('{:,.2f}'.format(abs(line.total)))           
            vals = {               
                'employee_id' : slip.employee_id.id ,
                'employee_number' : slip.employee_id.employee_no ,               
                'net_salary' : total_salary,
                'bank_account_id' : slip.employee_id.bank_account_id.id ,
                'actual_amount' : total_salary ,
                'payroll_id' : self.id
                }
            domain.append((0,0,vals))
           
        self.payroll_line_ids=domain
        
    @api.constrains('name')
    def check_name(self):
        for rec in self:
            name = self.env['payroll.payment.advice'].search([('name',"=",rec.name),('id',"!=",rec.id)])
            if name:
                raise exceptions.ValidationError(_("Period Name %s is Already Exist" % rec.name))                             
                                  
                                
    
class PayrollPaymentAdviceBankLine(models.Model):    
    _name = "payroll.payment.advice.line"    
    _description = "Payroll Payment Advice Bank Line Format One"        
    payroll_id = fields.Many2one('payroll.payment.advice',string = "payroll")        
    employee_id  = fields.Many2one('hr.employee',string="Employee Name")
    employee_number = fields.Char(string="Code")        
    bank_account_id = fields.Many2one('res.partner.bank',string = "Employee Bank Account number")
    net_salary = fields.Char(string = "Amount")    
    actual_amount = fields.Char(string = "Actual Amount paid")
     
    
    
    
    
    
    
    