from odoo import fields, models, api, _
from odoo.tools.misc import xlsxwriter
import io
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime


class PayrollPaymentExcelReport(models.AbstractModel):
    _name = 'report.payroll_payment_advice.report_payroll_payment_advice'
    _inherit = 'report.report_xlsx.abstract'
    
    _description = 'Payroll payment Excel Report'
    
    
    def generate_xlsx_report(self, workbook, data, lines):
    
        header_style = workbook.add_format({'font_name': 'Times', 'bold': True, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'center','color':'orange'})
        title_style = workbook.add_format({'font_name': 'Times', 'font_size': 18, 'bold': True, 'align': 'center','color':'blue','bg_color': '#6B8E23'})
        
        
        text_style = workbook.add_format({'font_name': 'Times', 'font_size': 12, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'left'})
        number_style = workbook.add_format({'font_name': 'Times', 'font_size': 12, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'right'})
        
        sheet = workbook.add_worksheet("Payroll Payment advice")
        sheet.set_row(0 , 25) 
        
        sheet.set_column('A:A',15)
        sheet.set_column('B:B',16)
        sheet.set_column('C:C',20)
        sheet.set_column('D:D',20)
        sheet.set_column('E:E',16)
        sheet.set_column('F:H',15)
        sheet.set_column('I:I',12)
        sheet.set_column('J:J',10)
        sheet.set_column('K:K',15)
        
        
        
        date_one = lines.from_date
        date_wise = datetime.strptime(str(date_one), "%Y-%m-%d")
        date_month=date_wise.month
        date_year=date_wise.year 
        
        
        sheet.merge_range('A1:L1', 'Payroll Payment Advice ('+ str(date_month) + ' -  '+str(date_year) + ' )', title_style)
        
        sheet.write(1,0,'Period Name',header_style)
        sheet.write(1,1,lines.name,text_style)
                
        col=0
        sheet.write(3, col, 'Employee ID', header_style)
        col += 1  
        sheet.write(3, col, 'Employee Resident Id', header_style)
        col += 1          
        sheet.write(3, col, 'Employee Bank ID', header_style)
        col += 1
        sheet.write(3, col, 'Employee Account Number', header_style)
        col += 1        
        sheet.write(3, col, 'Employee Name', header_style)
        col += 1
        sheet.write(3,col, 'Payment Amount', header_style)
        col += 1
        sheet.write(3, col, 'Basic Salary', header_style)
        col += 1
        sheet.write(3, col, 'Housing Allowance', header_style)
        col += 1  
        sheet.write(3, col, 'Other Earnings', header_style)
        col += 1  
        sheet.write(3, col, 'Deductions', header_style)
        col += 1  
        sheet.write(3, col, 'Regulatory Reporting', header_style)
        col += 1        
        sheet.write(3, col, 'Remarks', header_style)
        col += 1  
        
        
        row = 3
        
        for line in lines.payroll_advice_line_ids:
            row+=1 
            col=0
            sheet.write(row,col,line.employee_number,text_style)
            col+=1
            sheet.write(row,col,line.employee_resident_id,text_style)
            col+=1
            sheet.write(row,col,line.bank_code,text_style)
            col+=1
            sheet.write(row,col,line.bank_account_id.acc_number,text_style)
            col+=1
            # sheet.write(row,col,line.bank_ifsc,text_style)
            # col+=1
            sheet.write(row,col,line.employee_id.name,text_style)
            col+=1
            sheet.write(row,col,line.net_salary,number_style)
            col+=1
            sheet.write(row,col,line.basic_salary,number_style)
            col+=1
            sheet.write(row,col,line.housing_allowance,number_style)
            col+=1
            sheet.write(row,col,line.other_earning,number_style)
            col+=1
            sheet.write(row,col,line.deduction,number_style)
            col+=1
            sheet.write(row,col,line.regulatory,text_style)
            col+=1            
            sheet.write(row,col,line.remarks,text_style)
            col+=1
       
       
        
        # sheet.write(5,6,lines.payroll_advice_line_ids,header_style)
        
