from odoo import fields, models, api, _
import xlsxwriter
import io
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime,date,time
import time
from odoo.exceptions import ValidationError


class LeaveEncashReportExcel(models.AbstractModel):
    _name = 'report.leave_encash_hr.report_leave_encash_xlsx'
    _inherit = 'report.report_xlsx.abstract'    
    _description = 'Leave Encash Report Xlsx'
    
    
    def generate_xlsx_report(self, workbook, data, wizard):

        header_merge_format = workbook.add_format({'bold':True, 'align':'center', 'valign':'vcenter', \
                                            'font_size':10, 'bg_color':'#D3D3D3', 'border':1})

        header_data_format = workbook.add_format({'align':'right', 'valign':'vcenter', \
                                                   'font_size':10, 'border':1})
        header_data_format2 = workbook.add_format({'bold':True,'align':'center', 'valign':'vcenter', \
                                                   'font_size':10,'bg_color':'#F2D7D5', 'border':1})
        header_data_format3 = workbook.add_format({'bold':True,'align':'center', 'valign':'vcenter', \
                                                   'font_size':10,'bg_color':'#87CEFA', 'border':1})
        name_format = workbook.add_format({'align':'left', 'valign':'vcenter', \
                                                   'font_size':10, 'border':1})
        number_format = workbook.add_format({'align': 'right', 'valign': 'vcenter', \
                                           'font_size': 10, 'border': 1})
        header_left_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', \
                                                  'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})
        
        
        
        header_data_format4 = workbook.add_format({'bold':True,'align':'center', 'valign':'vcenter', \
                                                   'font_size':10,'bg_color':'#B7950B', 'border':1})

        sheet = workbook.add_worksheet("Leave Encash Report")
        sheet.set_row(0, 25)
        
        
        sheet.merge_range(0, 0, 2, 13, "Leave Encash Report" , header_merge_format)
        # sheet.write(8, 1, 'Employee Salary report', header_merge_format)
        
        sheet.merge_range(4, 0, 4, 1, 'Company', header_merge_format)
        sheet.merge_range(4, 2, 4, 3, wizard.company_id.name, header_merge_format)
        
        sheet.merge_range(4, 4, 4, 5, 'Start Date', header_merge_format)
        sheet.merge_range(4, 6, 4, 7, wizard.start_date.strftime("%d-%m-%Y"), header_merge_format)
        sheet.merge_range(4, 8, 4, 9, 'End Date', header_merge_format)
        sheet.merge_range(4, 10, 4, 11, wizard.end_date.strftime("%d-%m-%Y"), header_merge_format)
        

        
        row = 5
        col = 0
        sheet.write(row, col, 'S.No', header_merge_format)
        col += 1
        sheet.set_column(0, 0, 10)

        sheet.write(row, col, 'Employee No', header_merge_format)
        sheet.set_column(1, 1, 12)
        col += 1
        sheet.write(row, col, 'Employee Name', header_merge_format)
        col += 1
        sheet.set_column(2, 2, 25)
        # sheet.write(row, col, 'Nationality', header_merge_format)
        # sheet.set_column(3, 3, 18)
        # col += 1
        sheet.write(row, col, 'Department', header_merge_format)
        sheet.set_column(4, 4, 18)
        col += 1
        sheet.write(row, col, 'Job Position', header_merge_format)
        sheet.set_column(5, 5, 18)
        col += 1
        # sheet.write(row, col, 'Location', header_merge_format)
        # sheet.set_column(6, 6, 18)
        # col += 1
        sheet.write(row, col, 'Contract', header_merge_format)
        sheet.set_column(7, 7, 18)
        col += 1
        sheet.write(row, col, 'Reference', header_merge_format)
        sheet.set_column(8, 8, 18)
        col += 1
        sheet.write(row, col, 'Total Allowed leave', header_merge_format)
        sheet.set_column(9, 9, 18)
        col += 1
        sheet.write(row, col, 'Leave Type', header_merge_format)
        sheet.set_column(10, 10, 18)
        col += 1
        sheet.write(row, col, 'Applied Encash Leave', header_merge_format)
        sheet.set_column(11, 11, 12)
        col += 1
        sheet.write(row, col, 'Applied Date', header_merge_format)
        sheet.set_column(12, 12, 12)
        col += 1
        
        sheet.write(row, col, 'Amount', header_merge_format)
        sheet.set_column(13, 13, 18)
        col += 1
        sheet.write(row, col, 'Status', header_merge_format)
        sheet.set_column(14, 14, 18)
        col += 1
        sheet.write(row, col, 'Payslip', header_merge_format)
        sheet.set_column(15, 15, 18)
        
        row = 6
        no = 1
        
        employ_ids = False
        leave_ids = False
        leave_lst = []
        if wizard.employee_ids:
            employ_ids = wizard.employee_ids
        else:
            employ_ids = self.env['hr.employee'].search([])    
        
        if wizard.leave_type_ids:
            leave_ids = wizard.leave_type_ids
        else:
            leave_ids = self.env['hr.leave.type'].search([])    
        
        for employee in employ_ids:
            
            leave_encash_search = self.env['leave.encash'].search([('employee_id','=',employee.id),('date','>=', wizard.start_date),('date','<=',wizard.end_date)])
            
            for leave in leave_encash_search:
                col=0
                sheet.write(row,col,no,number_format)
                col += 1
                
                sheet.write(row,col,leave.employee_id.employee_no,number_format)
                col += 1
                
                sheet.write(row,col,leave.employee_id.name,name_format)
                col += 1
                # sheet.write(row,col,leave.employee_id.country_id.name or '',name_format )
                # col +=1
                sheet.write(row,col,leave.employee_id.department_id.name or '',name_format)
                col += 1
                sheet.write(row,col,leave.employee_id.job_id.name or '',name_format )
                col +=1
                # sheet.write(row,col,leave.employee_id.work_location_id.name,name_format)
                # col += 1
                sheet.write(row,col,leave.employee_id.contract_id.name,name_format )
                col +=1
                sheet.write(row,col,leave.name,name_format )
                col +=1
                sheet.write(row,col,leave.leave_carry,number_format)
                col += 1
                sheet.write(row,col,leave.leave_type_id.name,name_format )
                col +=1
                sheet.write(row,col,leave.days_want,number_format)
                col += 1
                sheet.write(row,col,leave.date.strftime("%d-%m-%Y"),name_format )
                col +=1
                sheet.write(row,col,'{:,.2f}'.format(leave.amount),number_format)
                col += 1
                status_approved_name = dict(leave._fields['state'].selection).get(
                    leave.state)
                sheet.write(row,col,status_approved_name,name_format )
                col +=1
                sheet.write(row,col,leave.payslip_id.name or ' ',name_format )
                col +=1
                
                leave_lst.append(leave)
                
                
                row +=1
                no +=1
        
        
        if len(leave_lst) ==0:
            raise ValidationError("Encash Leave Data is not there in the specific date range")        
            
            
       
        
