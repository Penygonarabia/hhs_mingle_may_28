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


class EmployeeDetailReportExcel(models.AbstractModel):
    _name = 'report.employee_details_report.report_employee_detail_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Employee Detail Report Xlsx'
    
    
    def generate_xlsx_report(self, workbook, data, wizard):

        header_merge_format = workbook.add_format({'bold':True, 'align':'center', 'valign':'vcenter', \
                                            'font_size':10, 'bg_color':'#D3D3D3', 'border':1})

        header_data_format = workbook.add_format({'align':'right', 'valign':'vcenter', \
                                                   'font_size':10, 'border':1})
        
        header_merge_format3 = workbook.add_format({'bold':True, 'align':'left', 'valign':'vcenter', \
                                            'font_size':10, 'bg_color':'#D3D3D3', 'border':1})

        header_data_format2 = workbook.add_format({'bold':True,'align':'center', 'valign':'vcenter', \
                                                   'font_size':10,'bg_color':'#F2D7D5', 'border':1})
        header_data_format3 = workbook.add_format({'bold':True,'align':'center', 'valign':'vcenter', \
                                                   'font_size':10,'bg_color':'#87CEFA', 'border':1})
        name_format = workbook.add_format({'align':'left', 'valign':'vcenter', \
                                                   'font_size':10, 'border':1})
        num_format = workbook.add_format({'align': 'right', 'valign': 'vcenter', \
                                           'font_size': 10, 'border': 1})
        header_left_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', \
                                                  'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})
        
        
        
        header_data_format4 = workbook.add_format({'bold':True,'align':'center', 'valign':'vcenter', \
                                                   'font_size':10,'bg_color':'#B7950B', 'border':1})

        sheet = workbook.add_worksheet("Employee List Report")
        sheet.set_row(0, 25)
        
        
        sheet.merge_range(0, 0, 2, 15, "Employee List Report" , header_merge_format)
        
        sheet.merge_range(4, 0, 4, 1, 'Company', header_merge_format)
        sheet.merge_range(4, 2, 4, 3, wizard.company_id.name, header_merge_format)
        
        sheet.merge_range(4, 4, 4, 5, 'Today Date', header_merge_format)
        sheet.merge_range(4, 6, 4, 7, datetime.today().strftime("%d-%m-%Y"), header_merge_format)
        

        
        row = 6
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
        sheet.write(row, col, 'Gender', header_merge_format)
        sheet.set_column(3, 3, 18)
        col += 1
        sheet.write(row, col, 'Date of Birth', header_merge_format)
        sheet.set_column(4, 4, 18)
        col += 1
        sheet.write(row, col, 'Nationality', header_merge_format)
        sheet.set_column(5, 5, 18)
        col += 1
        sheet.write(row, col, 'Religion', header_merge_format)
        sheet.set_column(6, 6, 18)
        col += 1
        sheet.write(row, col, 'Job Position', header_merge_format)
        sheet.set_column(8, 8, 18)
        col += 1
        sheet.write(row, col, 'Department', header_merge_format)
        sheet.set_column(7, 7, 18)
        col += 1
        sheet.write(row, col, 'Location', header_merge_format)
        sheet.set_column(9, 9, 18)
        col += 1
        sheet.write(row, col, 'Date of Joining', header_merge_format)
        sheet.set_column(10, 10, 12)
        col += 1
        
        sheet.write(row, col, 'Exit Date', header_merge_format)
        sheet.set_column(11, 11, 18)
        col += 1
        
        sheet.write(row, col, 'Contract Name', header_merge_format)
        sheet.set_column(12, 12, 18)
        col += 1
        sheet.write(row, col, 'Contract Start Date',header_merge_format)
        sheet.set_column(13, 13, 18)
        col += 1
        sheet.write(row, col, 'Contract End Date', header_merge_format)
        sheet.set_column(14, 14, 18)
        col += 1
        
        sheet.write(row, col, 'Status', header_merge_format)
        sheet.set_column(15, 15, 18)
        # col += 1
        
        row = 7
        no = 1
        
        
        domain = []
        
        employee_ids = False
        employee_status = False
        dept_ids=False
            
        domain += [('id', 'in', wizard.employee_ids.ids if wizard.employee_ids else self.env['hr.employee'].search([]).ids)]

        if wizard.from_joining_date and wizard.to_joining_date:
            domain += [('joining_date', '<=', wizard.to_joining_date), ('joining_date', '>=', wizard.from_joining_date)]
            
            sheet.merge_range(5, 0, 5, 1, 'From Joining Date', header_merge_format)
            sheet.merge_range(5, 2, 5, 3, wizard.from_joining_date.strftime("%d-%m-%Y"), header_merge_format)
            sheet.merge_range(5, 4, 5, 5, 'To Joining Date', header_merge_format)
            sheet.merge_range(5, 6, 5, 7, wizard.to_joining_date.strftime("%d-%m-%Y"), header_merge_format)
       
        if wizard.from_termination_date and wizard.to_termination_date:
            domain += [('exit_date', '<=', wizard.to_termination_date), ('exit_date', '>=', wizard.from_termination_date)]
            
            sheet.merge_range(5, 0, 5, 1, 'Termination Start Date', header_merge_format)
            sheet.merge_range(5, 2, 5, 3, wizard.from_termination_date.strftime("%d-%m-%Y"), header_merge_format)
            sheet.merge_range(5, 4, 5, 5, 'Termination End Date', header_merge_format)
            sheet.merge_range(5, 6, 5, 7, wizard.to_termination_date.strftime("%d-%m-%Y"), header_merge_format)
        
            

        if wizard.from_contract_expiry_date and wizard.to_contract_expiry_date:
            domain += [('contract_id.date_end', '<=', wizard.to_contract_expiry_date), ('contract_id.date_end', '>=', wizard.from_contract_expiry_date)]
            
            sheet.merge_range(5, 0, 5, 1, 'Contract Expiry Start Date', header_merge_format)
            sheet.merge_range(5, 2, 5, 3, wizard.from_contract_expiry_date.strftime("%d-%m-%Y"), header_merge_format)
            sheet.merge_range(5, 4, 5, 5, 'Contract Expiry End Date', header_merge_format)
            sheet.merge_range(5, 6, 5, 7, wizard.to_contract_expiry_date.strftime("%d-%m-%Y"), header_merge_format)
            
                      
    
        if wizard.employee_status:
            if wizard.employee_status == 'all':
                domain += [('state','in',['draft','exit'])]
                # domain += ['|', ('contract_warning', '=', False),
                #            ('contract_warning', '=', True)]
            elif wizard.employee_status == 'active':
                domain += [('state', '=', 'draft'), ('contract_warning', '=', False)]
            elif wizard.employee_status == 'terminated':
                domain += [('state', '=', 'exit'),('contract_warning', '=', True)]

                # domain += ['|', ('state', '=', 'exit'), ('contract_warning', '=', True)]


        
        if wizard.department_ids:
            domain += [('department_id', 'in', wizard.department_ids.ids)]
            sheet.merge_range(5, 0, 5, 15, "Department Wise Search" , header_merge_format)


        if wizard.job_title_ids:
            domain += [('job_id', 'in', wizard.job_title_ids.ids)]
            sheet.merge_range(5, 0, 5, 15, "Job Wise Search" , header_merge_format)


        if wizard.nationality_ids:
            domain += [('country_of_birth', 'in', wizard.nationality_ids.ids)]
            sheet.merge_range(5, 0, 5, 15, "Nation Wise Search" , header_merge_format)


        if wizard.branch_location_ids:
            domain += [('work_location_id', 'in', wizard.branch_location_ids.ids)]
            sheet.merge_range(5, 0, 5, 15, "Branch Location Wise Search" , header_merge_format)

        
        employee_search = self.env['hr.employee'].search(domain)
        employee_search = employee_search.sorted(key=lambda s:s.name.lower())

        
        employee_lst =[]
        
        if wizard.sort_by:
            if wizard.sort_by == 'department':
                employee_search = employee_search.filtered(lambda c : c.department_id)
                employee_search = employee_search.sorted(key=lambda c:c.department_id.name.lower())
                sheet.merge_range(5, 0, 5, 15, "Department Wise Sort" , header_merge_format)

            
            elif wizard.sort_by == 'job_title':
                employee_search = employee_search.filtered(lambda c : c.job_id) 
                employee_search = employee_search.sorted(key = lambda c : c.job_id.name.lower())
                sheet.merge_range(5, 0, 5, 15, "Job Wise Sort" , header_merge_format)

                
            elif wizard.sort_by == 'nationality':
                employee_search = employee_search.filtered(lambda c : c.country_of_birth)
                employee_search = employee_search.sorted(key = lambda c:c.country_of_birth.name.lower())
                sheet.merge_range(5, 0, 5, 15, "Nation Wise Sort" , header_merge_format)

            
            elif wizard.sort_by == 'branch_location':
                employee_search = employee_search.filtered(lambda c : c.work_location_id.id)
                employee_search = employee_search.sorted(key = lambda c:c.work_location_id.name.lower())
                sheet.merge_range(5, 0, 5, 15, "Branch Location Wise Sort" , header_merge_format)
            
            elif wizard.sort_by =='employee_no':
                employee_search = employee_search.sorted(
                    key=lambda c: (
                        0 if c.employee_no and isinstance(c.employee_no, str) and c.employee_no.isdigit() else 1,  # Prioritize numeric first
                        int(c.employee_no) if c.employee_no and isinstance(c.employee_no, str) and c.employee_no.isdigit() else c.employee_no or ''
                    ))

                sheet.merge_range(5, 0, 5, 15, "Employee Number Wise Sort", header_merge_format)

               
        
        '''for two department search only two department is sorting and display it'''
        if wizard.department_ids:
            employee_search = employee_search.sorted(key=lambda c:c.department_id.name.lower())
            # sheet.merge_range(5, 0, 5, 15, "Department Wise Search" , header_merge_format)

            
        if wizard.job_title_ids:
            employee_search = employee_search.sorted(key = lambda c : c.job_id.name.lower())
            # sheet.merge_range(5, 0, 5, 15, "Job Wise Search" , header_merge_format)

        
        if wizard.nationality_ids:
            employee_search = employee_search.sorted(key = lambda c:c.country_of_birth.name.lower())

        
        if wizard.branch_location_ids:
            employee_search = employee_search.sorted(key = lambda c:c.work_location_id.name.lower()) 
       
                        
                
        seen_department = set()
        seen_job = set()
        seen_nation = set()
        seen_branch = set()
        num = 1
        for employee in employee_search:
            if wizard.sort_by == 'department' and employee.department_id.name not in seen_department:
                sheet.merge_range(row, 0, row, 15, employee.department_id.name, header_merge_format3 )
                seen_department.add(employee.department_id.name)
                row += 1
                num = 1
                
            elif wizard.sort_by == 'job_title' and employee.job_id.name  not in seen_job :
                sheet.merge_range(row, 0, row, 15, employee.job_id.name, header_merge_format3)
                seen_job.add(employee.job_id.name)
                row += 1
                num = 1
                
            elif wizard.sort_by == 'nationality' and employee.country_of_birth.name not in seen_nation:
                sheet.merge_range(row, 0, row, 15, employee.country_of_birth.name, header_merge_format3 )
                seen_nation.add(employee.country_of_birth.name)
                row += 1
                num = 1
                
            elif wizard.sort_by == 'branch_location' and employee.work_location_id.name not in seen_branch:
                sheet.merge_range(row, 0, row, 15, employee.work_location_id.name, header_merge_format3)
                seen_branch.add(employee.work_location_id.name)
                row += 1
                num = 1          
            
            
            if wizard.sort_by in ['department','job_title','nationality','branch_location']:
                col = 0
                sheet.write(row,col,num, num_format)
            else:
                col = 0
                sheet.write(row,col,no, num_format)
                    
                
            # col = 0
            # sheet.write(row,col,no, num_format)
            col += 1
            sheet.write(row, col, employee.employee_no or ' ', name_format)
            col += 1
            sheet.write(row,col,employee.display_name or ' ' ,name_format)
            col += 1

            gender_display_name = dict(employee._fields['gender'].selection).get(
                employee.gender)
            sheet.write(row, col, gender_display_name or ' ', name_format)
            col += 1
            sheet.write(row, col, employee.birthday.strftime("%d-%m-%Y")  if employee.birthday else ' ', name_format)
            col += 1
            sheet.write(row, col, employee.country_of_birth.name or ' ', name_format)
            col += 1

            religion_display_name = dict(employee._fields['religion'].selection).get(
                employee.religion)
            sheet.write(row, col, religion_display_name or ' ', name_format)
            col += 1
          
            sheet.write(row, col, employee.job_id.name or ' ', name_format)
            col += 1
            sheet.write(row,col,employee.department_id.name or ' ',name_format)
            col += 1

            sheet.write(row,col,employee.work_location_id.name or ' ',name_format)
            col += 1
            
           
            sheet.write(row,col,employee.joining_date.strftime("%d-%m-%Y") if employee.joining_date else ' ',name_format)
            col += 1
     
            sheet.write(row,col,employee.exit_date.strftime("%d-%m-%Y") if employee.exit_date else ' ',name_format)
            col += 1
           
            sheet.write(row,col,employee.contract_id.name or ' ', name_format)
            col += 1
            
            sheet.write(row,col,employee.contract_id.date_start.strftime("%d-%m-%Y") if employee.contract_id.date_start else ' ', name_format)
            col += 1
           
            sheet.write(row,col,employee.contract_id.date_end.strftime("%d-%m-%Y")  if employee.contract_id.date_end else ' ', name_format)
            col += 1
            

            if employee.contract_id.state:
                state_display_name = dict(employee.contract_id._fields['state'].selection).get(
                    employee.contract_id.state)
                sheet.write(row, col, state_display_name or ' ', name_format)
            else:
                sheet.write(row,col,' ',name_format)

            col += 1

            employee_lst.append(employee.employee_no)
            row += 1
            no += 1
            num += 1
        
        if len(employee_lst)==0:
            raise ValidationError("Employee is not there in this Range")
        
        
    
    
        ''' Employee Joining Date'''
        # if wizard.from_joining_date and wizard.to_joining_date:
        #     sheet.merge_range(5, 0, 5, 1, 'From Joining Date', header_merge_format)
        #     sheet.merge_range(5, 2, 5, 3, wizard.from_joining_date.strftime("%d-%m-%Y"), header_merge_format)
        #
        #     sheet.merge_range(5, 4, 5, 5, 'To Joining Date', header_merge_format)
        #     sheet.merge_range(5, 6, 5, 7, wizard.to_joining_date.strftime("%d-%m-%Y"), header_merge_format)
        #
        #     employee_ids = False
        #     employee_status = False
        #     # dept_ids=False
        #
        #     if wizard.employee_status:
        #         employee_status = wizard.employee_status
        #
        #
        #     if wizard.employee_ids:
        #         employee_ids = wizard.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #
        #     ## for combination of department in joing date and ending date only
        #     # if wizard.department_ids:
        #     #     dept_ids = wizard.department_ids
        #     # else:
        #     #     dept_ids = self.env['hr.department'].search([])
        #
        #
        #     joining_lst = []
        #     for employee in employee_ids:
        #         joining_date_search = False
        #
        #         if employee_status == 'active':
        #             ### this is for department is added in employee for joining date
        #             # if dept_ids:
        #             #     joining_date_search = self.env['hr.employee'].search([('contract_warning','=',False),('id','=',employee.id),('joining_date','>=',wizard.from_joining_date),('joining_date','<=',wizard.to_joining_date),('state','=','draft'),('department_id','in',dept_ids.ids])
        #             #
        #             # else    
        #             #     joining_date_search = self.env['hr.employee'].search([('contract_warning','=',False),('id','=',employee.id),('joining_date','>=',wizard.from_joining_date),('joining_date','<=',wizard.to_joining_date),('state','=','draft')])
        #             joining_date_search = self.env['hr.employee'].search([('contract_warning','=',False),('id','=',employee.id),('joining_date','>=',wizard.from_joining_date),('joining_date','<=',wizard.to_joining_date),('state','=','draft')])
        #
        #         elif employee_status == 'terminated':
        #             joining_date_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('id','=',employee.id),('joining_date','>=',wizard.from_joining_date),('joining_date','<=',wizard.to_joining_date),('state','=','exit')])
        #
        #         elif employee_status == 'all':
        #             joining_date_search = self.env['hr.employee'].search([('id','=',employee.id),('joining_date','>=',wizard.from_joining_date),('joining_date','<=',wizard.to_joining_date)])
        #
        #
        #
        #         if joining_date_search:
        #             for joining_date in joining_date_search:
        #                 col = 0
        #                 sheet.write(row,col,no, num_format)
        #                 col += 1
        #                 sheet.write(row, col, joining_date.employee_no or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row,col,joining_date.display_name or ' ' ,name_format)
        #                 col += 1
        #
        #                 gender_display_name = dict(joining_date._fields['gender'].selection).get(
        #                     joining_date.gender)
        #                 sheet.write(row, col, gender_display_name or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, joining_date.birthday.strftime("%d-%m-%Y")  if joining_date.birthday else ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, joining_date.country_id.name or ' ', name_format)
        #                 col += 1
        #
        #                 religion_display_name = dict(joining_date._fields['religion'].selection).get(
        #                     joining_date.religion)
        #                 sheet.write(row, col, religion_display_name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row, col, joining_date.job_id.name or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row,col,joining_date.department_id.name or ' ',name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,joining_date.work_location_id.name or ' ',name_format)
        #                 col += 1
        #
        #
        #                 sheet.write(row,col,joining_date.joining_date.strftime("%d-%m-%Y") if joining_date.joining_date else ' ',name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,joining_date.exit_date.strftime("%d-%m-%Y") if joining_date.exit_date else ' ',name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,joining_date.contract_id.name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,joining_date.contract_id.date_start.strftime("%d-%m-%Y") if joining_date.contract_id.date_start else ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,joining_date.contract_id.date_end.strftime("%d-%m-%Y")  if joining_date.contract_id.date_end else ' ', name_format)
        #                 col += 1
        #
        #
        #                 if joining_date.contract_id.state:
        #                     state_display_name = dict(joining_date.contract_id._fields['state'].selection).get(
        #                         joining_date.contract_id.state)
        #                     sheet.write(row, col, state_display_name or ' ', name_format)
        #                 else:
        #                     sheet.write(row,col,' ',name_format)
        #
        #                 col += 1
        #
        #                 joining_lst.append(joining_date.employee_no)
        #                 row += 1
        #                 no += 1
        #
        #     if len(joining_lst)==0:
        #         raise ValidationError("Employee is not there in this Date  Range")
        #
        #     '''Contract Expiration Date'''
        # elif wizard.from_contract_expiry_date and wizard.to_contract_expiry_date:
        #
        #     sheet.merge_range(5, 0, 5, 1, 'Contract Expiry Start Date', header_merge_format)
        #     sheet.merge_range(5, 2, 5, 3, wizard.from_contract_expiry_date.strftime("%d-%m-%Y"), header_merge_format)
        #
        #     sheet.merge_range(5, 4, 5, 5, 'Contract Expiry End Date', header_merge_format)
        #     sheet.merge_range(5, 6, 5, 7, wizard.to_contract_expiry_date.strftime("%d-%m-%Y"), header_merge_format)
        #
        #
        #     employee_ids = False
        #     employee_status = False
        #     if wizard.employee_status:
        #         employee_status = wizard.employee_status
        #
        #
        #     if wizard.employee_ids:
        #         employee_ids = wizard.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #     expiry_lst = []
        #     for employee in employee_ids:
        #         expiration_search = False
        #
        #         if employee_status == 'active':
        #             expiration_search = self.env['hr.employee'].search([('contract_warning','=',False),('id','=',employee.id),('contract_id.date_end','>=',wizard.from_contract_expiry_date),('contract_id.date_end','<=',wizard.to_contract_expiry_date),('state','=','draft')])
        #         elif employee_status == 'terminated':
        #             expiration_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('id','=',employee.id),('contract_id.date_end','>=',wizard.from_contract_expiry_date),('contract_id.date_end','<=',wizard.to_contract_expiry_date),('state','=','exit')])
        #
        #         elif employee_status == 'all':
        #             expiration_search = self.env['hr.employee'].search([('id','=',employee.id),('contract_id.date_end','>=',wizard.from_contract_expiry_date),('contract_id.date_end','<=',wizard.to_contract_expiry_date)])
        #
        #         if expiration_search:
        #             for expiry in expiration_search:
        #                 col = 0
        #                 sheet.write(row,col,no, num_format)
        #                 col += 1
        #                 sheet.write(row, col, expiry.employee_no or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row,col,expiry.display_name or ' ' ,name_format)
        #                 col += 1
        #
        #                 gender_display_name = dict(expiry._fields['gender'].selection).get(
        #                     expiry.gender)
        #                 sheet.write(row, col, gender_display_name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row, col, expiry.birthday.strftime("%d-%m-%Y") if expiry.birthday else ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, expiry.country_id.name or ' ', name_format)
        #                 col += 1
        #
        #                 religion_display_name = dict(expiry._fields['religion'].selection).get(
        #                     expiry.religion)
        #                 sheet.write(row, col, religion_display_name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row, col, expiry.job_id.name or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row,col,expiry.department_id.name or ' ',name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,expiry.work_location_id.name or ' ',name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,expiry.joining_date.strftime("%d-%m-%Y") if expiry.joining_date else ' ',name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,expiry.exit_date.strftime("%d-%m-%Y") if expiry.exit_date else ' ',name_format)
        #                 col += 1
        #
        #
        #                 sheet.write(row,col,expiry.contract_id.name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,expiry.contract_id.date_start.strftime("%d-%m-%Y") if expiry.contract_id.date_start else ' ', name_format)
        #                 col += 1
        #                 sheet.write(row,col,expiry.contract_id.date_end.strftime("%d-%m-%Y") if expiry.contract_id.date_end else ' ', name_format)
        #
        #                 col += 1
        #
        #                 if expiry.contract_id.state:
        #                     state_display_name = dict(expiry.contract_id._fields['state'].selection).get(
        #                         expiry.contract_id.state)
        #                     sheet.write(row, col, state_display_name or ' ', name_format)
        #                 else:
        #                     sheet.write(row,col,' ',name_format)
        #
        #                 col += 1
        #
        #                 expiry_lst.append(expiry.employee_no)
        #                 row += 1
        #                 no += 1
        #
        #     if len(expiry_lst)==0:
        #         raise ValidationError("Contract Expiry Employee is not there in this Date  Range")
        #
        #
        #     '''Termination wise Employee search'''
        # elif wizard.from_termination_date and wizard.to_termination_date:
        #
        #     sheet.merge_range(5, 0, 5, 1, 'Termination Start Date', header_merge_format)
        #     sheet.merge_range(5, 2, 5, 3, wizard.from_termination_date.strftime("%d-%m-%Y"), header_merge_format)
        #
        #     sheet.merge_range(5, 4, 5, 5, 'Termination End Date', header_merge_format)
        #     sheet.merge_range(5, 6, 5, 7, wizard.to_termination_date.strftime("%d-%m-%Y"), header_merge_format)
        #
        #
        #     employee_ids = False
        #     employee_status = False
        #     if wizard.employee_status:
        #         employee_status = wizard.employee_status
        #
        #
        #     if wizard.employee_ids:
        #         employee_ids = wizard.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #     termination_lst = []
        #     for employee in employee_ids:
        #         termination_search = False
        #
        #         if employee_status == 'active':
        #             termination_search = self.env['hr.employee'].search([('contract_warning','=',False),('id','=',employee.id),('exit_date','>=',wizard.from_termination_date),('exit_date','<=',wizard.to_termination_date),('state','=','draft')])
        #         elif employee_status == 'terminated':
        #             termination_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('id','=',employee.id),('exit_date','>=',wizard.from_termination_date),('exit_date','<=',wizard.to_termination_date),('state','=','exit')])
        #
        #         elif employee_status == 'all':
        #             termination_search = self.env['hr.employee'].search([('id','=',employee.id),('exit_date','>=',wizard.from_termination_date),('exit_date','<=',wizard.to_termination_date)])
        #
        #         if termination_search:
        #             for terminate in termination_search:
        #                 col = 0
        #                 sheet.write(row,col,no, num_format)
        #                 col += 1
        #                 sheet.write(row, col, terminate.employee_no or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row,col,terminate.display_name or ' ' ,name_format)
        #                 col += 1
        #
        #                 gender_display_name = dict(terminate._fields['gender'].selection).get(
        #                     terminate.gender)
        #                 sheet.write(row, col, gender_display_name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row, col, terminate.birthday.strftime("%d-%m-%Y") if terminate.birthday else ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, terminate.country_id.name or ' ', name_format)
        #                 col += 1
        #
        #                 religion_display_name = dict(terminate._fields['religion'].selection).get(
        #                     terminate.religion)
        #                 sheet.write(row, col, religion_display_name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row, col, terminate.job_id.name or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row,col,terminate.department_id.name or ' ',name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,terminate.work_location_id.name or ' ',name_format)
        #                 col += 1
        #                 sheet.write(row,col,terminate.joining_date.strftime("%d-%m-%Y")  if terminate.joining_date else ' ',name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,terminate.exit_date.strftime("%d-%m-%Y") if terminate.exit_date else ' ',name_format)
        #                 col += 1
        #
        #
        #                 sheet.write(row,col,terminate.contract_id.name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,terminate.contract_id.date_start.strftime("%d-%m-%Y")  if terminate.contract_id.date_start else ' ' , name_format)
        #                 col += 1
        #                 sheet.write(row,col,terminate.contract_id.date_end.strftime("%d-%m-%Y") if terminate.contract_id.date_end else ' ', name_format)
        #                 col += 1
        #
        #                 if terminate.contract_id.state:
        #                     state_display_name = dict(terminate.contract_id._fields['state'].selection).get(
        #                         terminate.contract_id.state)
        #                     sheet.write(row, col, state_display_name or ' ', name_format)
        #                 else:
        #                     sheet.write(row,col,' ',name_format)
        #
        #                 col += 1
        #
        #                 termination_lst.append(terminate.employee_no)
        #                 row += 1
        #                 no += 1
        #
        #     if len(termination_lst)==0:
        #         raise ValidationError("Termination Employee is not there in this Date  Range")
        #
        #
        #     '''Department wise employee'''
        # elif wizard.department_ids:
        #     sheet.merge_range(5, 0, 5, 15, "Department Wise Search" , header_merge_format)
        #
        #     employee_ids = False
        #     dept_ids = False
        #     employee_status = False
        #
        #     if wizard.employee_status:
        #         employee_status = wizard.employee_status
        #
        #     if wizard.employee_ids:
        #         employee_ids = wizard.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #
        #     if wizard.department_ids:
        #         dept_ids = wizard.department_ids
        #     else:
        #         dept_ids = self.env['hr.department'].search([])
        #
        #     dept_lst = []
        #     for dept in dept_ids:
        #         department_search = False
        #         if employee_status == 'active':
        #             if employee_ids:
        #                 department_search = self.env['hr.employee'].search([('contract_warning','=',False),('department_id','=',dept.id),('state','=','draft'),('id','in',employee_ids.ids)])
        #             else:
        #                 department_search = self.env['hr.employee'].search([('contract_warning','=',False),('department_id','=',dept.id),('state','=','draft')])
        #         elif employee_status == 'terminated':
        #             if employee_ids:
        #                 department_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('department_id','=',dept.id),('state','=','exit'),('id','in',employee_ids.ids)])
        #             else:    
        #                 department_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('department_id','=',dept.id),('state','=','exit')])
        #         elif employee_status == 'all':
        #             if employee_ids:
        #                 department_search = self.env['hr.employee'].search([('department_id','=',dept.id),('id','in',employee_ids.ids)])
        #             else:
        #                 department_search = self.env['hr.employee'].search([('department_id','=',dept.id)])
        #
        #         if department_search:
        #             for department in department_search:
        #
        #                 col = 0
        #                 sheet.write(row,col,no, num_format)
        #                 col += 1
        #                 sheet.write(row, col, department.employee_no or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row,col,department.display_name or ' ' ,name_format)
        #                 col += 1
        #
        #                 gender_display_name = dict(department._fields['gender'].selection).get(
        #                     department.gender)
        #                 sheet.write(row, col, gender_display_name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row, col, department.birthday.strftime("%d-%m-%Y") if department.birthday else ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, department.country_id.name or ' ', name_format)
        #                 col += 1
        #
        #                 religion_display_name = dict(department._fields['religion'].selection).get(
        #                     department.religion)
        #                 sheet.write(row, col, religion_display_name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row, col, department.job_id.name or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row,col,department.department_id.name or ' ',name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,department.work_location_id.name or ' ',name_format)
        #                 col += 1
        #                 sheet.write(row,col,department.joining_date.strftime("%d-%m-%Y") if department.joining_date else ' ',name_format)
        #                 col += 1
        #                 sheet.write(row,col,department.exit_date.strftime("%d-%m-%Y")  if department.exit_date else ' ',name_format)
        #                 col += 1
        #
        #
        #                 sheet.write(row,col,department.contract_id.name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,department.contract_id.date_start.strftime("%d-%m-%Y") if department.contract_id.date_start else ' ' , name_format)
        #                 col += 1
        #                 sheet.write(row,col,department.contract_id.date_end.strftime("%d-%m-%Y")  if department.contract_id.date_end else ' ', name_format)
        #                 col += 1
        #
        #                 if department.contract_id.state:
        #                     state_display_name = dict(department.contract_id._fields['state'].selection).get(
        #                         department.contract_id.state)
        #                     sheet.write(row, col, state_display_name or ' ', name_format)
        #                 else:
        #                     sheet.write(row,col,' ',name_format)
        #
        #                 col += 1
        #
        #                 dept_lst.append(department.employee_no)
        #                 row += 1
        #                 no += 1
        #
        #     if len(dept_lst)==0:
        #         raise ValidationError("Department is not there")
        #
        #     '''Job wise search and sort wise job'''    
        # elif wizard.job_title_ids or wizard.sort_by=='job_title':
        #     sheet.merge_range(5, 0, 5, 15, "Job Wise Employee Search" , header_merge_format)
        #
        #     employee_ids = False
        #     job_ids = False
        #     employee_status = False
        #
        #     if wizard.employee_status:
        #         employee_status = wizard.employee_status
        #
        #     if wizard.employee_ids:
        #         employee_ids = wizard.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #
        #     if wizard.job_title_ids:
        #         job_ids = wizard.job_title_ids
        #     else:
        #         job_ids = self.env['hr.job'].search([])
        #
        #     job_lst = []
        #     for jobs in job_ids:
        #         job_search = False
        #         if employee_status == 'active':
        #             if employee_ids:
        #                 job_search = self.env['hr.employee'].search([('contract_warning','=',False),('job_id','=',jobs.id),('state','=','draft'),('id','in',employee_ids.ids)])
        #             else:
        #                 job_search = self.env['hr.employee'].search([('contract_warning','=',False),('job_id','=',jobs.id),('state','=','draft')])
        #         elif employee_status == 'terminated':
        #             if employee_ids:
        #                 job_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('job_id','=',jobs.id),('state','=','exit'),('id','in',employee_ids.ids)])
        #             else:
        #                 job_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('job_id','=',jobs.id),('state','=','exit')])
        #         elif employee_status == 'all':
        #             if employee_ids: 
        #                 job_search = self.env['hr.employee'].search([('job_id','=',jobs.id),('id','in',employee_ids.ids)])
        #             else:
        #                 job_search = self.env['hr.employee'].search([('job_id','=',jobs.id)])
        #
        #         if job_search:
        #             if wizard.sort_by=='job_title':
        #                 sheet.merge_range(row, 0, row, 15, jobs.name, header_merge_format)
        #                 row += 1
        #             for job in job_search:
        #                 col = 0
        #                 sheet.write(row,col,no, num_format)
        #                 col += 1
        #                 sheet.write(row, col, job.employee_no or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row,col,job.display_name or ' ' ,name_format)
        #                 col += 1
        #
        #                 gender_display_name = dict(job._fields['gender'].selection).get(
        #                     job.gender)
        #                 sheet.write(row, col, gender_display_name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row, col, job.birthday.strftime("%d-%m-%Y") if job.birthday else ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, job.country_id.name or ' ', name_format)
        #                 col += 1
        #
        #                 religion_display_name = dict(job._fields['religion'].selection).get(
        #                     job.religion)
        #                 sheet.write(row, col, religion_display_name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row, col, job.job_id.name or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row,col,job.department_id.name or ' ',name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,job.work_location_id.name or ' ',name_format)
        #                 col += 1
        #                 sheet.write(row,col,job.joining_date.strftime("%d-%m-%Y") if job.joining_date else ' ',name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,job.exit_date.strftime("%d-%m-%Y") if job.exit_date else ' ',name_format)
        #                 col += 1
        #
        #
        #                 sheet.write(row,col,job.contract_id.name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,job.contract_id.date_start.strftime("%d-%m-%Y") if job.contract_id.date_start else ' ', name_format)
        #                 col += 1
        #                 sheet.write(row,col,job.contract_id.date_end.strftime("%d-%m-%Y") if job.contract_id.date_end else ' ', name_format)
        #                 col += 1
        #
        #                 if job.contract_id.state:
        #                     state_display_name = dict(job.contract_id._fields['state'].selection).get(
        #                         job.contract_id.state)
        #                     sheet.write(row, col, state_display_name or ' ', name_format)
        #                 else:
        #                     sheet.write(row,col,' ',name_format)
        #
        #                 col += 1
        #
        #                 job_lst.append(job.employee_no)
        #                 row += 1
        #                 no += 1
        #
        #     if len(job_lst)==0:
        #         raise ValidationError("No Specific Jobs in this company")    
        #
        #
        #     '''Nationality wise Employee Details'''
        #
        # elif wizard.nationality_ids or wizard.sort_by=='nationality':
        #
        #     sheet.merge_range(5, 0, 5, 15, "Nation Wise Employee Search" , header_merge_format)
        #
        #     employee_ids = False
        #     nationality_ids = False
        #     employee_status = False
        #
        #     if wizard.employee_status:
        #         employee_status = wizard.employee_status
        #
        #     if wizard.employee_ids:
        #         employee_ids = wizard.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #
        #     if wizard.nationality_ids:
        #         nationality_ids = wizard.nationality_ids
        #     else:
        #         nationality_ids = self.env['res.country'].search([])
        #
        #
        #     nationality_lst = []
        #     for nationality in nationality_ids:
        #         nationality_search = False
        #         if employee_status == 'active':
        #             if employee_ids:
        #                 nationality_search = self.env['hr.employee'].search([('contract_warning','=',False),('country_of_birth','=',nationality.id),('state','=','draft'),('id','in',employee_ids.ids)])
        #             else:
        #                 nationality_search = self.env['hr.employee'].search([('contract_warning','=',False),('country_of_birth','=',nationality.id),('state','=','draft')])
        #         elif employee_status == 'terminated':
        #             if employee_ids:
        #                 nationality_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('country_of_birth','=',nationality.id),('state','=','exit'),('id','in',employee_ids.ids)])
        #             else:
        #                 nationality_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('country_of_birth','=',nationality.id),('state','=','exit')])
        #         elif employee_status == 'all':
        #             if employee_ids:
        #                 nationality_search = self.env['hr.employee'].search([('country_of_birth','=',nationality.id),('id','in',employee_ids.ids)])
        #             else:
        #                 nationality_search = self.env['hr.employee'].search([('country_of_birth','=',nationality.id)])
        #
        #         if nationality_search:
        #             if wizard.sort_by=='nationality':
        #                 sheet.merge_range(row, 0, row, 15, nationality.name, header_merge_format)
        #                 row += 1
        #
        #             for nation in nationality_search:
        #                 col = 0
        #                 sheet.write(row,col,no, num_format)
        #                 col += 1
        #                 sheet.write(row, col, nation.employee_no or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row,col,nation.display_name or ' ' ,name_format)
        #                 col += 1
        #
        #                 gender_display_name = dict(nation._fields['gender'].selection).get(
        #                     nation.gender)
        #                 sheet.write(row, col, gender_display_name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row, col, nation.birthday.strftime("%d-%m-%Y") if nation.birthday else ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, nation.country_id.name or ' ', name_format)
        #                 col += 1
        #
        #                 religion_display_name = dict(nation._fields['religion'].selection).get(
        #                     nation.religion)
        #                 sheet.write(row, col, religion_display_name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row, col, nation.job_id.name or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row,col,nation.department_id.name or ' ',name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,nation.work_location_id.name or ' ',name_format)
        #                 col += 1
        #                 sheet.write(row,col,nation.joining_date.strftime("%d-%m-%Y") if nation.joining_date else ' ',name_format)
        #                 col += 1
        #                 sheet.write(row,col,nation.exit_date.strftime("%d-%m-%Y")  if nation.exit_date else ' ',name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,nation.contract_id.name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row,col,nation.contract_id.date_start.strftime("%d-%m-%Y") if nation.contract_id.date_start else ' ' , name_format)
        #                 col += 1
        #                 sheet.write(row,col,nation.contract_id.date_end.strftime("%d-%m-%Y") if nation.contract_id.date_end else ' ', name_format)
        #                 col += 1
        #
        #
        #                 if nation.contract_id.state:
        #                     state_display_name = dict(nation.contract_id._fields['state'].selection).get(
        #                         nation.contract_id.state)
        #                     sheet.write(row, col, state_display_name or ' ', name_format)
        #                 else:
        #                     sheet.write(row,col,' ',name_format)
        #
        #                 col += 1
        #
        #                 nationality_lst.append(nation.employee_no)
        #                 row += 1
        #                 no += 1
        #
        #     if len(nationality_lst)==0:
        #         raise ValidationError("No Specific nationality in this company")   
        #
        #     ''' Branch Location'''
        # elif wizard.branch_location_ids or wizard.sort_by=='branch_location':
        #
        #     sheet.merge_range(5, 0, 5, 15, "Branch Location Wise Employee Search" , header_merge_format)
        #
        #     employee_ids = False
        #     branch_ids = False
        #     employee_status = False
        #
        #     if wizard.employee_status:
        #         employee_status = wizard.employee_status
        #
        #     if wizard.employee_ids:
        #         employee_ids = wizard.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #
        #     if wizard.branch_location_ids:
        #         branch_ids = wizard.branch_location_ids
        #     else:
        #         branch_ids = self.env['hr.work.location'].search([])
        #
        #     branch_lst = []
        #     for branch_location in branch_ids:
        #             branch_search = False
        #             if employee_status == 'active':
        #                 if employee_ids:
        #                     branch_search = self.env['hr.employee'].search([('contract_warning','=',False)('work_location_id','=',branch_location.id),('state','=','draft'),('id','in',employee_ids.ids)])
        #                 else:
        #                     branch_search = self.env['hr.employee'].search([('contract_warning','=',False)('work_location_id','=',branch_location.id),('state','=','draft')])
        #             elif employee_status == 'terminated':
        #                 if employee_ids:
        #                     branch_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('work_location_id','=',branch_location.id),('state','=','exit'),('id','in',employee_ids.ids)])
        #                 else:
        #                     branch_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('work_location_id','=',branch_location.id),('state','=','exit')])
        #             elif employee_status == 'all':
        #                 if employee_ids:
        #                     branch_search = self.env['hr.employee'].search([('work_location_id','=',branch_location.id),('id','in',employee_ids.ids)])
        #                 else:
        #                     branch_search = self.env['hr.employee'].search([('work_location_id','=',branch_location.id)])
        #
        #             if branch_search:
        #                 if wizard.sort_by=="branch_location":
        #                     sheet.merge_range(row, 0, row, 15, branch_location.name, header_merge_format)
        #                     row += 1
        #
        #                 for branch in branch_search:
        #                     col = 0
        #                     sheet.write(row,col,no, num_format)
        #                     col += 1
        #                     sheet.write(row, col, branch.employee_no or ' ', name_format)
        #                     col += 1
        #                     sheet.write(row,col,branch.display_name or ' ' ,name_format)
        #                     col += 1
        #
        #                     gender_display_name = dict(branch._fields['gender'].selection).get(
        #                         branch.gender)
        #                     sheet.write(row, col, gender_display_name or ' ', name_format)
        #                     col += 1
        #
        #                     sheet.write(row, col, branch.birthday.strftime("%d-%m-%Y") if branch.birthday else ' ', name_format)
        #                     col += 1
        #                     sheet.write(row, col, branch.country_id.name or ' ', name_format)
        #                     col += 1
        #
        #                     religion_display_name = dict(branch._fields['religion'].selection).get(
        #                         branch.religion)
        #                     sheet.write(row, col, religion_display_name or ' ', name_format)
        #                     col += 1
        #
        #                     sheet.write(row, col, branch.job_id.name or ' ', name_format)
        #                     col += 1
        #                     sheet.write(row,col,branch.department_id.name or ' ',name_format)
        #                     col += 1
        #
        #                     sheet.write(row,col,branch.work_location_id.name or ' ',name_format)
        #                     col += 1
        #                     sheet.write(row,col,branch.joining_date.strftime("%d-%m-%Y") if branch.joining_date else ' ',name_format)
        #                     col += 1
        #
        #                     sheet.write(row,col,branch.exit_date.strftime("%d-%m-%Y")  if branch.exit_date else ' ',name_format)
        #                     col += 1
        #
        #
        #                     sheet.write(row,col,branch.contract_id.name or ' ', name_format)
        #                     col += 1
        #
        #                     sheet.write(row,col,branch.contract_id.date_start.strftime("%d-%m-%Y") if branch.contract_id.date_start else ' ', name_format)
        #                     col += 1
        #                     sheet.write(row,col,branch.contract_id.date_end.strftime("%d-%m-%Y")  if branch.contract_id.date_end else ' ', name_format)
        #                     col += 1
        #
        #                     if branch.contract_id.state:
        #                         state_display_name = dict(branch.contract_id._fields['state'].selection).get(
        #                             branch.contract_id.state)
        #                         sheet.write(row, col, state_display_name or ' ', name_format)
        #                     else:
        #                         sheet.write(row,col,' ',name_format)
        #
        #                     col += 1
        #
        #                     branch_lst.append(branch.employee_no)
        #                     row += 1
        #                     no += 1
        #
        #     if len(branch_lst)==0:
        #         raise ValidationError("No Specific Branch in this company")  
        #
        #
        # elif wizard.sort_by == 'department':
        #     sheet.merge_range(5, 0, 5, 15, "Department Wise Sort", header_merge_format)
        #
        #     employee_ids = False
        #     dept_ids = False
        #     employee_status = False
        #
        #     if wizard.employee_status:
        #         employee_status = wizard.employee_status
        #
        #     if wizard.employee_ids:
        #         employee_ids = wizard.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #
        #     if wizard.department_ids:
        #         dept_ids = wizard.department_ids
        #     else:
        #         dept_ids = self.env['hr.department'].search([])
        #
        #     # employee_ids = wizard.employee_ids or self.env['hr.employee'].search([])
        #     # dept_ids = wizard.department_ids or self.env['hr.department'].search([])
        #     # employee_status = wizard.employee_status
        #     #
        #     dept_lst = []
        #     for dept in dept_ids:
        #         department_employees = False
        #         # Filter employees by department
        #         if employee_status == 'active':
        #             if employee_ids:
        #                 department_employees = self.env['hr.employee'].search([
        #                     ('contract_warning', '=', False),
        #                     ('department_id', '=', dept.id),
        #                     ('state', '=', 'draft'),('id','in',employee_ids.ids)
        #                 ])
        #             else:
        #                 department_employees = self.env['hr.employee'].search([
        #                     ('contract_warning', '=', False),
        #                     ('department_id', '=', dept.id),
        #                     ('state', '=', 'draft')
        #                 ])    
        #         elif employee_status == 'terminated':
        #             if employee_ids:
        #                 department_employees = self.env['hr.employee'].search([
        #                     '|', ('active', '=', True), ('active', '=', False),
        #                     ('contract_warning', '=', True),
        #                     ('department_id', '=', dept.id),
        #                     ('state', '=', 'exit'),('id','in',employee_ids.ids)
        #                 ])
        #             else:
        #                 department_employees = self.env['hr.employee'].search([
        #                     '|', ('active', '=', True), ('active', '=', False),
        #                     ('contract_warning', '=', True),
        #                     ('department_id', '=', dept.id),
        #                     ('state', '=', 'exit')
        #                 ])
        #         elif employee_status == 'all':
        #             if employee_ids:
        #                 department_employees = self.env['hr.employee'].search([
        #                     ('department_id', '=', dept.id),('id','in',employee_ids.ids)
        #                 ])
        #             else:    
        #                 department_employees = self.env['hr.employee'].search([
        #                     ('department_id', '=', dept.id)
        #                 ])
        #
        #         # If there are employees in the department, write the department name and details
        #         if department_employees:
        #             sheet.merge_range(row, 0, row, 15, dept.name, header_merge_format)
        #             row += 1
        #
        #             for employee in department_employees:
        #                 col = 0
        #                 sheet.write(row, col, no, num_format)
        #                 col += 1
        #                 sheet.write(row, col, employee.employee_no or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, employee.display_name or ' ', name_format)
        #                 col += 1
        #
        #                 gender_display_name = dict(employee._fields['gender'].selection).get(employee.gender)
        #                 sheet.write(row, col, gender_display_name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row, col, employee.birthday.strftime("%d-%m-%Y") if employee.birthday else ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, employee.country_id.name or ' ', name_format)
        #                 col += 1
        #
        #                 religion_display_name = dict(employee._fields['religion'].selection).get(employee.religion)
        #                 sheet.write(row, col, religion_display_name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row, col, employee.job_id.name or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, employee.department_id.name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row, col, employee.work_location_id.name or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, employee.joining_date.strftime("%d-%m-%Y") if employee.joining_date else ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, employee.exit_date.strftime("%d-%m-%Y") if employee.exit_date else ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row, col, employee.contract_id.name or ' ', name_format)
        #                 col += 1
        #
        #                 sheet.write(row, col, employee.contract_id.date_start.strftime("%d-%m-%Y")  if employee.contract_id.date_start else ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, employee.contract_id.date_end.strftime("%d-%m-%Y")  if employee.contract_id.date_end else ' ', name_format)
        #                 col += 1
        #
        #                 if employee.contract_id.state:
        #                     state_display_name = dict(employee.contract_id._fields['state'].selection).get(employee.contract_id.state)
        #                     sheet.write(row, col, state_display_name or ' ', name_format)
        #                 else:
        #                     sheet.write(row, col, ' ', name_format)
        #                 col += 1
        #
        #                 dept_lst.append('employee.employee_no')
        #                 row += 1
        #                 no += 1
        #
        #     if len(dept_lst) == 0:
        #         raise ValidationError("No employees found for the selected criteria")
        #
        #

            # '''Departwise sort'''
        # elif wizard.sort_by == 'department':
        # # elif wizard.department_ids:
        #     sheet.merge_range(5, 0, 5, 15, "Department Wise Sort" , header_merge_format)
        #
        #     employee_ids = False
        #     dept_ids = False
        #     employee_status = False
        #
        #     if wizard.employee_status:
        #         employee_status = wizard.employee_status
        #
        #     if wizard.employee_ids:
        #         employee_ids = wizard.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #
        #     if wizard.department_ids:
        #         dept_ids = wizard.department_ids
        #     else:
        #         dept_ids = self.env['hr.department'].search([])
        #
        #     dept_lst = []
        #     dept_name = ''
        #     for dept in dept_ids:
        #         if dept.name != dept_name:
        #             sheet.merge_range(row, 0, row, 15, dept.name , header_merge_format)
        #             row +=1              
        #
        #         dept.name = dept_name
        #         for employee in employee_ids:
        #             department_search = False
        #             if employee_status == 'active':
        #                 department_search = self.env['hr.employee'].search([('contract_warning','=',False),('id','=',employee.id),('department_id','=',dept.id),('state','=','draft')])
        #             elif employee_status == 'terminated':
        #                 department_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('id','=',employee.id),('department_id','=',dept.id),('state','=','exit')])
        #             elif employee_status == 'all':
        #                 department_search = self.env['hr.employee'].search([('id','=',employee.id),('department_id','=',dept.id)])
        #
        #             if department_search:
        #                 for department in department_search:
        #                     if dept_name == department.department_id.name:
        #                         # dept_name = department.department_id.name
        #                         col = 0
        #                         sheet.write(row,col,no, num_format)
        #                         col += 1
        #                         sheet.write(row, col, department.employee_no or ' ', name_format)
        #                         col += 1
        #                         sheet.write(row,col,department.display_name or ' ' ,name_format)
        #                         col += 1
        #
        #                         gender_display_name = dict(department._fields['gender'].selection).get(
        #                             department.gender)
        #                         sheet.write(row, col, gender_display_name or ' ', name_format)
        #                         col += 1
        #
        #
        #                         if department.birthday:
        #                             sheet.write(row, col, department.birthday.strftime("%d-%m-%Y") or ' ', name_format)
        #                         else:
        #                             sheet.write(row, col, '', name_format)
        #                         col += 1
        #                         sheet.write(row, col, department.country_id.name or ' ', name_format)
        #                         col += 1
        #
        #                         religion_display_name = dict(department._fields['religion'].selection).get(
        #                             department.religion)
        #                         sheet.write(row, col, religion_display_name or ' ', name_format)
        #                         col += 1
        #
        #                         sheet.write(row, col, department.job_id.name or ' ', name_format)
        #                         col += 1
        #                         sheet.write(row,col,department.department_id.name or ' ',name_format)
        #                         col += 1
        #
        #                         sheet.write(row,col,department.work_location_id.name or ' ',name_format)
        #                         col += 1
        #                         if department.joining_date:
        #                             sheet.write(row,col,department.joining_date.strftime("%d-%m-%Y"),name_format)
        #                         else:
        #                             sheet.write(row,col,'',name_format)
        #
        #                         col += 1
        #                         if department.exit_date:
        #                             sheet.write(row,col,department.exit_date.strftime("%d-%m-%Y"),name_format)
        #                         else:
        #                             sheet.write(row,col,'',name_format)
        #                         col += 1
        #
        #
        #                         sheet.write(row,col,department.contract_id.name or ' ', name_format)
        #                         col += 1
        #
        #                         if department.contract_id.date_start:
        #                             sheet.write(row,col,department.contract_id.date_start.strftime("%d-%m-%Y") , name_format)
        #                         else:
        #                             sheet.write(row,col,'',name_format)
        #
        #                         col += 1
        #                         if department.contract_id.date_end:
        #                             sheet.write(row,col,department.contract_id.date_end.strftime("%d-%m-%Y"), name_format)
        #                         else:
        #                             sheet.write(row,col,'',name_format)
        #                         col += 1
        #
        #                         if department.contract_id.state:
        #                             state_display_name = dict(department.contract_id._fields['state'].selection).get(
        #                                 department.contract_id.state)
        #                             sheet.write(row, col, state_display_name or ' ', name_format)
        #                         else:
        #                             sheet.write(row,col,' ',name_format)
        #
        #                         col += 1
        #
        #                         dept_lst.append(department.employee_no)
        #                         row += 1
        #                         no += 1
        #         # if dept.name == dept_name: 
        #         #     sheet.merge_range(row, 0, row, 15, dept.name , header_merge_format)
        #         #     row +=1              
        #         #
        #
        #     if len(dept_lst)==0:
        #         raise ValidationError("Department is not there")
        
        
            
            # ''' Only Employee Status'''    
        # else:
        #     employee_ids = False
        #     employee_status = False
        #
        #     if wizard.employee_status:
        #         employee_status = wizard.employee_status
        #     if wizard.employee_ids:
        #         employee_ids = wizard.employee_ids
        #     else:
        #        employee_ids = self.env['hr.employee'].search([])
        #
        #     contract_lst = []
        #     for employee in employee_ids:
        #         contract_search = False
        #         if employee_status == 'active':
        #             contract_search = self.env['hr.employee'].search([('contract_warning','=',False),('id','=',employee.id),('state','=','draft')])
        #         elif employee_status == 'terminated':
        #             contract_search = self.env['hr.employee'].search(['|',('active','=',True),('active','=',False),('contract_warning','=',True),('id','=',employee.id),('state','=','exit')])
        #         elif employee_status == 'all':
        #             contract_search = self.env['hr.employee'].search([('id','=',employee.id)])
        #         for contract in contract_search:
        #             col = 0
        #             sheet.write(row,col,no, num_format)
        #             col += 1
        #             sheet.write(row, col, contract.employee_no or ' ', name_format)
        #             col += 1
        #             sheet.write(row,col,contract.display_name or ' ' ,name_format)
        #             col += 1
        #
        #             gender_display_name = dict(contract._fields['gender'].selection).get(
        #                 contract.gender)
        #             sheet.write(row, col, gender_display_name or ' ', name_format)
        #             col += 1
        #
        #             sheet.write(row, col, contract.birthday.strftime("%d-%m-%Y") if contract.birthday else ' ', name_format)
        #             col += 1
        #             sheet.write(row, col, contract.country_id.name or ' ', name_format)
        #             col += 1
        #
        #             religion_display_name = dict(contract._fields['religion'].selection).get(
        #                 contract.religion)
        #             sheet.write(row, col, religion_display_name or ' ', name_format)
        #             col += 1
        #
        #             sheet.write(row, col, contract.job_id.name or ' ', name_format)
        #             col += 1
        #             sheet.write(row,col,contract.department_id.name or ' ',name_format)
        #             col += 1
        #
        #             sheet.write(row,col,contract.work_location_id.name or ' ',name_format)
        #             col += 1
        #             sheet.write(row,col,contract.joining_date.strftime("%d-%m-%Y")  if contract.joining_date else ' ',name_format)
        #             col += 1
        #
        #             sheet.write(row,col,contract.exit_date.strftime("%d-%m-%Y")  if contract.exit_date else ' ',name_format)
        #             col += 1
        #
        #             sheet.write(row,col,contract.contract_id.name or ' ', name_format)
        #             col += 1
        #
        #             sheet.write(row,col,contract.contract_id.date_start.strftime("%d-%m-%Y") if contract.contract_id.date_start else ' ' , name_format)
        #             col += 1
        #             sheet.write(row,col,contract.contract_id.date_end.strftime("%d-%m-%Y") if contract.contract_id.date_end else ' ', name_format)
        #             col += 1
        #
        #             if contract.contract_id.state:
        #                 state_display_name = dict(contract.contract_id._fields['state'].selection).get(
        #                     contract.contract_id.state)
        #                 sheet.write(row, col, state_display_name or ' ', name_format)
        #             else:
        #                 sheet.write(row,col,' ',name_format)
        #
        #             col += 1
        #             contract_lst.append(contract.employee_no)
        #
        #             row += 1
        #             no += 1
        #     if len(contract_lst) == 0:
        #         raise ValidationError("No Employee is there")
            
        
        
        
        
        
        
        
