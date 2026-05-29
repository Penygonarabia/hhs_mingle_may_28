from odoo import fields, models, api, _
from odoo.tools.misc import xlsxwriter
import io
from datetime import datetime
import pytz
import pandas as pd
from odoo.exceptions import warnings, ValidationError


class EmployeeDocumentsRenewalReportExcel(models.AbstractModel):
    _name = 'report.employee_document_renewal_report.report_renewal_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Employee Document Renewal Report Xlsx'

    def generate_xlsx_report(self, workbook, data, wizard):

        # Formats
        header_merge_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter',
                                                   'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})

        header_merge_format3 = workbook.add_format({'bold':True, 'align':'left', 'valign':'vcenter', \
                                            'font_size':10, 'bg_color':'#D3D3D3', 'border':1})

        header_data_format = workbook.add_format({'align': 'right', 'valign': 'vcenter',
                                                  'font_size': 10, 'border': 1})
        header_data_format2 = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter',
                                                   'font_size': 10, 'bg_color': '#F2D7D5', 'border': 1})
        header_data_format3 = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter',
                                                   'font_size': 10, 'bg_color': '#87CEFA', 'border': 1})
        name_format = workbook.add_format({'align': 'left', 'valign': 'vcenter',
                                           'font_size': 10, 'border': 1})
        num_format = workbook.add_format({'align': 'right', 'valign': 'vcenter',
                                          'font_size': 10, 'border': 1})
        header_left_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter',
                                                  'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})

        header_data_format4 = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter',
                                                   'font_size': 10, 'bg_color': '#B7950B', 'border': 1})

        # Sheet
        sheet = workbook.add_worksheet("Employee Documents Renewals Report")
        sheet.set_row(0, 25)
        sheet.merge_range(0, 0, 2, 11, "Employee Documents Renewals Report", header_merge_format)
 
     
        sheet.merge_range(4, 0, 4, 1, 'Company', header_merge_format)
        sheet.merge_range(4, 2, 4, 3, wizard.company_id.name, header_merge_format)

        sheet.merge_range(4, 4, 4, 5, 'Today Date', header_merge_format)
        sheet.merge_range(4, 6, 4, 7, datetime.today().strftime("%d-%m-%Y"), header_merge_format)

        # Header
        row = 6
        col = 0
       
        headers = ['S.No', 'Employee No', 'Employee Name', 'Department Name', 'Job Position', 'Nationality',
                   'Location', 'Document Name','Document Number','Place of Issue','Issue Date','Expiry Date']
        col_widths = [10, 12, 25, 20, 15, 18, 15, 15, 15,18, 18, 18]

        for header, width in zip(headers, col_widths):
            sheet.write(row, col, header, header_merge_format)
            sheet.set_column(col, col, width)
            col += 1
                

        # Data rows
        row = 7
        no = 1
        domain = []
        
        domain = [('employee_ref', 'in', wizard.employee_ids.ids if wizard.employee_ids else self.env['hr.employee'].search([]).ids)]

        if wizard.from_expiry_date and wizard.to_expiry_date:
            domain += [('expiry_date', '<=', wizard.to_expiry_date), ('expiry_date', '>=', wizard.from_expiry_date)]

        if wizard.employee_status:
            if wizard.employee_status == 'all':
                domain += [('employee_ref.state', 'in', ['exit','draft'])]
                # domain += ['|', ('employee_ref.contract_warning', '=', False),
                #            ('employee_ref.contract_warning', '=', True)]
            elif wizard.employee_status == 'active':
                domain += [('employee_ref.state', '=', 'draft'), ('employee_ref.contract_warning', '=', False)]
            elif wizard.employee_status == 'terminated':
                domain += [('employee_ref.state', '=', 'exit'), ('employee_ref.contract_warning', '=', True)]

        
        if wizard.document_type_ids:
            domain += [('document_name','in',wizard.document_type_ids.ids)]
      
        if wizard.department_ids:
            domain += [('employee_ref.department_id', 'in', wizard.department_ids.ids)]
            sheet.merge_range(5, 0, 5, 11, "Department Wise Search" , header_merge_format)


        if wizard.job_title_ids:
            domain += [('employee_ref.job_id', 'in', wizard.job_title_ids.ids)]
            sheet.merge_range(5, 0, 5, 11, "Job Wise Search" , header_merge_format)


        if wizard.nationality_ids:
            domain += [('employee_ref.country_of_birth', 'in', wizard.nationality_ids.ids)]
            sheet.merge_range(5, 0, 5, 11, "Nation Wise Search" , header_merge_format)


        if wizard.branch_location_ids:
            domain += [('employee_ref.work_location_id', 'in', wizard.branch_location_ids.ids)]
            sheet.merge_range(5, 0, 5, 11, "Branch Location Wise Search" , header_merge_format)


        renewal_search = self.env['hr.employee.document'].search(domain)
        renewal_search = renewal_search.sorted(key=lambda c:c.employee_ref.name.lower())


      
        if wizard.sort_by:
            if wizard.sort_by == 'department':
                renewal_search = renewal_search.filtered(lambda c: c.employee_ref.department_id)
                renewal_search = renewal_search.sorted(key=lambda c: c.employee_ref.department_id.name.lower())
                sheet.merge_range(5, 0, 5, 11, "Department Wise Sort" , header_merge_format)

            elif wizard.sort_by == 'job_title':
                renewal_search = renewal_search.filtered(lambda c: c.employee_ref.job_id)
                renewal_search = renewal_search.sorted(key=lambda c: c.employee_ref.job_id.name.lower())
                sheet.merge_range(5, 0, 5, 11, "Job Wise Sort" , header_merge_format)

            elif wizard.sort_by == 'nationality':
                renewal_search = renewal_search.filtered(lambda c: c.employee_ref.country_of_birth)
                renewal_search = renewal_search.sorted(key=lambda c: c.employee_ref.country_of_birth.name.lower())
                sheet.merge_range(5, 0, 5, 11, "Nation Wise Sort" , header_merge_format)

            elif wizard.sort_by == 'branch_location':
                renewal_search = renewal_search.filtered(lambda c: c.employee_ref.work_location_id)
                renewal_search = renewal_search.sorted(key=lambda c: c.employee_ref.work_location_id.name.lower())
                sheet.merge_range(5, 0, 5, 11, "Branch Location Wise Sort" , header_merge_format)

            elif wizard.sort_by == 'employee_no':
                renewal_search = renewal_search.sorted(key = lambda c:(
                    0 if c.employee_ref.employee_no and isinstance(c.employee_ref.employee_no,str) and c.employee_ref.employee_no.isdigit() else 1,
                    int(c.employee_ref.employee_no) if c.employee_ref.employee_no and isinstance(c.employee_ref.employee_no,str) and c.employee_ref.employee_no.isdigit() else c.employee_ref.employee_no or ' '
                    ))
                sheet.merge_range(5, 0, 5, 11, "Employee Number Wise Sort" , header_merge_format)

                
        
        if wizard.department_ids:
            renewal_search = renewal_search.sorted(key=lambda c: c.employee_ref.department_id.name.lower())

        if wizard.job_title_ids:
            renewal_search = renewal_search.sorted(key=lambda c: c.employee_ref.job_id.name.lower())

        if wizard.nationality_ids:
            renewal_search = renewal_search.sorted(key=lambda c: c.employee_ref.country_of_birth.name.lower())

        
        if wizard.branch_location_ids:
            renewal_search = renewal_search.sorted(key=lambda c: c.employee_ref.work_location_id.name.lower())

        
        seen_departments = set()
        seen_job_titles = set()
        seen_nationalities = set()
        seen_location = set()
        num = 1
        renewal_lst = []
        for renewal in renewal_search:
            if wizard.sort_by == 'department' and renewal.employee_ref.department_id.name not in seen_departments:
                sheet.merge_range(row, 0, row, 11, renewal.employee_ref.department_id.name, header_merge_format3)
                seen_departments.add(renewal.employee_ref.department_id.name)
                row += 1
                num = 1
            elif wizard.sort_by == 'job_title' and renewal.employee_ref.job_id.name not in seen_job_titles:
                sheet.merge_range(row, 0, row, 11, renewal.employee_ref.job_id.name, header_merge_format3)
                seen_job_titles.add(renewal.employee_ref.job_id.name)
                row += 1
                num = 1
            elif wizard.sort_by == 'nationality' and renewal.employee_ref.country_of_birth.name not in seen_nationalities:
                sheet.merge_range(row, 0, row, 10, renewal.employee_ref.country_of_birth.name, header_merge_format3)
                seen_nationalities.add(renewal.employee_ref.country_of_birth.name)
                row += 1
                num = 1
            elif wizard.sort_by =='branch_location' and renewal.employee_ref.work_location_id.name not in seen_location:
                sheet.merge_range(row, 0, row, 11, renewal.employee_ref.work_location_id.name, header_merge_format3)
                seen_location.add(renewal.employee_ref.work_location_id.name)
                row += 1 
                num = 1  
            
            if wizard.sort_by == 'department' or wizard.sort_by == 'job_title' or wizard.sort_by == 'nationality' or wizard.sort_by == 'branch_location':
                col = 0
                sheet.write(row, col, num, num_format)
                col += 1
            else:
                col = 0
                sheet.write(row, col, no, num_format)
                col += 1
           
            sheet.write(row, col, renewal.employee_ref.employee_no or ' ', name_format)
            col += 1
            sheet.write(row, col, renewal.employee_ref.display_name or ' ', name_format)
            col += 1
            sheet.write(row, col, renewal.employee_ref.department_id.display_name or ' ', name_format)
            col += 1
            sheet.write(row, col, renewal.employee_ref.job_id.display_name or ' ', name_format)
            col += 1
            sheet.write(row, col, renewal.employee_ref.country_of_birth.display_name or ' ', name_format)
            col += 1
            sheet.write(row, col, renewal.employee_ref.work_location_id.display_name or ' ', name_format)
            col += 1
            sheet.write(row, col, renewal.document_name.display_name or ' ', name_format)
            col += 1
            sheet.write(row, col, renewal.display_name or ' ', name_format)
            col += 1
            sheet.write(row, col, renewal.place_city_id.display_name or ' ', name_format)
            col += 1
            sheet.write(row, col, renewal.issue_date.strftime("%d-%m-%Y") if renewal.issue_date else ' ', name_format)
            col += 1
            sheet.write(row, col, renewal.expiry_date.strftime("%d-%m-%Y") if renewal.expiry_date else ' ', name_format)
            col += 1
       
            renewal_lst.append(renewal.employee_ref.display_name)
            row += 1
            no += 1
            num += 1
        if len(renewal_lst)==0:
            raise ValidationError("No Renewal documents for the Employees is not there in this range")
        

    
    
    
        
        
        
        
        
        
        
        
        
        
        