from odoo import fields, models, api, _
from odoo.tools.misc import xlsxwriter
import io
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, time
import time
import pytz
import pandas as pd
from odoo.exceptions import ValidationError
import warnings


class EmployeeCustodyReportExcel(models.AbstractModel):
    _name = 'report.hr_custody.report_employee_custody_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Hr Custody Detail Report Xlsx'

    def generate_xlsx_report(self, workbook, data, wizard):

        header_merge_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', \
                                                   'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})

        header_merge_format3 = workbook.add_format({'bold':True, 'align':'left', 'valign':'vcenter', \
                                            'font_size':10, 'bg_color':'#D3D3D3', 'border':1})

        header_data_format = workbook.add_format({'align': 'right', 'valign': 'vcenter', \
                                                  'font_size': 10, 'border': 1})
        header_data_format2 = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', \
                                                   'font_size': 10, 'bg_color': '#F2D7D5', 'border': 1})
        header_data_format3 = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', \
                                                   'font_size': 10, 'bg_color': '#87CEFA', 'border': 1})
        name_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', \
                                           'font_size': 10, 'border': 1})
        num_format = workbook.add_format({'align': 'right', 'valign': 'vcenter', \
                                          'font_size': 10, 'border': 1})
        header_left_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', \
                                                  'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})

        header_data_format4 = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', \
                                                   'font_size': 10, 'bg_color': '#B7950B', 'border': 1})

        sheet = workbook.add_worksheet("Employees Custody Report")
        sheet.set_row(0, 25)

        sheet.merge_range(0, 0, 2, 18, "Employees Custody Report", header_merge_format)

        sheet.merge_range(4, 0, 4, 1, 'Company', header_merge_format)
        sheet.merge_range(4, 2, 4, 3, wizard.company_id.name, header_merge_format)

        sheet.merge_range(4, 4, 4, 5, 'Today Date', header_merge_format)
        sheet.merge_range(4, 6, 4, 7, datetime.today().strftime("%d-%m-%Y"), header_merge_format)

        row = 6
        col = 0
        
        header = ['S.No','Employee No','Employee Name','Department','Job Position','Nationality',
                  'Location','Date of Joining','Exit Date','Contract Name','Contract Start Date',
                  'Contract End Date','Custody Reference','Requested Date','Asset Type','Asset','Return Date',
                  'Reason','Status'
                  ]
        
        col_width = [10,12,20,18,15,15,15,15,15,12,12,12,12,12,12,12,12,12,12]
        
        for head,width in zip(header,col_width):
            sheet.write(row, col, head, header_merge_format)
            sheet.set_column(col,col,width)
            col += 1

        

        row = 7
        no = 1
        
        domain = []
        
        domain += [('employee','in',wizard.employee_ids.ids if wizard.employee_ids else self.env['hr.employee'].search([]).ids)]

        
        
        if wizard.department_ids:
            domain += [('employee.department_id','in',wizard.department_ids.ids)]
            sheet.merge_range(5, 0, 5, 18, "Department Wise Search" , header_merge_format)

            
        if wizard.job_title_ids:
            domain += [('employee.job_id','in',wizard.job_title_ids.ids)] 
            sheet.merge_range(5, 0, 5, 18, "Job Wise Search" , header_merge_format)

        
        if wizard.nationality_ids:
            domain += [('employee.country_of_birth','in',wizard.nationality_ids.ids)]
            sheet.merge_range(5, 0, 5, 18, "Nation Wise Search" , header_merge_format)

            
        if wizard.branch_location_ids:
            domain += [('employee.work_location_id','in',wizard.branch_location_ids.ids)] 
            sheet.merge_range(5, 0, 5, 18, "Branch Location Wise Search" , header_merge_format)
          
        
        
        if wizard.from_request_date and wizard.to_request_date:
            domain += [('date_request','>=',wizard.from_request_date),('date_request','<=',wizard.to_request_date)]
            sheet.merge_range(5, 0, 5, 1, 'From Request Date', header_merge_format)
            sheet.merge_range(5, 2, 5, 3, wizard.from_request_date.strftime("%d-%m-%Y"), header_merge_format)
            sheet.merge_range(5, 4, 5, 5, 'To Request Date', header_merge_format)
            sheet.merge_range(5, 6, 5, 7, wizard.to_request_date.strftime("%d-%m-%Y"), header_merge_format)
            
        if wizard.from_return_date and wizard.to_return_date:
            domain += [('return_date','>=',wizard.from_return_date),('return_date','<=',wizard.to_return_date)]
            sheet.merge_range(5, 0, 5, 1, 'From Return Date', header_merge_format)
            sheet.merge_range(5, 2, 5, 3, wizard.from_return_date.strftime("%d-%m-%Y"), header_merge_format)
            sheet.merge_range(5, 4, 5, 5, 'To Return Date', header_merge_format)
            sheet.merge_range(5, 6, 5, 7, wizard.to_return_date.strftime("%d-%m-%Y"), header_merge_format)
        
        if wizard.asset_type_ids:
            domain += [('asset_types','in',wizard.asset_type_ids.ids)] 
            
        if wizard.approval_status:
            if wizard.approval_status=='draft':
                domain += [('state','in',['draft'])]
            elif wizard.approval_status == 'waiting_for_approval':
                domain += [('state','in','to_approve')]
            elif wizard.approval_status == 'approved':
                domain += [('state','in',['approved'])]
                
            elif wizard.approval_status == 'rejected':
                domain += [('state','in',['rejected'])]
            
            elif wizard.approval_status == 'returned':
                domain += [('state','=','returned')]
            
            elif wizard.approval_status == 'all':
                domain += [('state','in',['draft','to_approve','approved','rejected','returned'])]        
        
        
        if wizard.employee_status:
            if wizard.employee_status == 'all':
                domain += [('employee.state', 'in', ['draft','exit'])]
                # domain += ['|', ('employee.contract_warning', '=', False),
                #            ('employee.contract_warning', '=', True)]
            elif wizard.employee_status == 'active':
                domain += [('employee.state', '=', 'draft'), ('employee.contract_warning', '=', False)]
            elif wizard.employee_status == 'terminated':
                domain += [('employee.state', '=', 'exit'), ('employee.contract_warning', '=', True)]                   
        
        custody_search = self.env['hr.custody'].search(domain)
        custody_search = custody_search.sorted(lambda s:s.employee.name.lower())

        
        if wizard.sort_by:
            if wizard.sort_by =='department':
                custody_search = custody_search.filtered(lambda c:c.employee.department_id)
                custody_search = custody_search.sorted(key=lambda c:c.employee.department_id.name.lower())
                sheet.merge_range(5, 0, 5, 18, "Department Wise Sort" , header_merge_format)

                
            elif wizard.sort_by =='job_title':
                custody_search = custody_search.filtered(lambda c:c.employee.job_id)
                custody_search = custody_search.sorted(key=lambda c:c.employee.job_id.name.lower())
                sheet.merge_range(5, 0, 5, 18, "Job Wise Sort" , header_merge_format)

                
            elif wizard.sort_by == 'nationality':
                custody_search = custody_search.filtered(lambda c:c.employee.country_of_birth)
                custody_search =custody_search.sorted(key=lambda c:c.employee.country_of_birth.name.lower())
                sheet.merge_range(5, 0, 5, 18, "Nation Wise Sort" , header_merge_format)

            
            elif wizard.sort_by == 'branch_location':
                custody_search = custody_search.filtered(lambda c:c.employee.work_location_id)
                custody_search = custody_search.sorted(key = lambda c:c.employee.work_location_id.name.lower())
                sheet.merge_range(5, 0, 5, 18, "Branch Location Wise Sort" , header_merge_format)

                    
        department_sort = set()
        job_title_sort = set()
        nationality_sort = set()
        location_sort = set()
        custody_lst = []
        num = 1 
        if wizard.department_ids:
            custody_search = custody_search.sorted(key=lambda c:c.employee.department_id.name.lower())

        if wizard.job_title_ids:
            custody_search = custody_search.sorted(key=lambda c:c.employee.job_id.name.lower())

        if wizard.nationality_ids:
            custody_search =custody_search.sorted(key=lambda c:c.employee.country_of_birth.name.lower())

        if wizard.branch_location_ids:
            custody_search = custody_search.sorted(key=lambda c:c.employee.work_location_id.name.lower())    
       
        
        for custody in custody_search:
            if wizard.sort_by == 'department' and  custody.employee.department_id.display_name not in department_sort:
                sheet.merge_range(row,0,row, 18, custody.employee.department_id.display_name, header_merge_format3)
                department_sort.add(custody.employee.department_id.display_name)
                row += 1
                num =1
            
            elif wizard.sort_by =='job_title' and custody.employee.job_id.name not in job_title_sort:
                sheet.merge_range(row, 0, row, 18, custody.employee.job_id.name, header_merge_format3)
                job_title_sort.add(custody.employee.job_id.name) 
                row += 1
                num = 1
            
            elif wizard.sort_by == 'nationality' and  custody.employee.country_of_birth.name not in nationality_sort:
                sheet.merge_range(row, 0, row, 18, custody.employee.country_of_birth.name, header_merge_format3) 
                nationality_sort.add(custody.employee.country_of_birth.name)
                row += 1
                num = 1
            elif wizard.sort_by == 'branch_location' and custody.employee.work_location_id.name not in location_sort:
                sheet.merge_range(row, 0, row, 18,custody.employee.work_location_id.name, header_merge_format3 )
                location_sort.add(custody.employee.work_location_id.name)
                row += 1
                num = 1
            
            col = 0         
            if wizard.sort_by in ['department','job_title','nationality','branch_location']:
                sheet.write(row, col, num, num_format)
            else:
                sheet.write(row, col, no,num_format)    
            
            col += 1
            sheet.write(row, col, custody.employee.employee_no or ' ', name_format)
            col += 1
            sheet.write(row, col, custody.employee.display_name or ' ', name_format)
            col += 1
            sheet.write(row, col, custody.employee.department_id.display_name or ' ', name_format)
            col += 1
            sheet.write(row, col, custody.employee.job_id.name or ' ', name_format)
            col += 1
            sheet.write(row, col, custody.employee.country_of_birth.name or ' ', name_format)
            col += 1
            sheet.write(row, col, custody.employee.work_location_id.name or ' ', name_format)
            col += 1
            
            sheet.write(row, col, custody.employee.joining_date.strftime("%d-%m-%Y") if  custody.employee.joining_date else ' ', name_format)
            col += 1
            sheet.write(row, col, custody.employee.exit_date.strftime("%d-%m-%Y") if  custody.employee.exit_date else ' ', name_format)
            col += 1
            sheet.write(row, col, custody.employee.contract_id.name or ' ', name_format)
            col += 1
            sheet.write(row, col, custody.employee.contract_id.date_start.strftime("%d-%m-%Y") if custody.employee.contract_id.date_start else ' ', name_format)
            col += 1
            sheet.write(row, col, custody.employee.contract_id.date_end.strftime("%d-%m-%Y") if custody.employee.contract_id.date_end else ' ', name_format)
            col += 1
            sheet.write(row, col, custody.name or ' ', name_format)
            col += 1
            sheet.write(row, col, custody.date_request.strftime("%d-%m-%Y") if custody.date_request else  ' ', name_format)
            col += 1
            sheet.write(row, col, custody.asset_types.display_name or ' ', name_format)
            col += 1
            sheet.write(row, col, custody.custody_name.display_name  or ' ', name_format)
            col += 1
            sheet.write(row, col, custody.return_date.strftime("%d-%m-%Y") if custody.return_date else ' ', name_format)
            col += 1
            sheet.write(row, col, custody.purpose or ' ', name_format)
            col += 1
            if custody.state:
                state_display_name = dict(custody._fields['state'].selection).get(
                    custody.state)
                sheet.write(row, col, state_display_name or ' ', name_format)
            else:
                sheet.write(row, col, ' ', name_format)
                
            custody_lst.append(custody.employee.display_name)    

            row += 1
            no += 1
            num += 1

        if len(custody_lst) == 0:
            raise ValidationError("Custody of the employees are not in these range")                
        

        # employee_ids = False
        # if wizard.employee_ids:
        #     employee_ids = wizard.employee_ids
        # else:
        #     employee_ids = self.env['hr.employee'].search([])
        #
        # for employee in employee_ids:
        #     hr_custody = self.env['hr.custody'].search([('employee', '=', employee.id)])
        #
        #     for custody in hr_custody:
        #         col = 0
        #         sheet.write(row, col, no, num_format)
        #         col += 1
        #         sheet.write(row, col, custody.employee.display_name or ' ', name_format)
        #         col += 1
        #         sheet.write(row, col, custody.name or ' ', name_format)
        #         col += 1
        #         if custody.date_request:
        #             sheet.write(row, col, custody.date_request.strftime("%d-%m-%Y") or ' ', name_format)
        #         else:
        #             sheet.write(row, col, '', name_format)
        #         col += 1
        #         sheet.write(row, col, custody.asset_types.display_name or ' ', name_format)
        #         col += 1
        #         sheet.write(row, col, custody.custody_name.display_name  or ' ', name_format)
        #         col += 1
        #         if custody.return_date:
        #             sheet.write(row, col, custody.return_date.strftime("%d-%m-%Y"), name_format)
        #         else:
        #             sheet.write(row, col, '', name_format)
        #         col += 1
        #         sheet.write(row, col, custody.purpose or ' ', name_format)
        #         col += 1
        #         if custody.state:
        #             state_display_name = dict(custody._fields['state'].selection).get(
        #                 custody.state)
        #             sheet.write(row, col, state_display_name or ' ', name_format)
        #         else:
        #             sheet.write(row, col, ' ', name_format)
        #         col += 1
        #
        #         row += 1
        #         no += 1









