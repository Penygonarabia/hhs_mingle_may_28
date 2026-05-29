from odoo import fields, models, api, _
import xlsxwriter
import io
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime,date,time
import time
import pytz
import pandas as pd
from odoo.exceptions import warnings
from odoo.exceptions import ValidationError


class EmployeeAdvanceReportExcel(models.AbstractModel):
    _name = 'report.employee_advance_report.report_employee_advance_xlsx'
    _inherit = 'report.report_xlsx.abstract'    
    _description = 'Employee Advance Report Xlsx'

    
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

        sheet = workbook.add_worksheet("Advance_Transaction_Report")
        sheet.set_row(0, 25)
        
        
        sheet.merge_range(0, 0, 2, 9, "Advance Transaction Report" , header_merge_format)
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
        col += 1
        sheet.set_column(0, 0, 10)

        sheet.write(row, col, 'Employee No', header_merge_format)
        sheet.set_column(1, 1, 12)
        col += 1
        sheet.write(row, col, 'Employee Name', header_merge_format)
        col += 1
        sheet.set_column(2, 2, 25)
        sheet.write(row, col, 'Advance type', header_merge_format)
        sheet.set_column(3, 3, 18)
        col += 1
        sheet.write(row, col, 'Reference', header_merge_format)
        sheet.set_column(4, 4, 18)
        col += 1
        sheet.write(row, col, 'Advance start Date', header_merge_format)
        sheet.set_column(5, 5, 22)
        col += 1
        sheet.write(row, col, 'Advance Amount', header_merge_format)
        sheet.set_column(6, 6, 18)
        col += 1
        sheet.write(row, col, 'Installment Rate', header_merge_format)
        sheet.set_column(8, 8, 18)
        col += 1
        sheet.write(row, col, 'Advance Repayment Date', header_merge_format)
        sheet.set_column(7, 7, 22)
        col += 1
        sheet.write(row, col, 'Balance Amount', header_merge_format)
        sheet.set_column(9, 9, 18)
        col += 1
        # sheet.write(row, col, 'Status', header_merge_format)
        # sheet.set_column(10, 10, 12)
        # col += 1
        
        # sheet.write(row, col, 'Date of Left', header_merge_format)
        # sheet.set_column(11, 11, 18)
        # col += 1
        # sheet.write(row, col, 'Status', header_merge_format)
        # sheet.set_column(12, 12, 18)
        # col += 1
        
        row = 6
        no = 1
        
        
        employee_ids = False
        if wizard.employee_ids:
            employee_ids = wizard.employee_ids
        else:
            employee_ids = self.env['hr.employee'].search([])

        for employee in employee_ids:
            contract_search = self.env['hr.employee.advance.ps'].search([('employee_id','=',employee.id)])
            
            for contract in contract_search:
                col = 0
                sheet.write(row, col, no, num_format)
                col += 1
                sheet.write(row, col, contract.employee_id.employee_no or ' ', name_format)
                col += 1
                sheet.write(row, col, contract.employee_id.display_name or ' ', name_format)
                col += 1

                # gender_display_name = dict(contract._fields['gender'].selection).get(
                #     contract.gender)
                sheet.write(row, col, contract.type_id.display_name or ' ', name_format)
                col += 1

                sheet.write(row, col, contract.display_name or ' ', name_format)
                col += 1
                if contract.advance_ins_start_date:
                    sheet.write(row, col, contract.advance_ins_start_date.strftime("%d-%m-%Y") or ' ', name_format)
                else:
                    sheet.write(row, col, '', name_format)
                col += 1
                sheet.write(row, col, '{:.2f}'.format(contract.advance_amount) or ' ', num_format)
                col += 1
                ins_rate = 0.00
                ins_date = ''
                ins_remaining_amount = 0.00
                for ins in contract.hr_employee_advance_line_ps:
                    ins_rate = ins.amount
                    if ins.state in ['deducted']:
                        ins_date = ins.installment_date.strftime("%d-%m-%Y")
                        ins_remaining_amount = ins.remaining_value
                sheet.write(row, col, '{:.2f}'.format(ins_rate) or ' ', num_format)
                col += 1
                sheet.write(row, col, ins_date or ' ', name_format)
                col += 1
                sheet.write(row, col, '{:.2f}'.format(ins_remaining_amount) or ' ', num_format)
                col += 1

                row += 1
                no += 1
        
        
        
        
        
        
        
        
        
