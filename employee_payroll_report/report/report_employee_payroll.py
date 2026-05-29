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
from collections import defaultdict


class EmployeePayrollReportExcel(models.AbstractModel):
    _name = 'report.employee_payroll_report.report_payroll_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Employee Payroll Report Xlsx'
    
    
    def generate_xlsx_report(self, workbook, data, wizard):

        header_merge_format = workbook.add_format({'bold':True, 'align':'center', 'valign':'vcenter', \
                                            'font_size':10, 'bg_color':'#D3D3D3', 'border':1})

        
        header_merge_format2 = workbook.add_format({'bold':True, 'align':'right', 'valign':'vcenter', \
                                            'font_size':10, 'bg_color':'#D3D3D3', 'border':1})
        
        header_merge_format3 = workbook.add_format({'bold':True, 'align':'left', 'valign':'vcenter', \
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

        sheet = workbook.add_worksheet("Employee_Payroll_Report")
        sheet.set_row(0, 25)
        
        
        sheet.merge_range(0, 0, 2, 27, "Employee Payroll Report" , header_merge_format)
        
        sheet.merge_range(3, 0, 3, 1, 'Company', header_merge_format)
        sheet.merge_range(3, 2, 3, 3, wizard.company_id.name, header_merge_format)
        
        sheet.merge_range(3, 4, 3, 5, 'Today Date', header_merge_format)
        sheet.merge_range(3, 6, 3, 7, datetime.today().strftime("%d-%m-%Y"), header_merge_format)
        
        sheet.merge_range(4, 0, 4, 1, 'From Date',header_merge_format)
        sheet.merge_range(4, 2, 4, 3, wizard.from_date.strftime("%d-%m-%Y"),header_merge_format)
        
        sheet.merge_range(4, 4, 4, 5, 'To Date',header_merge_format )
        sheet.merge_range(4, 6, 4, 7, wizard.to_date.strftime("%d-%m-%Y"),header_merge_format )
        
        
        sheet.merge_range(6, 0, 6, 10, 'Basic Details', header_data_format4)
        sheet.merge_range(6, 11, 6, 21, 'Allowances', header_data_format2)
        sheet.merge_range(6, 23, 6, 26, 'Deduction', header_data_format3)

        
        row = 7
        col = 0
       
        headers = ['S.No','Employee No','Employee Name','Reference No','Date From','Date To','Department','Job Position','Nationality','Location',
                   'Wage', 'House Allowance', 'Transport Allowance',
                   'School Allowance', 'Food Allowance', 'Fuel Allowance', 'Ticket Allowance','Fixed Allowance',
                   'Mobile Allowance', 'Medical Allowance', 'Other Allowance','Other Transaction','Gross Salary','Gosi','Loan','Others','Total Deduction','Net Salary'
                   ]
        
        col_width = [5,12,25,12,15,15,20,20,18,18,18,15,15,15,15,15,15,15,15,15,15,15,12,12,12,12,15,15]
        
        for header,width in zip(headers,col_width):
            sheet.write(row,col,header,header_merge_format)
            sheet.set_column(col,col,width)
            col +=1
            
         
         
        row = 8
        no = 1
        
        
        domain = []
        
        domain += [('employee_id','in',wizard.employee_ids.ids if wizard.employee_ids else self.env['hr.employee'].search([]).ids)]
        
        if wizard.from_date and wizard.to_date:
            domain += [('date_from','>=',wizard.from_date),('date_to','<=',wizard.to_date)]
         
         
        if wizard.department_ids:
            domain += [('employee_id.department_id','in',wizard.department_ids.ids)]
            sheet.merge_range(5, 0, 5, 27, "Department Wise Search" , header_merge_format)

        
        
        if wizard.job_title_ids:
            domain += [('employee_id.job_id','in', wizard.job_title_ids.ids)]
            sheet.merge_range(5, 0, 5, 27, "Job Wise Search" , header_merge_format)

            
            
        if wizard.nationality_ids:
            domain += [('employee_id.country_of_birth', 'in', wizard.nationality_ids.ids)]
            sheet.merge_range(5, 0, 5, 27, "Nation Wise Search" , header_merge_format)

            
            
        if wizard.branch_location_ids:
            domain += [('employee_id.work_location_id','in', wizard.branch_location_ids.ids)]
            sheet.merge_range(5, 0, 5, 27, "Branch Location Wise Search" , header_merge_format)

                
            
        if wizard.structure_id:
            domain += [('struct_id','=',wizard.structure_id.id)]  
            
            
        payroll_search = self.env['hr.payslip'].search(domain) 
        payroll_search = payroll_search.sorted(key=lambda s:s.employee_id.name.lower())
        
        if wizard.sort_by:
            if wizard.sort_by == 'department':
                payroll_search = payroll_search.filtered(lambda s:s.employee_id.department_id)
                payroll_search = payroll_search.sorted(key=lambda s:s.employee_id.department_id.name.lower())
                sheet.merge_range(5, 0, 5, 27, "Department Wise Sort" , header_merge_format)
  
            elif wizard.sort_by == 'job_title':
                payroll_search = payroll_search.filtered(lambda s:s.employee_id.job_id)
                payroll_search = payroll_search.sorted(key=lambda s:s.employee_id.job_id.name.lower())
                sheet.merge_range(5, 0, 5, 27, "Job Wise Sort" , header_merge_format)

                
            elif wizard.sort_by == 'branch_location':
                payroll_search = payroll_search.filtered(lambda s:s.employee_id.work_location_id)
                payroll_search = payroll_search.sorted(key=lambda s:s.employee_id.work_location_id.name.lower())
                sheet.merge_range(5, 0, 5, 27, "Branch Location Wise Sort" , header_merge_format)

                
            elif wizard.sort_by == 'nationality':
                payroll_search = payroll_search.filtered(lambda s:s.employee_id.country_of_birth)
                payroll_search = payroll_search.sorted(key=lambda s:s.employee_id.country_of_birth.name.lower())     
                sheet.merge_range(5, 0, 5, 27, "Nation Wise Sort" , header_merge_format)

            elif wizard.sort_by == 'employee_no':
                payroll_search = payroll_search.sorted(key = lambda s:(
                    0 if s.employee_id.employee_no and isinstance(s.employee_id.employee_no, str) and s.employee_id.employee_no.isdigit() else 1,
                    int(s.employee_id.employee_no) if s.employee_id.employee_no and isinstance(s.employee_id.employee_no, str) and s.employee_id.employee_no.isdigit() else s.employee_id.employee_no or ' '
                    ))
                sheet.merge_range(5, 0, 5, 27, "Employee Number Wise Sort" , header_merge_format)
    

        
        
        if wizard.department_ids:
            payroll_search = payroll_search.sorted(key=lambda c:c.employee_id.department_id.name.lower())

            
        if wizard.job_title_ids:
            payroll_search = payroll_search.sorted(key = lambda c : c.employee_id.job_id.name.lower())

        
        if wizard.nationality_ids:
            payroll_search = payroll_search.sorted(key = lambda c:c.employee_id.country_of_birth.name.lower())

        
        if wizard.branch_location_ids:
            payroll_search = payroll_search.sorted(key = lambda c:c.employee_id.work_location_id.name.lower()) 
        

        
        '''This is working without grouping'''  
        total_alw = 0.0
        grand_basic_total = 0.0
        grand_hra_total = 0.0
        grand_transport_total = 0.0
        grand_school_total = 0.0
        grand_food_total = 0.0 
        grand_fuel_total = 0.0
        grand_ticket_total = 0.0
        grand_fixed_total = 0.0
        grand_mobile_total = 0.0
        grand_medical_total = 0.0
        grand_others_total = 0.0
        grand_other_allowance_total = 0.0
        
        
        grand_gross_total = 0.0
        grand_gosi_total = 0.0
        grand_loan_total = 0.0
        grand_other_deduction_total = 0.0
        grand_total_other_deduction = 0.0
        grand_net_total = 0.0
        payroll_lst = []
        num =1
        
        group_basic_total = 0.0
        
        group_hra_total = 0.0
        group_transport_total = 0.0
        group_school_total = 0.0
        group_food_total = 0.0 
        group_fuel_total = 0.0
        group_ticket_total = 0.0
        group_fixed_total = 0.0
        group_mobile_total = 0.0
        group_medical_total = 0.0
        group_others_total = 0.0
        group_other_allowance_total = 0.0
    
    
        group_gross_total = 0.0
        group_gosi_total = 0.0
        group_loan_total = 0.0
        group_other_deduction_total = 0.0
        group_total_other_deduction = 0.0
        group_net_total = 0.0
    
        
        department_sort = set()
        job_sort = set()
        nation_sort = set()
        location_sort = set()
        previous_dept_group = None
        previous_job_group = None
        previous_nation_group = None
        previous_branch_group = None
        
        
        for payroll in payroll_search:
            if wizard.sort_by:
                current_dept_group = payroll.employee_id.department_id.name
                current_job_group = payroll.employee_id.job_id.name
                current_nation_group = payroll.employee_id.country_of_birth.name
                current_branch_group = payroll.employee_id.work_location_id.name
                
                if wizard.sort_by == 'department' and payroll.employee_id.department_id.name not in department_sort:
                    if previous_dept_group != current_dept_group and previous_dept_group is not None:
                        sheet.write(row, 9, 'Department Total',header_merge_format2)
                        col = 10
                        sheet.write(row, col, "{:,.2f}".format(group_basic_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_hra_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_transport_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_school_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_food_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_fuel_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_ticket_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_fixed_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_mobile_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_medical_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_others_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_other_allowance_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_gross_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(abs(group_gosi_total)), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(abs(group_loan_total)), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(abs(group_other_deduction_total)), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(abs(group_total_other_deduction)), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_net_total), header_merge_format2)
                        
                        
                        group_basic_total = 0.0
                        group_hra_total = 0.0
                        group_transport_total = 0.0
                        group_school_total = 0.0
                        group_food_total = 0.0 
                        group_fuel_total = 0.0
                        group_ticket_total = 0.0
                        group_fixed_total = 0.0
                        group_mobile_total = 0.0
                        group_medical_total = 0.0
                        group_others_total = 0.0
                        group_other_allowance_total = 0.0
                    
                    
                        group_gross_total = 0.0
                        group_gosi_total = 0.0
                        group_loan_total = 0.0
                        group_other_deduction_total = 0.0
                        group_total_other_deduction = 0.0
                        group_net_total = 0.0
        
                        row += 1
                    previous_dept_group = current_dept_group  
                    
                    
                if wizard.sort_by =='job_title' and payroll.employee_id.job_id.name not in job_sort:
                    if previous_job_group != current_job_group and previous_job_group is not None:
                        sheet.write(row,9, 'Jobwise Total',header_merge_format2)
                        col = 10
                        sheet.write(row, col, "{:,.2f}".format(group_basic_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_hra_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_transport_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_school_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_food_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_fuel_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_ticket_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_fixed_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_mobile_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_medical_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_others_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_other_allowance_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_gross_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(abs(group_gosi_total)), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(abs(group_loan_total)), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(abs(group_other_deduction_total)), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(abs(group_total_other_deduction)), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_net_total), header_merge_format2)
                        
                        group_basic_total = 0.0
                        group_hra_total = 0.0
                        group_transport_total = 0.0
                        group_school_total = 0.0
                        group_food_total = 0.0 
                        group_fuel_total = 0.0
                        group_ticket_total = 0.0
                        group_fixed_total = 0.0
                        group_mobile_total = 0.0
                        group_medical_total = 0.0
                        group_others_total = 0.0
                        group_other_allowance_total = 0.0
                    
                        group_gross_total = 0.0
                        group_gosi_total = 0.0
                        group_loan_total = 0.0
                        group_other_deduction_total = 0.0
                        group_total_other_deduction = 0.0
                        group_net_total = 0.0
                        row += 1
                    previous_job_group = current_job_group      
                    
                if wizard.sort_by == 'nationality' and payroll.employee_id.country_of_birth.name not in  nation_sort:
                    if previous_nation_group != current_nation_group and previous_nation_group is not None:
                        sheet.write(row, 9, 'Nationwise Total',header_merge_format2) 
                        col = 10
                        sheet.write(row, col, "{:,.2f}".format(group_basic_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_hra_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_transport_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_school_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_food_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_fuel_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_ticket_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_fixed_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_mobile_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_medical_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_others_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_other_allowance_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_gross_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(abs(group_gosi_total)), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(abs(group_loan_total)), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(abs(group_other_deduction_total)), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(abs(group_total_other_deduction)), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_net_total), header_merge_format2)
                        
                        group_basic_total = 0.0
                        group_hra_total = 0.0
                        group_transport_total = 0.0
                        group_school_total = 0.0
                        group_food_total = 0.0 
                        group_fuel_total = 0.0
                        group_ticket_total = 0.0
                        group_fixed_total = 0.0
                        group_mobile_total = 0.0
                        group_medical_total = 0.0
                        group_others_total = 0.0
                        group_other_allowance_total = 0.0
                    
                        group_gross_total = 0.0
                        group_gosi_total = 0.0
                        group_loan_total = 0.0
                        group_other_deduction_total = 0.0
                        group_total_other_deduction = 0.0
                        group_net_total = 0.0
                        row += 1
                    previous_nation_group = current_nation_group
                if wizard.sort_by == 'branch_location' and payroll.employee_id.work_location_id.name  not in  location_sort:
                    if previous_branch_group != current_branch_group and previous_branch_group is not None:
                        sheet.write(row,9,'Locationwise Total',header_merge_format2)
                        col = 10
                        sheet.write(row, col, "{:,.2f}".format(group_basic_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_hra_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_transport_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_school_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_food_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_fuel_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_ticket_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_fixed_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_mobile_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_medical_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_others_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_other_allowance_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_gross_total), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(abs(group_gosi_total)), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(abs(group_loan_total)), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(abs(group_other_deduction_total)), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(abs(group_total_other_deduction)), header_merge_format2)
                        col += 1
                        sheet.write(row, col, "{:,.2f}".format(group_net_total), header_merge_format2)
                        
                        group_basic_total = 0.0
                        group_hra_total = 0.0
                        group_transport_total = 0.0
                        group_school_total = 0.0
                        group_food_total = 0.0 
                        group_fuel_total = 0.0
                        group_ticket_total = 0.0
                        group_fixed_total = 0.0
                        group_mobile_total = 0.0
                        group_medical_total = 0.0
                        group_others_total = 0.0
                        group_other_allowance_total = 0.0
                    
                        group_gross_total = 0.0
                        group_gosi_total = 0.0
                        group_loan_total = 0.0
                        group_other_deduction_total = 0.0
                        group_total_other_deduction = 0.0
                        group_net_total = 0.0
                        row += 1
                        
                    previous_branch_group = current_branch_group
                    
                     
            if wizard.sort_by == 'department' and payroll.employee_id.department_id.name not in department_sort:
                sheet.merge_range(row,0,row,27,payroll.employee_id.department_id.name,header_merge_format3)
                department_sort.add(payroll.employee_id.department_id.name)
                row += 1
                num = 1
                
            elif wizard.sort_by == 'job_title' and payroll.employee_id.job_id.name not in job_sort:
                sheet.merge_range(row, 0, row, 27, payroll.employee_id.job_id.name, header_merge_format3)
                job_sort.add(payroll.employee_id.job_id.name)
                row += 1
                num = 1
        
            elif wizard.sort_by=='branch_location' and payroll.employee_id.work_location_id.name not in location_sort:
                sheet.merge_range(row, 0, row, 27, payroll.employee_id.work_location_id.name,header_merge_format3)
                location_sort.add(payroll.employee_id.work_location_id.name)
                row += 1
                num = 1
        
            elif wizard.sort_by == 'nationality' and payroll.employee_id.country_of_birth.name not in nation_sort:
                sheet.merge_range(row, 0, row, 27, payroll.employee_id.country_of_birth.name,header_merge_format3)
                nation_sort.add(payroll.employee_id.country_of_birth.name)
                row += 1
                num = 1    
        
        
            if wizard.sort_by in ['department','job_title','nationality','branch_location']:
                col = 0
                sheet.write(row,col,num, name_format)
            else:
                col = 0
                sheet.write(row,col,no, name_format)    
                
                 
            col += 1
        
            sheet.write(row, col, payroll.employee_id.employee_no or ' ', name_format)
            col += 1
        
            sheet.write(row, col, payroll.employee_id.display_name or '', name_format)
            col += 1
        
            sheet.write(row, col, payroll.number or '', name_format)
            col += 1
            
            sheet.write(row, col, payroll.date_from.strftime("%d-%m-%Y") or '', name_format)
            col += 1
            
            sheet.write(row, col, payroll.date_to.strftime("%d-%m-%Y") or '', name_format)
            col += 1
        
            sheet.write(row, col, payroll.employee_id.department_id.name or ' ', name_format)
            col += 1
        
            sheet.write(row, col, payroll.employee_id.job_id.name or ' ', name_format)
            col += 1
        
            sheet.write(row, col, payroll.employee_id.country_of_birth.name or ' ',name_format)
            col += 1
        
            sheet.write(row, col, payroll.employee_id.work_location_id.name or ' ',name_format)
            col += 1
        
            basic_total = 0.0
            hra_total = 0.0
            transport_total = 0.0
            school_total = 0.0
            food_total = 0.0 
            fuel_total = 0.0
            ticket_total = 0.0
            fixed_total = 0.0
            mobile_total = 0.0
            medical_total = 0.0
            others_total = 0.0
            other_allowance_total = 0.0
        
        
            gross_total = 0.0
            gosi_total = 0.0
            loan_total = 0.0
            other_deduction_total = 0.0
            total_other_deduction = 0.0
            net_total = 0.0
            ''' for gross calculation'''
            all_allowance_total = 0.0
            all_allowance_total_individual_group = 0.0
            all_allowance_total_grand = 0.0
            
            '''for net calculation'''
            all_deduction_total = 0.0
            all_deduction_total_individual_group = 0.0
            all_deduction_total_grand = 0.0
            
        
            for line in payroll.line_ids:
                if line.code == 'BASIC':
                    sheet.write(row, col, "{:,.2f}".format(line.total) or ' ' ,header_data_format)
                    basic_total += line.total
                    grand_basic_total += line.total
                    group_basic_total += line.total
                    col += 1
                if line.code == 'HRA':
                    sheet.write(row, col, "{:,.2f}".format(line.total) or ' ',header_data_format)
                    hra_total += line.total
                    grand_hra_total += line.total
                    group_hra_total += line.total
                    col += 1
                if line.code == 'TRANSPORT':
                    sheet.write(row, col, "{:,.2f}".format(line.total) or ' ',header_data_format)
                    transport_total += line.total
                    grand_transport_total += line.total
                    group_transport_total += line.total
                    col += 1
        
                if line.code == 'SCHOOL':
                    sheet.write(row, col, "{:,.2f}".format(line.total) or ' ' ,header_data_format)
                    school_total += line.total
                    grand_school_total += line.total
                    group_school_total += line.total
                    col += 1
        
                if line.code == 'FOOD':
                    sheet.write(row, col, "{:,.2f}".format(line.total) or ' ',header_data_format)
                    food_total += line.total
                    grand_food_total += line.total
                    group_food_total += line.total
                    col += 1    
        
                if line.code == 'FUEL':
                    sheet.write(row, col, "{:,.2f}".format(line.total) or ' ',header_data_format)
                    fuel_total += line.total
                    grand_fuel_total += line.total
                    group_fuel_total += line.total
                    col += 1 
        
                if line.code == 'TICKET':
                    sheet.write(row, col, "{:,.2f}".format(line.total) or ' ',header_data_format)
                    ticket_total += line.total
                    grand_ticket_total += line.total
                    group_ticket_total += line.total
                    col += 1
        
                if line.code == 'FIXED':
                    sheet.write(row, col, "{:,.2f}".format(line.total) or ' ',header_data_format)
                    fixed_total += line.total
                    grand_fixed_total += line.total 
                    group_fixed_total += line.total
                    col += 1
        
                if line.code == 'MOBILE':
                    sheet.write(row, col, "{:,.2f}".format(line.total) or ' ',header_data_format)
                    mobile_total += line.total 
                    grand_mobile_total += line.total
                    group_mobile_total += line.total
                    col += 1        
        
                if line.code == 'MEDICAL':
                    sheet.write(row, col, "{:,.2f}".format(line.total) or ' ' ,header_data_format)
                    medical_total += line.total
                    grand_medical_total += line.total
                    group_medical_total += line.total                        
                    col += 1
        
                if line.code == 'OTA':
                    sheet.write(row, col, "{:,.2f}".format(line.total) or ' ',header_data_format)
                    others_total += line.total
                    grand_others_total += line.total
                    group_others_total += line.total
                    col += 1
        
                if line.category_id.code == 'ALW':
                    if not line.code in ['HRA','TRANSPORT','SCHOOL','FOOD','FUEL','TICKET','FIXED','MOBILE','MEDICAL','OTA']:
                        other_allowance_total += line.total
                        grand_other_allowance_total += line.total
                        group_other_allowance_total += line.total
                
                
                if line.category_id.code in ['BASIC','ALW']:
                    all_allowance_total += line.total
                    all_allowance_total_individual_group += line.total
                    all_allowance_total_grand += line.total
        
                # if line.category_id.code =="GROSS":
                #     print("..........lssssssssssssssssssssssssssssssssss",line.total,line.amount)
                #     gross_total += line.total
                #     grand_gross_total += line.total
                #     group_gross_total += line.total
                #

        
                if line.code == 'GOSI':
                    gosi_total += line.total
                    grand_gosi_total += line.total
                    group_gosi_total += line.total
        
                if line.code == 'Loan':
                    loan_total += line.total
                    grand_loan_total += line.total
                    group_loan_total += line.total
        
                if line.category_id.code  == 'DED':
                    if not line.code in ['GOSI','Loan']:
                        other_deduction_total += line.total
                        grand_other_deduction_total += line.total
                        group_other_deduction_total += line.total
        
                if line.category_id.code  == 'DED':
                    total_other_deduction += line.total
                    grand_total_other_deduction += line.total
                    group_total_other_deduction += line.total
        
        
                # if line.code=="NET":
                #     net_total += line.total
                #     grand_net_total += line.total
                #     group_net_total += line.total
            ''' for gross calculation'''
            gross_total += all_allowance_total
            group_gross_total += all_allowance_total_individual_group
            grand_gross_total += all_allowance_total_grand

            
            ''' for net calculation'''
            net_total += all_allowance_total + total_other_deduction
            group_net_total += all_allowance_total_individual_group + total_other_deduction
            # grand_net_total += all_allowance_total_grand + grand_total_other_deduction

            sheet.write(row, col, "{:,.2f}".format(other_allowance_total) or ' ', header_data_format)
            col += 1
            sheet.write(row, col, "{:,.2f}".format(gross_total) or ' ', header_data_format)
            col += 1 
        
            sheet.write(row, col, "{:,.2f}".format(abs(gosi_total)) or ' ', header_data_format)
            col += 1
        
            sheet.write(row, col, "{:,.2f}".format(abs(loan_total)) or ' ', header_data_format)
            col += 1
        
            sheet.write(row, col, "{:,.2f}".format(abs(other_deduction_total)) or ' ', header_data_format)
            col += 1
        
            sheet.write(row, col, "{:,.2f}".format(abs(total_other_deduction)) or ' ', header_data_format)
            col += 1
        
        
            sheet.write(row, col, "{:,.2f}".format(net_total) or ' ', header_data_format)
            col += 1 
        
            payroll_lst.append(payroll.employee_id.display_name)
        
            row += 1
            no += 1
            
            num += 1
 
        ''' Department Group wise total'''   
        if wizard.sort_by:
            if previous_dept_group is not None:
                sheet.write(row, 9, 'Department Total', header_merge_format2)
                col = 10
                sheet.write(row, col, "{:,.2f}".format(group_basic_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_hra_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_transport_total) or ' ' , header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_school_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_food_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_fuel_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_ticket_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_fixed_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_mobile_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_medical_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_others_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_other_allowance_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_gross_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(abs(group_gosi_total)) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(abs(group_loan_total)) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(abs(group_other_deduction_total)) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(abs(group_total_other_deduction)) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_net_total) or ' ', header_merge_format2)
                row += 1
            
            ''' Job Groupwise Sub total'''
            if previous_job_group is not None:
                sheet.write(row, 9,'JobWise Total',header_merge_format2)
                col = 10
                sheet.write(row, col, "{:,.2f}".format(group_basic_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_hra_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_transport_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_school_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_food_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_fuel_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_ticket_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_fixed_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_mobile_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_medical_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_others_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_other_allowance_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_gross_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(abs(group_gosi_total)) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(abs(group_loan_total)) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(abs(group_other_deduction_total)) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(abs(group_total_other_deduction)) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_net_total) or ' ', header_merge_format2)
                row += 1
            
            '''Nation group wise total'''
            if previous_nation_group is not None:
                col = 9
                sheet.write(row,col,'Nationwise Total',header_merge_format2)
                col = 10
                sheet.write(row, col, "{:,.2f}".format(group_basic_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_hra_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_transport_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_school_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_food_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_fuel_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_ticket_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_fixed_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_mobile_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_medical_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_others_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_other_allowance_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_gross_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(abs(group_gosi_total)) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(abs(group_loan_total)) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(abs(group_other_deduction_total)) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(abs(group_total_other_deduction)) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_net_total) or ' ', header_merge_format2)
                row += 1
            '''Branch location group wise total'''
            if previous_branch_group is not None:
                sheet.write(row, 9, 'Locationwise Total' , header_merge_format2)
                col = 10
                sheet.write(row, col, "{:,.2f}".format(group_basic_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_hra_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_transport_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_school_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_food_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_fuel_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_ticket_total) or  ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_fixed_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_mobile_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_medical_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_others_total) or  ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_other_allowance_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_gross_total) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(abs(group_gosi_total)) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(abs(group_loan_total)) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(abs(group_other_deduction_total)) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(abs(group_total_other_deduction)) or ' ', header_merge_format2)
                col += 1
                sheet.write(row, col, "{:,.2f}".format(group_net_total) or ' ', header_merge_format2)
                row += 1
            
            
        if wizard.sort_by in ['department','job_title','nationality','branch_location']:   
            sheet.merge_range(row,0,row, 9, 'Grand Total',header_merge_format2)
        else:
            sheet.merge_range(row,0,row, 9, 'Total',header_merge_format2)
        
        '''for grand net total '''
        grand_net_total += grand_gross_total + grand_total_other_deduction
       
        col=10
        sheet.write(row,col,"{:,.2f}".format(grand_basic_total) or ' ',header_merge_format2)
        col += 1
        
        sheet.write(row,col,"{:,.2f}".format(grand_hra_total) or ' ' ,header_merge_format2)
        col += 1
        
        sheet.write(row,col,"{:,.2f}".format(grand_transport_total) or ' ',header_merge_format2)
        col += 1
        
        sheet.write(row,col,"{:,.2f}".format(grand_school_total) or ' ',header_merge_format2)
        col += 1
        
        sheet.write(row,col,"{:,.2f}".format(grand_food_total) or ' ',header_merge_format2)
        col += 1
        
        sheet.write(row,col,"{:,.2f}".format(grand_fuel_total) or ' ',header_merge_format2)
        col += 1
        
        
        sheet.write(row,col,"{:,.2f}".format(grand_ticket_total) or ' ',header_merge_format2)
        col += 1
        
        sheet.write(row,col,"{:,.2f}".format(grand_fixed_total) or ' ',header_merge_format2)
        col += 1
        
        sheet.write(row,col,"{:,.2f}".format(grand_mobile_total) or ' ',header_merge_format2)
        col += 1
        
        sheet.write(row,col,"{:,.2f}".format(grand_medical_total) or ' ' ,header_merge_format2)
        col += 1
        
        sheet.write(row,col,"{:,.2f}".format(grand_others_total) or ' ',header_merge_format2)
        col += 1
        
        sheet.write(row,col,"{:,.2f}".format(grand_other_allowance_total) or ' ',header_merge_format2)
        col += 1
        
        sheet.write(row,col,"{:,.2f}".format(grand_gross_total) or ' ',header_merge_format2)
        col += 1
        
        sheet.write(row,col,"{:,.2f}".format(abs(grand_gosi_total)) or ' ',header_merge_format2)
        col += 1
        
        sheet.write(row,col,"{:,.2f}".format(abs(grand_loan_total)) or ' ',header_merge_format2)
        col += 1
        
        sheet.write(row,col,"{:,.2f}".format(abs(grand_other_deduction_total)) or ' ',header_merge_format2)
        col += 1
        
        sheet.write(row,col,"{:,.2f}".format(abs(grand_total_other_deduction)) or ' ',header_merge_format2)
        col += 1    
        
        sheet.write(row,col,"{:,.2f}".format(grand_net_total) or ' ',header_merge_format2)
       
        if len(payroll_lst) ==0:
            raise ValidationError("Sorry Payroll of the Employees is not there in this range.")   
        
        
        
        
        
        
        
        

        
        
        
        
        
        
        
        
            
            