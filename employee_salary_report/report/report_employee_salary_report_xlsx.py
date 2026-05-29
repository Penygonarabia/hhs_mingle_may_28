from odoo import fields, models, api, _
import io
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime,date,time
import time
import pytz
import pandas as pd
from odoo.exceptions import warnings
from odoo.exceptions import ValidationError
from odoo.tools.misc import xlsxwriter


class PayrollEmployeeReportExcel(models.AbstractModel):
    _name = 'report.employee_salary_report.report_salary_employee_xlsx'
    _inherit = 'report.report_xlsx.abstract'    
    _description = 'Employee Salary Report Xlsx'
    
    
    def generate_xlsx_report(self, workbook, data, wizard):

        header_merge_format = workbook.add_format({'bold':True, 'align':'center', 'valign':'vcenter', \
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

        sheet = workbook.add_worksheet("Employee_Salary_Report")
        sheet.set_row(0, 25)
        
        
        sheet.merge_range(0, 0, 2, 24, "Employee Salary Report" , header_merge_format)
        # sheet.write(8, 1, 'Employee Salary report', header_merge_format)
        
        sheet.merge_range(4, 0, 4, 1, 'Company', header_merge_format)
        sheet.merge_range(4, 2, 4, 3, wizard.company_id.name, header_merge_format)
        
        sheet.merge_range(4, 4, 4, 5, 'Today Date', header_merge_format)
        sheet.merge_range(4, 6, 4, 7, datetime.today().strftime("%d-%m-%Y"), header_merge_format)
        
        sheet.merge_range(6, 0, 6, 12, 'Basic Details', header_data_format4)
        sheet.merge_range(6, 13, 6, 22, 'Allowances', header_data_format2)
        sheet.merge_range(6, 23, 6, 24, 'Deduction', header_data_format3)

        
        row = 7
        col = 0
       
        headers = ['S.No','Employee No','Employee Name','Department','Job Position','Nationality','Location','HR Responsible',
                   'Date Of Joining','Exit Date','Contract Start Date','Contract End Date',  'Wage', 'House Allowance', 'Transport Allowance',
                   'School Allowance', 'Food Allowance', 'Fuel Allowance', 'Ticket Allowance','Fixed Allowance',
                   'Mobile Allowance', 'Medical Allowance', 'Other Allowance','Employee contribution',
                   'Employer contribution',
                   ]
        
        col_width = [10,12,25,20,18,18,18,18,18,15,15,15,15,15,15,15,15,15,15,15,12,12,12,12,15]
        
        for header,width in zip(headers,col_width):
            sheet.write(row,col,header,header_merge_format)
            sheet.set_column(col,col,width)
            col +=1
            
        row = 8
        no = 1
        
        
        
        domain = []
        domain  += [('employee_id', 'in', wizard.employee_ids.ids if wizard.employee_ids else self.env['hr.employee'].search([]).ids)]
        
        if wizard.from_joining_date and wizard.to_joining_date:
            domain += [('employee_id.joining_date','>=',wizard.from_joining_date),('employee_id.joining_date','<=',wizard.to_joining_date)]
            sheet.merge_range(5, 0, 5, 1, 'From Joining Date', header_merge_format)
            sheet.merge_range(5, 2, 5, 3, wizard.from_joining_date.strftime("%d-%m-%Y"), header_merge_format)
            sheet.merge_range(5, 4, 5, 5, 'To Joining Date', header_merge_format)
            sheet.merge_range(5, 6, 5, 7, wizard.to_joining_date.strftime("%d-%m-%Y"), header_merge_format)
            
        if wizard.from_contract_expiry_date and wizard.to_contract_expiry_date:
            domain += [('date_end','>=',wizard.from_contract_expiry_date),('date_end','<=',wizard.to_contract_expiry_date)]
            sheet.merge_range(5, 0, 5, 1, 'Contract Expiry Start Date', header_merge_format)
            sheet.merge_range(5, 2, 5, 3, wizard.from_contract_expiry_date.strftime("%d-%m-%Y"), header_merge_format)
            sheet.merge_range(5, 4, 5, 5, 'Contract Expiry End Date', header_merge_format)
            sheet.merge_range(5, 6, 5, 7, wizard.to_contract_expiry_date.strftime("%d-%m-%Y"), header_merge_format)
            
        
        if wizard.from_termination_date and wizard.to_termination_date:
            domain += [('exit_date', '<=', wizard.to_termination_date), ('exit_date', '>=', wizard.from_termination_date)]
            sheet.merge_range(5, 0, 5, 1, 'Termination Start Date', header_merge_format)
            sheet.merge_range(5, 2, 5, 3, wizard.from_termination_date.strftime("%d-%m-%Y"), header_merge_format)
            sheet.merge_range(5, 4, 5, 5, 'Termination End Date', header_merge_format)
            sheet.merge_range(5, 6, 5, 7, wizard.to_termination_date.strftime("%d-%m-%Y"), header_merge_format)
        
            
        
        if wizard.employee_status:
            if wizard.employee_status == 'all':
                domain += [('employee_id.state', 'in', ['draft','exit'])]
                # domain += ['|', ('employee_id.contract_warning', '=', False),
                #            ('employee_id.contract_warning', '=', True)]
            elif wizard.employee_status == 'active':
                domain += [('employee_id.state', '=', 'draft'), ('employee_id.contract_warning', '=', False)]
            elif wizard.employee_status == 'terminated':
                domain += [('employee_id.state', '=', 'exit'),('employee_id.contract_warning', '=', True)]
                # domain += ['|', ('employee_id.state', '=', 'exit'), ('employee_id.contract_warning', '=', True)]
                
                
        if wizard.department_ids:
            domain += [('department_id','in',wizard.department_ids.ids)]
            sheet.merge_range(5, 0, 5, 24, "Department Wise Search" , header_merge_format)
 
            
            
        if wizard.job_title_ids:
            domain += [('job_id','in',wizard.job_title_ids.ids)]
            sheet.merge_range(5, 0, 5, 24, "Job Wise Search" , header_merge_format)

         
        if wizard.nationality_ids:
            domain += [('employee_id.country_of_birth','in',wizard.nationality_ids.ids)]
            sheet.merge_range(5, 0, 5, 24, "Nation Wise Search" , header_merge_format)

            
        
        if wizard.branch_location_ids :
            domain += [('employee_id.work_location_id','in',wizard.branch_location_ids.ids)]
            sheet.merge_range(5, 0, 5, 24, "Branch Location Wise Search" , header_merge_format)

        
                
        # domain += [('state','=','open')]
        salary_search = self.env['hr.contract'].search(domain)
        salary_search = salary_search.sorted(lambda s:s.employee_id.name.lower())
  
        
        if wizard.sort_by:
            if wizard.sort_by == 'department':
                salary_search = salary_search.filtered(lambda s:s.department_id)
                salary_search = salary_search.sorted(key=lambda s:s.department_id.name.lower())
                sheet.merge_range(5, 0, 5, 24, "Department Wise Sort" , header_merge_format)
  
            elif wizard.sort_by == 'job_title':
                salary_search = salary_search.filtered(lambda s:s.job_id)
                salary_search = salary_search.sorted(key=lambda s:s.job_id.name.lower())
                sheet.merge_range(5, 0, 5, 24, "Job Wise Sort" , header_merge_format)

                
            elif wizard.sort_by == 'branch_location':
                salary_search = salary_search.filtered(lambda s:s.employee_id.work_location_id)
                salary_search = salary_search.sorted(key=lambda s:s.employee_id.work_location_id.name.lower())
                sheet.merge_range(5, 0, 5, 24, "Branch Location Wise Sort" , header_merge_format)

                
            elif wizard.sort_by == 'nationality':
                salary_search = salary_search.filtered(lambda s:s.employee_id.country_of_birth)
                salary_search = salary_search.sorted(key=lambda s:s.employee_id.country_of_birth.name.lower())     
                sheet.merge_range(5, 0, 5, 24, "Nation Wise Sort" , header_merge_format)

            elif wizard.sort_by == 'employee_no':
                '''first employee number integer field is come and then string is come'''
                salary_search = salary_search.sorted(key = lambda s : (
                    0 if s.employee_id.employee_no and isinstance(s.employee_id.employee_no,str) and s.employee_id.employee_no.isdigit() else 1,
                    int(s.employee_id.employee_no) if s.employee_id.employee_no and isinstance(s.employee_id.employee_no,str) and s.employee_id.employee_no.isdigit() else s.employee_id.employee_no or ''
                    ))
                sheet.merge_range(5, 0, 5, 24, "Employee Number Wise Sort", header_merge_format)

        
        if wizard.department_ids:
            salary_search = salary_search.sorted(key=lambda c:c.department_id.name.lower())

            
        if wizard.job_title_ids:
            salary_search = salary_search.sorted(key = lambda c : c.job_id.name.lower())

        
        if wizard.nationality_ids:
            salary_search = salary_search.sorted(key = lambda c:c.employee_id.country_of_birth.name.lower())

        
        if wizard.branch_location_ids:
            salary_search = salary_search.sorted(key = lambda c:c.employee_id.work_location_id.name.lower()) 
        
        salary_lst = []
        num =1
        department_sort = set()
        job_sort = set()
        nation_sort = set()
        location_sort = set()
        
        for salary in salary_search:
            if wizard.sort_by == 'department' and salary.department_id.name not in department_sort:
                sheet.merge_range(row,0,row,24,salary.department_id.name,header_merge_format3)
                department_sort.add(salary.department_id.name)
                row += 1
                num = 1
            elif wizard.sort_by == 'job_title' and salary.job_id.name not in job_sort:
                sheet.merge_range(row, 0, row, 24, salary.job_id.name, header_merge_format3)
                job_sort.add(salary.job_id.name)
                row += 1
                num = 1
                
            elif wizard.sort_by=='branch_location' and salary.employee_id.work_location_id.name not in location_sort:
                sheet.merge_range(row, 0, row, 24, salary.employee_id.work_location_id.name,header_merge_format3)
                location_sort.add(salary.employee_id.work_location_id.name)
                row += 1
                num = 1
                
            elif wizard.sort_by == 'nationality' and salary.employee_id.country_of_birth.name not in nation_sort:
                sheet.merge_range(row, 0, row, 24, salary.employee_id.country_of_birth.name,header_merge_format3)
                nation_sort.add(salary.employee_id.country_of_birth.name)
                row += 1
                num = 1    
                         
                
            if wizard.sort_by in ['department','job_title','nationality','branch_location']:
                col = 0
                sheet.write(row,col,num, name_format)
            else:
                col = 0
                sheet.write(row,col,no, name_format)    
                
            # col = 0
            # sheet.write(row,col,no, name_format)
           
            col += 1
            sheet.write(row,col,salary.employee_no or ' ',name_format)
            col += 1
            
            sheet.write(row,col,salary.employee_id.display_name or ' ' ,name_format)
            col += 1
            
            sheet.write(row,col,salary.department_id.name or ' ',name_format)
            col += 1
            
            sheet.write(row,col,salary.job_id.name or ' ',name_format)
            col += 1
            
            sheet.write(row,col,salary.employee_id.country_of_birth.name or ' ',name_format)
            col += 1
            
            sheet.write(row,col,salary.employee_id.work_location_id.name or ' ',name_format)
            col += 1
            
            sheet.write(row,col,salary.hr_responsible_id.display_name or ' ',name_format)
            col += 1
            sheet.write(row,col,salary.employee_id.joining_date.strftime("%d-%m-%Y") if salary.employee_id.joining_date else ' ',name_format)
            col += 1
            
            sheet.write(row,col,salary.employee_id.exit_date.strftime("%d-%m-%Y") if salary.employee_id.exit_date else ' ',name_format)
            col += 1
            
            sheet.write(row,col,salary.date_start.strftime("%d-%m-%Y") if salary.date_start else ' ',name_format)
            
            col += 1
            
            sheet.write(row,col,salary.date_end.strftime("%d-%m-%Y") if salary.date_end else ' ',name_format)
            col += 1
            sheet.write(row,col,"{:,.2f}".format(salary.wage) or ' ',header_data_format)
            col += 1 
           
           
            sheet.write(row,col,"{:,.2f}".format(salary.house_allowance) or ' ',header_data_format)
            col += 1 
           
            sheet.write(row,col,"{:,.2f}".format(salary.transport_allowance) or ' ',header_data_format)
            col += 1 
           
            sheet.write(row,col,"{:,.2f}".format(salary.school_allowance) or ' ',header_data_format)
            col += 1 
           
            
            sheet.write(row,col,"{:,.2f}".format(salary.food_allowance) or ' ',header_data_format)
            col += 1 
           
            sheet.write(row,col,"{:,.2f}".format(salary.fuel_allowance) or ' ',header_data_format)
            col += 1 
           
            sheet.write(row,col,"{:,.2f}".format(salary.ticket_allowance) or ' ',header_data_format)
            col += 1 
           
            sheet.write(row,col,"{:,.2f}".format(salary.fixed_allowance) or ' ',header_data_format)
            col += 1 
           
            sheet.write(row,col,"{:,.2f}".format(salary.mobile_allowance) or ' ',header_data_format)
            col += 1 
           
            sheet.write(row,col,"{:,.2f}".format(salary.work_allowance) or ' ',header_data_format)
            col += 1 
           
            sheet.write(row,col,"{:,.2f}".format(salary.housing_allowance) or ' ',header_data_format)
            col += 1
            
            sheet.write(row,col,"{:,.2f}".format(salary.gosi_amt) or ' ',header_data_format)
            col += 1 
            

            salary_gosi_amount = 0
            
            if not salary.employee_id.is_saudi:
                salary_gosi_amount += salary.gosi_non_comp
            if salary.employee_id.is_saudi:
                salary_gosi_amount += salary.gosi_comp_amt
            
            sheet.write(row,col,"{:,.2f}".format(salary_gosi_amount) or ' ',header_data_format)
            col += 1 
            
            salary_lst.append(salary.employee_id.display_name)

       
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
            num += 1
    
        if len(salary_lst) ==0:
            raise ValidationError("Sorry Salary of the Employees is not there.")   
            
        
        
        # employee_ids = False
        # if wizard.employee_ids:
        #     employee_ids = wizard.employee_ids
        # else:
        #    employee_ids = self.env['hr.employee'].search([])
        # # gross_salary = 0
        #
        # for employee in employee_ids:
        #
        #     contract_search = self.env['hr.contract'].search([('employee_id','=',employee.id),('state','=','open')])
        #
        #     for contract in contract_search:
        #         col = 0
        #         sheet.write(row,col,no, name_format)
        #         col += 1
        #         sheet.write(row,col,contract.employee_id.display_name or ' ' ,name_format)
        #         col += 1
        #
        #         sheet.write(row,col,contract.employee_no or ' ',name_format)
        #         col += 1
        #
        #         sheet.write(row,col,contract.department_id.name or ' ',name_format)
        #         col += 1
        #
        #         sheet.write(row,col,contract.job_id.name or ' ',name_format)
        #         col += 1
        #
        #         sheet.write(row,col,contract.type_id.name or ' ',name_format)
        #         col += 1
        #
        #         sheet.write(row,col,contract.hr_responsible_id.display_name or ' ',name_format)
        #         col += 1
        #         if contract.employee_id.join_date:
        #             sheet.write(row,col,contract.employee_id.join_date.strftime("%d-%m-%Y"),name_format)
        #         else:
        #             sheet.write(row,col,'',name_format)
        #
        #         col += 1
        #         if contract.date_start:
        #             sheet.write(row,col,contract.date_start.strftime("%d-%m-%Y") or ' ',name_format)
        #         else:
        #             sheet.write(row,col, ' ',name_format)
        #
        #         col += 1
        #
        #         if contract.date_end:
        #             sheet.write(row,col,contract.date_end.strftime("%d-%m-%Y") or ' ',name_format)
        #         else:
        #             sheet.write(row,col,' ',name_format)
        #
        #         col += 1
        #         sheet.write(row,col,"{:,.2f}".format(contract.wage) or ' ',header_data_format)
        #         col += 1 
        #
        #         # sheet.write(row,col,"{:,.2f}".format(contract.hra) or ' ',header_data_format)
        #         # col += 1 
        #         #
        #         # sheet.write(row,col,"{:,.2f}".format(contract.da) or ' ',header_data_format)
        #         # col += 1 
        #         #
        #         # sheet.write(row,col,"{:,.2f}".format(contract.travel_allowance) or ' ',header_data_format)
        #         # col += 1 
        #         #
        #         # sheet.write(row,col,"{:,.2f}".format(contract.meal_allowance) or ' ',header_data_format)
        #         # col += 1 
        #         #
        #         # sheet.write(row,col,"{:,.2f}".format(contract.medical_allowance) or ' ',header_data_format)
        #         # col += 1 
        #         #
        #         # sheet.write(row,col,"{:,.2f}".format(contract.other_allowance) or ' ',header_data_format)
        #         # col += 1 
        #         #
        #
        #
        #
        #         sheet.write(row,col,"{:,.2f}".format(contract.house_allowance) or ' ',header_data_format)
        #         col += 1 
        #
        #         sheet.write(row,col,"{:,.2f}".format(contract.transport_allowance) or ' ',header_data_format)
        #         col += 1 
        #
        #         sheet.write(row,col,"{:,.2f}".format(contract.school_allowance) or ' ',header_data_format)
        #         col += 1 
        #
        #
        #
        #         sheet.write(row,col,"{:,.2f}".format(contract.food_allowance) or ' ',header_data_format)
        #         col += 1 
        #
        #
        #         sheet.write(row,col,"{:,.2f}".format(contract.fuel_allowance) or ' ',header_data_format)
        #         col += 1 
        #
        #
        #         sheet.write(row,col,"{:,.2f}".format(contract.ticket_allowance) or ' ',header_data_format)
        #         col += 1 
        #
        #         sheet.write(row,col,"{:,.2f}".format(contract.fixed_allowance) or ' ',header_data_format)
        #         col += 1 
        #
        #         sheet.write(row,col,"{:,.2f}".format(contract.mobile_allowance) or ' ',header_data_format)
        #         col += 1 
        #
        #         sheet.write(row,col,"{:,.2f}".format(contract.work_allowance) or ' ',header_data_format)
        #         col += 1 
        #
        #         sheet.write(row,col,"{:,.2f}".format(contract.housing_allowance) or ' ',header_data_format)
        #         col += 1
        #
        #         sheet.write(row,col,"{:,.2f}".format(contract.gosi_amt) or ' ',header_data_format)
        #         col += 1 
        #
        #
        #         sheet.write(row,col,"{:,.2f}".format(contract.gosi_comp_amt) or ' ',header_data_format)
        #         col += 1 
        #
        #
        #         sheet.write(row,col,"{:,.2f}".format(contract.gosi_non_comp) or ' ',header_data_format)
        #         col += 1 
        #
        #         # gross_salary =  contract.wage + contract.hra + contract.da + contract.da + contract.travel_allowance +\
        #         #                 contract.meal_allowance  + contract.medical_allowance + contract.other_allowance + \
        #         #                 contract.house_allowance + contract.transport_allowance + contract.school_allowance + \
        #         #                 contract.food_allowance + contract.fuel_allowance + contract.ticket_allowance + \
        #         #                 contract.fixed_allowance + contract.mobile_allowance + contract.work_allowance + contract.housing_allowance - \
        #         #                 contract.gosi_amt - contract.gosi_comp_amt - contract.gosi_non_comp
        #         #
        #         # sheet.write(row,col,"{:,.2f}".format(gross_salary) or ' ',header_data_format)
        #         #
        #
        #         row += 1
        #         no += 1
        #

        
        
        
        
        
        
        
        
