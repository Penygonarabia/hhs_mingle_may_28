from odoo import fields, models, api, _
from odoo.tools.misc import xlsxwriter
import io
from datetime import datetime
import pytz
import pandas as pd
from odoo.exceptions import warnings, ValidationError


class EmployeeLoanReportExcel(models.AbstractModel):
    _name = 'report.employee_loan_report.report_employee_loan_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Employee Loan Report Xlsx'

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
        sheet = workbook.add_worksheet("Employee Loan and Advances Report")
        sheet.set_row(0, 25)
        if wizard.type=='loan':
            sheet.merge_range(0, 0, 2, 19, "Employee Loan and Advances Report", header_merge_format)
            sheet.merge_range(5,0,5,19,'Loan Based Report',header_merge_format)
        else:
            sheet.merge_range(0, 0, 2, 18, "Employee Loan and Advances Report", header_merge_format)
            sheet.merge_range(5,0,5,18,'Advance Based Report',header_merge_format)

            
        sheet.merge_range(4, 0, 4, 1, 'Company', header_merge_format)
        sheet.merge_range(4, 2, 4, 3, wizard.company_id.name, header_merge_format)

        sheet.merge_range(4, 4, 4, 5, 'Today Date', header_merge_format)
        sheet.merge_range(4, 6, 4, 7, datetime.today().strftime("%d-%m-%Y"), header_merge_format)

        # Header
        row = 6
        col = 0
        if wizard.type=='loan':
            headers = ['S.No', 'Employee No', 'Employee Name', 'Department Name', 'Job Position', 'Nationality',
                       'Location', 'Loan Type', 'Loan Reference', 'Loan Guarantor', 'Loan Start Date',
                       'Loan Amount', 'Loan Installment Rate', 'Last Repayment Date', 'Number of Installments',
                       'Paid Installments', 'Unpaid Installments', 'Paid Amount', 'Balance Amount', 'Status']
            col_widths = [10, 12, 25, 20, 15, 18, 15, 15, 15, 18, 18, 18, 18, 18, 18, 18, 18, 15, 18, 12]
    
            for header, width in zip(headers, col_widths):
                sheet.write(row, col, header, header_merge_format)
                sheet.set_column(col, col, width)
                col += 1
        else:
            headers = ['S.No', 'Employee No', 'Employee Name', 'Department Name', 'Job Position', 'Nationality',
                       'Location', 'Advance Type', 'Advance Reference', 'Advance Start Date',
                       'Advance Amount', 'Advance Installment Rate', 'Last Advance Repayment Date', 'Number of Installments',
                       'Paid Installments', 'Unpaid Installments', 'Paid Amount', 'Balance Amount', 'Status']
            col_widths = [10, 12, 25, 20, 15, 18, 15, 15, 15, 18, 18, 18, 18, 18, 18, 18, 15, 18, 12]
    
            for header, width in zip(headers, col_widths):
                sheet.write(row, col, header, header_merge_format)
                sheet.set_column(col, col, width)
                col += 1
                    

        # Data rows
        row = 7
        no = 1
        if wizard.type == 'loan':
            domain = [('employee_id', 'in', wizard.employee_ids.ids if wizard.employee_ids else self.env['hr.employee'].search([]).ids)]

            if wizard.from_date and wizard.to_date:
                domain += [('request_date', '<=', wizard.to_date), ('request_date', '>=', wizard.from_date)]

            if wizard.employee_status:
                if wizard.employee_status == 'all':
                    domain += [('employee_id.state', 'in', ['exit','draft'])]
                    # domain += ['|', ('employee_id.contract_warning', '=', False),
                    #            ('employee_id.contract_warning', '=', True)]
                elif wizard.employee_status == 'active':
                    domain += [('employee_id.state', '=', 'draft'), ('employee_id.contract_warning', '=', False)]
                elif wizard.employee_status == 'terminated':
                    domain += [('employee_id.state', '=', 'exit'), ('employee_id.contract_warning', '=', True)]


            if wizard.approval_status:
                if wizard.approval_status == 'approved':
                    domain += [('state', '=', 'approve')]
                elif wizard.approval_status == 'draft':
                    domain += [('state', '=', 'draft')]
                elif wizard.approval_status == 'rejected':
                    domain += [('state', '=', 'refused')]
                elif wizard.approval_status == 'waiting_for_approval':
                    domain += [('state', 'in', ['request', 'progress', 'progress2', 'progress3'])]
                elif wizard.approval_status == 'all':
                    domain += [('state', 'in', ['draft', 'request', 'progress', 'progress2', 'progress3', 'approve', 'refused'])]

            if wizard.department_ids:
                domain += [('employee_id.department_id', 'in', wizard.department_ids.ids)]

            if wizard.job_title_ids:
                domain += [('employee_id.job_id', 'in', wizard.job_title_ids.ids)]

            if wizard.nationality_ids:
                domain += [('employee_id.country_of_birth', 'in', wizard.nationality_ids.ids)]

            if wizard.branch_location_ids:
                domain += [('employee_id.work_location_id', 'in', wizard.branch_location_ids.ids)]

            loan_search = self.env['hr.employee.loan.ps'].search(domain)
            loan_search = loan_search.sorted(lambda c:c.employee_id.name.lower())

            if wizard.payment_status:
                if wizard.payment_status == 'fully_paid':
                    loan_search = loan_search.filtered(lambda c: c.balance_amount == 0.0 and c.state == 'approve')
                elif wizard.payment_status == 'outstanding':
                    loan_search = loan_search.filtered(lambda c: c.balance_amount > 0.0 and c.state == 'approve')
                elif wizard.payment_status == 'all':
                    loan_search = loan_search.filtered(lambda c: c.balance_amount >= 0.0 and c.state == 'approve')

            if wizard.sort_by:
                if wizard.sort_by == 'department':
                    loan_search = loan_search.filtered(lambda c: c.employee_id.department_id)
                    loan_search = loan_search.sorted(key=lambda c: c.employee_id.department_id.name.lower())
                elif wizard.sort_by == 'job_title':
                    loan_search = loan_search.filtered(lambda c: c.employee_id.job_id)
                    loan_search = loan_search.sorted(key=lambda c: c.employee_id.job_id.name.lower())
                elif wizard.sort_by == 'nationality':
                    loan_search = loan_search.filtered(lambda c: c.employee_id.country_of_birth)
                    loan_search = loan_search.sorted(key=lambda c: c.employee_id.country_of_birth.name.lower())
                elif wizard.sort_by == 'branch_location':
                    loan_search = loan_search.filtered(lambda c: c.employee_id.work_location_id)
                    loan_search = loan_search.sorted(key=lambda c: c.employee_id.work_location_id.name.lower())
                elif wizard.sort_by == 'employee_no':
                    loan_search = loan_search.sorted(key = lambda c:(
                        0 if c.employee_id.employee_no and isinstance(c.employee_id.employee_no,str) and c.employee_id.employee_no.isdigit() else 1,
                        int(c.employee_id.employee_no) if c.employee_id.employee_no and isinstance(c.employee_id.employee_no, str) and c.employee_id.employee_no.isdigit() else c.employee_id.employee_no or ''
                        ))
            
            if wizard.department_ids:
                loan_search = loan_search.sorted(key=lambda c: c.employee_id.department_id.name.lower())
                
            if wizard.job_title_ids:
                loan_search = loan_search.sorted(key=lambda c: c.employee_id.job_id.name.lower())
            
            if wizard.nationality_ids:
                loan_search = loan_search.sorted(key=lambda c: c.employee_id.country_of_birth.name.lower())
            
            if wizard.branch_location_ids:
                loan_search = loan_search.sorted(key=lambda c: c.employee_id.work_location_id.name.lower())
            
            seen_departments = set()
            seen_job_titles = set()
            seen_nationalities = set()
            seen_location = set()
            num = 1
            loan_lst = []
            for loan in loan_search:
                if wizard.sort_by == 'department' and loan.employee_id.department_id.name not in seen_departments:
                    sheet.merge_range(row, 0, row, 19, loan.employee_id.department_id.name, header_merge_format3)
                    seen_departments.add(loan.employee_id.department_id.name)
                    row += 1
                    num = 1
                elif wizard.sort_by == 'job_title' and loan.employee_id.job_id.name not in seen_job_titles:
                    sheet.merge_range(row, 0, row, 19, loan.employee_id.job_id.name, header_merge_format3)
                    seen_job_titles.add(loan.employee_id.job_id.name)
                    row += 1
                    num = 1
                elif wizard.sort_by == 'nationality' and loan.employee_id.country_of_birth.name not in seen_nationalities:
                    sheet.merge_range(row, 0, row, 19, loan.employee_id.country_of_birth.name, header_merge_format3)
                    seen_nationalities.add(loan.employee_id.country_of_birth.name)
                    row += 1
                    num = 1
                elif wizard.sort_by =='branch_location' and loan.employee_id.work_location_id.name not in seen_location:
                    sheet.merge_range(row, 0, row, 19, loan.employee_id.work_location_id.name, header_merge_format3)
                    seen_location.add(loan.employee_id.work_location_id.name)
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
                # col = 0
                # sheet.write(row, col, no, num_format)
                # col += 1
                sheet.write(row, col, loan.employee_id.employee_no or ' ', name_format)
                col += 1
                sheet.write(row, col, loan.employee_id.display_name or ' ', name_format)
                col += 1
                sheet.write(row, col, loan.employee_id.department_id.display_name or ' ', name_format)
                col += 1
                sheet.write(row, col, loan.employee_id.job_id.display_name or ' ', name_format)
                col += 1
                sheet.write(row, col, loan.employee_id.country_of_birth.display_name or ' ', name_format)
                col += 1
                sheet.write(row, col, loan.employee_id.work_location_id.display_name or ' ', name_format)
                col += 1
                sheet.write(row, col, loan.type_id.display_name or ' ', name_format)
                col += 1
                sheet.write(row, col, loan.display_name or ' ', name_format)
                col += 1
                sheet.write(row, col, loan.guarantor_id.name or ' ', name_format)
                col += 1
                sheet.write(row, col, loan.loan_ins_start_date.strftime("%d-%m-%Y") if loan.loan_ins_start_date else ' ', name_format)
                col += 1
                sheet.write(row, col, '{:.2f}'.format(loan.loan_amount) or ' ', num_format)
                col += 1

                ins_rate = 0.00
                ins_date = ''
                for ins in loan.hr_employee_loan_line_ps:
                    if ins.state == 'deducted':
                        ins_rate = ins.amount
                        ins_date = ins.installment_date.strftime("%d-%m-%Y")

                sheet.write(row, col, '{:.2f}'.format(ins_rate) or ' ', num_format)
                col += 1
                sheet.write(row, col, ins_date or ' ', name_format)
                col += 1
                sheet.write(row, col, '{:.2f}'.format(loan.loan_month_ins) or ' ', num_format)
                col += 1
                sheet.write(row, col, '{:.2f}'.format(loan.paid_installment) or ' ', num_format)
                col += 1
                sheet.write(row, col, '{:.2f}'.format(loan.unpaid_installment) or ' ', num_format)
                col += 1
                sheet.write(row, col, '{:.2f}'.format(loan.paid_amount) or ' ', num_format)
                col += 1
                sheet.write(row, col, '{:.2f}'.format(loan.balance_amount) or ' ', num_format)
                col += 1

                state_display_name = dict(loan._fields['state'].selection).get(loan.state, ' ')
                sheet.write(row, col, state_display_name or ' ', name_format)
                loan_lst.append(loan.employee_id.display_name)
                row += 1
                no += 1
                num += 1
            if len(loan_lst)==0:
                raise ValidationError("Employees are not in this range")
            
        else:
            if wizard.type == 'advance':
                domain = [('employee_id', 'in', wizard.employee_ids.ids if wizard.employee_ids else self.env['hr.employee'].search([]).ids)]
    
                if wizard.from_date and wizard.to_date:
                    domain += [('request_date', '<=', wizard.to_date), ('request_date', '>=', wizard.from_date)]
    
                if wizard.employee_status:
                    if wizard.employee_status == 'all':
                        domain += [('employee_id.state', 'in', ['exit','draft'])]
                        # domain += ['|', ('employee_id.contract_warning', '=', False),
                        #            ('employee_id.contract_warning', '=', True)]
                    elif wizard.employee_status == 'active':
                        domain += [('employee_id.state', '=', 'draft'), ('employee_id.contract_warning', '=', False)]
                    elif wizard.employee_status == 'terminated':
                        domain += [('employee_id.state', '=', 'exit'), ('employee_id.contract_warning', '=', True)]
    
    
                if wizard.approval_status:
                    if wizard.approval_status == 'approved':
                        domain += [('state', '=', 'approve')]
                    elif wizard.approval_status == 'draft':
                        domain += [('state', '=', 'draft')]
                    elif wizard.approval_status == 'rejected':
                        domain += [('state', '=', 'refused')]
                    elif wizard.approval_status == 'waiting_for_approval':
                        domain += [('state', 'in', ['request', 'progress', 'progress2', 'progress3'])]
                    elif wizard.approval_status == 'all':
                        domain += [('state', 'in', ['draft', 'request', 'progress', 'progress2', 'progress3', 'approve', 'refused'])]
    
                if wizard.department_ids:
                    domain += [('employee_id.department_id', 'in', wizard.department_ids.ids)]
    
                if wizard.job_title_ids:
                    domain += [('employee_id.job_id', 'in', wizard.job_title_ids.ids)]
    
                if wizard.nationality_ids:
                    domain += [('employee_id.country_of_birth', 'in', wizard.nationality_ids.ids)]
    
                if wizard.branch_location_ids:
                    domain += [('employee_id.work_location_id', 'in', wizard.branch_location_ids.ids)]
    
                advance_search = self.env['hr.employee.advance.ps'].search(domain)
                advance_search = advance_search.sorted(lambda c:c.employee_id.name.lower())

                
                if wizard.payment_status:
                    if wizard.payment_status == 'fully_paid':
                        advance_search = advance_search.filtered(lambda c: c.balance_amount == 0.0 and c.state == 'approve')
                    elif wizard.payment_status == 'outstanding':
                        advance_search = advance_search.filtered(lambda c: c.balance_amount > 0.0 and c.state == 'approve')
                    elif wizard.payment_status == 'all':
                        advance_search = advance_search.filtered(lambda c: c.balance_amount >= 0.0 and c.state == 'approve')
    
                if wizard.sort_by:
                    if wizard.sort_by == 'department':
                        advance_search = advance_search.filtered(lambda c: c.employee_id.department_id)
                        advance_search = advance_search.sorted(key=lambda c: c.employee_id.department_id.name.lower())
                    elif wizard.sort_by == 'job_title':
                        advance_search = advance_search.filtered(lambda c: c.employee_id.job_id)
                        advance_search = advance_search.sorted(key=lambda c: c.employee_id.job_id.name.lower())
                    elif wizard.sort_by == 'nationality':
                        advance_search = advance_search.filtered(lambda c: c.employee_id.country_of_birth)
                        advance_search = advance_search.sorted(key=lambda c: c.employee_id.country_of_birth.name.lower())
                    elif wizard.sort_by == 'branch_location':
                        advance_search = advance_search.filtered(lambda c: c.employee_id.work_location_id)
                        advance_search = advance_search.sorted(key=lambda c: c.employee_id.work_location_id.name.lower())
                    
                    elif wizard.sort_by == 'employee_no':
                        advance_search = advance_search.sorted(key = lambda c:(
                            0 if c.employee_id.employee_no and isinstance(c.employee_id.employee_no,str) and c.employee_id.employee_no.isdigit() else 1,
                            int(c.employee_id.employee_no) if c.employee_id.employee_no and isinstance(c.employee_id.employee_no, str) and c.employee_id.employee_no.isdigit() else c.employee_id.employee_no or ''
                            ))
                    
                if wizard.department_ids:
                    advance_search = advance_search.sorted(key=lambda c: c.employee_id.department_id.name.lower())
                    
                if wizard.job_title_ids:
                    advance_search = advance_search.sorted(key=lambda c: c.employee_id.job_id.name.lower())
                
                if wizard.nationality_ids:
                    advance_search = advance_search.sorted(key=lambda c: c.employee_id.country_of_birth.name.lower())
                
                if wizard.branch_location_ids:
                    advance_search = advance_search.sorted(key=lambda c: c.employee_id.work_location_id.name.lower())
                seen_departments = set()
                seen_job_titles = set()
                seen_nationalities = set()
                seen_location = set()
                num = 1
                advance_lst = []
                for advance in advance_search:
                    if wizard.sort_by == 'department' and advance.employee_id.department_id.name not in seen_departments:
                        sheet.merge_range(row, 0, row, 19, advance.employee_id.department_id.name, header_merge_format3)
                        seen_departments.add(advance.employee_id.department_id.name)
                        row += 1
                        num = 1
                    elif wizard.sort_by == 'job_title' and advance.employee_id.job_id.name not in seen_job_titles:
                        sheet.merge_range(row, 0, row, 19, advance.employee_id.job_id.name, header_merge_format3)
                        seen_job_titles.add(advance.employee_id.job_id.name)
                        row += 1
                        num = 1
                    elif wizard.sort_by == 'nationality' and advance.employee_id.country_of_birth.name not in seen_nationalities:
                        sheet.merge_range(row, 0, row, 19, advance.employee_id.country_of_birth.name, header_merge_format3)
                        seen_nationalities.add(advance.employee_id.country_of_birth.name)
                        row += 1
                        num = 1
                    elif wizard.sort_by =='branch_location' and advance.employee_id.work_location_id.name not in seen_location:
                        sheet.merge_range(row, 0, row, 19, advance.employee_id.work_location_id.name, header_merge_format3)
                        seen_location.add(advance.employee_id.work_location_id.name)
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
                    # col = 0
                    # sheet.write(row, col, no, num_format)
                    # col += 1
                    sheet.write(row, col, advance.employee_id.employee_no or ' ', name_format)
                    col += 1
                    sheet.write(row, col, advance.employee_id.display_name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, advance.employee_id.department_id.display_name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, advance.employee_id.job_id.display_name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, advance.employee_id.country_of_birth.display_name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, advance.employee_id.work_location_id.display_name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, advance.type_id.display_name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, advance.display_name or ' ', name_format)
                    col += 1
                    # sheet.write(row, col, contract.guarantor_id.name or ' ', name_format)
                    # col += 1
                    sheet.write(row, col, advance.advance_ins_start_date.strftime("%d-%m-%Y") if advance.advance_ins_start_date else ' ', name_format)
                    col += 1
                    sheet.write(row, col, '{:.2f}'.format(advance.advance_amount_required) or ' ', num_format)
                    col += 1
    
                    ins_rate = 0.00
                    ins_date = ''
                    for ins in advance.hr_employee_advance_line_ps:
                        if ins.state == 'deducted':
                            ins_rate = ins.amount
                            ins_date = ins.installment_date.strftime("%d-%m-%Y")
    
                    sheet.write(row, col, '{:.2f}'.format(ins_rate) or ' ', num_format)
                    col += 1
                    sheet.write(row, col, ins_date or ' ', name_format)
                    col += 1
                    sheet.write(row, col, '{:.2f}'.format(advance.advance_month_ins) or ' ', num_format)
                    col += 1
                    sheet.write(row, col, '{:.2f}'.format(advance.paid_installment) or ' ', num_format)
                    col += 1
                    sheet.write(row, col, '{:.2f}'.format(advance.unpaid_installment) or ' ', num_format)
                    col += 1
                    sheet.write(row, col, '{:.2f}'.format(advance.paid_amount) or ' ', num_format)
                    col += 1
                    sheet.write(row, col, '{:.2f}'.format(advance.balance_amount) or ' ', num_format)
                    col += 1
    
                    state_display_name = dict(advance._fields['state'].selection).get(advance.state, ' ')
                    sheet.write(row, col, state_display_name or ' ', name_format)
                    advance_lst.append(advance.employee_id.display_name)
                    row += 1
                    no += 1
                    num += 1
                if len(advance_lst)==0:
                    raise ValidationError("Employees are not in this range")
                






