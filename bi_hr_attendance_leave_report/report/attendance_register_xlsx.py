from odoo import fields, models, api, registry, _
import xlsxwriter
import io
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, time 

class AttendanceRegisterReportExcel(models.AbstractModel):
    
    _name = "report.bi_hr_attendance_leave_report.report_employee_register"
    
    _inherit ="report.report_xlsx.abstract"
    
    _description ="Attendance Register Report Excel"
    
    
   
    
    '''Working correctly'''
    def generate_xlsx_report(self, workbook, data, wizard):
    
        top_header_merge_format = workbook.add_format({'bold':True, 'valign':'vcenter',
                                                      'align':'center', 
                                                    'font_size':14, 'bg_color':'#D3D3D3', 'border':1})
    
        header_merge_format = workbook.add_format({'bold':True , 'align':'center', 
                                                    'font_size':10, 'bg_color':'#D3D3D3', 'border':1})
    
        header_data_format = workbook.add_format({'align': 'right',  'font_size':10,  'border': 1})
    
        header_leave_format = workbook.add_format({'align':'center','font_size':10, 'border': 1, 'bg_color':'#ff0000' ,'font_color':'white' })
    
        header_holiday_format = workbook.add_format({'align':'center','font_size':10,'border':1, 'bg_color':'#FFBF00' ,'font_color':'black'})
    
        holiday_absent_format = workbook.add_format({'align':'center', 'font_size':10,'border':1, 'bg_color':'#E1C16E' , 'font_color':'black'})
    
    
        header_present_format = workbook.add_format({'align':'center','font_size':10,'border':1, 'bg_color':'#008000' , 'font_color':'black'})
    
        weekend_holiday_format = workbook.add_format({'align':'center','font_size': 10, 'border': 1, 'bg_color':'##FFA500', 'font_color':'black'})
    
        annual_vacation_format = workbook.add_format({'align':'center', 'font_size': 10, 'border': 1, 'bg_color':'#0000FF' ,'font_color':'white' })
    
        name_format_one = workbook.add_format({'align': 'left', 'font_size':10,  'border': 1})
    
        number_format = workbook.add_format({'align':'right', 'font_size':10, 'border': 1})
        
        termination_format = workbook.add_format({'align':'center', 'font_size':10, 'border':1,'bg_color':'#6E260E' ,'font_color':'white'})
        
        sheet = workbook.add_worksheet("Employee Attendance Report")
    
        sheet.set_row(0, 25)
    
    
        sheet.merge_range(2,0,2,1,'Start Date',header_merge_format)
        sheet.write(2,2 ,wizard.start_date.strftime("%d-%m-%Y"),header_merge_format)
        sheet.write(2,3,'End Date',header_merge_format)
        sheet.write(2,4, wizard.end_date.strftime("%d-%m-%Y"), header_merge_format)
    
    
        sheet.write(4, 0, 'S.no', header_merge_format)
    
        sheet.write(4, 1, 'Employee Code', header_merge_format)
        sheet.write(4, 2, 'Employee Name' , header_merge_format)
        sheet.write(4, 3, 'Department', header_merge_format)
        sheet.write(4, 4, 'Designation', header_merge_format)
        sheet.write(4, 5, 'G', header_merge_format )
    
    
        sheet.write(2, 6, 'HO', header_holiday_format)
        sheet.merge_range(2, 7, 2, 8, 'Holiday',header_merge_format)
        sheet.write(2, 10, '✔',header_present_format)
        sheet.merge_range(2,11,2,12,'Present',header_merge_format)
        sheet.write(2, 14, 'LC', header_leave_format)
        sheet.merge_range(2,15,2,17,'Leave Code',header_merge_format)
        sheet.write(2, 19, 'AB', holiday_absent_format)
        sheet.merge_range(2,20,2,21,'Absent',header_merge_format)
        sheet.write(2, 23, 'WK', header_holiday_format)
        sheet.merge_range(2,24,2,25,'Weekend',header_merge_format) 
        sheet.write(2, 27, 'AV', annual_vacation_format)
        sheet.merge_range(2, 28, 2, 30,'Annual Vacation', header_merge_format) 
        sheet.write(2, 32, 'T', termination_format)
        sheet.merge_range(2,33,2,35,'Termination',header_merge_format)
    
    
        leave_type_code = self.env['hr.leave.type'].search([])  
        col = 3 
        for leave in leave_type_code: 
            if leave.code != 'AV':           
                sheet.write(3, col, leave.code, header_leave_format)            
                sheet.merge_range(3, col + 1, 3, col + 3, leave.name, header_merge_format)           
                col += 4
    
    
        sheet.set_column(0, 0, 3)
        sheet.set_column(1, 1, 5)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 15)
        sheet.set_column(4, 4, 12)
        sheet.set_column(5, 5, 3)
        for col in range(6, 40): 
            sheet.set_column(col, col, 4)
    
    
    
        start_date = wizard.start_date
        end_date = wizard.end_date
    
        no_of_days = (end_date - start_date).days
    
        sheet.merge_range(0, 0, 1, (0+6+no_of_days), 'Employee Attendance Report',top_header_merge_format )
    
        sheet.merge_range(4, 6, 4, (6 + no_of_days), 'Dates', header_merge_format)
    
        # for i in range(0,no_of_days+1):
        #     i += 1
        #     sheet.write(row, col, i, header_merge_format)
        #     col += 1
    
        col = 6
        for i in range(0, no_of_days + 1):
            sheet.write(5, col, (start_date + timedelta(days=i)).strftime("%d"), header_merge_format)
            # sheet.write(5, col, (start_date + timedelta(days=i)).strftime("%d-%m-%Y"), header_merge_format)
            col += 1   
    
    
        domain = []
        domain = [('id', 'in', wizard.employee_ids.ids if wizard.employee_ids else self.env['hr.employee'].search([]).ids),
                    '|',  # This ensures either the employee has no exit date or their exit date is after the report start date.
                    ('exit_date', '=', False),
                    ('exit_date', '>=', wizard.start_date)]
    
        if wizard.dept_ids:
            domain += [('department_id', 'in', wizard.dept_ids.ids)]
            
        domain += [('contract_warning','=',False)] 
        
        employees = self.env['hr.employee'].search(domain, order='employee_no asc')
        
    
        public_holiday = self.env['resource.calendar.leaves'].search([
            # ('calendar_id', '=', employee.resource_calendar_id.id),  
            # ('date_from', '<=', current_day_end),
            # ('date_to', '>=', current_day_start),
            ('resource_id', '=', False)  # Assuming it's a public holiday
        ])
    
        holiday_dates = []  # List to store all dates within the range
    
        for holiday in public_holiday:
    
            holiday_start = max(holiday.date_from.date(), wizard.start_date)
            holiday_end = min(holiday.date_to.date(), wizard.end_date)
    
            # Check if holiday_start <= holiday_end
            if holiday_start <= holiday_end:
                # Iterate over each day between holiday_start and holiday_end
                current_date = holiday_start
                while current_date <= holiday_end:
                    holiday_dates.append(current_date)  # Append the date to the list
                    current_date += timedelta(days=1)  # Move to the next day
    
    
    
        row = 6
        for no, employee in enumerate(employees, start=1):
            col = 0
            sheet.write(row, col, no, header_data_format) 
            sheet.write(row, col + 1, employee.employee_no or '',name_format_one)
            sheet.write(row, col + 2, employee.name, name_format_one)   
            sheet.write(row, col + 3, employee.department_id.name, name_format_one)  
            sheet.write(row, col + 4, employee.job_id.name or '', name_format_one)  
            sheet.write(row, col + 5, employee.gender.upper()[0] if employee.gender else '', name_format_one)  
    
            col = 6
            for day in range(no_of_days + 1):
                current_day = start_date + timedelta(days=day)
    
                current_day_start = datetime.combine(current_day, time.min)
                current_day_end = datetime.combine(current_day, time.max)
                
                if employee.exit_date and current_day >= employee.exit_date:
                    sheet.write(row, col, 'T', termination_format)
                
                else:
    
                    non_working_day = not self.env['resource.calendar.attendance'].search([
                        ('calendar_id', '=', employee.resource_calendar_id.id),  
                        ('dayofweek', '=', str(current_day.weekday())),  
                    ])
        
                    # public_holiday = self.env['resource.calendar.leaves'].search([
                    #     # ('calendar_id', '=', employee.resource_calendar_id.id),  
                    #     # ('date_from', '<=', current_day_end),
                    #     # ('date_to', '>=', current_day_start),
                    #     ('resource_id', '=', False) 
                    # ])
                    #
                    # for holiday in public_holiday:
                    #     if holiday.date_from.date() == current_day:
                    #         sheet.write(row, col, 'HO', header_holiday_format)
        
                    if non_working_day:
                        sheet.write(row, col, 'WK', header_holiday_format)
        
        
                    else:    
        
                        attendance = self.env['hr.attendance'].search([
                            ('employee_id', '=', employee.id),
                            ('check_in', '>=', current_day),
                            ('check_in', '<', current_day + timedelta(days=1))
                        ])
        
                        if attendance:
                            sheet.write(row, col, '✔', header_present_format)
                        else:
                            leave = self.env['hr.leave'].search(
                                [('employee_id', '=', employee.id),
                                 ('state', '=', 'validate'),
                                 ('request_date_from', '<=', current_day),
                                 ('request_date_to', '>=', current_day)
                                 ])
                            if leave:
                                if leave.holiday_status_id.code == 'AV':
                                    sheet.write(row, col, 'AV', annual_vacation_format)
                                else:    
                                    sheet.write(row, col, leave.holiday_status_id.code  or False, header_leave_format)
        
                            else:
                                sheet.write(row, col, 'AB', holiday_absent_format)
        
        
                    for current_day_check in holiday_dates:
                        if current_day == current_day_check:
                            sheet.write(row, col, 'HO', header_holiday_format)
    
                col += 1
    
            row += 1
    

        # domain += [('id', 'in', wizard.employee_ids.ids if wizard.employee_ids else self.env['hr.employee'].search([]).ids)]
        #
        # if wizard.employee_ids :
        #
        #     domain += [('id' , 'in', wizard.employee_ids.ids)]
        #
        # else:
        #
        #     domain +=[('id','in' ,self.env['hr.employee'].search([]).ids)] 
        #
        # if wizard.start_date:
        #
        #     domain += [('check_in','>=', wizard.start_date)]
        #
        # if wizard.end_date:
        #
        #     domain +=[('check_in','<=', wizard.end_date)] 
        #
        #
        # if wizard.dept_ids :
        #
        #      domain +=[('employee_id.department_id', 'in',wizard.dept_ids.ids)]   
        #
        #
        # print("......domain",domain)
        # attendance_search = self.env['hr.attendance'].search(domain)
        #
        #
        # row = 6
        # no = 1
        # for attendance in attendance_search:
        #     print("........atendance",attendance)
        
        #     col = 0 
        #     sheet.write (row, col, no, name_format_one )
        #     col +=1
        #     sheet.write(row, col, attendance.employee_id.department_id.name or ' ', name_format_one)
        #     col += 1
        #     sheet.write(row, col, attendance.employee_id.name or ' ', name_format_one)
        #     col += 1
        #     sheet.write(row, col, attendance.employee_id.job_title or ' ', name_format_one)
        #     col += 1
        #
        #     gender_display_name = dict(attendance.employee_id._fields['gender'].selection).get(
        #         attendance.employee_id.gender)
        #
        #     sheet.write(row, col, gender_display_name or ' ',name_format_one)
        #     col += 1 
            
            # no += 1
            # row += 1
            
            
             
            
               
        
        
        
        
        
        
        
        
        
    
    