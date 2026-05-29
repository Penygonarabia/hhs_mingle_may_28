from odoo import fields, models, api,_
from datetime import datetime
import time
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.tools.misc import xlsxwriter
from odoo.exceptions import ValidationError, AccessError
from stdnum.exceptions import ValidationError
from odoo.osv import expression
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date, datetime, time


class PayrollAdvice(models.Model):
    
    _name = "hr.payroll.advice"
    
    _description = "Payroll Payment--Bank III"
    
    
    name = fields.Char(string = "Period Name")
    from_date = fields.Date(string = "Date",required=True,default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
   
    payroll_advice_line_ids = fields.One2many('hr.payroll.advice.line', 'advice_id', string='Banks')
  
   
    @api.onchange('from_date')
    def _onchange_payment(self):
        domain = [(5,0,0)]
        if self.from_date:
            date_wise = datetime.strptime(str(self.from_date), "%Y-%m-%d").strftime('%b - %Y')
            self.name=str(date_wise)
       
        payslip_date_wise = self.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('date_from','<=',self.from_date),('date_to','>=', self.from_date)],order="name asc")
      
        for slip in payslip_date_wise:
        
            # employ_name = slip.employee_id.
            # emp_number = slip.employee_id.employee_no
            # name_bank = slip.employee_id.bank_account_id.bank_id.name
            iqam_no = slip.employee_id.is_saudi
            
            if iqam_no == True:
                employee = slip.employee_id.identification_id
            else:               
                employee = slip.employee_id.iqama_no

            
            if slip.employee_id:
                deduction=0.0
                total_emp_all=0.0
                value=0.0

                for line in slip.line_ids:
                    if line.code=="BASIC":
                        salary_basic =('{:,.2f}'.format(abs(line.amount)))
                    if line.code == "NET":          
                        total_salary = ('{:,.2f}'.format(abs(line.total)))
                    if line.code == "HRA":          
                        housing_amount = ('{:,.2f}'.format(abs(line.amount)))
                    if line.category_id.code == 'DED':
                        deduction+= line.amount
                        ded =('{:,.2f}'.format(abs(deduction)))
                   
                    if line.category_id.code == 'ALW':
                        value+=line.amount
                        if line.code=="HRA":
                            total=line.amount
                        total_emp_all= value - total
                          
                      
                      
            vals={
               
                'employee_id':slip.employee_id.id,
                'employee_number': slip.employee_id.employee_no,
                'employee_resident_id':employee,
                'basic_salary':salary_basic,
                'housing_allowance':housing_amount,
                'net_salary':total_salary,
                'bank_account_id':slip.employee_id.bank_account_id.id,
                'bank_code':slip.employee_id.bank_account_id.bank_id.name,
                # 'bank_ifsc':slip.employee_id.bank_account_id.bank_id.bic ,
                'other_earning':total_emp_all,
                'deduction':ded,
              
                'advice_id' : self.id
                }
            domain.append((0,0,vals))
           
        self.payroll_advice_line_ids=domain
        
    @api.constrains('name')
    def check_name(self):
        for rec in self:
            name = self.env['hr.payroll.advice'].search([('name',"=",rec.name),('id',"!=",rec.id)])
            if name:
                raise ValidationError(("Period Name %s is Already Exist" % rec.name))
                
            


         
class PayrollAdviceLine(models.Model):   
    _name = "hr.payroll.advice.line"
    _description = "Payroll Payment Advice Line"
    
   
    advice_id = fields.Many2one('hr.payroll.advice',string="name")
    employee_id  = fields.Many2one('hr.employee',string="Employee Name")

    employee_number = fields.Char(string="Employee ID")
    
    bank_account_id = fields.Many2one('res.partner.bank',string = "Employee Account number")
    # bank_account_number = fields.Char(string="Bank Number")
    bank_code = fields.Char(string = "Employee Bank ID")
    # bank_ifsc = fields.Char(string="Bank IFSC")
    employee_resident_id = fields.Char(string = "Employee Resident ID")
    
    net_salary = fields.Char(string = "Payment Amount")
    basic_salary = fields.Char(string = "Basic Salary")
    housing_allowance = fields.Char(string = "Housing Allowance")
    other_earning = fields.Char(string = "Other Earnings")
    deduction = fields.Char(string = "Deductions")
    regulatory = fields.Char(string = "Regulatory Reporting", default = "SAL")
    remarks = fields.Char(string = "Remarks")
    payment_desciption = fields.Char(string = "Payment Desciption (Optional)")

    
    
    
     
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
                     
    
