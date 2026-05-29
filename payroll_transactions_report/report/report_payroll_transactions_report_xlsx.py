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
from odoo.exceptions import UserError



class PayrollTransactionReportExcel(models.AbstractModel):
    _name = 'report.payroll_transactions_report.payroll_transaction_report'
    _inherit = 'report.report_xlsx.abstract'    
    _description = 'Payroll Transactions Report Xlsx'
    
    
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
        header_num_format = workbook.add_format({'bold':True,'align': 'right', 'valign': 'vcenter', \
                                           'font_size': 10, 'border': 1,'bg_color':'#D3D3D3'})
        
        
        total_num_format = workbook.add_format({'align': 'right', 'valign': 'vcenter', \
                                           'font_size': 10, 'border': 1,'bold':True,'bg_color':'#D3D3D3'})
        header_left_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', \
                                                  'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})

        header_merge_format3 = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', \
                                                    'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})
        
        header_data_format4 = workbook.add_format({'bold':True,'align':'center', 'valign':'vcenter', \
                                                   'font_size':10,'bg_color':'#B7950B', 'border':1})

        sheet = workbook.add_worksheet("Employee Payroll Transaction Report")
        sheet.set_row(0, 25)
        
        
        sheet.merge_range(0, 0, 2, 15, "Employee Payroll Transaction Report" , header_merge_format)
        # sheet.write(8, 1, 'Employee Salary report', header_merge_format)
        
        sheet.merge_range(3, 0, 3, 1, 'Company', header_merge_format)
        sheet.merge_range(3, 2, 3, 3, wizard.company_id.name, header_merge_format)
        
        sheet.merge_range(3, 4, 3, 5, 'Today Date', header_merge_format)
        sheet.merge_range(3, 6, 3, 7, datetime.today().strftime("%d-%m-%Y"), header_merge_format)
        
        sheet.merge_range(4, 0, 4, 1, 'From Date',header_merge_format)
        sheet.merge_range(4, 2, 4, 3, wizard.from_date.strftime("%d-%m-%Y"),header_merge_format)
        
        sheet.merge_range(4, 4, 4, 5, 'To Date',header_merge_format )
        sheet.merge_range(4, 6, 4, 7, wizard.to_date.strftime("%d-%m-%Y"),header_merge_format )
        
        # sheet.merge_range(4, 0, 4, 1, 'Company', header_merge_format)
        # sheet.merge_range(4, 2, 4, 3, wizard.company_id.name, header_merge_format)
        #
        # sheet.merge_range(4, 4, 4, 5, 'Today Date', header_merge_format)
        # sheet.merge_range(4, 6, 4, 7, datetime.today().strftime("%d-%m-%Y"), header_merge_format)
        
        # sheet.merge_range(5, 0, 5, 10, 'Basic Details', header_data_format4)
        # sheet.merge_range(5, 11, 5, 20, 'Allowances', header_data_format2)
        # sheet.merge_range(5, 21, 5, 23, 'Deduction', header_data_format3)

        
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
        sheet.write(row, col, 'Department', header_merge_format)
        sheet.set_column(3, 3, 18)
        col += 1
        sheet.write(row, col, 'Job Title', header_merge_format)
        sheet.set_column(4, 4, 18)
        col += 1
        sheet.write(row, col, 'Nationality', header_merge_format)
        sheet.set_column(5, 5, 18)
        col += 1
        sheet.write(row, col, 'Location', header_merge_format)
        sheet.set_column(6, 6, 18)
        col += 1
        sheet.write(row, col, 'Reference', header_merge_format)
        sheet.set_column(7, 7, 18)
        col += 1
        sheet.write(row, col, 'Date', header_merge_format)
        sheet.set_column(8, 8, 18)
        col += 1
        sheet.write(row, col, 'Code', header_merge_format)
        sheet.set_column(9, 9, 18)
        col += 1
        sheet.write(row, col, 'Description', header_merge_format)
        sheet.set_column(10, 10, 18)
        col += 1
        
        sheet.write(row,col,'Transaction Entry',header_merge_format)
        sheet.set_column(15, 15, 18)
        col += 1
        
        sheet.write(row, col, 'Units', header_merge_format)
        sheet.set_column(11, 11, 18)
        col += 1

        sheet.write(row, col, 'Amount', header_merge_format)
        sheet.set_column(12, 12, 18)
        col += 1
        sheet.write(row, col, 'Remarks', header_merge_format)
        sheet.set_column(13, 13, 18)
        col += 1
        sheet.write(row, col, 'Status', header_merge_format)
        sheet.set_column(14, 14, 18)
        col += 1
      
        
        row = 7
        no = 1
        
        
        # Initialize domain for filtering
        domain = []

        # Build domain for filtering employee records
        domain.append(('employee_id', 'in', wizard.employee_ids.ids if wizard.employee_ids else self.env['hr.employee'].search([]).ids))
        
        if wizard.from_date and wizard.to_date:
            domain.append(('date', '>=', wizard.from_date))
            domain.append(('date', '<=', wizard.to_date))
        
        # Add filter headers to Excel (avoid overwriting)
        row = 5
        if wizard.department_ids:
            domain.append(('employee_id.department_id', 'in', wizard.department_ids.ids))
            sheet.merge_range(row, 0, row, 15, "Department Wise Search", header_merge_format)
            row += 1
        
        if wizard.job_title_ids:
            domain.append(('employee_id.job_id', 'in', wizard.job_title_ids.ids))
            sheet.merge_range(row, 0, row, 15, "Job Wise Search", header_merge_format)
            row += 1
        
        if wizard.nationality_ids:
            domain.append(('employee_id.country_of_birth', 'in', wizard.nationality_ids.ids))
            sheet.merge_range(row, 0, row, 15, "Nation Wise Search", header_merge_format)
            row += 1
        
        if wizard.branch_location_ids:
            domain.append(('employee_id.work_location_id', 'in', wizard.branch_location_ids.ids))
            sheet.merge_range(row, 0, row, 15, "Branch Location Wise Search", header_merge_format)
            row += 1
        
        # Search for salary allowance detection records
        domain.append(('state', '!=', 'cancel'))
        employee_search = self.env['salary.allowance.detection'].search(domain)
        
        if not employee_search:
            raise UserError("No data found for the selected Employees and date range.")
        
        # Initialize variables
        excel_list = []
        row = 7  # Start data at row 7
        num = 1
        grand_total = 0.0
        
        # Dynamically get unique transaction types if grouping by transaction
        transaction_types = []
        if wizard.group_by_transaction:
            transaction_types = sorted(
                {record.hr_transaction_id.description for record in employee_search if record.hr_transaction_id.description},
                key=lambda x: x.lower()
            )
        
        # Define sorting key based on wizard.sort_by
        def get_sort_key(record):
            sort_key = [record.employee_id.name.lower()]
            if wizard.group_by_transaction:
                sort_key.append(record.hr_transaction_id.description or '')
            else:
                sort_key.append(record.date or fields.Date.today())
        
            if wizard.sort_by == 'department':
                sort_key.insert(0, record.employee_id.department_id.name.lower() if record.employee_id.department_id else '')
            elif wizard.sort_by == 'job_title':
                sort_key.insert(0, record.employee_id.job_id.name.lower() if record.employee_id.job_id else '')
            elif wizard.sort_by == 'branch_location':
                sort_key.insert(0, record.employee_id.work_location_id.name.lower() if record.employee_id.work_location_id else '')
            elif wizard.sort_by == 'nationality':
                sort_key.insert(0, record.employee_id.country_of_birth.name.lower() if record.employee_id.country_of_birth else '')
            elif wizard.sort_by == 'employee_no':
                employee_no = record.employee_id.employee_no or ''
                sort_key.insert(0, int(employee_no) if isinstance(employee_no, str) and employee_no.isdigit() else employee_no)
            return tuple(sort_key)
        
        # Sort records
        employee_search = employee_search.sorted(key=get_sort_key)
        
        # Define group field mapping
        group_field_map = {
            'department': ('department_id', 'hr.department'),
            'job_title': ('job_id', 'hr.job'),
            'branch_location': ('work_location_id', 'hr.work.location'),
            'nationality': ('country_of_birth', 'res.country'),
            'employee_no': ('employee_id', 'hr.employee')
        }
        
        # Get unique groups (e.g., all departments)
        group_field, model = group_field_map.get(wizard.sort_by, ('employee_id', 'hr.employee'))
        groups = []
        if wizard.sort_by:
            groups = sorted(
                {record.employee_id[group_field].id for record in employee_search if record.employee_id[group_field]},
                key=lambda x: (
                    self.env[model].browse(x).name.lower()
                    if self.env[model].browse(x).name
                    else ''
                )
            )
        else:
            # If no sorting, treat all records as one group (employee-based)
            groups = sorted(
                {record.employee_id.id for record in employee_search},
                key=lambda x: self.env['hr.employee'].browse(x).name.lower()
            )
        
        # Initialize totals
        group_totals = {group_id: 0.0 for group_id in groups}
        employee_totals = {}
        transaction_totals = {}
        
        for group_id in groups:
            # Fetch group name
            if wizard.sort_by:
                group = self.env[model].browse(group_id)
                group_name = group.name or f"No {wizard.sort_by.replace('_', ' ').title()}"
            else:
                group = self.env['hr.employee'].browse(group_id)
                group_name = group.name or "Unknown Employee"
        
            # Write group header
            if wizard.sort_by:
                sheet.merge_range(row, 0, row, 15, group_name, header_merge_format3)
                row += 1
                num = 1
        
            # Filter records for this group
            if wizard.sort_by:
                group_records = employee_search.filtered(lambda r: r.employee_id[group_field].id == group_id)
            else:
                group_records = employee_search.filtered(lambda r: r.employee_id.id == group_id)
        
            # Group by employee
            employee_groups = {}
            for record in group_records:
                emp_id = record.employee_id.id
                if emp_id not in employee_groups:
                    employee_groups[emp_id] = []
                employee_groups[emp_id].append(record)
        
            if wizard.group_by_transaction:
                # Group by transaction type across all employees in the group
                transaction_groups = {}
                for record in group_records:
                    trans_type = record.hr_transaction_id.description or 'Unknown'
                    if trans_type not in transaction_groups:
                        transaction_groups[trans_type] = []
                    transaction_groups[trans_type].append(record)
        
                # Process each transaction type
                for trans_type in transaction_types:
                    if trans_type not in transaction_groups:
                        continue
                    transaction_records = sorted(transaction_groups[trans_type], key=lambda r: (r.employee_id.name.lower(), r.date))
                    transaction_total = 0.0
        
                    # Write transaction type header once per transaction type in the group
                    sheet.merge_range(row, 0, row, 15, trans_type, header_merge_format3)
                    row += 1
                    num = 1
        
                    # Group transaction records by employee
                    trans_employee_groups = {}
                    for record in transaction_records:
                        emp_id = record.employee_id.id
                        if emp_id not in trans_employee_groups:
                            trans_employee_groups[emp_id] = []
                        trans_employee_groups[emp_id].append(record)
        
                    # Process each employee for this transaction type
                    for emp_id in sorted(trans_employee_groups.keys(), key=lambda x: self.env['hr.employee'].browse(x).name.lower()):
                        emp_records = trans_employee_groups[emp_id]
                        current_employee = emp_records[0].employee_id
                        employee_total = 0.0
        
                        # Write employee header
                        sheet.merge_range(row, 0, row, 15, current_employee.name or 'Unknown Employee', header_merge_format3)
                        row += 1
                        num = 1
        
                        # Write transaction records for this employee
                        for payroll in emp_records:
                            col = 0
                            sheet.write(row, col, num, name_format)
                            col += 1
                            sheet.write(row, col, payroll.employee_id.employee_no or ' ', name_format)
                            col += 1
                            sheet.write(row, col, payroll.employee_id.name or ' ', name_format)
                            col += 1
                            sheet.write(row, col, payroll.employee_id.department_id.name or ' ', name_format)
                            col += 1
                            sheet.write(row, col, payroll.employee_id.job_id.name or ' ', name_format)
                            col += 1
                            sheet.write(row, col, payroll.employee_id.country_of_birth.name or ' ', name_format)
                            col += 1
                            sheet.write(row, col, payroll.employee_id.work_location_id.name or ' ', name_format)
                            col += 1
                            sheet.write(row, col, payroll.name or ' ', name_format)
                            col += 1
                            sheet.write(row, col, payroll.date.strftime("%d-%m-%Y") or ' ', name_format)
                            col += 1
                            sheet.write(row, col, payroll.code or ' ', name_format)
                            col += 1
                            sheet.write(row, col, payroll.transaction_type_id.name or ' ', name_format)
                            col += 1
                            sheet.write(row, col, payroll.hr_transaction_id.description or ' ', name_format)
                            col += 1
                            units_display_name = dict(payroll._fields['units'].selection).get(payroll.units, '')
                            if payroll.units == 'days':
                                sheet.write(row, col, f"{round(payroll.days, 2)}/{units_display_name}", num_format)
                            elif payroll.units == 'hours':
                                sheet.write(row, col, f"{round(payroll.hours, 2)}/{units_display_name}", num_format)
                            else:
                                sheet.write(row, col, ' ', num_format)
                            col += 1
                            display_amount = float_round(payroll.amount, 2)
                            sheet.write(row, col, display_amount, num_format)
                            col += 1
                            grand_total += display_amount
                            group_totals[group_id] += display_amount
                            employee_total += display_amount
                            transaction_total += display_amount
                            sheet.write(row, col, payroll.reason or ' ', name_format)
                            col += 1
                            state_display_name = dict(payroll._fields['state'].selection).get(payroll.state, '')
                            sheet.write(row, col, state_display_name, name_format)
        
                            excel_list.append(payroll.employee_id.display_name)
                            row += 1
                            num += 1
        
                        # Write employee total
                        sheet.merge_range(row, 0, row, 12, 'Employee Total', header_num_format)
                        sheet.write(row, 13, f"{employee_total:,.2f}", total_num_format)
                        row += 1
        
                    # Write transaction type subtotal
                    sheet.merge_range(row, 0, row, 12, f'{trans_type} Subtotal', header_num_format)
                    sheet.write(row, 13, f"{transaction_total:,.2f}", total_num_format)
                    row += 1
            else:
                # Sort employees by name
                for emp_id in sorted(employee_groups.keys(), key=lambda x: employee_groups[x][0].employee_id.name.lower()):
                    emp_records = employee_groups[emp_id]
                    current_employee = emp_records[0].employee_id
                    employee_total = 0.0
        
                    # Write employee header
                    sheet.merge_range(row, 0, row, 15, current_employee.name or 'Unknown Employee', header_merge_format3)
                    row += 1
                    num = 1
        
                    # Write transactions without grouping
                    for payroll in sorted(emp_records, key=lambda r: r.date):
                        col = 0
                        sheet.write(row, col, num, name_format)
                        col += 1
                        sheet.write(row, col, payroll.employee_id.employee_no or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.employee_id.name or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.employee_id.department_id.name or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.employee_id.job_id.name or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.employee_id.country_of_birth.name or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.employee_id.work_location_id.name or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.name or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.date.strftime("%d-%m-%Y") or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.code or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.transaction_type_id.name or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.hr_transaction_id.description or ' ', name_format)
                        col += 1
                        units_display_name = dict(payroll._fields['units'].selection).get(payroll.units, '')
                        if payroll.units == 'days':
                            sheet.write(row, col, f"{round(payroll.days, 2)}/{units_display_name}", num_format)
                        elif payroll.units == 'hours':
                            sheet.write(row, col, f"{round(payroll.hours, 2)}/{units_display_name}", num_format)
                        else:
                            sheet.write(row, col, ' ', num_format)
                        col += 1
                        display_amount = float_round(payroll.amount, 2)
                        sheet.write(row, col, display_amount, num_format)
                        col += 1
                        grand_total += display_amount
                        group_totals[group_id] += display_amount
                        employee_total += display_amount
                        sheet.write(row, col, payroll.reason or ' ', name_format)
                        col += 1
                        state_display_name = dict(payroll._fields['state'].selection).get(payroll.state, '')
                        sheet.write(row, col, state_display_name, name_format)
        
                        excel_list.append(payroll.employee_id.display_name)
                        row += 1
                        num += 1
        
                    # Write employee total
                    sheet.merge_range(row, 0, row, 12, 'Employee Total', header_num_format)
                    sheet.write(row, 13, f"{employee_total:,.2f}", total_num_format)
                    row += 1
        
            # Write group total
            if wizard.sort_by:
                sheet.write(row, 12, f"{wizard.sort_by.replace('_', ' ').title()} Total", header_num_format)
                sheet.write(row, 13, f"{group_totals[group_id]:,.2f}", total_num_format)
                row += 1
        
        # Write grand total
        sheet.merge_range(row, 0, row, 12, 'Grand Total', header_num_format)
        sheet.write(row, 13, f"{grand_total:,.2f}", total_num_format)
        
        #currently working only group_by transaction heading  duplicate 
        # domain = []
        #
        # # Build domain for filtering employee records
        # domain.append(('employee_id', 'in', wizard.employee_ids.ids if wizard.employee_ids else self.env['hr.employee'].search([]).ids))
        #
        # if wizard.from_date and wizard.to_date:
        #     domain.append(('date', '>=', wizard.from_date))
        #     domain.append(('date', '<=', wizard.to_date))
        #
        # # Add filter headers to Excel (avoid overwriting)
        # row = 5
        # if wizard.department_ids:
        #     domain.append(('employee_id.department_id', 'in', wizard.department_ids.ids))
        #     sheet.merge_range(row, 0, row, 15, "Department Wise Search", header_merge_format)
        #     row += 1
        #
        # if wizard.job_title_ids:
        #     domain.append(('employee_id.job_id', 'in', wizard.job_title_ids.ids))
        #     sheet.merge_range(row, 0, row, 15, "Job Wise Search", header_merge_format)
        #     row += 1
        #
        # if wizard.nationality_ids:
        #     domain.append(('employee_id.country_of_birth', 'in', wizard.nationality_ids.ids))
        #     sheet.merge_range(row, 0, row, 15, "Nation Wise Search", header_merge_format)
        #     row += 1
        #
        # if wizard.branch_location_ids:
        #     domain.append(('employee_id.work_location_id', 'in', wizard.branch_location_ids.ids))
        #     sheet.merge_range(row, 0, row, 15, "Branch Location Wise Search", header_merge_format)
        #     row += 1
        #
        # # Search for salary allowance detection records
        # domain.append(('state', '!=', 'cancel'))
        # employee_search = self.env['salary.allowance.detection'].search(domain)
        #
        # if not employee_search:
        #     raise UserError("No data found for the selected Employees and date range.")
        #
        # # Initialize variables
        # excel_list = []
        # row = 7  # Start data at row 7
        # num = 1
        # grand_total = 0.0
        #
        # # Dynamically get unique transaction types if grouping by transaction
        # transaction_types = []
        # if wizard.group_by_transaction:
        #     transaction_types = sorted(
        #         {record.hr_transaction_id.description for record in employee_search if record.hr_transaction_id.description},
        #         key=lambda x: x.lower()
        #     )
        #
        # # Define sorting key based on wizard.sort_by
        # def get_sort_key(record):
        #     sort_key = [record.employee_id.name.lower()]
        #     if wizard.group_by_transaction:
        #         sort_key.append(record.hr_transaction_id.description or '')
        #     else:
        #         sort_key.append(record.date or fields.Date.today())
        #
        #     if wizard.sort_by == 'department':
        #         sort_key.insert(0, record.employee_id.department_id.name.lower() if record.employee_id.department_id else '')
        #     elif wizard.sort_by == 'job_title':
        #         sort_key.insert(0, record.employee_id.job_id.name.lower() if record.employee_id.job_id else '')
        #     elif wizard.sort_by == 'branch_location':
        #         sort_key.insert(0, record.employee_id.work_location_id.name.lower() if record.employee_id.work_location_id else '')
        #     elif wizard.sort_by == 'nationality':
        #         sort_key.insert(0, record.employee_id.country_of_birth.name.lower() if record.employee_id.country_of_birth else '')
        #     elif wizard.sort_by == 'employee_no':
        #         employee_no = record.employee_id.employee_no or ''
        #         sort_key.insert(0, int(employee_no) if isinstance(employee_no, str) and employee_no.isdigit() else employee_no)
        #     return tuple(sort_key)
        #
        # # Sort records
        # employee_search = employee_search.sorted(key=get_sort_key)
        #
        # # Define group field mapping
        # group_field_map = {
        #     'department': ('department_id', 'hr.department'),
        #     'job_title': ('job_id', 'hr.job'),
        #     'branch_location': ('work_location_id', 'hr.work.location'),
        #     'nationality': ('country_of_birth', 'res.country'),
        #     'employee_no': ('employee_id', 'hr.employee')
        # }
        #
        # # Get unique groups (e.g., all departments)
        # group_field, model = group_field_map.get(wizard.sort_by, ('employee_id', 'hr.employee'))
        # groups = []
        # if wizard.sort_by:
        #     groups = sorted(
        #         {record.employee_id[group_field].id for record in employee_search if record.employee_id[group_field]},
        #         key=lambda x: (
        #             self.env[model].browse(x).name.lower()
        #             if self.env[model].browse(x).name
        #             else ''
        #         )
        #     )
        # else:
        #     # If no sorting, treat all records as one group (employee-based)
        #     groups = sorted(
        #         {record.employee_id.id for record in employee_search},
        #         key=lambda x: self.env['hr.employee'].browse(x).name.lower()
        #     )
        #
        # # Initialize totals
        # group_totals = {group_id: 0.0 for group_id in groups}
        # employee_totals = {}
        # transaction_totals = {}
        #
        # for group_id in groups:
        #     # Fetch group name
        #     if wizard.sort_by:
        #         group = self.env[model].browse(group_id)
        #         group_name = group.name or f"No {wizard.sort_by.replace('_', ' ').title()}"
        #     else:
        #         group = self.env['hr.employee'].browse(group_id)
        #         group_name = group.name or "Unknown Employee"
        #
        #     # Write group header
        #     sheet.merge_range(row, 0, row, 15, group_name, header_merge_format3)
        #     row += 1
        #     num = 1
        #
        #     # Filter records for this group
        #     if wizard.sort_by:
        #         group_records = employee_search.filtered(lambda r: r.employee_id[group_field].id == group_id)
        #     else:
        #         group_records = employee_search.filtered(lambda r: r.employee_id.id == group_id)
        #
        #     # Group by employee
        #     employee_groups = {}
        #     for record in group_records:
        #         emp_id = record.employee_id.id
        #         if emp_id not in employee_groups:
        #             employee_groups[emp_id] = []
        #         employee_groups[emp_id].append(record)
        #
        #     # Sort employees by name
        #     for emp_id in sorted(employee_groups.keys(), key=lambda x: employee_groups[x][0].employee_id.name.lower()):
        #         emp_records = employee_groups[emp_id]
        #         current_employee = emp_records[0].employee_id
        #         employee_total = 0.0
        #
        #         # Write employee header
        #         sheet.merge_range(row, 0, row, 15, current_employee.name or 'Unknown Employee', header_merge_format3)
        #         row += 1
        #         num = 1
        #
        #         if wizard.group_by_transaction:
        #             # Group by transaction type
        #             transaction_groups = {}
        #             for record in emp_records:
        #                 trans_type = record.hr_transaction_id.description or 'Unknown'
        #                 if trans_type not in transaction_groups:
        #                     transaction_groups[trans_type] = []
        #                 transaction_groups[trans_type].append(record)
        #
        #             # Process each transaction type
        #             for trans_type in transaction_types:
        #                 if trans_type not in transaction_groups:
        #                     continue
        #                 transaction_records = sorted(transaction_groups[trans_type], key=lambda r: r.date)
        #                 transaction_total = 0.0
        #
        #                 # Write transaction type header
        #                 sheet.merge_range(row, 0, row, 15, trans_type, header_merge_format3)
        #                 row += 1
        #                 num = 1
        #
        #                 # Write transaction records
        #                 for payroll in transaction_records:
        #                     col = 0
        #                     sheet.write(row, col, num, name_format)
        #                     col += 1
        #                     sheet.write(row, col, payroll.employee_id.employee_no or ' ', name_format)
        #                     col += 1
        #                     sheet.write(row, col, payroll.employee_id.name or ' ', name_format)
        #                     col += 1
        #                     sheet.write(row, col, payroll.employee_id.department_id.name or ' ', name_format)
        #                     col += 1
        #                     sheet.write(row, col, payroll.employee_id.job_id.name or ' ', name_format)
        #                     col += 1
        #                     sheet.write(row, col, payroll.employee_id.country_of_birth.name or ' ', name_format)
        #                     col += 1
        #                     sheet.write(row, col, payroll.employee_id.work_location_id.name or ' ', name_format)
        #                     col += 1
        #                     sheet.write(row, col, payroll.name or ' ', name_format)
        #                     col += 1
        #                     sheet.write(row, col, payroll.date.strftime("%d-%m-%Y") or ' ', name_format)
        #                     col += 1
        #                     sheet.write(row, col, payroll.code or ' ', name_format)
        #                     col += 1
        #                     sheet.write(row, col, payroll.transaction_type_id.name or ' ', name_format)
        #                     col += 1
        #                     sheet.write(row, col, payroll.hr_transaction_id.description or ' ', name_format)
        #                     col += 1
        #                     units_display_name = dict(payroll._fields['units'].selection).get(payroll.units, '')
        #                     if payroll.units == 'days':
        #                         sheet.write(row, col, f"{round(payroll.days, 2)}/{units_display_name}", num_format)
        #                     elif payroll.units == 'hours':
        #                         sheet.write(row, col, f"{round(payroll.hours, 2)}/{units_display_name}", num_format)
        #                     else:
        #                         sheet.write(row, col, ' ', num_format)
        #                     col += 1
        #                     display_amount = float_round(payroll.amount, 2)
        #                     sheet.write(row, col, display_amount, num_format)
        #                     col += 1
        #                     grand_total += display_amount
        #                     group_totals[group_id] += display_amount
        #                     employee_total += display_amount
        #                     transaction_total += display_amount
        #                     sheet.write(row, col, payroll.reason or ' ', name_format)
        #                     col += 1
        #                     state_display_name = dict(payroll._fields['state'].selection).get(payroll.state, '')
        #                     sheet.write(row, col, state_display_name, name_format)
        #
        #                     excel_list.append(payroll.employee_id.display_name)
        #                     row += 1
        #                     num += 1
        #
        #                 # Write transaction type subtotal
        #                 sheet.merge_range(row, 0, row, 12, f'{trans_type} Subtotal', header_num_format)
        #                 sheet.write(row, 13, f"{transaction_total:,.2f}", total_num_format)
        #                 row += 1
        #         else:
        #             # Write transactions without grouping
        #             for payroll in sorted(emp_records, key=lambda r: r.date):
        #                 col = 0
        #                 sheet.write(row, col, num, name_format)
        #                 col += 1
        #                 sheet.write(row, col, payroll.employee_id.employee_no or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, payroll.employee_id.name or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, payroll.employee_id.department_id.name or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, payroll.employee_id.job_id.name or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, payroll.employee_id.country_of_birth.name or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, payroll.employee_id.work_location_id.name or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, payroll.name or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, payroll.date.strftime("%d-%m-%Y") or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, payroll.code or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, payroll.transaction_type_id.name or ' ', name_format)
        #                 col += 1
        #                 sheet.write(row, col, payroll.hr_transaction_id.description or ' ', name_format)
        #                 col += 1
        #                 units_display_name = dict(payroll._fields['units'].selection).get(payroll.units, '')
        #                 if payroll.units == 'days':
        #                     sheet.write(row, col, f"{round(payroll.days, 2)}/{units_display_name}", num_format)
        #                 elif payroll.units == 'hours':
        #                     sheet.write(row, col, f"{round(payroll.hours, 2)}/{units_display_name}", num_format)
        #                 else:
        #                     sheet.write(row, col, ' ', num_format)
        #                 col += 1
        #                 display_amount = float_round(payroll.amount, 2)
        #                 sheet.write(row, col, display_amount, num_format)
        #                 col += 1
        #                 grand_total += display_amount
        #                 group_totals[group_id] += display_amount
        #                 employee_total += display_amount
        #                 sheet.write(row, col, payroll.reason or ' ', name_format)
        #                 col += 1
        #                 state_display_name = dict(payroll._fields['state'].selection).get(payroll.state, '')
        #                 sheet.write(row, col, state_display_name, name_format)
        #
        #                 excel_list.append(payroll.employee_id.display_name)
        #                 row += 1
        #                 num += 1
        #
        #         # Write employee total
        #         sheet.merge_range(row, 0, row, 12, 'Employee Total', header_num_format)
        #         sheet.write(row, 13, f"{employee_total:,.2f}", total_num_format)
        #         row += 1
        #
        #     # Write group total
        #     if wizard.sort_by:
        #         sheet.write(row, 12, f"{wizard.sort_by.replace('_', ' ').title()} Total", header_num_format)
        #         sheet.write(row, 13, f"{group_totals[group_id]:,.2f}", total_num_format)
        #         row += 1
        #
        # # Write grand total
        # sheet.merge_range(row, 0, row, 12, 'Grand Total', header_num_format)
        # sheet.write(row, 13, f"{grand_total:,.2f}", total_num_format)
                       
         
        '''currently working
        domain = []
        
        # Build domain for filtering employee records
        domain += [('employee_id', 'in', wizard.employee_ids.ids if wizard.employee_ids else self.env['hr.employee'].search([]).ids)]
        
        if wizard.from_date and wizard.to_date:
            domain += [('date', '>=', wizard.from_date), ('date', '<=', wizard.to_date)]
        
        if wizard.department_ids:
            domain += [('employee_id.department_id', 'in', wizard.department_ids.ids)]
            sheet.merge_range(5, 0, 5, 15, "Department Wise Search", header_merge_format)
        
        if wizard.job_title_ids:
            domain += [('employee_id.job_id', 'in', wizard.job_title_ids.ids)]
            sheet.merge_range(5, 0, 5, 15, "Job Wise Search", header_merge_format)
        
        if wizard.nationality_ids:
            domain += [('employee_id.country_of_birth', 'in', wizard.nationality_ids.ids)]
            sheet.merge_range(5, 0, 5, 15, "Nation Wise Search", header_merge_format)
        
        if wizard.branch_location_ids:
            domain += [('employee_id.work_location_id', 'in', wizard.branch_location_ids.ids)]
            sheet.merge_range(5, 0, 5, 15, "Branch Location Wise Search", header_merge_format)
        
        excel_list = []
        employee_ids = wizard.employee_ids or self.env['hr.employee'].search([])
        
        # Search for salary allowance detection records
        domain += [('state','!=','cancel')]
        employee_search = self.env['salary.allowance.detection'].search(domain)
        
        # Dynamically get unique transaction types only if group_by_transaction is True
        transaction_types = []
        if wizard.group_by_transaction:
            transaction_types = sorted(
                set(record.hr_transaction_id.description for record in employee_search if record.hr_transaction_id.description),
                key=lambda x: x.lower()
            )
        
        # Sort records by employee and transaction type (if grouping by transaction)
        if wizard.group_by_transaction:
            employee_search = employee_search.sorted(key=lambda s: (s.employee_id.name.lower(), s.hr_transaction_id.description, s.date))
        else:
            employee_search = employee_search.sorted(key=lambda s: (s.employee_id.name.lower(), s.date))
        
        # Apply sorting based on wizard.sort_by
        if wizard.sort_by:
            if wizard.sort_by == 'department':
                employee_search = employee_search.sorted(key=lambda s: (
                    s.employee_id.department_id.name.lower() if s.employee_id.department_id else '',
                    s.employee_id.name.lower(),
                    s.hr_transaction_id.description if wizard.group_by_transaction else s.date
                ))
                sheet.merge_range(5, 0, 5, 15, "Department Wise Sort", header_merge_format)
            elif wizard.sort_by == 'job_title':
                employee_search = employee_search.sorted(key=lambda s: (
                    s.employee_id.job_id.name.lower() if s.employee_id.job_id else '',
                    s.employee_id.name.lower(),
                    s.hr_transaction_id.description if wizard.group_by_transaction else s.date
                ))
                sheet.merge_range(5, 0, 5, 15, "Job Wise Sort", header_merge_format)
            elif wizard.sort_by == 'branch_location':
                employee_search = employee_search.sorted(key=lambda s: (
                    s.employee_id.work_location_id.name.lower() if s.employee_id.work_location_id else '',
                    s.employee_id.name.lower(),
                    s.hr_transaction_id.description if wizard.group_by_transaction else s.date
                ))
                sheet.merge_range(5, 0, 5, 15, "Branch Location Wise Sort", header_merge_format)
            elif wizard.sort_by == 'nationality':
                employee_search = employee_search.sorted(key=lambda s: (
                    s.employee_id.country_of_birth.name.lower() if s.employee_id.country_of_birth else '',
                    s.employee_id.name.lower(),
                    s.hr_transaction_id.description if wizard.group_by_transaction else s.date
                ))
                sheet.merge_range(5, 0, 5, 15, "Nation Wise Sort", header_merge_format)
            elif wizard.sort_by == 'employee_no':
                employee_search = employee_search.sorted(key=lambda s: (
                    0 if s.employee_id.employee_no and isinstance(s.employee_id.employee_no, str) and s.employee_id.employee_no.isdigit() else 1,
                    int(s.employee_id.employee_no) if s.employee_id.employee_no and isinstance(s.employee_id.employee_no, str) and s.employee_id.employee_no.isdigit() else s.employee_id.employee_no or '',
                    s.employee_id.name.lower(),
                    s.hr_transaction_id.description if wizard.group_by_transaction else s.date
                ))
                sheet.merge_range(5, 0, 5, 15, "Employee Number Wise Sort", header_merge_format)
        
        # Initialize variables
        num = 1
        row = 7  # Assuming row 7 is where data starts
        grand_total = 0.0
        department_sort = set()
        job_sort = set()
        nation_sort = set()
        location_sort = set()
        current_employee = None
        employee_total = 0.0
        transaction_total = 0.0
        previous_group = None
        group_total = 0.0
        
        # Group records by employee
        employee_groups = {}
        for record in employee_search:
            emp_id = record.employee_id.id
            if emp_id not in employee_groups:
                employee_groups[emp_id] = []
            employee_groups[emp_id].append(record)
        
        for emp_id in sorted(employee_groups.keys(), key=lambda x: employee_groups[x][0].employee_id.name.lower()):
            emp_records = employee_groups[emp_id]
            current_employee = emp_records[0].employee_id
            employee_total = 0.0
        
            # Handle sorting group headers (department, job_title, etc.)
            current_group = None
            if wizard.sort_by:
                if wizard.sort_by == 'department':
                    current_group = current_employee.department_id.complete_name
                    if current_group not in department_sort:
                        if previous_group is not None:
                            sheet.write(row, 12, 'Department Total', header_num_format)
                            sheet.write(row, 13, f"{group_total:,.2f}", num_format)
                            row += 1
                            group_total = 0.0
                        sheet.merge_range(row, 0, row, 15, current_group or 'No Department', header_merge_format3)
                        department_sort.add(current_group)
                        row += 1
                        num = 1
                elif wizard.sort_by == 'job_title':
                    current_group = current_employee.job_id.name
                    if current_group not in job_sort:
                        if previous_group is not None:
                            sheet.write(row, 12, 'Job Total', header_num_format)
                            sheet.write(row, 13, f"{group_total:,.2f}", num_format)
                            row += 1
                            group_total = 0.0
                        sheet.merge_range(row, 0, row, 15, current_group or 'No Job', header_merge_format3)
                        job_sort.add(current_group)
                        row += 1
                        num = 1
                elif wizard.sort_by == 'branch_location':
                    current_group = current_employee.work_location_id.name
                    if current_group not in location_sort:
                        if previous_group is not None:
                            sheet.write(row, 12, 'Branch Total', header_num_format)
                            sheet.write(row, 13, f"{group_total:,.2f}", num_format)
                            row += 1
                            group_total = 0.0
                        sheet.merge_range(row, 0, row, 15, current_group or 'No Location', header_merge_format3)
                        location_sort.add(current_group)
                        row += 1
                        num = 1
                elif wizard.sort_by == 'nationality':
                    current_group = current_employee.country_of_birth.name
                    if current_group not in nation_sort:
                        if previous_group is not None:
                            sheet.write(row, 12, 'Nationalwise Total', header_num_format)
                            sheet.write(row, 13, f"{group_total:,.2f}", num_format)
                            row += 1
                            group_total = 0.0
                        sheet.merge_range(row, 0, row, 15, current_group or 'No Nationality', header_merge_format3)
                        nation_sort.add(current_group)
                        row += 1
                        num = 1
                previous_group = current_group
        
            # Write employee header
            sheet.merge_range(row, 0, row, 15, current_employee.name or 'Unknown Employee', header_merge_format3)
            row += 1
            num = 1
        
            if wizard.group_by_transaction:
                # Group records by transaction type
                transaction_groups = {}
                for record in emp_records:
                    trans_type = record.hr_transaction_id.description
                    if trans_type not in transaction_groups:
                        transaction_groups[trans_type] = []
                    transaction_groups[trans_type].append(record)
        
                # Process each transaction type in order
                for trans_type in transaction_types:
                    if trans_type not in transaction_groups:
                        continue  # Skip if no transactions of this type
                    transaction_records = sorted(transaction_groups[trans_type], key=lambda s: s.date)
                    transaction_total = 0.0
        
                    # Write transaction type header
                    sheet.merge_range(row, 0, row, 15, trans_type, header_merge_format3)
                    row += 1
                    num = 1
        
                    # Write transaction records
                    for payroll in transaction_records:
                        col = 0
                        sheet.write(row, col, num, name_format)
                        col += 1
                        sheet.write(row, col, payroll.employee_id.employee_no or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.employee_id.name or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.employee_id.department_id.name or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.employee_id.job_id.name or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.employee_id.country_of_birth.name or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.employee_id.work_location_id.name or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.name or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.date.strftime("%d-%m-%Y") or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.code or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.transaction_type_id.name or ' ', name_format)
                        col += 1
                        sheet.write(row, col, payroll.hr_transaction_id.description or ' ', name_format)
                        col += 1
                        units_display_name = dict(payroll._fields['units'].selection).get(payroll.units)
                        if payroll.units == 'days':
                            sheet.write(row, col, f"{round(payroll.days, 2)}/{units_display_name}" or ' ', num_format)
                        elif payroll.units == 'hours':
                            sheet.write(row, col, f"{round(payroll.hours, 2)}/{units_display_name}" or ' ', num_format)
                        else:
                            sheet.write(row, col, ' ', num_format)
                        col += 1
                        display_amount = float_round(payroll.amount, 2)
                        sheet.write(row, col, display_amount or ' ', num_format)
                        col += 1
                        grand_total += display_amount
                        group_total += display_amount
                        employee_total += display_amount
                        transaction_total += display_amount
                        sheet.write(row, col, payroll.reason or ' ', name_format)
                        col += 1
                        state_display_name = dict(payroll._fields['state'].selection).get(payroll.state)
                        sheet.write(row, col, state_display_name or ' ', name_format)
        
                        excel_list.append(payroll.employee_id.display_name)
                        row += 1
                        num += 1
        
                    # Write transaction type subtotal
                    sheet.merge_range(row,0,row, 12, f'{trans_type} Subtotal', header_num_format)
                    sheet.write(row, 13, f"{transaction_total:,.2f}", total_num_format)
                    row += 1
            else:
                # Write transactions without grouping by transaction type
                transaction_records = sorted(emp_records, key=lambda s: s.date)
                for payroll in transaction_records:
                    col = 0
                    sheet.write(row, col, num, name_format)
                    col += 1
                    sheet.write(row, col, payroll.employee_id.employee_no or ' ', name_format)
                    col += 1
                    sheet.write(row, col, payroll.employee_id.name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, payroll.employee_id.department_id.name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, payroll.employee_id.job_id.name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, payroll.employee_id.country_of_birth.name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, payroll.employee_id.work_location_id.name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, payroll.name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, payroll.date.strftime("%d-%m-%Y") or ' ', name_format)
                    col += 1
                    sheet.write(row, col, payroll.code or ' ', name_format)
                    col += 1
                    sheet.write(row, col, payroll.transaction_type_id.name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, payroll.hr_transaction_id.description or ' ', name_format)
                    col += 1
                    units_display_name = dict(payroll._fields['units'].selection).get(payroll.units)
                    if payroll.units == 'days':
                        sheet.write(row, col, f"{round(payroll.days, 2)}/{units_display_name}" or ' ', num_format)
                    elif payroll.units == 'hours':
                        sheet.write(row, col, f"{round(payroll.hours, 2)}/{units_display_name}" or ' ', num_format)
                    else:
                        sheet.write(row, col, ' ', num_format)
                    col += 1
                    display_amount = float_round(payroll.amount, 2)
                    sheet.write(row, col, display_amount or ' ', num_format)
                    col += 1
                    grand_total += display_amount
                    group_total += display_amount
                    employee_total += display_amount
                    sheet.write(row, col, payroll.reason or ' ', name_format)
                    col += 1
                    state_display_name = dict(payroll._fields['state'].selection).get(payroll.state)
                    sheet.write(row, col, state_display_name or ' ', name_format)
        
                    excel_list.append(payroll.employee_id.display_name)
                    row += 1
                    num += 1
        
            # Write employee total
            sheet.merge_range(row,0,row,12, 'Employee Total', header_num_format)
            sheet.write(row, 13, f"{employee_total:,.2f}", total_num_format)
            row += 1
        
        # Write final group total if sorting is applied
        if wizard.sort_by:
            if wizard.sort_by == 'department' and previous_group is not None:
                sheet.write(row, 12, 'Department Total', header_num_format)
                sheet.write(row, 13, f"{group_total:,.2f}", total_num_format)
                row += 1
            elif wizard.sort_by == 'job_title' and previous_group is not None:
                sheet.write(row, 12, 'Job Total', header_num_format)
                sheet.write(row, 13, f"{group_total:,.2f}", total_num_format)
                row += 1
            elif wizard.sort_by == 'branch_location' and previous_group is not None:
                sheet.write(row, 12, 'Branch Total', header_num_format)
                sheet.write(row, 13, f"{group_total:,.2f}", total_num_format)
                row += 1
            elif wizard.sort_by == 'nationality' and previous_group is not None:
                sheet.write(row, 12, 'National Wise Total', header_num_format)
                sheet.write(row, 13, f"{grand_total:,.2f}", total_num_format)
                row += 1        
        
        # Write grand total
        sheet.merge_range(row, 0, row, 12, 'Grand Total', header_num_format)
        sheet.write(row, 13, f"{grand_total:,.2f}", total_num_format)
        row += 1
        
        if not excel_list:
            raise UserError("No data found for the selected Employees and date range.") 
        ''' 
         
         
                                
        # currently working usual one group_by traansaction is not shown
        # domain = []
        #
        # domain += [('employee_id', 'in',
        #             wizard.employee_ids.ids if wizard.employee_ids else self.env['hr.employee'].search([]).ids)]
        #
        # if wizard.from_date and wizard.to_date:
        #     domain += [('date', '>=', wizard.from_date), ('date', '<=', wizard.to_date)]
        #
        # if wizard.department_ids:
        #     domain += [('employee_id.department_id', 'in', wizard.department_ids.ids)]
        #     sheet.merge_range(5, 0, 5, 15, "Department Wise Search", header_merge_format)
        #
        # if wizard.job_title_ids:
        #     domain += [('employee_id.job_id', 'in', wizard.job_title_ids.ids)]
        #     sheet.merge_range(5, 0, 5, 15, "Job Wise Search", header_merge_format)
        #
        # if wizard.nationality_ids:
        #     domain += [('employee_id.country_of_birth', 'in', wizard.nationality_ids.ids)]
        #     sheet.merge_range(5, 0, 5, 15, "Nation Wise Search", header_merge_format)
        #
        # if wizard.branch_location_ids:
        #     domain += [('employee_id.work_location_id', 'in', wizard.branch_location_ids.ids)]
        #     sheet.merge_range(5, 0, 5, 15, "Branch Location Wise Search", header_merge_format)
        #
        # excel_list = []
        # from_date = False
        # to_date = False
        # employee_ids = False
        # if wizard.employee_ids:
        #     employee_ids = wizard.employee_ids
        # else:
        #     employee_ids = self.env['hr.employee'].search([])
        #
        #
        # # for employees in employee_ids:
        #     # employee_search = self.env['salary.allowance.detection'].search([('employee_id', '=', employees.id),('date', '>=', wizard.from_date),('date', '<=', wizard.to_date)])
        # employee_search = self.env['salary.allowance.detection'].search(domain)
        #
        # employee_search = employee_search.sorted(key=lambda s: s.employee_id.name.lower())
        # employee_search = employee_search.sorted(key=lambda d: d.date)
        #
        #
        #
        # if wizard.sort_by:
        #     if wizard.sort_by == 'department':
        #         employee_search = employee_search.filtered(lambda s: s.employee_id.department_id)
        #         employee_search = employee_search.sorted(key=lambda s: s.employee_id.department_id.name.lower())
        #         sheet.merge_range(5, 0, 5, 15, "Department Wise Sort", header_merge_format)
        #
        #     elif wizard.sort_by == 'job_title':
        #         employee_search = employee_search.filtered(lambda s: s.employee_id.job_id)
        #         employee_search = employee_search.sorted(key=lambda s: s.employee_id.job_id.name.lower())
        #         sheet.merge_range(5, 0, 5, 15, "Job Wise Sort", header_merge_format)
        #
        #
        #     elif wizard.sort_by == 'branch_location':
        #         employee_search = employee_search.filtered(lambda s: s.employee_id.work_location_id)
        #         employee_search = employee_search.sorted(key=lambda s: s.employee_id.work_location_id.name.lower())
        #         sheet.merge_range(5, 0, 5, 15, "Branch Location Wise Sort", header_merge_format)
        #
        #
        #     elif wizard.sort_by == 'nationality':
        #         employee_search = employee_search.filtered(lambda s: s.employee_id.country_of_birth)
        #         employee_search = employee_search.sorted(key=lambda s: s.employee_id.country_of_birth.name.lower())
        #         sheet.merge_range(5, 0, 5, 15, "Nation Wise Sort", header_merge_format)
        #
        #     elif wizard.sort_by == 'employee_no':
        #         employee_search = employee_search.sorted(key = lambda s: (
        #             0 if s.employee_id.employee_no and isinstance(s.employee_id.employee_no,str) and s.employee_id.employee_no.isdigit() else 1,
        #             int(s.employee_id.employee_no) if s.employee_id.employee_no and isinstance(s.employee_id.employee_no,str) and s.employee_id.employee_no.isdigit() else s.employee_id.employee_no or ''
        #             ))
        #         sheet.merge_range(5, 0, 5, 15, "Employee Number Wise Sort", header_merge_format)
        #
        # if wizard.group_by_transaction:
        #     employee_search = employee_search.filtered(lambda s :s.hr_transaction_id)
        #
        # if wizard.department_ids:
        #     employee_search = employee_search.sorted(key=lambda c: c.employee_id.department_id.name.lower())
        #
        # if wizard.job_title_ids:
        #     employee_search = employee_search.sorted(key=lambda c: c.employee_id.job_id.name.lower())
        #
        # if wizard.nationality_ids:
        #     employee_search = employee_search.sorted(key=lambda c: c.employee_id.country_of_birth.name.lower())
        #
        # if wizard.branch_location_ids:
        #     employee_search = employee_search.sorted(key=lambda c: c.employee_id.work_location_id.name.lower())
        #
        # num = 1
        # department_sort = set()
        # job_sort = set()
        # nation_sort = set()
        # location_sort = set()
        # transaction_entry = set()
        # grand_total = 0.0
        # group_total = 0.0
        # grand_group_total = 0.0
        # previous_dept_group = None
        # previous_job_group = None
        # previous_nation_group = None
        # previous_branch_group = None
        # previous_transaction_entry = None
        # current_employee = None
        # current_transaction = None
        # employee_total = 0.0
        # transaction_total = 0.0
        # previous_employee =None
        # previous_transaction = None
        #
        #
        # for payroll in employee_search:
        #     current_transaction_entry = payroll.hr_transaction_id.description
        #     current_employee = payroll.employee_id
        #     current_transaction = payroll.hr_transaction_id.description
        #     current_group = None
        #
        #     if wizard.sort_by:
        #         current_dept_group = payroll.employee_id.department_id.complete_name
        #         current_job_group = payroll.employee_id.job_id.name
        #         current_nation_group = payroll.employee_id.country_of_birth.name
        #         current_branch_group = payroll.employee_id.work_location_id.name
        #
        #         if wizard.sort_by == 'department' and payroll.employee_id.department_id.complete_name not in department_sort:
        #             if previous_dept_group != current_dept_group and previous_dept_group is not None:
        #                 sheet.write(row,12,'Department Total',header_merge_format3)
        #                 col = 13
        #                 sheet.write(row,col,group_total,num_format)
        #                 group_total = 0.0
        #
        #                 row += 1
        #             previous_dept_group = current_dept_group
        #
        #         elif wizard.sort_by == 'job_title' and payroll.employee_id.job_id.name not in job_sort:
        #             if previous_job_group != current_job_group and previous_job_group is not None:
        #                 sheet.write(row, 12, 'Job wise Total',header_merge_format3)
        #                 col = 13
        #                 sheet.write(row, col, group_total ,num_format)
        #                 group_total = 0.0
        #                 row += 1
        #             previous_job_group = current_job_group 
        #
        #         elif wizard.sort_by == 'branch_location' and payroll.employee_id.work_location_id.name not in branch_sort:
        #             if previous_branch_group != current_job_group and previous_job_group is not None:
        #                 sheet.write(row,12, 'Branch wise Total',header_merge_format3)
        #                 col = 13
        #                 sheet.write(row, col, group_total,num_format)
        #                 group_total  = 0.0
        #                 row += 1
        #             previous_branch_group = current_branch_group
        #
        #         elif wizard.sort_by == 'nationality' and payroll.employee_id.country_of_birth.name not in nation_sort:
        #             if previous_nation_group != current_nation_group and previous_job_group is not None:
        #                 sheet.write(row,12, 'nation wise Total',header_merge_format3)
        #                 col = 13
        #                 sheet.write(row, col, group_total,num_format)
        #                 group_total  = 0.0
        #                 row += 1
        #             previous_nation_group = current_nation_group    
        #
        #     if current_employee != previous_employee and previous_employee is not None:
        #         # Write transaction total for previous transaction
        #         if current_transaction != previous_transaction:
        #             sheet.write(row, 12, f'{previous_transaction} Subtotal', header_merge_format3)
        #             sheet.write(row, 13, transaction_total, num_format)
        #             row += 1
        #             transaction_total = 0.0
        #         # Write employee total
        #         sheet.write(row, 12, 'Employee Total', header_merge_format3)
        #         sheet.write(row, 13, employee_total, num_format)
        #         row += 1
        #         employee_total = 0.0
        #         num = 1
        #         # Write employee header
        #         sheet.merge_range(row, 0, row, 14, current_employee.name, header_merge_format3)
        #         row += 1
        #
        #     # Handle transaction type header
        #     if current_transaction != previous_transaction or current_employee != previous_employee:
        #         if previous_transaction is not None and current_employee == previous_employee:
        #             sheet.write(row, 12, f'{previous_transaction} Subtotal', header_merge_format3)
        #             sheet.write(row, 13, transaction_total, num_format)
        #             row += 1
        #             transaction_total = 0.0
        #         sheet.merge_range(row, 0, row, 14, current_transaction or 'No Transaction', header_merge_format3)
        #         row += 1
        #         num = 1
        #     # if wizard.group_by_transaction and payroll.hr_transaction_id.description not in transaction_entry:
        #     #     if previous_transaction_entry != current_transaction_entry  and previous_transaction_entry is not None:
        #     #         sheet.write(row,12,'Sub Total',header_merge_format3)
        #     #         col =13
        #     #         sheet.write(row,col , group_total,num_format)
        #     #         group_total = 0.0
        #     #         row += 1
        #     #     previous_transaction_entry = current_transaction_entry     
        #     #
        #     # if wizard.group_by_transaction and payroll.hr_transaction_id.description not in transaction_entry:
        #     #     sheet.merge_range(row, 0, row, 14, payroll.hr_transaction_id.description,header_merge_format3)
        #     #     transaction_entry.add(payroll.hr_transaction_id.description)
        #     #     row +=1
        #     #     num = 1      
        #     if wizard.sort_by == 'department' and payroll.department.name not in department_sort:
        #         sheet.merge_range(row, 0, row, 14, payroll.department.name, header_merge_format3)
        #         department_sort.add(payroll.department.name)
        #         row += 1
        #         num = 1
        #     elif wizard.sort_by == 'job_title' and payroll.employee_id.job_id.name not in job_sort:
        #         sheet.merge_range(row, 0, row, 14, payroll.employee_id.job_id.name, header_merge_format3)
        #         job_sort.add(payroll.employee_id.job_id.name)
        #         row += 1
        #         num = 1
        #
        #     elif wizard.sort_by == 'branch_location' and payroll.employee_id.work_location_id.name not in location_sort:
        #         sheet.merge_range(row, 0, row, 14, payroll.employee_id.work_location_id.name, header_merge_format3)
        #         location_sort.add(payroll.employee_id.work_location_id.name)
        #         row += 1
        #         num = 1
        #
        #     elif wizard.sort_by == 'nationality' and payroll.employee_id.country_of_birth.name not in nation_sort:
        #         sheet.merge_range(row, 0, row, 14, payroll.employee_id.country_of_birth.name, header_merge_format3)
        #         nation_sort.add(payroll.employee_id.country_of_birth.name)
        #         row += 1
        #         num = 1
        #
        #     if wizard.sort_by in ['department', 'job_title', 'nationality', 'branch_location'] or wizard.group_by_transaction:
        #         col = 0
        #         sheet.write(row, col, num, name_format)
        #     else:
        #         col = 0
        #         sheet.write(row, col, no, name_format)
        #     # col = 0
        #     # sheet.write(row, col, no, num_format)
        #     col += 1
        #     sheet.write(row, col, payroll.employee_id.employee_no or ' ', name_format)
        #     col += 1
        #     sheet.write(row, col, payroll.employee_id.name or ' ', name_format)
        #     col += 1
        #
        #     sheet.write(row, col, payroll.department.name or ' ', name_format)
        #     col += 1
        #
        #     sheet.write(row, col, payroll.employee_id.job_title or ' ', name_format)
        #     col += 1
        #
        #     sheet.write(row, col, payroll.employee_id.country_of_birth.name or ' ', name_format)
        #     col += 1
        #
        #     sheet.write(row, col, payroll.employee_id.work_location_id.name or ' ', name_format)
        #     col += 1
        #     sheet.write(row, col, payroll.name or ' ', name_format)
        #     col += 1
        #     sheet.write(row, col, payroll.date.strftime("%d-%m-%Y") or ' ', name_format)
        #     col += 1
        #     sheet.write(row, col, payroll.code or ' ', name_format)
        #     col += 1
        #     sheet.write(row, col, payroll.transaction_type_id.name or ' ', name_format)
        #     col += 1
        #     sheet.write(row,col,payroll.hr_transaction_id.description or '',name_format)
        #     col += 1
        #     units_display_name = dict(payroll._fields['units'].selection).get(
        #         payroll.units)
        #     if payroll.units == 'days':
        #         sheet.write(row, col, str(round(payroll.days,2)) + '/' + str(units_display_name) or ' ', num_format)
        #     elif payroll.units == 'hours':
        #         sheet.write(row, col, str(round(payroll.hours,2)) + '/' + str(units_display_name) or ' ', num_format)
        #
        #     # sheet.write(row, col, units_display_name or ' ', name_format)
        #
        #     col += 1
        #     display_amount = float_round(payroll.amount, 2)
        #     sheet.write(row, col, display_amount or ' ', num_format)
        #     col += 1
        #     grand_total += display_amount
        #     group_total += display_amount
        #     employee_total += display_amount
        #     transaction_total += display_amount
        #     sheet.write(row, col, payroll.reason or ' ', name_format)
        #     col += 1
        #     state_display_name = dict(payroll._fields['state'].selection).get(
        #         payroll.state)
        #     sheet.write(row, col, state_display_name or ' ', name_format)
        #     col += 1
        #
        #
        #     excel_list.append(payroll.employee_id.display_name)
        #
        #     row += 1
        #     no += 1
        #     num += 1
        #     previous_employee = current_employee
        #     previous_transaction = current_transaction
        #
        # # Write final totals
        # if previous_transaction is not None:
        #     sheet.write(row, 12, f'{previous_transaction} Subtotal', header_merge_format3)
        #     sheet.write(row, 13, transaction_total, num_format)
        #     row += 1
        #
        # if previous_employee is not None:
        #     sheet.write(row, 12, 'Employee Total', header_merge_format3)
        #     sheet.write(row, 13, employee_total, num_format)
        #     row += 1
        #
        #
        # if wizard.sort_by:
        #     if previous_dept_group is not None:
        #         sheet.write(row, 12,'Department Total',header_merge_format)
        #         col = 13
        #         sheet.write(row,col,group_total,num_format)
        #         row += 1
        #     elif previous_job_group is not None:
        #         sheet.write(row,12, 'Job Total',header_merge_format)
        #         col =13
        #         sheet.write(row, col, group_total, num_format)
        #         row +=1
        #     elif previous_branch_group is not None:
        #         sheet.write(row, 12 , 'Branch Total',header_merge_format)
        #         col = 13
        #         sheet.write(row, col , group_total, num_format)
        #         row +=1
        #
        #     elif previous_nation_group is not None:
        #         sheet.write(row, 12, 'Nation total',header_merge_format)
        #         col =13
        #         sheet.write(row, col, group_total,num_format)
        #         row +=1
        # if wizard.group_by_transaction:
        #     if previous_transaction_entry is not None:
        #         sheet.write(row, 12, 'Sub Total',header_merge_format)
        #         col = 13
        #         sheet.write(row,col,group_total, num_format)
        #         row += 1         
        #
        # row+=1
        # col = 12
        # sheet.merge_range(row,0,row,col,'Total',header_merge_format)
        # col+=1
        # sheet.write(row,col,grand_total,num_format)
        #
        #
        # if  len(excel_list) == 0:
        #     raise UserError("No data found for the selected Employees and date range.")
        #
        #


        
        
        
        
        
        
