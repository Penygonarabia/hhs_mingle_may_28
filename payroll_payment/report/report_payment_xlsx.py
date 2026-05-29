from odoo import fields, models, api, _
from odoo.tools.misc import xlsxwriter
import io
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime

class PayrollPaymentBankOneExcelReport(models.AbstractModel):
    _name = 'report.payroll_payment.report_payroll_payment_format'
    _inherit = 'report.report_xlsx.abstract'    
    _description = 'Payroll payment Bank one Excel Report'    
    
    def generate_xlsx_report(self, workbook, data, lines):    
        header_style = workbook.add_format({'font_name': 'Times', 'bold': True, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'center','color':'orange'})
        title_style = workbook.add_format({'font_name': 'Times', 'font_size': 18, 'bold': True, 'align': 'center','color':'blue','bg_color': '#6B8E23'})      
        text_style = workbook.add_format({'font_name': 'Times', 'font_size': 12, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'right'})
        num_style = workbook.add_format({'font_name': 'Times', 'font_size': 12, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'left'})
        sheet = workbook.add_worksheet("Payroll Payment advice")
        sheet.set_row(0 , 25)         
        sheet.set_column('A:A', 15)
        sheet.set_column('B:B', 16)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:E', 16)
        sheet.set_column('F:F', 25)      
        date_one = lines.from_date
        date_wise = datetime.strptime(str(date_one), "%Y-%m-%d")
        date_month=date_wise.month
        date_year=date_wise.year                
        sheet.merge_range('A1:F1', 'Payroll Payment Advice ('+ str(date_month) + ' -  '+str(date_year) + ' )', title_style)
        sheet.write(1,0,'Period Name',header_style)
        sheet.write(1,1,lines.name,text_style)                
        col=0
        sheet.write(3, col, 'S.No', header_style)
        col += 1 
        sheet.write(3, col, 'Code', header_style)
        col += 1            
        sheet.write(3, col, 'Employee Name', header_style)
        col += 1
        sheet.write(3, col, 'Account', header_style)
        col += 1
        sheet.write(3, col,'Amount',header_style)
        col += 1
        sheet.write(3, col,'Actual Amount paid',header_style)
        col += 1
        no=1
        row = 3        
        for line in lines.payroll_line_ids:
            row += 1 
            col = 0            
            sheet.write(row, col, no, text_style)
            col += 1
            sheet.write(row, col, line.employee_number, text_style)
            col += 1
            sheet.write(row, col, line.employee_id.name, text_style)
            col += 1
            sheet.write(row, col, line.bank_account_id.acc_number, text_style)
            col += 1
            sheet.write(row, col, line.net_salary, num_style)
            col += 1
            sheet.write(row, col, line.actual_amount, num_style)
            col += 1            
            no += 1                      