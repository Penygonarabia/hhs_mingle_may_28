from odoo import fields, models, api, _
import xlsxwriter
import io
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime


class PayrollPaymentBankTwoExcelReport(models.AbstractModel):
    _name = 'report.payment_bank_two.report_payroll_payment_xlsx'
    _inherit = 'report.report_xlsx.abstract'    
    _description = 'Payroll payment Excel Report'    
    
    def generate_xlsx_report(self, workbook, data, lines): 
        
        if lines.bank_format =='sib_format':   
            header_style = workbook.add_format({'font_name': 'Times', 'bold': True, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'center','color':'orange'})
            title_style = workbook.add_format({'font_name': 'Times', 'font_size': 18, 'bold': True, 'align': 'center','color':'blue','bg_color': '#6B8E23'})
            text_style = workbook.add_format({'font_name': 'Times', 'font_size': 12, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'left'})
            number_style = workbook.add_format({'font_name': 'Times', 'font_size': 12, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'right'})
            sheet = workbook.add_worksheet("Payroll Payment advice")
              
            sheet.set_column('A:A', 12)
            sheet.set_column('B:B', 16)
            sheet.set_column('C:C', 20)
            sheet.set_column('D:E', 16)
            sheet.set_column('F:F', 15)        
            sheet.set_column('G:G', 25)
            sheet.set_column('H:H', 10)
            sheet.set_column('I:I', 16)
            sheet.set_column('J:J', 15)
            sheet.set_column('K:K', 13)
            sheet.set_column('L:L', 15)                       
            date_one = lines.from_date
            date_wise = datetime.strptime(str(date_one), "%Y-%m-%d")
            date_month = date_wise.month
            date_year = date_wise.year                 
            sheet.merge_range(0,0,1,11, 'Payroll Payment Advice ('+ str(date_month) + ' -  '+str(date_year) + ' )', title_style)
            sheet.write(2, 0,'Period Name',header_style)
            sheet.write(2, 1,lines.name ,text_style)                
            col = 0
            sheet.write(4,col, 'Net salary', header_style)
            col += 1        
            sheet.write(4, col, 'Beneficiary Account', header_style)
            col += 1  
            
            sheet.write(4, col, 'Beneficiary Name', header_style)
            col += 1        
            sheet.write(4, col, 'Beneficiary Address 1', header_style)
            col += 1
            sheet.write(4, col, 'Beneficiary Address 2', header_style)
            col += 1
            sheet.write(4, col, 'Beneficiary Address 3', header_style)
            col += 1
            sheet.write(4, col, 'Payment Description (optional)', header_style)
            col += 1                        
            sheet.write(4, col, 'Basic Salary', header_style)
            col += 1        
            sheet.write(4, col, 'Housing Allowance', header_style)
            col += 1  
            sheet.write(4, col, 'Other Earnings', header_style)
            col += 1  
            sheet.write(4, col, 'Deductions', header_style)
            col += 1 
            sheet.write(4, col, 'Beneficiary ID', header_style)
            col += 1              
            row = 4        
            for line in lines.payroll_two_line_ids:
                row += 1 
                col = 0
                sheet.write(row,col,line.net_salary,number_style)
                col += 1
                sheet.write(row,col,line.employee_id.bank_account_id.display_name or ' ' ,text_style)
                col += 1
                # sheet.write(row,col,line.payroll_reference or ' ' ,text_style)
                # col += 1
                # sheet.write(row,col,line.date_from or ' ' ,text_style)
                # col += 1
                # sheet.write(row,col,line.date_to or ' ' ,text_style)
                # col += 1
                sheet.write(row,col,line.employee_id.name,text_style)
                col += 1
                sheet.write(row,col,line.employee_beneficiary or ' ',text_style)
                col += 1
                sheet.write(row,col,line.employee_beneficiary_address_two or ' ',text_style)
                col += 1
                sheet.write(row,col,line.employee_beneficiary_address_three or ' ',text_style)
                col += 1
                # sheet.write(row,col,line.bank_name or ' ',text_style)
                # col += 1
                sheet.write(row,col,line.payment_description or ' ',text_style)
                col += 1            
                sheet.write(row,col,line.basic_salary or ' ',number_style)
                col += 1
                sheet.write(row,col,line.housing_allowance or ' ',number_style)
                col += 1
                sheet.write(row,col,line.other_earning or ' ',number_style)
                col += 1
                sheet.write(row,col,line.deduction or ' ',number_style)
                col += 1
                sheet.write(row,col,line.beneficiary_id or ' ',text_style)
                # col += 1
              
        
        # sheet.write(5,6,lines.payroll_advice_line_ids,header_style)
        
        if lines.bank_format =='sabb_format':
            header_style = workbook.add_format({'font_name': 'Times', 'bold': True, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'center','color':'orange'})
            title_style = workbook.add_format({'font_name': 'Times', 'font_size': 18, 'bold': True, 'align': 'center','color':'blue','bg_color': '#6B8E23'})      
            text_style = workbook.add_format({'font_name': 'Times', 'font_size': 12, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'left'})
            num_style = workbook.add_format({'font_name': 'Times', 'font_size': 12, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'right'})
            sheet = workbook.add_worksheet("Payroll Payment advice")
            sheet.set_row(0 , 25)         
            sheet.set_column('A:A', 10)
            sheet.set_column('B:B', 10)
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
            sheet.write(1,2,'Date',header_style)
            sheet.write(1,3,lines.from_date.strftime("%d-%m-%Y"),text_style)                 
            col=0
            sheet.write(3, col, 'S.No', header_style)
            col += 1 
            sheet.write(3, col, 'Code', header_style)
            col += 1            
            sheet.write(3, col, 'Employee Name', header_style)
            col += 1
            # sheet.write(3, col, 'Payroll Reference', header_style)
            # col += 1
            sheet.write(3, col, 'Bank Name', header_style)
            col += 1
            sheet.write(3, col,'Bank Account Number',header_style)
            col += 1
            sheet.write(3, col,'Amount',header_style)
            col += 1
            no=1
            row = 3        
            for line in lines.payroll_two_line_ids:
                row += 1 
                col = 0            
                sheet.write(row, col, no, text_style)
                col += 1
                sheet.write(row, col, line.employee_id.employee_no or "", text_style)
                col += 1
                sheet.write(row, col, line.employee_id.name or "", text_style)
                col += 1
                # sheet.write(row, col, line.payroll_reference or "", text_style)
                # col += 1
                
                sheet.write(row, col, line.employee_id.bank_account_id.bank_id.name or "", text_style)
                col += 1
                sheet.write(row, col, line.employee_id.bank_account_id.acc_number or "", num_style)
                col += 1
                # sheet.write(row, col, line.bank_name or "", text_style)
                # col += 1
                # sheet.write(row, col, line.bank_account_number or "", num_style)
                # col += 1
                sheet.write(row, col, line.net_salary or " ", num_style)
                col += 1
                no += 1                      
        
        if lines.bank_format =='bank_3_format':
            header_style = workbook.add_format({'font_name': 'Times', 'bold': True, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'center','color':'orange'})
            title_style = workbook.add_format({'font_name': 'Times', 'font_size': 18, 'bold': True, 'align': 'center','color':'blue','bg_color': '#6B8E23'})
            
            
            text_style = workbook.add_format({'font_name': 'Times', 'font_size': 12, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'left'})
            number_style = workbook.add_format({'font_name': 'Times', 'font_size': 12, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'right'})
            
            sheet = workbook.add_worksheet("Payroll Payment advice - Bank Format III")
            sheet.set_row(0 , 25) 
            
            sheet.set_column('A:A',15)            # col += 1  
            # sheet.write(3, col, 'Regulatory Reporting', header_style)
            # col += 1        
            # sheet.write(3, col, 'Remarks', header_style)
            # col += 1  
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
            
            
            sheet.merge_range('A1:K1', 'Bank III  Payment Advice ('+ str(date_month) + ' -  '+str(date_year) + ' )', title_style)
            
            sheet.write(1,0,'Period Name',header_style)
            sheet.write(1,1,lines.name,text_style)
            sheet.write(1,2,'Date',header_style)
            sheet.write(1,3,lines.from_date.strftime("%d-%m-%Y"),text_style)  
                    
            col=0
            sheet.write(3, col, 'S.No', header_style)
            col += 1
            sheet.write(3, col, 'Employee No', header_style)
            col += 1  
            sheet.write(3, col, 'Employee Resident Id', header_style)
            col += 1          
            sheet.write(3, col, 'Employee Bank ID', header_style)
            col += 1
            sheet.write(3, col, 'Employee Account Number', header_style)
            col += 1        
            sheet.write(3, col, 'Employee Name', header_style)
            col += 1
            # sheet.write(3, col, 'Payroll Reference', header_style)
            # col += 1
            sheet.write(3,col, 'Payment Amount', header_style)
            col += 1
            sheet.write(3, col, 'Basic Salary', header_style)
            col += 1
            sheet.write(3, col, 'Housing Allowance', header_style)
            col += 1  
            sheet.write(3, col, 'Other Earnings', header_style)
            col += 1  
            sheet.write(3, col, 'Deductions', header_style)
            # col += 1  
            # sheet.write(3, col, 'Regulatory Reporting', header_style)
            # col += 1        
            # sheet.write(3, col, 'Remarks', header_style)
            # col += 1  
            
            
            row = 3
            no = 1
            
            for line in lines.payroll_two_line_ids:
                row+=1 
                col=0
                sheet.write(row,col,no or "",text_style)
                col+=1
                sheet.write(row,col,line.employee_id.employee_no or "",text_style)
                col+=1
                sheet.write(row,col,line.beneficiary_id or "",text_style)
                col+=1
                # sheet.write(row,col,line.bank_code or "",text_style)
                # col+=1
                # sheet.write(row,col,line.bank_account_id.acc_number or "",text_style)
                # col+=1
                
                sheet.write(row,col,line.employee_id.bank_account_id.bank_id.name or "",text_style)
                col+=1
                sheet.write(row,col,line.employee_id.bank_account_id.acc_number or "",text_style)
                col+=1
                # sheet.write(row,col,line.bank_ifsc,text_style)
                # col+=1
                sheet.write(row,col,line.employee_id.name or "",text_style)
                col+=1
                # sheet.write(row,col,line.payroll_reference or "",text_style)
                # col+=1
                sheet.write(row,col,line.net_salary or "",number_style)
                col+=1
                sheet.write(row,col,line.basic_salary or "",number_style)
                col+=1
                sheet.write(row,col,line.housing_allowance or "",number_style)
                col+=1
                sheet.write(row,col,line.other_earning or "",number_style)
                col+=1
                sheet.write(row,col,line.deduction or "",number_style)
                col+=1
                # sheet.write(row,col,line.regulatory or "",text_style)
                # col+=1            
                # sheet.write(row,col,line.remarks or "",text_style)
                # col+=1
                
                no += 1
                 
                        
        
