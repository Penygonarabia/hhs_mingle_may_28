from odoo import fields,models,api,_
from datetime import datetime
import time
from datetime import timedelta
from dateutil.relativedelta import relativedelta



class PayrollAdvice(models.Model):
    
    _name = "hr.payroll.advice"
    
    _description = "Payroll Payment"
    
    
    name = fields.Char(string = "Period Name")
    from_date = fields.Date(string = "From Date")
    to_date = fields.Date(string = "To Date")   
    payroll_advice_line_ids = fields.One2many('hr.payroll.advice.line', 'advice_id', string='Banks')
  

    
    
    # def action_date_done(self):
    #     domain = []
    #     for bank in self:
    #         bank.bank_name_ids.unlink()
    #         for rec in bank:
    #             payslip = self.env['hr.payslip'].search([('date_from','=',rec.from_date),('date_to','=',rec.to_date)])
    #             # print("date wise >>>>>>>>>>>>>",date_wise)
    #             for payslip_id in payslip:
    #
    #                 employ_name = payslip_id.employee_id.name
    #                 emp_id = payslip_id.employee_id.id
    #
    #                 print(",,,,,,,,,,,,,,",employ_name)
    #
    #                 self.env['bank.transfer.line'].create({
    #                     'employ_id':emp_id,
    #                     'employee_name':employ_name
    #
    #                     })
    #     return True 
   
                         
    # @api.onchange('from_date')
    # def change_function(self):
    #      domain = []
    #      for rec in self:
    #         payslip = self.env['hr.payslip'].search([('date_from','=',rec.from_date),('date_to','=',rec.to_date)])
    #
    #         for payslip_id in payslip:
    # #
    #             employ_name = payslip_id.employee_id.name
    #             emp_id = payslip_id.employee_id.id
    #
    #             print(",,,,,,,,,,,,,,",employ_name)
    #
    #             self.env['bank.transfer.line'].create({
    #                 'employ_id':emp_id,
    #                 'employee_name':employ_name
    #
    #                 })
    #         return True 
            
                # bank_name_ids.append[(0 , 0 ,{
                #     'employ_id' : employee.employee_id.id ,
                #     'employee_name' : employee.employee_id.name
                #
                #     })]
                # self.update(bank_name_ids)
                
                # print("bank_name_ids:::::::::::",bank_name_ids)
                # employee.write({'employ_id': employee.employee_id.id, 'employee_name': employee.employee_id.name})
     
class PayrollAdviceLine(models.Model):   
    _name = "hr.payroll.advice.line"
    _discription = "Payroll Payment Advice Line"
    
   
    advice_id = fields.Many2one('hr.payroll.advice',string="bank name")
    employee_id  = fields.Many2one('hr.employee', string="Employee")

    employee_resident = fields.Char(string = "Resident ID")
    employee_bank =fields.Char(string = "Bank Name")
    employee_account_number = fields.Char(string = "Acc Number")
    employee_name = fields.Char(string = "Name")
    net_salary = fields.Char(string = "Net")
    basic_salary = fields.Char(string = "Basic")
    housing_allowance = fields.Char(string = "Hous")
    other_earning = fields.Char(string = "Other")
    deduction = fields.Char(string = "Ded")
     
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
                     
    