# from odoo import fields, models, api, _
# import xlsxwriter
# import io
# from datetime import timedelta
# from dateutil.relativedelta import relativedelta
# from datetime import datetime,date,time
# import time
# import pytz
# import pandas as pd
# from odoo.exceptions import Warning
# from odoo.exceptions import ValidationError
#
#
# class EmployeeLoanReportExcel(models.AbstractModel):
#     _name = 'report.employee_loan_report.report_employee_loan_xlsx'
#     _inherit = 'report.report_xlsx.abstract'    
#     _description = 'Employee Loan Report Xlsx'
#
#
#     def generate_xlsx_report(self, workbook, data, wizard):
#
#         header_merge_format = workbook.add_format({'bold':True, 'align':'center', 'valign':'vcenter', \
#                                             'font_size':10, 'bg_color':'#D3D3D3', 'border':1})
#
#         header_data_format = workbook.add_format({'align':'right', 'valign':'vcenter', \
#                                                    'font_size':10, 'border':1})
#         header_data_format2 = workbook.add_format({'bold':True,'align':'center', 'valign':'vcenter', \
#                                                    'font_size':10,'bg_color':'#F2D7D5', 'border':1})
#         header_data_format3 = workbook.add_format({'bold':True,'align':'center', 'valign':'vcenter', \
#                                                    'font_size':10,'bg_color':'#87CEFA', 'border':1})
#         name_format = workbook.add_format({'align':'left', 'valign':'vcenter', \
#                                                    'font_size':10, 'border':1})
#         num_format = workbook.add_format({'align': 'right', 'valign': 'vcenter', \
#                                            'font_size': 10, 'border': 1})
#         header_left_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', \
#                                                   'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})
#
#
#
#         header_data_format4 = workbook.add_format({'bold':True,'align':'center', 'valign':'vcenter', \
#                                                    'font_size':10,'bg_color':'#B7950B', 'border':1})
#
#         sheet = workbook.add_worksheet("Employee Loan and Advances Report")
#         sheet.set_row(0, 25)
#
#
#         sheet.merge_range(0, 0, 2, 19, "Employee Loan and Advances Report" , header_merge_format)
#
#         sheet.merge_range(4, 0, 4, 1, 'Company', header_merge_format)
#         sheet.merge_range(4, 2, 4, 3, wizard.company_id.name, header_merge_format)
#
#         sheet.merge_range(4, 4, 4, 5, 'Today Date', header_merge_format)
#         sheet.merge_range(4, 6, 4, 7, datetime.today().strftime("%d-%m-%Y"), header_merge_format)
#
#
#
#         row = 5
#         col = 0
#         sheet.write(row, col, 'S.No', header_merge_format)
#         col += 1
#         sheet.set_column(0, 0, 10)
#
#         sheet.write(row, col, 'Employee No', header_merge_format)
#         sheet.set_column(1, 1, 12)
#         col += 1
#         sheet.write(row, col, 'Employee Name', header_merge_format)
#         col += 1
#         sheet.set_column(2, 2, 25)
#         sheet.write(row, col, 'Department Name', header_merge_format)
#         col += 1
#         sheet.set_column(3, 3, 20)
#         sheet.write(row, col, 'Job Position', header_merge_format)
#         col += 1
#         sheet.set_column(4, 4, 15)
#         sheet.write(row, col, 'Nationality', header_merge_format)
#         col += 1
#         sheet.set_column(5, 5, 18)
#
#         sheet.write(row, col, 'Location', header_merge_format)
#         col += 1
#         sheet.set_column(6, 6, 15)
#         sheet.write(row, col, 'Loan type', header_merge_format)
#         sheet.set_column(7, 7, 15)
#         col += 1
#         sheet.write(row, col, 'Loan Reference', header_merge_format)
#         sheet.set_column(8, 8, 15)
#         col += 1
#         sheet.write(row, col, 'Loan Guarantor', header_merge_format)
#         sheet.set_column(9, 9, 18)
#         col += 1
#         sheet.write(row, col, 'Loan start Date', header_merge_format)
#         sheet.set_column(10, 10, 18)
#         col += 1
#         sheet.write(row, col, 'Loan Amount', header_merge_format)
#         sheet.set_column(11, 11, 18)
#         col += 1
#         sheet.write(row, col, 'Loan Installment Rate', header_merge_format)
#         sheet.set_column(12, 12, 18)
#         col += 1
#         sheet.write(row, col, 'Last Repayment Date', header_merge_format)
#         sheet.set_column(13, 13, 18)
#         col += 1
#         sheet.write(row, col, 'Number of Installment', header_merge_format)
#         sheet.set_column(14, 14, 18)
#         col += 1
#         sheet.write(row, col, 'Paid Installment', header_merge_format)
#         sheet.set_column(15,15, 18)
#         col += 1
#         sheet.write(row, col, 'Unpaid Installment', header_merge_format)
#         sheet.set_column(16, 16, 18)
#         col += 1
#         sheet.write(row, col, 'Paid Amount', header_merge_format)
#         sheet.set_column(17, 17, 15)
#         col += 1
#         sheet.write(row, col, 'Balance Amount', header_merge_format)
#         sheet.set_column(18, 18, 18)
#         col += 1
#         sheet.write(row, col, 'Status', header_merge_format)
#         sheet.set_column(19, 19, 12)
#         col += 1
#
#
#         row = 6
#         no = 1
#         if wizard.type=='loan':
#             # if wizard.from_date and wizard.to_date:
#             employee_ids = False
#             employee_status = False
#             approval_status = False
#             payment_status = False
#             dept_ids = False
#             job_ids = False
#             nationality_ids = False
#             branch_ids = False
#             sort_by = False
#
#             domain = []
#
#
#             if wizard.from_date and wizard.to_date:
#                 domain += [('request_date', '<=', wizard.to_date),
#                            ('request_date', '>=', wizard.from_date)]
#
#             if wizard.employee_ids:
#                 employee_ids = wizard.employee_ids
#             else:
#                employee_ids = self.env['hr.employee'].search([])
#
#             if wizard.employee_status:
#                 employee_status = wizard.employee_status 
#
#             if wizard.approval_status:
#                 approval_status = wizard.approval_status
#
#             if wizard.payment_status:
#                 payment_status = wizard.payment_status
#
#             if wizard.department_ids:
#                 dept_ids = wizard.department_ids
#             else:
#                 dept_ids = self.env['hr.department'].search([]) 
#
#
#             if wizard.job_title_ids:
#                 job_ids = wizard.job_title_ids
#             else:
#                 job_ids = self.env['hr.job'].search([])
#
#
#             if wizard.nationality_ids:
#                 nationality_ids = wizard.nationality_ids
#             else:
#                 nationality_ids = self.env['res.country'].search([])    
#
#
#             if wizard.branch_location_ids:
#                 branch_ids = wizard.branch_location_ids
#             else:
#                 branch_ids = self.env['hr.work.location'].search([])
#
#
#             contract_search=False 
#             domain = [
#             ('employee_id', 'in', employee_ids.ids),
#
#             ]
#             if employee_status == 'active':
#                 domain += [('employee_id.state', '=', 'draft'), ('employee_id.contract_warning', '=', False)]
#             elif employee_status == 'terminated':
#                 domain += [('employee_id.state','=','exit'), ('employee_id.contract_warning', '=', True)]
#
#             elif employee_status == 'all':
#                 domain += ['|',('employee_id.contract_warning', '=', False), ('employee_id.contract_warning', '=', True)]
#
#             if approval_status == 'approved':
#                 domain += [('state', '=', 'approve')]
#             elif approval_status =='draft':
#                 domain += [('state','=','draft')]
#
#             elif approval_status == 'rejected':
#                 domain += [('state','=','refused')] 
#
#             elif approval_status == 'waiting_for_approval':
#                 domain += [('state','in',['request','progress','progress2','progress3'])]   
#
#             elif approval_status =='all':
#                 domain += [('state','in',['draft','request','progress','progress2','progress3','approve','refused'])]            
#
#
#             if dept_ids:
#                 domain +=[('employee_id.department_id','in',dept_ids.ids)]
#
#             if job_ids:
#                 domain += [('employee_id.job_id','in',job_ids.ids)]
#
#             if nationality_ids:
#                 domain += [('employee_id.country_of_birth','in',nationality_ids.ids)]  
#
#             if branch_ids:
#                 domain += [('employee_id.work_location_id','in',branch_ids.ids)] 
#
#             if wizard.sort_by:
#                 sort_by = wizard.sort_by
#
#
#
#             # if wizard.approval_status:
#             #     state_mapping = {
#             #         'approved': 'approve',
#             #         'draft': 'draft',
#             #         'rejected': 'refused',
#             #         'waiting_for_approval': ('request', 'progress', 'progress2', 'progress3')
#             #     }
#             #     state = state_mapping.get(wizard.approval_status)
#             #     if isinstance(state, tuple):
#             #         domain += [('state', 'in', state)]
#             #     else:
#             #         domain += [('state', '=', state)]
#             #
#
#             #
#             #
#             #
#             contract_search = self.env['hr.employee.loan.ps'].search(domain)
#             # if employee_status == 'active':
#             #     contract_search = self.env['hr.employee.loan.ps'].search([('employee_id','in',employee_ids.ids),('employee_id.state','=','draft'),('employee_id.contract_warning','=',False),('loan_ins_start_date','<=',wizard.to_date),('loan_ins_start_date','>=',wizard.from_date)])
#             #
#             #
#             # elif employee_status == 'terminated':
#             #     contract_search = self.env['hr.employee.loan.ps'].search([('employee_id','in',employee_ids.ids),('employee_id.state','=','exit'),('employee_id.contract_warning','=',True),('loan_ins_start_date','<=',wizard.to_date),('loan_ins_start_date','>=',wizard.from_date)])
#             #
#             # elif employee_status == 'all':
#             #     contract_search = self.env['hr.employee.loan.ps'].search([('employee_id','in',employee_ids.ids),('loan_ins_start_date','<=',wizard.to_date),('loan_ins_start_date','>=',wizard.from_date)])                   
#             #
#             # # if contract_search:
#             # if approval_status=='draft':
#             #     contract_search = contract_search.filtered(lambda c: c.state == 'draft')                        
#             #
#             if contract_search:
#
#                 if payment_status == 'fully_paid' :
#                     contract_search = contract_search.filtered(lambda c: c.balance_amount == 0.0 and c.state=='approve')                        
#                 elif payment_status =='outstanding':
#                     contract_search = contract_search.filtered(lambda c: c.balance_amount > 0.0 and c.state=='approve')                        
#                 elif payment_status =='all':
#                     contract_search = contract_search.filtered(lambda c: c.balance_amount >= 0.0 and c.state=='approve')                        
#                 if sort_by =='department':
#                     contract_search = contract_search.filtered(lambda c: c.employee_id.department_id)
#                 #     contract_search = contract_search.employee_id.department_id
#                 #     print("contract_search.department", contract_search)
#                 for contract in contract_search:
#                     # if contract.employee_id.department_id in dept_ids:
#
#                     col = 0
#                     sheet.write(row, col, no, num_format)
#                     col += 1
#                     sheet.write(row, col, contract.employee_id.employee_no or ' ', name_format)
#                     col += 1
#                     sheet.write(row, col, contract.employee_id.display_name or ' ' ,name_format)
#                     col += 1
#                     sheet.write(row, col, contract.employee_id.department_id.display_name or ' ' ,name_format)
#                     col += 1
#                     sheet.write(row, col, contract.employee_id.job_id.display_name or ' ' ,name_format)
#                     col += 1
#                     sheet.write(row, col, contract.employee_id.country_of_birth.display_name or ' ' ,name_format)
#                     col += 1
#                     sheet.write(row, col, contract.employee_id.work_location_id.display_name or ' ' ,name_format)
#                     col += 1
#
#                     # gender_display_name = dict(contract._fields['gender'].selection).get(
#                     #     contract.gender)
#                     sheet.write(row, col, contract.type_id.display_name or ' ', name_format)
#                     col += 1
#
#                     sheet.write(row, col, contract.display_name or ' ', name_format)
#                     col += 1
#                     sheet.write(row, col, contract.guarantor_id.name or ' ', name_format)
#                     col += 1
#                     sheet.write(row, col, contract.loan_ins_start_date.strftime("%d-%m-%Y")  if contract.loan_ins_start_date else ' ', name_format)
#
#                     col += 1
#                     sheet.write(row, col, '{:.2f}'.format(contract.loan_amount) or ' ', num_format)
#                     col += 1
#                     ins_rate = 0.00
#                     ins_date = ''
#                     ins_remaining_amount = 0.00
#                     for ins in contract.hr_employee_loan_line_ps:
#                         ins_rate = ins.amount
#                         if ins.state in ['deducted']:
#                             ins_date = ins.installment_date.strftime("%d-%m-%Y")
#                             ins_remaining_amount = ins.remaining_value
#                     sheet.write(row, col, '{:.2f}'.format(ins_rate) or ' ', num_format)
#                     col += 1
#                     sheet.write(row, col, ins_date or ' ', name_format)
#                     col += 1
#
#
#                     sheet.write(row, col, '{:.2f}'.format(contract.loan_month_ins) or ' ', num_format)
#                     col += 1 
#                     sheet.write(row, col, '{:.2f}'.format(contract.paid_installment) or ' ', num_format)
#                     col += 1 
#                     sheet.write(row, col, '{:.2f}'.format(contract.unpaid_installment) or ' ', num_format)
#                     col += 1     
#                     sheet.write(row, col, '{:.2f}'.format(contract.paid_amount) or ' ', num_format)
#                     col += 1
#                     sheet.write(row, col, '{:.2f}'.format(contract.balance_amount) or ' ', num_format)
#                     col += 1
#
#                     if contract.state:
#                         state_display_name = dict(contract._fields['state'].selection).get(
#                             contract.state)
#                         sheet.write(row, col, state_display_name or ' ', name_format)
#                     else:
#                         sheet.write(row,col,' ',name_format)
#                     # sheet.write(row, col, '{:.2f}'.format(ins_remaining_amount) or ' ', num_format)
#                     # col += 1
#
#                     row += 1
#                     no += 1
#
#
#
#
#
#
#
#
#

