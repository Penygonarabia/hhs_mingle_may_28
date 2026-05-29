from odoo import fields, models, api, _
from odoo.tools.misc import xlsxwriter
import io
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime,date,time
import time
import pytz
import pandas as pd
from odoo.exceptions import warnings
from odoo.exceptions import ValidationError


class PayrollEmployeeReportExcel(models.AbstractModel):
    _name = 'report.payroll_employee_report.report_employee_salary_xlsx'
    _inherit = 'report.report_xlsx.abstract'    
    _description = 'Employee Salary Report Xlsx'
    
    
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
        header_left_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', \
                                                  'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})
        
        
        
        header_data_format4 = workbook.add_format({'bold':True,'align':'center', 'valign':'vcenter', \
                                                   'font_size':10,'bg_color':'#B7950B', 'border':1})

        sheet = workbook.add_worksheet("Employee_Salary_Report")
        sheet.set_row(0, 25)
        
        
        sheet.merge_range(0, 0, 2, 23, "Employee Salary Report" , header_merge_format)
        # sheet.write(8, 1, 'Employee Salary report', header_merge_format)
        
        sheet.merge_range(4, 0, 4, 1, 'Company', header_merge_format)
        sheet.merge_range(4, 2, 4, 3, wizard.company_id.name, header_merge_format)
        
        sheet.merge_range(4, 4, 4, 5, 'Today Date', header_merge_format)
        sheet.merge_range(4, 6, 4, 7, datetime.today().strftime("%d-%m-%Y"), header_merge_format)
        
        sheet.merge_range(5, 0, 5, 10, 'Basic Details', header_data_format4)
        sheet.merge_range(5, 11, 5, 20, 'Allowances', header_data_format2)
        sheet.merge_range(5, 21, 5, 23, 'Deduction', header_data_format3)

        
        row = 6
        col = 0
        sheet.write(row, col, 'S.No', header_merge_format)
        col += 1
        sheet.set_column(0, 0, 10)
        sheet.write(row, col, 'Employee Name', header_merge_format)
        col += 1
        sheet.set_column(1, 1, 25)
        sheet.write(row, col, 'Employee No', header_merge_format)
        sheet.set_column(2, 2, 12)
        col += 1
        sheet.write(row, col, 'Department', header_merge_format)
        sheet.set_column(3, 3, 18)
        col += 1
        sheet.write(row, col, 'Job Position', header_merge_format)
        sheet.set_column(4, 4, 18)
        col += 1
        sheet.write(row, col, 'Employee Category', header_merge_format)
        sheet.set_column(5, 5, 12)
        col += 1
        
        sheet.write(row, col, 'HR Responsible', header_merge_format)
        sheet.set_column(6, 6, 18)
        col += 1
        
        sheet.write(row, col, 'Date Of Joining', header_merge_format)
        sheet.set_column(7, 7, 12)
        col += 1
        sheet.write(row, col, 'Contract Start Date', header_merge_format)
        sheet.set_column(8,8,12)
        col += 1
        sheet.write(row, col, 'Contract End Date', header_merge_format)
        sheet.set_column(9,9,12)
        col += 1
        
        
        sheet.write(row, col, 'Wage', header_merge_format)
        col += 1
        
        sheet.write(row, col, 'House Allowance', header_merge_format)
        col += 1
        
        sheet.write(row, col, 'Transport Allowance', header_merge_format)
        col += 1
        
        sheet.write(row, col, 'School Allowance', header_merge_format)
        col += 1
        sheet.write(row, col, 'Food Allowance', header_merge_format)
        col += 1
        
        sheet.write(row, col, 'Fuel Allowance', header_merge_format)
        col += 1
        
        
        sheet.write(row, col, 'Ticket Allowance', header_merge_format)
        col += 1
        
        sheet.write(row, col, 'Fixed Allowance', header_merge_format)
        col += 1
        
        sheet.write(row, col, 'Mobile Allowance', header_merge_format)
        col += 1
        
        sheet.write(row, col, 'Medical Allowance', header_merge_format)
        col += 1
        sheet.write(row, col, 'Other Allowance', header_merge_format)
        col += 1
        


        sheet.write(row, col, 'Employee contribution', header_merge_format)
        col += 1
        
        sheet.write(row, col, 'Employer contribution for Saudi', header_merge_format)
        col += 1
        sheet.write(row, col, 'Employer contribution for Non-Saudi', header_merge_format)
        # col += 1
        # sheet.write(row, col, 'Gross Salary', header_merge_format)
        #

        sheet.set_column('K:AD',14)
        
        row = 7
        no = 1
        
        
        employee_ids = False
        if wizard.employee_ids:
            employee_ids = wizard.employee_ids
        else:
           employee_ids = self.env['hr.employee'].search([])
        # gross_salary = 0
  
        for employee in employee_ids:
            
            contract_search = self.env['hr.contract'].search([('employee_id','=',employee.id),('state','=','open')])
            
            for contract in contract_search:
                col = 0
                sheet.write(row,col,no, name_format)
                col += 1
                sheet.write(row,col,contract.employee_id.display_name or ' ' ,name_format)
                col += 1
                
                sheet.write(row,col,contract.employee_no or ' ',name_format)
                col += 1
                
                sheet.write(row,col,contract.department_id.name or ' ',name_format)
                col += 1
                
                sheet.write(row,col,contract.job_id.name or ' ',name_format)
                col += 1
                
                sheet.write(row,col,contract.type_id.name or ' ',name_format)
                col += 1
                
                sheet.write(row,col,contract.hr_responsible_id.display_name or ' ',name_format)
                col += 1
                if contract.employee_id.join_date:
                    sheet.write(row,col,contract.employee_id.join_date.strftime("%d-%m-%Y"),name_format)
                else:
                    sheet.write(row,col,'',name_format)
                    
                col += 1
                if contract.date_start:
                    sheet.write(row,col,contract.date_start.strftime("%d-%m-%Y") or ' ',name_format)
                else:
                    sheet.write(row,col, ' ',name_format)
                    
                col += 1
                
                if contract.date_end:
                    sheet.write(row,col,contract.date_end.strftime("%d-%m-%Y") or ' ',name_format)
                else:
                    sheet.write(row,col,' ',name_format)

                col += 1
                sheet.write(row,col,"{:,.2f}".format(contract.wage) or ' ',header_data_format)
                col += 1 
               
                # sheet.write(row,col,"{:,.2f}".format(contract.hra) or ' ',header_data_format)
                # col += 1 
                #
                # sheet.write(row,col,"{:,.2f}".format(contract.da) or ' ',header_data_format)
                # col += 1 
                #
                # sheet.write(row,col,"{:,.2f}".format(contract.travel_allowance) or ' ',header_data_format)
                # col += 1 
                #
                # sheet.write(row,col,"{:,.2f}".format(contract.meal_allowance) or ' ',header_data_format)
                # col += 1 
                #
                # sheet.write(row,col,"{:,.2f}".format(contract.medical_allowance) or ' ',header_data_format)
                # col += 1 
                #
                # sheet.write(row,col,"{:,.2f}".format(contract.other_allowance) or ' ',header_data_format)
                # col += 1 
                #

               
               
                sheet.write(row,col,"{:,.2f}".format(contract.house_allowance) or ' ',header_data_format)
                col += 1 
               
                sheet.write(row,col,"{:,.2f}".format(contract.transport_allowance) or ' ',header_data_format)
                col += 1 
               
                sheet.write(row,col,"{:,.2f}".format(contract.school_allowance) or ' ',header_data_format)
                col += 1 
               
               
                
                sheet.write(row,col,"{:,.2f}".format(contract.food_allowance) or ' ',header_data_format)
                col += 1 
               
               
                sheet.write(row,col,"{:,.2f}".format(contract.fuel_allowance) or ' ',header_data_format)
                col += 1 
               
               
                sheet.write(row,col,"{:,.2f}".format(contract.ticket_allowance) or ' ',header_data_format)
                col += 1 
               
                sheet.write(row,col,"{:,.2f}".format(contract.fixed_allowance) or ' ',header_data_format)
                col += 1 
               
                sheet.write(row,col,"{:,.2f}".format(contract.mobile_allowance) or ' ',header_data_format)
                col += 1 
               
                sheet.write(row,col,"{:,.2f}".format(contract.work_allowance) or ' ',header_data_format)
                col += 1 
               
                sheet.write(row,col,"{:,.2f}".format(contract.housing_allowance) or ' ',header_data_format)
                col += 1
               
                sheet.write(row,col,"{:,.2f}".format(contract.gosi_amt) or ' ',header_data_format)
                col += 1 
               
               
                sheet.write(row,col,"{:,.2f}".format(contract.gosi_comp_amt) or ' ',header_data_format)
                col += 1 
               

                sheet.write(row,col,"{:,.2f}".format(contract.gosi_non_comp) or ' ',header_data_format)
                col += 1 
                
                # gross_salary =  contract.wage + contract.hra + contract.da + contract.da + contract.travel_allowance +\
                #                 contract.meal_allowance  + contract.medical_allowance + contract.other_allowance + \
                #                 contract.house_allowance + contract.transport_allowance + contract.school_allowance + \
                #                 contract.food_allowance + contract.fuel_allowance + contract.ticket_allowance + \
                #                 contract.fixed_allowance + contract.mobile_allowance + contract.work_allowance + contract.housing_allowance - \
                #                 contract.gosi_amt - contract.gosi_comp_amt - contract.gosi_non_comp
                #
                # sheet.write(row,col,"{:,.2f}".format(gross_salary) or ' ',header_data_format)
                #

                row += 1
                no += 1
        
        
        
        
        
        
        
        
        
