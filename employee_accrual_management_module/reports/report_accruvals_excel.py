from odoo import fields, models, api, _
import xlsxwriter
import io
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime, date

class AccrualsExcelReport(models.AbstractModel):
    _name = 'report.employee_accrual.report_employee_accruals_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Employee Accruals Excel Report'

    def generate_xlsx_report(self, workbook, data, lines):
        header_merge_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', \
                                                   'font_size': 14, 'bg_color': '#D3D3D3', 'border': 1})

        header_data_format = workbook.add_format({'align': 'right', 'valign': 'vcenter', \
                                                  'font_size': 10, 'border': 1})

        header_merge_format3 = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', \
                                                    'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})

        header_data_format2 = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', \
                                                   'font_size': 10, 'bg_color': '#F2D7D5', 'border': 1})
        header_data_format3 = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', \
                                                   'font_size': 10, 'bg_color': '#87CEFA', 'border': 1})
        name_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', \
                                           'font_size': 10, 'border': 1})
        num_format = workbook.add_format({'align': 'right', 'valign': 'vcenter', \
                                          'font_size': 10, 'border': 1, 'num_format': '#,##0.00'})
        header_left_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', \
                                                  'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})

        header_data_format4 = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', \
                                                   'font_size': 10, 'bg_color': '#B7950B', 'border': 1})
        sheet = workbook.add_worksheet("Employee Accruals")
        sheet.set_row(0, 25)
        sheet.set_column('A:A', 22)
        sheet.set_column('B:B', 22)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:E', 16)
        sheet.set_column('F:F', 15)
        sheet.set_column('G:G', 25)
        sheet.set_column('H:H', 10)
        sheet.set_column('I:I', 16)
        sheet.set_column('J:J', 15)
        sheet.set_column('K:K', 13)
        sheet.set_column('L:L', 15)
        if lines:
            date_from = lines.date_from
            date_to = lines.date_to
            name = lines.name
            accrual_type = lines.accrual_type
            if accrual_type == 'annual_leave':
                sheet.merge_range('A1:I1', 'Employee Accruals for Annual Leave (' + str(date_from) + ' -  ' + str(date_to) + ' )',
                                  header_merge_format)
                sheet.write(1, 0, 'Reference', header_merge_format3)
                sheet.write(1, 1, name, header_merge_format3)
                sheet.write(1, 2, 'Accrual Type', header_merge_format3)
                sheet.write(1, 3, dict(lines._fields['accrual_type'].selection).get(lines.accrual_type, ""), header_merge_format3)
                col = 0
                sheet.write(3, col, 'Employee', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Contract', header_merge_format3)
                col += 1
                # sheet.write(3, col, 'Accrual Type', header_style)
                # col += 1
                sheet.write(3, col, 'Entitlement', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Entitlement Amount', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Accrual Days', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Accrual Amount', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Analytical Code', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Status', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Account Moves', header_merge_format3)
                col += 1
                row = 3
                for line in lines.accrual_line_ids:
                    row += 1
                    col = 0
                    sheet.write(row, col, line.employee_id.name or "", name_format)
                    col += 1
                    sheet.write(row, col, line.contract_id.name or "", name_format)
                    col += 1
                    # sheet.write(row, col, line.accrual_type or "", text_style)
                    # col += 1
                    sheet.write(row, col, line.entitlement_days or "", num_format)
                    col += 1
                    sheet.write(row, col, line.entitlement_amount or "", num_format)
                    col += 1
                    sheet.write(row, col, line.accrual_days or "", num_format)
                    col += 1
                    sheet.write(row, col, line.accrual_amount or "", num_format)
                    col += 1
                    sheet.write(row, col, line.analytical_code.name or "", name_format)
                    col += 1
                    sheet.write(row, col, line.status or "", name_format)
                    col += 1
                    sheet.write(row, col, line.account_move_id.display_name or "", name_format)
                    col += 1

            if accrual_type == 'annual_tickets':
                sheet.merge_range('A1:I1', 'Employee Accruals for Annual Tickets (' + str(date_from) + ' -  ' + str(
                    date_to) + ' )',
                                  header_merge_format)
                sheet.write(1, 0, 'Reference', header_merge_format3)
                sheet.write(1, 1, name, header_merge_format3)
                sheet.write(1, 3, 'Accrual Type', header_merge_format3)
                sheet.write(1, 4,  dict(lines._fields['accrual_type'].selection).get(lines.accrual_type, ""), header_merge_format3)
                col = 0
                sheet.write(3, col, 'Employee', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Contract', header_merge_format3)
                col += 1
                # sheet.write(3, col, 'Accrual Type', header_style)
                # col += 1
                sheet.write(3, col, 'Ticket Entitlement', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Ticket Entitlement Amount', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Ticket Accrual', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Ticket Accrual amount', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Analytical Code', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Status', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Account Moves', header_merge_format3)
                col += 1
                row = 3
                for line in lines.accrual_line_ids:
                    row += 1
                    col = 0
                    sheet.write(row, col, line.employee_id.name or "", name_format)
                    col += 1
                    sheet.write(row, col, line.contract_id.name or "", name_format)
                    col += 1
                    # sheet.write(row, col, line.accrual_type or "", text_style)
                    # col += 1
                    sheet.write(row, col, line.ticket_entitlement or "", num_format)
                    col += 1
                    sheet.write(row, col, line.ticket_entitlement_amount or "", num_format)
                    col += 1
                    sheet.write(row, col, line.ticket_accrual or "", num_format)
                    col += 1
                    sheet.write(row, col, line.ticket_accrual_amount or "", num_format)
                    col += 1
                    sheet.write(row, col, line.analytical_code.name or "", name_format)
                    col += 1
                    sheet.write(row, col, line.status or "", name_format)
                    col += 1
                    sheet.write(row, col, line.account_move_id.display_name or "", name_format)
                    col += 1

            if accrual_type == 'gratuity':
                sheet.merge_range('A1:P1', 'Employee Accruals for EOS Accruals (' + str(date_from) + ' -  ' + str(
                    date_to) + ' )',
                                  header_merge_format)
                sheet.write(1, 0, 'Reference', header_merge_format3)
                sheet.write(1, 1, name, header_merge_format3)
                sheet.write(1, 3, 'Accrual Type', header_merge_format3)
                sheet.write(1, 4,  dict(lines._fields['accrual_type'].selection).get(lines.accrual_type, ""), header_merge_format3)
                col = 0
                sheet.write(3, col, 'Employee', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Type', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Contract', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Contract Start Date', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Accrual Month Date', header_merge_format3)
                col += 1
                sheet.write(3, col, 'No of Days', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Eligible Days', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Eligible days for first 5 years', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Eligible days for after 5 Years', header_merge_format3)
                col += 1
                sheet.write(3, col, 'EOSB for 1825 days(for 1st 5 year)', header_merge_format3)
                col += 1
                sheet.write(3, col, 'EOSB for 1825 days(After 5 year)', header_merge_format3)
                col += 1
                sheet.write(3, col, 'EOSB Days', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Custom Net Salary ', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Custon Per Day Salary', header_merge_format3)
                col += 1
                sheet.write(3, col, 'EOSB Amount', header_merge_format3)
                col += 1
                sheet.write(3, col, 'Journal', header_merge_format3)
                col += 1
                row = 3
                for line in lines.gratuity_line_ids:
                    row += 1
                    col = 0
                    sheet.write(row, col, line.custom_employee_id.name or "", name_format)
                    col += 1
                    sheet.write(row, col, dict(line._fields['custom_type'].selection).get(line.custom_type, ""), name_format)
                    col += 1
                    sheet.write(row, col, line.custom_contract_id.name or "", name_format)
                    col += 1
                    sheet.write(row, col,
                                line.custom_date_of_join.strftime('%d-%m-%Y') if line.custom_date_of_join else "",
                                name_format)
                    col += 1
                    sheet.write(row, col, line.custom_late_working_day.strftime(
                        '%d-%m-%Y') if line.custom_late_working_day else "", name_format)
                    col += 1
                    sheet.write(row, col, line.no_of_days or "", num_format)
                    col += 1
                    sheet.write(row, col, line.custom_eligible_days or "", num_format)
                    col += 1
                    sheet.write(row, col, line.eligible_days_f_five_years or "", num_format)
                    col += 1
                    sheet.write(row, col, line.eligible_days_a_five_years or "", num_format)
                    col += 1
                    sheet.write(row, col, line.esob_days or "", num_format)
                    col += 1
                    sheet.write(row, col, line.esob_a_days or "", num_format)
                    col += 1
                    sheet.write(row, col, line.custom_esob_days_sum or "", num_format)
                    col += 1
                    sheet.write(row, col, line.custom_net_salary or "", num_format)
                    col += 1
                    sheet.write(row, col, line.custom_per_day_salary or "", num_format)
                    col += 1
                    sheet.write(row, col, line.custom_esob_amounts or "", num_format)
                    col += 1
                    sheet.write(row, col, line.custom_move_id.display_name or "", name_format)
                    col += 1


