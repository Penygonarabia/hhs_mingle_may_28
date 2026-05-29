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
from odoo.tools import float_round
from odoo.exceptions import ValidationError



class TerminationDetailsReportExcel(models.AbstractModel):
    _name = 'report.termination_details_report.termination_details_report'
    _inherit = 'report.report_xlsx.abstract'    
    _description = 'Termination Details Report Xlsx'
    
    
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
        num_format = workbook.add_format({'align': 'right', 'valign': 'vcenter', \
                                           'font_size': 10, 'border': 1})
        header_left_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', \
                                                  'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})
        
        
        
        header_data_format4 = workbook.add_format({'bold':True,'align':'center', 'valign':'vcenter', \
                                                   'font_size':10,'bg_color':'#B7950B', 'border':1})

        sheet = workbook.add_worksheet("Termination_Details_Report")
        sheet.set_row(0, 25)


        sheet.merge_range(0, 0, 2, 11, "Termination Details Report" , header_merge_format)
        # sheet.write(8, 1, 'Employee Salary report', header_merge_format)

        sheet.merge_range(4, 0, 4, 1, 'Company', header_merge_format)
        sheet.merge_range(4, 2, 4, 3, wizard.company_id.name, header_merge_format)

        sheet.merge_range(4, 4, 4, 5, 'Today Date', header_merge_format)
        sheet.merge_range(4, 6, 4, 7, datetime.today().strftime("%d-%m-%Y"), header_merge_format)

        # sheet.merge_range(5, 0, 5, 10, 'Basic Details', header_data_format4)
        # sheet.merge_range(5, 11, 5, 20, 'Allowances', header_data_format2)
        # sheet.merge_range(5, 21, 5, 23, 'Deduction', header_data_format3)


        row = 5
        col = 0
        sheet.write(row, col, 'S.No', header_merge_format)
        sheet.set_column(0, 0, 10)
        col += 1
        sheet.write(row, col, 'Reason For Termination', header_merge_format)
        sheet.set_column(1, 1, 12)
        col += 1
        sheet.write(row, col, 'Employee No', header_merge_format)
        sheet.set_column(2, 2, 25)
        col += 1
        sheet.write(row, col, 'Employee Name', header_merge_format)
        sheet.set_column(3, 3, 25)
        col += 1
        sheet.write(row, col, 'Gender', header_merge_format)
        sheet.set_column(4, 4, 18)
        col += 1
        sheet.write(row, col, 'Job title', header_merge_format)
        sheet.set_column(5, 5, 18)
        col += 1
        sheet.write(row, col, 'Location', header_merge_format)
        sheet.set_column(6, 6, 18)
        col += 1
        sheet.write(row, col, 'Date', header_merge_format)
        sheet.set_column(7, 7, 18)
        col += 1
        sheet.write(row, col, 'Joining Date', header_merge_format)
        sheet.set_column(8, 8, 18)
        col += 1
        sheet.write(row, col, 'Termination Date', header_merge_format)
        sheet.set_column(9, 9, 18)
        col += 1
        sheet.write(row, col, 'No.Of Days', header_merge_format)
        sheet.set_column(10, 10, 18)
        col += 1
        sheet.write(row, col, 'Eos Reward', header_merge_format)
        sheet.set_column(11, 11, 12)
        col += 1
        # sheet.write(row, col, 'State', header_merge_format)
        # sheet.set_column(12, 12, 18)
        # col += 1
        
        row = 6
        no = 1

        excel_list = []
        from_date = False
        to_date = False
        employee_ids = False
        if wizard.employee_ids:
            employee_ids = wizard.employee_ids

        else:
            employee_ids = self.env['hr.employee'].search(['|',('active', '=', True),  ('active','=',False)])

        for employees in employee_ids:
            eos_search = self.env['hr.end.service.benefit'].search([('employee_id', '=', employees.id),('date','>=',wizard.from_date),('date','<=',wizard.to_date), ('state', '=', 'validated')])
            termination_search = self.env['hr.exit'].search([('employee_id', '=', eos_search.employee_id.id)])
            for eos in eos_search:

                if eos.employee_id == employees:
                    col = 0
                    sheet.write(row, col, no, num_format)
                    col += 1
                    sheet.write(row, col, eos.end_service_benefit_type_id.name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, eos.employee_id.employee_no or ' ', name_format),
                    col += 1
                    sheet.write(row, col, eos.employee_id.name or ' ', name_format)
                    col += 1
                    gender_display_name = dict(employees._fields['gender'].selection).get(
                        employees.gender)
                    sheet.write(row, col, gender_display_name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, eos.employee_id.job_title or ' ', name_format)
                    col += 1

                    sheet.write(row, col, eos.employee_id.work_location_id.name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, eos.date.strftime("%d-%m-%Y") or ' ', num_format)
                    col += 1
                    if eos.employee_id.joining_date:
                        sheet.write(row, col, eos.employee_id.joining_date.strftime("%d-%m-%Y"), num_format)
                    else:
                        sheet.write(row, col, ' ', num_format)
                    col += 1
                    for term in termination_search:
                        if term.last_work_date:
                            sheet.write(row, col, term.last_work_date.strftime("%d-%m-%Y"), num_format)
                        else:
                            sheet.write(row, col,  ' ', num_format)

                    col += 1
                    total_worked_days = float_round(eos.total_days, 2)
                    sheet.write(row, col, total_worked_days or ' ', num_format)
                    col += 1
                    display_amount = float_round(eos.available_amount, 2)
                    sheet.write(row, col, display_amount or ' ', num_format)
                    col += 1

                    # state_display_name = dict(eos._fields['state'].selection).get(
                    #     eos.state)
                    # sheet.write(row, col, state_display_name or ' ', name_format)
                    # col += 1
                    row += 1
                    no += 1
                    excel_list.append(eos)

        if len(excel_list)==0:
            raise ValidationError("No data found for selected date range")


        
        
        
        
        
        
        
