from odoo import fields,models,api,_
from datetime import datetime
import time
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime
import xlsxwriter
from odoo.exceptions import ValidationError, AccessError
from stdnum.exceptions import ValidationError
# from odoo.osv.query import Query
from odoo import api,exceptions
from datetime import date, datetime, time



class PayrollPaymentAdviceBankTwo(models.Model):    
    _name = "payroll.advice.two"    
    _description = "Payroll Payment Advice Bank  Format Two"    
    
    
    # @api.model
    # def _default_bank_format(self):
    #     bank_format = self.env['ir.config_parameter'].sudo().get_param('om_hr_payroll.bank_transfer_format')
    #     return bank_format or False
    
    name = fields.Char(string = "Period Name")
    from_date = fields.Date(string = "Date",required=True,default=lambda self: fields.Date.to_string(date.today().replace(day=1)))    
    payroll_two_line_ids = fields.One2many('payroll.advice.two.line','payroll_two_id',string = "Bank Format one")
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,required=True)
    
    bank_format = fields.Char('Bank Transfer format' , compute="_compute_bank_format")
    
    @api.depends('from_date')
    def _compute_bank_format(self):
        for rec in self:
            rec.bank_format = self.env['ir.config_parameter'].sudo().get_param('om_hr_payroll.bank_transfer_format') 
        
    
    
    
    @api.onchange('from_date')
    def _change_date_function(self):
        domain = [(5,0,0)]
        
        self.bank_format = self.env['ir.config_parameter'].sudo().get_param('om_hr_payroll.bank_transfer_format') 
        
        if self.from_date:
            date_wise = datetime.strptime(str(self.from_date), "%Y-%m-%d").strftime('%b - %Y')
            self.name=str(date_wise)
        
        from_date =self.from_date.replace(day = 1)
        to_date = self.from_date.replace(day=28)+timedelta(days=4)
        last_day = to_date - timedelta(days=to_date.day)
        
            
        payslip_date_wise = self.env['hr.payslip'].search(['|',('state','=','draft'),('state','=','done'),('date_from','>=',from_date),('date_to','<=', last_day)],order="number asc")
        for slip in payslip_date_wise:
            iqam_no = slip.employee_id.is_saudi            
            if iqam_no == True:
                employee = slip.employee_id.identification_id
            else:               
                employee = slip.employee_id.iqama_no                
            
            if slip.employee_id:
                deduction = 0.0
                total_emp_all = 0.0
                value = 0.0 
                housing_amount= 0.0
                total_salary =0.0
                ded  = 0.0
                basic_amount = 0.0
                house_allowance = 0.0  
                total_net = 0.0
                total_sal = 0.0  
                total_alw =0.0  
                gross_total =0.0 
                gosi_total =0.0                        
                for line in slip.line_ids:
                 
                    # if line.category_id.code == 'ALW':
                    #     total_alw += line.total
                        
                    if line.code == "BASIC":
                        basic_amount = line.total
                        salary_basic = ('{:,.2f}'.format(abs(line.total)))
                    # if line.code == "NET": 
                    #     total_sal= line.total         
                    #     total_salary = ('{:,.2f}'.format(abs(line.total)))
                    if line.code == "HRA": 
                        house_allowance = line.total         
                        housing_amount = ('{:,.2f}'.format(abs(line.total)))
                    if line.category_id.code == 'DED':
                        deduction += line.total
                        ded = ('{:,.2f}'.format(abs(deduction)))                      
                    if line.category_id.code == 'ALW':
                        value += line.total
                        if line.code == "HRA":
                            total = line.total
                        total_net = value - total
                        total_emp_all = ('{:,.2f}'.format(value - total ))
                
                vals={                                
                    'employee_id' : slip.employee_id.id ,                
                    'basic_salary': salary_basic ,
                    'housing_allowance' : housing_amount ,
                    'net_salary' : '{:,.2f}'.format(basic_amount + house_allowance + total_net + deduction) ,
                    'bank_account_id' : slip.employee_id.bank_account_id.id ,
                    'bank_name' : slip.employee_id.bank_account_id.bank_id.name ,
                    'other_earning' : total_emp_all ,
                    'deduction' : ded ,
                    'beneficiary_id' : employee ,        
                    'payroll_two_id' : self.id,
                    'payroll_reference':slip.number,
                    'date_from' : slip.date_from.strftime("%d-%m-%Y"),
                    'date_to':slip.date_to.strftime("%d-%m-%Y"),
                    'employee_beneficiary' : slip.employee_id.address_home_id.street or ' ',
                    'employee_beneficiary_address_two' : slip.employee_id.address_home_id.street2 or '',
                    'employee_beneficiary_address_three' :slip.employee_id.address_home_id.city or ''
                    
                    }
                domain.append((0,0,vals))         
                self.payroll_two_line_ids = domain 
        
        
    @api.constrains('name')
    def check_name(self):
        for rec in self:
            name = self.env['payroll.advice.two'].search([('name',"=",rec.name),('id',"!=",rec.id)])
            if name:
                raise exceptions.ValidationError(_("Period Name %s is Already Exist " % rec.name))
                    
                                                   
class PayrollPaymentAdviceBankTwoLine(models.Model):    
    _name = "payroll.advice.two.line"    
    _description = "Payroll Payment Advice Bank Line Format Two" 
           
    payroll_two_id = fields.Many2one('payroll.advice.two', string = "payroll")        
    employee_id  = fields.Many2one('hr.employee', string = "Beneficiary Name")
    employee_beneficiary = fields.Char(string = "Beneficiary Address 1")
    employee_beneficiary_address_two = fields.Char(string = "Beneficiary Address 2")
    employee_beneficiary_address_three = fields.Char(string = "Beneficiary Address 3")
    bank_name = fields.Char(string = "Beneficiary Bank")
    payment_description = fields.Char(string = "Payment Description (optional)")                      
    bank_account_id = fields.Many2one('res.partner.bank', string = "Beneficiary Account")
    net_salary = fields.Char(string = "Net Salary")    
    basic_salary = fields.Char(string = "Basic Salary")
    housing_allowance = fields.Char(string = "Housing Allowance")
    other_earning = fields.Char(string = "Other Earnings")
    deduction = fields.Char(string = "Deductions")
    beneficiary_id = fields.Char(string="Beneficiary ID")
    payroll_reference = fields.Char(string="Payroll Reference")
    date_from = fields.Char(string = "Period From")
    date_to = fields.Char(string = "Period To")
    
    # regulatory = fields.Char(string = "Regulatory Reporting", default = "SAL")
    # remarks = fields.Char(string = "Remarks")
    #
    #

     
    
    
    
    
    
    
    