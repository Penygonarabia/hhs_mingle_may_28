from odoo import fields, models, api, registry, _
import xlsxwriter
import io
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, time 

class AttendanceLeaveRegisterReportExcel(models.AbstractModel):
    
    _name = "report.bi_hr_attendance_leave_report.report_register_leave"
    
    _inherit ="report.report_xlsx.abstract"
    
    _description ="Attendance Register Report Excel"
    
    
    
    def generate_xlsx_report(self, workbook, data, wizard):
        
        
        header_merge_format = workbook.add_format({'bold':True , 'align':'center', 
                                                    'font_size':10, 'bg_color':'#D3D3D3', 'border':1})
        
        header_data_format = workbook.add_format({'align': 'right',  'font_size':10,  'border': 1})
        
        name_format_one = workbook.add_format({'align': 'left', 'font_size':10,  'border': 1})
        
        number_format = workbook.add_format({'align':'right', 'font_size':10, 'border': 1})
        
        
        header_utilised_format = workbook.add_format({'align':'right','font_size':10, 'border': 1, 'font_color':'red' })
        
        header_allocated_format = workbook.add_format({'align':'right','font_size':10,'border':1, 'font_color':'green'})
        
        holiday_remaining_format = workbook.add_format({'align':'right', 'font_size':10,'border':1, 'font_color':'brown'})
        

        
        sheet = workbook.add_worksheet("Employee Leave Register")
        
        sheet.set_row(0, 25)
        
        sheet.merge_range(0, 0, 1, 25, 'Employee Leave Register',header_merge_format )
        
        sheet.merge_range(2,0,2,1,'Start Date',header_merge_format)
        sheet.merge_range(2,2,2,3 ,wizard.start_date.strftime("%d-%m-%Y"),header_merge_format)
        sheet.merge_range(2,4,2,5,'End Date',header_merge_format)
        sheet.merge_range(2,6,2,7, wizard.end_date.strftime("%d-%m-%Y"), header_merge_format)
        
  
        sheet.set_column(0, 0, 3)
        sheet.set_column(1, 1, 5)
        sheet.set_column(2, 2, 18)
        sheet.set_column(3, 3, 18)
        sheet.set_column(4, 4, 12)
        sheet.set_column(5, 5, 3)
        for col in range(6, 40): 
            sheet.set_column(col, col, 5)
        
      

        # Headers for the table
        sheet.write(4, 0, 'S.no', header_merge_format)
        sheet.write(4, 1, 'Employee Code', header_merge_format)
        sheet.write(4, 2, 'Employee Name', header_merge_format)
        sheet.write(4, 3, 'Department', header_merge_format)
        sheet.write(4, 4, 'Designation', header_merge_format)
        sheet.write(4, 5, 'G', header_merge_format)
        # sheet.write(4, 6, 'Dates', header_merge_format)
        
        leave_types = self.env['hr.leave.type'].search([])
        max_leave_types = 10  # Adjust this to set a maximum limit if needed
        desired_number_of_leave_types = min(len(leave_types), max_leave_types)
        
        # Adjust the number of leave types displayed if there are more than the desired number
        leave_types = leave_types[:desired_number_of_leave_types]
    
        # Step 1: Create common headers for "Allocated", "Used", and "Remaining" with subheaders for each leave type
        col = 6  # Start column for leave data
    
        # Write common "Allocated" header merged over all leave types
        allocated_col_start = col
        col += len(leave_types) - 1  # Move the column based on leave types count
        sheet.merge_range(4, allocated_col_start, 4, col, 'Allocated', header_merge_format)
        
        # Subheaders for each leave type under "Allocated"
        col = 6
        for leave_type in leave_types:
            two_letter = ''.join([leave[0].upper() for leave in leave_type.name.split()])
            sheet.write(5, col, two_letter[:2], header_merge_format)
            col += 1
    
        # Write common "Used" header merged over all leave types
        used_col_start = col
        col += len(leave_types) - 1  # Move the column based on leave types count
        sheet.merge_range(4, used_col_start, 4, col, 'Utilised', header_merge_format)
        
        # Subheaders for each leave type under "Used"
        col = used_col_start
        for leave_type in leave_types:
            two_letter = ''.join([leave[0].upper() for leave in leave_type.name.split()])
            sheet.write(5, col, two_letter[:2], header_merge_format)
            col += 1
    
        # Write common "Remaining" header merged over all leave types
        remaining_col_start = col
        col += len(leave_types) - 1  # Move the column based on leave types count
        sheet.merge_range(4, remaining_col_start, 4, col, 'Remaining', header_merge_format)
        
        # Subheaders for each leave type under "Remaining"
        col = remaining_col_start
        for leave_type in leave_types:
            first_two_letter = ''.join([leave[0].upper() for leave in leave_type.name.split()])
            sheet.write(5, col, first_two_letter[:2], header_merge_format)
            col += 1
    
        # Set column sizes for employee details
        # sheet.set_column(1, 1, 10)
        # sheet.set_column(2, 2, 15)
        # sheet.set_column(3, 3, 15)
        # sheet.set_column(4, 4, 12)
        # sheet.set_column(5, 5, 13)
        #
        # # Set column size for leave types
        # sheet.set_column(6, col - 1, 10)
    
        # Filter employees based on wizard inputs
        domain = [('id', 'in', wizard.employee_ids.ids if wizard.employee_ids else self.env['hr.employee'].search([]).ids)]
        if wizard.dept_id:
            domain += [('department_id', 'in', wizard.dept_id.ids)]
    
        employees = self.env['hr.employee'].search(domain, order='employee_no asc')
    
        row = 6  # Start row for employee data
        for no, employee in enumerate(employees, start=1):
            col = 0
            # Basic employee information
            sheet.write(row, col, no, header_data_format)
            sheet.write(row, col + 1, employee.employee_no or '', name_format_one)
            sheet.write(row, col + 2, employee.name, name_format_one)
            sheet.write(row, col + 3, employee.department_id.name, name_format_one)
            sheet.write(row, col + 4, employee.job_id.name or '', name_format_one)
            sheet.write(row, col + 5, employee.gender.upper()[0] if employee.gender else '', name_format_one)
    
            # Fetch leave data
            leave_allocations = self.env['hr.leave.allocation'].search([('employee_id', '=', employee.id), ('state', '=', 'validate')])
            leaves_taken = self.env['hr.leave'].search([('employee_id', '=', employee.id), ('state', '=', 'validate') ,
                                                        ('request_date_from','>=',wizard.start_date),('request_date_to','<=',wizard.end_date)])
    
            # Step 2: Write Allocated Leave data for each leave type
            col = 6  # Reset column to leave data section
            for leave_type in leave_types:
                allocated_leaves = sum(allocation.number_of_days for allocation in leave_allocations if allocation.holiday_status_id == leave_type)
                sheet.write(row, col, allocated_leaves or 0.0, header_allocated_format)
                col += 1
    
            # Step 3: Write Used Leave data for each leave type
            for leave_type in leave_types:
                used_leaves = sum(leave.number_of_days for leave in leaves_taken if leave.holiday_status_id == leave_type)
                sheet.write(row, col, used_leaves or 0.0, header_utilised_format)
                col += 1
    
            # Step 4: Write Remaining Leave data for each leave type
            for leave_type in leave_types:
                allocated_leaves = sum(allocation.number_of_days for allocation in leave_allocations if allocation.holiday_status_id == leave_type)
                used_leaves = sum(leave.number_of_days for leave in leaves_taken if leave.holiday_status_id == leave_type)
                remaining_leaves = allocated_leaves - used_leaves
                sheet.write(row, col, abs(remaining_leaves) or 0.0, holiday_remaining_format)
                col += 1
    
            row += 1  # Move to the next row for the next employee
    
            
    
        
        
        
        
        
        
        
        