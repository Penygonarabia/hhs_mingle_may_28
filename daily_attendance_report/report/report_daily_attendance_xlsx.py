from odoo import api , fields, models, _
from datetime import date, time, datetime, timedelta
import base64
import io
from odoo.exceptions import ValidationError


class DailyAttendnceReportExcel(models.AbstractModel):
    
    _name = "report.daily_attendance_report.report_daily_attendance_xlsx"
    
    _inherit = "report.report_xlsx.abstract"
    
    _description = "Daily Attendance Report Excel"
    
    
    def generate_xlsx_report(self, workbook, data, wizard):

        header_merge_format = workbook.add_format({'bold':True, 'align':'center', 'valign':'vcenter', \
                                            'font_size':10, 'bg_color':'#D3D3D3', 'border':1 })

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

        sheet = workbook.add_worksheet("Daily Attendance Report")
        sheet.set_row(0, 25)
        
        
        # sheet.merge_range(0, 0, 2, 14, "Daily Attendance Report" , header_merge_format)
        
        sheet.merge_range(4, 0, 4, 1, 'Company', header_merge_format)
        sheet.merge_range(4, 2, 4, 4, wizard.company_id.name, header_merge_format)
        
        sheet.merge_range(4, 5, 4, 6, 'From Date', header_merge_format)
        sheet.merge_range(4, 7, 4, 8, wizard.from_date.strftime("%d-%m-%Y"), header_merge_format)
        
        sheet.merge_range(4, 9, 4, 10, 'To Date', header_merge_format)
        sheet.merge_range(4, 11, 4, 12, wizard.to_date.strftime("%d-%m-%Y"), header_merge_format)
        
       
        
        if wizard.company_id.logo:
            logo_data = base64.b64decode(wizard.company_id.logo)
            logo_stream = io.BytesIO(logo_data)
            # sheet.set_column('P:Q', 15)  # Set width for columns P and Q
            if not wizard.summary_based_report:
                sheet.merge_range(0, 0, 2, 14, "Daily Attendance Report", header_merge_format)
            else:
                sheet.merge_range(0, 0, 2, 11, "Daily Attendance Report", header_merge_format)
                    
        
        # Insert the image inside the merged range (adjust scale for fit)
            sheet.insert_image('A1:B1', 'logo.png', {
                'image_data': logo_stream,
                'x_scale': 0.70,# Adjust scale to fit image within the merged cells
                'y_scale': 0.70, # Adjust scale as needed
                # 'x_offset': 0.20,  # Optional: fine-tune positioning horizontally
                # 'y_offset': 0.20    # Optional: fine-tune positioning vertically
            })
            # Insert the image into the specified cell range (P1:Q3)
            # sheet.insert_image('P1', 'logo.png', {
            #     'image_data': logo_stream,
            #     'x_scale': 0.1,  # Adjust scale for width
            #     'y_scale': 0.1   # Adjust scale for height
            # })
            
        row = 6
        col = 0
        
        if not wizard.summary_based_report:
            sheet.write(row, col , 'S.No',  header_merge_format)
            col += 1
            
            sheet.write(row, col, 'Employee No', header_merge_format)
            col += 1
            
            sheet.write(row, col, 'Employee Name', header_merge_format)
            col += 1
            sheet.set_column(2,2,20)
            
            sheet.write(row, col, 'Department' , header_merge_format)
            col += 1
            sheet.set_column(3,3,20)
            
            sheet.write(row, col, 'Date', header_merge_format )
            col += 1 
            sheet.set_column(4,4,10)
            
            sheet.write(row, col, 'Day', header_merge_format)
            col += 1
            sheet.set_column(5,5,8)
    
            sheet.write(row, col, 'Clock In', header_merge_format )
            col += 1
            
            sheet.write(row, col, 'Clock Out', header_merge_format)
            col += 1
            
            sheet.write(row, col, 'Check In', header_merge_format)
            col += 1
            
            sheet.write(row, col, 'Check Out', header_merge_format)
            col += 1
            
            sheet.write(row, col, 'Late In', header_merge_format)
            col += 1
            
            sheet.write(row, col, 'Early Out', header_merge_format)
            col += 1
            
            sheet.write(row, col, 'Overtime', header_merge_format)
            
            col += 1
            
            sheet.write(row, col, 'Status',header_merge_format)
            col += 1
            
            sheet.write(row, col, 'Work Type', header_merge_format)
            col += 1
            
        else:
            sheet.write(row, col , 'S.No',  header_merge_format)
            col += 1
            
            sheet.write(row, col, 'Employee No', header_merge_format)
            col += 1
            
            sheet.write(row, col, 'Employee Name', header_merge_format)
            col += 1
            sheet.set_column(2,2,20)
            
            sheet.write(row, col, 'Department' , header_merge_format)
            col += 1
            sheet.set_column(3,3,20)
            
            # sheet.write(row, col, 'Date', header_merge_format )
            # col += 1 
            #

            # sheet.write(row, col, 'Day', header_merge_format)
            # col += 1
            
            
            sheet.write(row, col, 'Late In', header_merge_format)
            col += 1
            
            sheet.write(row,col,'Total Late In',header_merge_format)
            col += 1
            
           
            sheet.write(row, col, 'Early Out', header_merge_format)
            col += 1
            
            sheet.write(row,col,'Total Early Out',header_merge_format)
            col += 1
            
            sheet.write(row, col, 'Overtime', header_merge_format)
            col += 1
            
            sheet.write(row,col,'Total Overtime',header_merge_format)
            
            
            
                
        
        
        domain = []
        
        if wizard.employee_ids :
            
            domain += [('name_id.employee_id' ,'in' , wizard.employee_ids.ids)]
            
        else :
            
            domain += [('name_id.employee_id' , 'in', self.env['hr.employee'].search([]).ids)]
            
            
        if wizard.department_ids :
             
            domain += [('name_id.employee_id.department_id', 'in' , wizard.department_ids.ids)]
            
            
        if wizard.from_date :
            
            domain += [('date' ,'>=' , wizard.from_date)]
            
        if wizard.to_date : 
            
            domain += [('date' ,'<=' , wizard.to_date)]  
         
        attendance_sheet_total = False 
        
        if wizard.summary_based_report:
            
            attendance_sheet_total = self.env['hr.attendance.sheet.line'].search(domain) 
            attendance_sheet_total = attendance_sheet_total.sorted(key=lambda c:c.name_id.employee_number)

            
        if wizard.attendance_policy_ids:
            
            domain += [('name_id.employee_id.contract_id.attend_police_id','in', wizard.attendance_policy_ids.ids)]
        
        # attendance_sheet_search = self.env['hr.attendance.sheet'].search(domain,order="employee_number asc") 
        
        attendance_lines = self.env['hr.attendance.sheet.line'].search(domain,order="date ASC")
        
        # attendance_lines = self.env['hr.attendance.sheet.line'].search([('name_id', 'in', attendance_sheet_search.ids)],order="date ASC")
        
        # attendance_sheet_lines = attendance_sheet_search.attendance_sheet_ids
        attendance_sheet_lines = attendance_lines
        # attendance_sheet_lines = sorted(
        #     attendance_lines, 
        #     key=lambda line: (line.date, line.name_id.employee_id.employee_no)
        # )
                
        
        
        if wizard.sort_by:
            
            if wizard.sort_by =='department':
                
                attendance_sheet_lines = attendance_sheet_lines.filtered(lambda c:c.name_id.employee_id.department_id)
                attendance_sheet_lines = attendance_sheet_lines.sorted(key=lambda c:c.name_id.employee_id.department_id.name.lower())
                # attendance_sheet_lines = attendance_sheet_lines.attendance_sheet_ids
                sheet.merge_range(5, 0, 5, 14, "Department Wise Sort" , header_merge_format)
            
            elif wizard.sort_by == 'employee':
                
                attendance_sheet_lines = attendance_sheet_lines.filtered(lambda c:c.name_id.employee_id)
                attendance_sheet_lines = attendance_sheet_lines.sorted(key = lambda c:c.name_id.employee_id.name.lower())
                sheet.merge_range (5, 0, 5, 14, "Employee Wise Sort", header_merge_format)
                # attendance_sheet_lines = attendance_sheet_search.attendance_sheet_ids

            elif wizard.sort_by == 'date':
                sheet.merge_range(5, 0, 5, 14, "Date Wise Sort", header_merge_format)
                # Sort by date, and we will display all employees under each date
                # attendance_sheet_lines = attendance_sheet_lines.sorted(key=lambda c: min([line.date for line in c.attendance_sheet_ids]))            #

        if wizard.report_for_option =='overtime' :
            attendance_sheet_lines = attendance_sheet_lines.filtered(
        lambda line: line.overtime > 0.0 and line.date >= wizard.from_date and line.date <= wizard.to_date
        )
            
            
        if wizard.report_for_option =='latein' :
            attendance_sheet_lines = attendance_sheet_lines.filtered(
        lambda line: line.latein > 0.0 and line.date >= wizard.from_date and line.date <= wizard.to_date
        ) 
        if wizard.report_for_option =='early_out' :
            attendance_sheet_lines = attendance_sheet_lines.filtered(
        lambda line: line.early_out_line > 0.0 and line.date >= wizard.from_date and line.date <= wizard.to_date
        )  
        if  wizard.report_for_option =='all':
            attendance_sheet_lines = attendance_sheet_lines.filtered(
        lambda line:line.date >= wizard.from_date and line.date <= wizard.to_date)

        if wizard.status_filter:            
            if wizard.status_filter=='weekday':
                attendance_sheet_lines = attendance_sheet_lines.filtered(
            lambda line: (
                (line.status=='weekday') 
                and line.date >= wizard.from_date and line.date <= wizard.to_date))
                
            if wizard.status_filter=='weekend':
                attendance_sheet_lines = attendance_sheet_lines.filtered(
            lambda line: (
                (line.status=='weekend') 
                and line.date >= wizard.from_date and line.date <= wizard.to_date))   
                
            if wizard.status_filter=='absence':
                attendance_sheet_lines = attendance_sheet_lines.filtered(
            lambda line: (
                (line.status=='absence') 
                and line.date >= wizard.from_date and line.date <= wizard.to_date))
            
            if wizard.status_filter == 'leave': 
                attendance_sheet_lines = attendance_sheet_lines.filtered(
            lambda line: (
                (line.status=='leave') 
                and line.date >= wizard.from_date and line.date <= wizard.to_date))  
            
            if wizard.status_filter == 'holiday': 
                attendance_sheet_lines = attendance_sheet_lines.filtered(
            lambda line: (
                (line.status=='holiday') 
                and line.date >= wizard.from_date and line.date <= wizard.to_date))  
                
                
                            
              
            
    #         attendance_sheet_search = attendance_sheet_search.filtered(
    #     lambda c: any(
    #         line.overtime > 0.0 and 
    #         line.date >= wizard.from_date and 
    #         line.date <= wizard.to_date 
    #         for line in c.attendance_sheet_ids
    #     ) )
    #
    #         attendance_sheet_search = attendance_sheet_search.mapped('attendance_sheet_ids').filtered(
    #     lambda line: line.overtime > 0.0
    # )
        #     attendance_sheet_search = attendance_sheet_search.filtered(
        # lambda c: any(line.overtime and line.overtime > 0.0 for line in c.attendance_sheet_ids)
        # )           
          


        department_sort = set()
        employee_sort = set()
        date_sort = set()
        current_date = None
        
        row = 7
        no = 1
        num = 1
        
        attendance_by_date = {}

        # Group attendance lines by date
        for line in sorted(attendance_lines, key=lambda l: (l.name_id.employee_id.employee_no, l.date)):
        # for line in attendance_lines:
            attendance_date = line.date
            if attendance_date not in attendance_by_date:
                attendance_by_date[attendance_date] = []
            attendance_by_date[attendance_date].append(line)
        
        # Sort dates for ordered display
        sorted_dates = sorted(attendance_by_date.keys())
        
       
        
        if wizard.sort_by == 'date':
            date_lst = []
            for attendance_date in sorted_dates:
                # Merge the date header
                sheet.merge_range(row, 0, row, 14, attendance_date.strftime('%d-%m-%Y'), header_merge_format)
                row += 1  # Move to the next row for the data
            
                # Get all lines for the current date
                for line in attendance_by_date[attendance_date]:
                    col = 0
                    sheet.write(row, col, num, num_format)  # Row number
                    col += 1
                    sheet.write(row, col, line.name_id.employee_number or ' ', name_format)
                    col += 1
                    sheet.write(row, col, line.name_id.employee_id.name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, line.name_id.employee_id.department_id.name or '', name_format)
                    col += 1
                    sheet.write(row, col, line.date.strftime('%d-%m-%Y'), name_format)
                    col += 1
                    sheet.write(row, col, line.day, name_format)
                    col += 1
                    hours_psign = int(line.psignin)
                    min_psign = int((line.psignin - hours_psign) * 60)
                    sheet.write(row, col, "{:02d}:{:02d}".format(hours_psign, min_psign) or ' ', num_format)
                    col += 1
                    hours_psignout = int(line.psignout)
                    min_psignout = int((line.psignout - hours_psignout) * 60)
                    sheet.write(row, col, "{:02d}:{:02d}".format(hours_psignout, min_psignout) or ' ', num_format)
                    col += 1
                    
                    hours_asignin = int(line.asignin)
                    min_asignin = int((line.asignin - hours_asignin) * 60)
                
                    sheet.write(row,col, "{:02d}:{:02d}".format(hours_asignin,min_asignin) or ' ', num_format)
                    col += 1
                        
                    hours_asignout = int(line.asignout)
                    min_asignout = int((line.asignout - hours_asignout) * 60)
                
                    sheet.write(row, col, "{:02d}:{:02d}".format(hours_asignout,min_asignout) or ' ', num_format)
                    col += 1
                
                    hours_latein = int(line.latein)
                    min_latein = int((line.latein - hours_latein) * 60)
                
                    sheet.write(row,col, "{:02d}:{:02d}".format(hours_latein,min_latein) or ' ', num_format)
                    col += 1
                
                    hours_earlyout = int(line.early_out_line)
                    min_earlyout = int((line.early_out_line - hours_earlyout)* 60)
                
                    sheet.write(row, col, "{:02d}:{:02d}".format(hours_earlyout,min_earlyout ), num_format)
                    col += 1
                
                    hours_overtime = int(line.overtime)
                    min_overtime = int((line.overtime - hours_overtime) * 60)
                
                    sheet.write(row, col, "{:02d}:{:02d}".format(hours_overtime,min_overtime) or ' ', num_format)
                    col += 1
                
                    sheet.write(row,col, line.status.capitalize(), name_format)
                    col += 1
                    
                    if line.work_type =='wfo':
                        sheet.write(row, col, 'Office Work', name_format)
                    elif line.work_type =='wfh': 
                        sheet.write(row, col, 'Remote Work', name_format)
                    else:
                        sheet.write(row, col, '', name_format)

                        
                    
                    date_lst.append(line.name_id.employee_id.name)
           
                    row += 1
                    num += 1  
         
            if len(date_lst) == 0:
                raise ValidationError("Attendance is not there for that particular Period")        
        # for attendance_sheet in  attendance_sheet_search.:
        #     if wizard.sort_by =='department' and attendance_sheet.employee_id.department_id.display_name not in department_sort :
        #         sheet.merge_range(row, 0 , row, 15, attendance_sheet.employee_id.department_id.display_name, header_merge_format)
        #         department_sort.add(attendance_sheet.employee_id.department_id.display_name)
        #         row += 1
        #         num = 1
        #
        #     elif wizard.sort_by =='employee' and attendance_sheet.employee_id.name not in employee_sort:
        #         sheet.merge_range ( row, 0, row, 15,attendance_sheet.employee_id.name, header_merge_format )
        #         employee_sort.add(attendance_sheet.employee_id.name)
        #         row += 1
        #         num = 1  
        #     elif wizard.sort_by =='date' and attendance_sheet.attendance_sheet_ids.date not in date_sort:
        #         sheet.merge_range ( row, 0, row, 15, attendance_sheet.attendance_sheet_ids.date, header_merge_format)
        #         date_sort.add(attendance_sheet.attendance_sheet_ids.date)
        #         row += 1
        #         num = 1
        #
        #
        #     col = 0         
        #     if wizard.sort_by in ['department','employee','date']:
        #         sheet.write(row, col, num, num_format)
        #     else:
        #         sheet.write(row, col, no,num_format)      
        #     # col = 0
        #     # sheet.write(row, col, no, num_format)
        #     col += 1
        #     sheet.write(row, col, attendance_sheet.employee_number or ' ', name_format)
        #     col += 1
        #     sheet.write(row,col, attendance_sheet.employee_id.name or ' ', name_format)
        #     col += 1
        #     sheet.write(row, col, attendance_sheet.employee_id.department_id.name or '', name_format)
        #     col += 1
        #
        # else:
        #     if not wizard.summary_based_report:
        #         employee_lst = []
        #         date_sort = set()
        #         current_date = None
        #
        #         employee_lst = []
        #         employee_sort = set()
        #         current_employee = None
        #         current_date = None
        #
        #         # Loop through attendance sheet lines sorted by employee and date
        #         for line in sorted(attendance_sheet_lines, key=lambda l: (l.name_id.employee_id.name, l.date)):
        #             # Sorting by employee
        #             if line.name_id.employee_id.name != current_employee:
        #                 current_employee = line.name_id.employee_id.name
        #                 sheet.merge_range(row, 0, row, 14, current_employee, header_merge_format)
        #                 employee_sort.add(current_employee)
        #                 row += 1
        #                 current_date = None  # Reset current_date for each new employee
        #                 num = 1
        #
        #             # Sorting by date within the employee
        #             if line.date != current_date:
        #                 current_date = line.date
        #                 # sheet.merge_range(row, 0, row, 14, line.date.strftime('%d-%m-%Y'), header_merge_format)
        #                 # row += 1
        #                 # num = 1
        #
        #         # Loop through attendance sheet lines
        #         # for line in attendance_sheet_lines:
        #             # Sorting by date
        #             # if wizard.sort_by == 'date':
        #             #     if line.date != current_date:
        #             #         current_date = line.date
        #             #         sheet.merge_range(row, 0, row, 14, line.date.strftime('%d-%m-%Y'), header_merge_format)
        #             #         date_sort.add(line.date)
        #             #
        #             #         row += 1
        #             #         num = 1
        #
        #             # Sorting by department
        #             elif wizard.sort_by == 'department' and line.name_id.employee_id.department_id.display_name not in department_sort:
        #                 sheet.merge_range(row, 0, row, 14, line.name_id.employee_id.department_id.display_name, header_merge_format)
        #                 department_sort.add(line.name_id.employee_id.department_id.display_name)
        #                 print("...........depattment_saort",)
        #                 row += 1
        #                 num = 1
        #
        #             # Sorting by employee
        #             elif wizard.sort_by == 'employee' and line.name_id.employee_id.name not in employee_sort:
        #                 sheet.merge_range(row, 0, row, 14, line.name_id.employee_id.name, header_merge_format)
        #                 employee_sort.add(line.name_id.employee_id.name)
        #                 row += 1
        #                 num = 1
        #
        #             # Write data for each attendance line
        #             col = 0
        #             if wizard.sort_by in ['department', 'employee', 'date']:
        #                 sheet.Statuswrite(row, col, num, num_format)
        #             else:
        #                 sheet.write(row, col, no, num_format)
        #             col += 1
        #
        #             sheet.write(row, col, line.name_id.employee_number or ' ', name_format)
        #             col += 1
        #             sheet.write(row, col, line.name_id.employee_id.name or ' ', name_format)
        #             col += 1
        #             sheet.write(row, col, line.name_id.employee_id.department_id.name or '', name_format)
        #             col += 1
        #             sheet.write(row, col, line.date.strftime('%d-%m-%Y'), name_format)
        #             col += 1
        #             sheet.write(row, col, line.day, name_format)
        #             col += 1
        #
        #             # Time formatting
        #             hours_psign = int(line.psignin)
        #             min_psign = int((line.psignin - hours_psign) * 60)
        #             sheet.write(row, col, "{:02d}:{:02d}".format(hours_psign, min_psign) or ' ', num_format)
        #             col += 1
        #
        #             hours_psignout = int(line.psignout)
        #             min_psignout = int((line.psignout - hours_psignout) * 60)
        #             sheet.write(row, col, "{:02d}:{:02d}".format(hours_psignout, min_psignout) or ' ', num_format)
        #             col += 1
        #
        #             hours_asignin = int(line.asignin)
        #             min_asignin = int((line.asignin - hours_asignin) * 60)
        #             sheet.write(row, col, "{:02d}:{:02d}".format(hours_asignin, min_asignin) or ' ', num_format)
        #             col += 1
        #
        #             hours_asignout = int(line.asignout)
        #             min_asignout = int((line.asignout - hours_asignout) * 60)
        #             sheet.write(row, col, "{:02d}:{:02d}".format(hours_asignout, min_asignout) or ' ', num_format)
        #             col += 1
        #
        #             hours_latein = int(line.latein)
        #             min_latein = int((line.latein - hours_latein) * 60)
        #             sheet.write(row, col, "{:02d}:{:02d}".format(hours_latein, min_latein) or ' ', num_format)
        #             col += 1
        #
        #             hours_earlyout = int(line.early_out_line)
        #             min_earlyout = int((line.early_out_line - hours_earlyout) * 60)
        #             sheet.write(row, col, "{:02d}:{:02d}".format(hours_earlyout, min_earlyout), num_format)
        #             col += 1
        #
        #             hours_overtime = int(line.overtime)
        #             min_overtime = int((line.overtime - hours_overtime) * 60)
        #             sheet.write(row, col, "{:02d}:{:02d}".format(hours_overtime, min_overtime) or ' ', num_format)
        #             col += 1
        #
        #             sheet.write(row, col, line.status.capitalize(), name_format)
        #             col += 1
        #             sheet.write(row, col, line.work_type or ' ', name_format)
        #             col += 1
        #
        #             employee_lst.append(line.name_id.employee_id.name)
        #             row += 1
        #             num += 1
        #             no += 1
        #
        #         if len(employee_lst) == 0:
        #             raise ValidationError("Attendance is not there for that particular period")
        
        
        else:
            if not wizard.summary_based_report:
                # Initialize variables
                employee_sort = set()
                department_sort = set()
                current_date = None
                current_employee = None
                if wizard.sort_by == 'department':
                    sorted_lines = sorted(attendance_sheet_lines, key=lambda l: (l.name_id.employee_id.department_id.display_name, l.name_id.employee_id.employee_no,l.date))
                else:
                   sorted_lines = sorted(attendance_sheet_lines, key=lambda l: ( l.name_id.employee_id.employee_no,l.date))
                    # sorted_lines = attendance_sheet_lines
                    
                
                # Loop through attendance sheet lines sorted by employee and date
                for line in sorted_lines:
                # for line in sorted(attendance_sheet_lines, key=lambda l: ( l.name_id.employee_id,date)):

                    # Sorting by department
                    if wizard.sort_by == 'department' and line.name_id.employee_id.department_id.display_name not in department_sort:
                        sheet.merge_range(row, 0, row, 14, line.name_id.employee_id.department_id.display_name, header_merge_format)
                        department_sort.add(line.name_id.employee_id.department_id.display_name)
                        row += 1
                        num = 1
                
                    # Sorting by employee
                    if wizard.sort_by == 'employee' and line.name_id.employee_id.name not in employee_sort:
                        sheet.merge_range(row, 0, row, 14, line.name_id.employee_id.name, header_merge_format)
                        employee_sort.add(line.name_id.employee_id.name)
                        row += 1
                        num = 1
                
                    # Sorting by date within the employee
                    if line.date != current_date:
                        current_date = line.date
                        # sheet.merge_range(row, 0, row, 14, line.date.strftime('%d-%m-%Y'), header_merge_format)
                        # row += 1
                        # num = 1
                
                    # Write data for each attendance line
                    col = 0
                    if wizard.sort_by in ['department', 'employee', 'date']:
                        sheet.write(row, col, num, num_format)
                    else:
                        sheet.write(row, col, no, num_format)
                    col += 1
                
                    sheet.write(row, col, line.name_id.employee_number or ' ', name_format)
                    col += 1
                    sheet.write(row, col, line.name_id.employee_id.name or ' ', name_format)
                    col += 1
                    sheet.write(row, col, line.name_id.employee_id.department_id.name or '', name_format)
                    col += 1
                    sheet.write(row, col, line.date.strftime('%d-%m-%Y'), name_format)
                    col += 1
                    sheet.write(row, col, line.day, name_format)
                    col += 1
                
                    # Time formatting
                    hours_psign = int(line.psignin)
                    min_psign = int((line.psignin - hours_psign) * 60)
                    sheet.write(row, col, "{:02d}:{:02d}".format(hours_psign, min_psign) or ' ', num_format)
                    col += 1
                
                    hours_psignout = int(line.psignout)
                    min_psignout = int((line.psignout - hours_psignout) * 60)
                    sheet.write(row, col, "{:02d}:{:02d}".format(hours_psignout, min_psignout) or ' ', num_format)
                    col += 1
                
                    hours_asignin = int(line.asignin)
                    min_asignin = int((line.asignin - hours_asignin) * 60)
                    sheet.write(row, col, "{:02d}:{:02d}".format(hours_asignin, min_asignin) or ' ', num_format)
                    col += 1
                
                    hours_asignout = int(line.asignout)
                    min_asignout = int((line.asignout - hours_asignout) * 60)
                    sheet.write(row, col, "{:02d}:{:02d}".format(hours_asignout, min_asignout) or ' ', num_format)
                    col += 1
                
                    hours_latein = int(line.latein)
                    min_latein = int((line.latein - hours_latein) * 60)
                    sheet.write(row, col, "{:02d}:{:02d}".format(hours_latein, min_latein) or ' ', num_format)
                    col += 1
                
                    hours_earlyout = int(line.early_out_line)
                    min_earlyout = int((line.early_out_line - hours_earlyout) * 60)
                    sheet.write(row, col, "{:02d}:{:02d}".format(hours_earlyout, min_earlyout), num_format)
                    col += 1
                
                    hours_overtime = int(line.overtime)
                    min_overtime = int((line.overtime - hours_overtime) * 60)
                    sheet.write(row, col, "{:02d}:{:02d}".format(hours_overtime, min_overtime) or ' ', num_format)
                    col += 1
                
                    sheet.write(row, col, line.status.capitalize(), name_format)
                    col += 1
                    
                    if line.work_type =='wfo':
                        sheet.write(row, col, 'Office Work', name_format)
                    elif line.work_type =='wfh': 
                        sheet.write(row, col, 'Remote Work', name_format)
                    else:
                        sheet.write(row, col, '', name_format)                   
                    # sheet.write(row, col, line.work_type or ' ', name_format)
                    col += 1
                
                    row += 1
                    num += 1
                    no += 1
                
                # Raise validation error if no data
                if not attendance_sheet_lines:
                    raise ValidationError("Attendance is not available for the selected period.")
                
                        
        ############# Currently working
        # else:
        #     if not wizard.summary_based_report:
        #         employee_lst = []
        #
        #         for line in attendance_sheet_lines :
        #
        #             if wizard.sort_by =='department' and line.name_id.employee_id.department_id.display_name not in department_sort :
        #                 sheet.merge_range(row, 0 , row, 14, line.name_id.employee_id.department_id.display_name, header_merge_format)
        #                 department_sort.add(line.name_id.employee_id.department_id.display_name)
        #                 row += 1
        #                 num = 1
        #
        #             elif wizard.sort_by =='employee' and line.name_id.employee_id.name not in employee_sort:
        #                 sheet.merge_range ( row, 0, row, 14,line.name_id.employee_id.name, header_merge_format )
        #                 employee_sort.add(line.name_id.employee_id.name)
        #                 row += 1
        #                 num = 1  
        #
        #
        #
        #
        #             # elif wizard.sort_by =='date' and line.date not in date_sort:
        #             #     sheet.merge_range ( row, 0, row, 15, line.date.strftime("%d-%m-%Y"), header_merge_format)
        #             #     date_sort.add(line.date)
        #             #     print("............datesort",date_sort)
        #             #     row += 1
        #             #     num = 1
        #             # elif wizard.sort_by =='date' :
        #             #     if line.date != current_date:
        #             #         current_date = line.date
        #             #         sheet.merge_range(row, 0, row, 14, line.date.strftime('%d-%m-%Y'), header_merge_format)
        #             #         row += 1
        #             #         no = 1
        #
        #             col = 0         
        #             if wizard.sort_by in ['department','employee']:
        #                 sheet.write(row, col, num, num_format)
        #             else:
        #                 sheet.write(row, col, no,num_format)      
        #             col += 1
        #             sheet.write(row, col, line.name_id.employee_number or ' ', name_format)
        #             col += 1
        #             sheet.write(row,col, line.name_id.employee_id.name or ' ', name_format)
        #             col += 1
        #             sheet.write(row, col, line.name_id.employee_id.department_id.name or '', name_format)
        #             col += 1
        #
        #             sheet.write(row, col, line.date.strftime('%d-%m-%Y'),  name_format)
        #
        #             col += 1
        #
        #             sheet.write(row, col, line.day, name_format)
        #
        #             col += 1
        #
        #             hours_psign = int(line.psignin)
        #             min_psign = int((line.psignin - hours_psign)* 60)
        #
        #             sheet.write(row,col, "{:02d}:{:02d}".format(hours_psign,min_psign) or ' ', num_format)
        #             col += 1
        #
        #             hours_psignout = int(line.psignout)
        #             min_psignout = int((line.psignout - hours_psignout)*60)
        #
        #             sheet.write(row, col, "{:02d}:{:02d}".format(hours_psignout,min_psignout) or ' ', num_format)
        #
        #             col += 1
        #
        #             hours_asignin = int(line.asignin)
        #             min_asignin = int((line.asignin - hours_asignin) * 60)
        #
        #             sheet.write(row,col, "{:02d}:{:02d}".format(hours_asignin,min_asignin) or ' ', num_format)
        #             col += 1
        #
        #             hours_asignout = int(line.asignout)
        #             min_asignout = int((line.asignout - hours_asignout) * 60)
        #
        #             sheet.write(row, col, "{:02d}:{:02d}".format(hours_asignout,min_asignout) or ' ', num_format)
        #             col += 1
        #
        #             hours_latein = int(line.latein)
        #             min_latein = int((line.latein - hours_latein) * 60)
        #
        #             sheet.write(row,col, "{:02d}:{:02d}".format(hours_latein,min_latein) or ' ', num_format)
        #             col += 1
        #
        #             hours_earlyout = int(line.early_out_line)
        #             min_earlyout = int((line.early_out_line - hours_earlyout)* 60)
        #
        #             sheet.write(row, col, "{:02d}:{:02d}".format(hours_earlyout,min_earlyout ), num_format)
        #             col += 1
        #
        #             hours_overtime = int(line.overtime)
        #             min_overtime = int((line.overtime - hours_overtime) * 60)
        #
        #             sheet.write(row, col, "{:02d}:{:02d}".format(hours_overtime,min_overtime) or ' ', num_format)
        #             col += 1
        #
        #             sheet.write(row,col, line.status.capitalize(), name_format)
        #             col += 1
        #
        #             sheet.write(row, col, line.work_type or ' ', name_format)
        #             col += 1
        #             # sheet.write(row, col, line.name_id.employee_id.contract_id.attend_police_id.name or ' ', name_format)
        #             employee_lst.append(line.name_id.employee_id.name)
        #
        #             row += 1
        #
        #
        #             # row += 1
        #             no += 1
        #             num += 1
        #         if len(employee_lst)==0:
        #             raise ValidationError("Attendance is not there for that particular Period")        
        if wizard.summary_based_report:
            summary_lst = []  # To store employee names
            sheet.merge_range(5, 0, 5, 11, "Summary Based Report", header_merge_format)
        
            # Initialize variables for totals and counts
            total_late_in = 0.0
            total_early_out = 0.0
            total_overtime = 0.0
            late_in_count = 0
            early_out_count = 0
            overtime_count = 0
            employee_no = False
        
            # Create a dictionary to store the summary per employee
            employee_summary = {}
        
            # Grouping data by employee_id
            for line in attendance_sheet_total:
                employee = line.name_id.employee_id
        
                # If this is the first occurrence of the employee, initialize the summary
                if employee.id not in employee_summary:
                    employee_summary[employee.id] = {
                        'employee_number': employee.employee_no,
                        'employee_name': employee.name,
                        'department': line.name_id.employee_id.department_id.name,
                        'late_in_total': 0.0,
                        'early_out_total': 0.0,
                        'overtime_total': 0.0,
                        'late_in_count': 0,
                        'early_out_count': 0,
                        'overtime_count': 0
                    }
        
                # Accumulate totals and counts
                if line.latein >0:
                    employee_summary[employee.id]['late_in_count'] += 1
                    employee_summary[employee.id]['late_in_total'] += round(line.latein, 2)
        
                if line.early_out_line > 0:
                    employee_summary[employee.id]['early_out_count'] += 1
                    employee_summary[employee.id]['early_out_total'] += round(line.early_out_line, 2)
        
                if line.overtime > 0:
                    employee_summary[employee.id]['overtime_count'] += 1
                    employee_summary[employee.id]['overtime_total'] += round(line.overtime, 2)
        
            # Writing data to the sheet
            row = 7  # Start from row 6 to avoid overlap with the header
            no = 1  # Row number for the employee
            for employee_id, summary in employee_summary.items():
                col = 0
        
                # Write employee number and name
                sheet.write(row, col, no, num_format)
                col += 1
                sheet.write(row, col, summary['employee_number'] or ' ', name_format)
                col += 1
                sheet.write(row, col, summary['employee_name'] or ' ', name_format)
                col += 1
                sheet.write(row, col, summary['department'] or '', name_format)
                col += 1
        
                # Write the summary for late in
                hours_latein_total = int(summary['late_in_total'])
                min_latein_total = int((summary['late_in_total'] - hours_latein_total) * 60)
                sheet.write(row, col, "{:02d}:{:02d}".format(hours_latein_total, min_latein_total) or ' ', num_format)
                col += 1
                sheet.write(row, col, summary['late_in_count'] or ' ', num_format)
                col += 1
        
                # Write the summary for early out
                hours_earlyout = int(summary['early_out_total'])
                min_earlyout = int((summary['early_out_total'] - hours_earlyout) * 60)
                sheet.write(row, col, "{:02d}:{:02d}".format(hours_earlyout, min_earlyout) or ' ', num_format)
                col += 1
                sheet.write(row, col, summary['early_out_count'] or ' ', num_format)
                col += 1
        
                # Write the summary for overtime
                hours_overtime = int(summary['overtime_total'])
                min_overtime = int((summary['overtime_total'] - hours_overtime) * 60)
                sheet.write(row, col, "{:02d}:{:02d}".format(hours_overtime, min_overtime) or ' ', num_format)
                col += 1
                sheet.write(row, col, summary['overtime_count'] or ' ', num_format)
                col += 1
        
                # Move to the next row
                row += 1
                no += 1
                summary_lst.append(summary['employee_name'])
        
            # Check if the summary list is empty and raise an error if no data is found
            if len(summary_lst) == 0:
                raise ValidationError("Attendance Summary is not there for that particular Period")

                
                    
            
            # if wizard.summary_based_report:
            #     summary_lst = []
            #     sheet.merge_range (5, 0, 5, 11, "Summary Based Report", header_merge_format)
            #
            #     total_late_in = 0.0
            #     total_early_out = 0.0
            #     total_overtime = 0.0
            #     late_in_count = 0
            #     early_out_count = 0
            #     overtime_count = 0
            #     employee_no = False
            #     employee_sort = set()
            #     for line in attendance_sheet_total: 
            #
            #         col = 0
            #
            #         if line.name_id.employee_number != employee_no and employee_sort not in line.name_id.employee_number:
            #             sheet.write(row, col, no,num_format)  
            #
            #             col += 1
            #             employee_noline.name_id.employee_number
            #             sheet.write(row, col, line.name_id.employee_number or ' ', name_format)
            #             col += 1
            #             sheet.write(row,col, line.name_id.employee_id.name or ' ', name_format)
            #             col += 1
            #             sheet.write(row, col, line.name_id.employee_id.department_id.name or '', name_format)
            #         col += 1
            #
            #         # sheet.write(row, col, line.date.strftime('%d-%m-%Y'),  name_format)
            #         #
            #         # col += 1
            #         #
            #         # sheet.write(row, col, line.day, name_format)
            #         #
            #         # col += 1
            #
            #
            #         # for total in line.name_id.attendance_sheet_ids:
            #         if line.latein > 0.0:
            #             late_in_count += 1
            #
            #         if line.early_out_line > 0.0:
            #             early_out_count  += 1
            #
            #         if line.overtime > 0.0:
            #             overtime_count += 1
            #
            #
            #
            #         total_late_in += round(line.latein,2)
            #         hours_latein_total = int(total_late_in)
            #         min_latein_total = int((total_late_in - hours_latein_total)*60)
            #
            #
            #
            #         total_early_out += round(line.early_out_line,2)
            #         hours_earlyout = int(total_early_out)
            #         min_earlyout = int((total_early_out - hours_earlyout) * 60)
            #
            #
            #
            #         total_overtime += round(line.overtime,2)
            #         hours_overtime = int(total_overtime)
            #         min_overtime = int((total_overtime - hours_overtime)* 60)
            #
            #
            #
            #
            #         sheet.write(row, col, "{:02d}:{:02d}".format(hours_latein_total,min_latein_total) or ' ', num_format)
            #         col += 1
            #
            #         sheet.write ( row, col, late_in_count or ' ', num_format) 
            #         col += 1
            #
            #         sheet.write(row,col, "{:02d}:{:02d}".format(hours_earlyout,min_earlyout) or ' ', num_format)
            #         col += 1
            #
            #         sheet.write ( row, col, early_out_count or ' ', num_format) 
            #         col += 1
            #
            #
            #         sheet.write(row,col, "{:02d}:{:02d}".format(hours_overtime,min_overtime) or ' ', num_format)
            #         col += 1
            #
            #         sheet.write ( row, col, overtime_count or ' ', num_format) 
            #
            #         # sheet.write(row, col, line.name_id.employee_id.contract_id.attend_police_id.name or ' ', name_format)
            #         summary_lst.append(line.name_id.employee_id.name)
            #         row += 1
            #
            #
            #         # row += 1
            #         no += 1  
            #
            #     if len(summary_lst) == 0:
            #         raise ValidationError("Attendance Summary is not there for that particular Period")
            #

        ''' It  is working'''
        # for attendance_sheet in  attendance_sheet_search:
        #     if wizard.sort_by =='department' and attendance_sheet.employee_id.department_id.display_name not in department_sort :
        #         sheet.merge_range(row, 0 , row, 15, attendance_sheet.employee_id.department_id.display_name, header_merge_format)
        #         department_sort.add(attendance_sheet.employee_id.department_id.display_name)
        #         row += 1
        #         num = 1
        #
        #     elif wizard.sort_by =='employee' and attendance_sheet.employee_id.name not in employee_sort:
        #         sheet.merge_range ( row, 0, row, 15,attendance_sheet.employee_id.name, header_merge_format )
        #         employee_sort.add(attendance_sheet.employee_id.name)
        #         row += 1
        #         num = 1  
        #     elif wizard.sort_by =='date' and attendance_sheet.attendance_sheet_ids.date not in date_sort:
        #         sheet.merge_range ( row, 0, row, 15, attendance_sheet.attendance_sheet_ids.date, header_merge_format)
        #         date_sort.add(attendance_sheet.attendance_sheet_ids.date)
        #         row += 1
        #         num = 1
        #
        #
        #     col = 0         
        #     if wizard.sort_by in ['department','employee','date']:
        #         sheet.write(row, col, num, num_format)
        #     else:
        #         sheet.write(row, col, no,num_format)      
        #     # col = 0
        #     # sheet.write(row, col, no, num_format)
        #     col += 1
        #     sheet.write(row, col, attendance_sheet.employee_number or ' ', name_format)
        #     col += 1
        #     sheet.write(row,col, attendance_sheet.employee_id.name or ' ', name_format)
        #     col += 1
        #     sheet.write(row, col, attendance_sheet.employee_id.department_id.name or '', name_format)
        #     col += 1
        #
        #     for line in attendance_sheet.attendance_sheet_ids:
        #
        #
        #         col = 4
        #         sheet.write(row, col, line.date.strftime('%d-%m-%Y'),  name_format)
        #
        #         col += 1
        #
        #         sheet.write(row, col, line.day, name_format)
        #
        #         col += 1
        #
        #         hours_psign = int(line.psignin)
        #         min_psign = int((line.psignin - hours_psign)* 60)
        #
        #         sheet.write(row,col, "{:02d}:{:02d}".format(hours_psign,min_psign) or ' ', name_format)
        #         col += 1
        #
        #         hours_psignout = int(line.psignout)
        #         min_psignout = int((line.psignout - hours_psignout)*60)
        #
        #         sheet.write(row, col, "{:02d}:{:02d}".format(hours_psignout,min_psignout) or ' ', name_format)
        #
        #         col += 1
        #
        #         hours_asignin = int(line.asignin)
        #         min_asignin = int((line.asignin - hours_asignin) * 60)
        #
        #         sheet.write(row,col, "{:02d}:{:02d}".format(hours_asignin,min_asignin) or ' ', name_format)
        #         col += 1
        #
        #         hours_asignout = int(line.asignout)
        #         min_asignout = int((line.asignout - hours_asignout) * 60)
        #
        #         sheet.write(row, col, "{:02d}:{:02d}".format(hours_asignout,min_asignout) or ' ', name_format)
        #         col += 1
        #
        #         hours_latein = int(line.latein)
        #         min_latein = int((line.latein - hours_latein) * 60)
        #
        #         sheet.write(row,col, "{:02d}:{:02d}".format(hours_latein,min_latein) or ' ', name_format)
        #         col += 1
        #
        #         hours_earlyout = int(line.early_out_line)
        #         min_earlyout = int((line.early_out_line - hours_earlyout)* 60)
        #
        #         sheet.write(row, col, "{:02d}:{:02d}".format(hours_earlyout,min_earlyout ), name_format)
        #         col += 1
        #
        #         hours_overtime = int(line.overtime)
        #         min_overtime = int((line.overtime - hours_overtime) * 60)
        #
        #         sheet.write(row, col, "{:02d}:{:02d}".format(hours_overtime,min_overtime) or ' ', name_format)
        #         col += 1
        #
        #         sheet.write(row,col, line.status.capitalize(), name_format)
        #         col += 1
        #
        #         sheet.write(row, col, line.work_type or ' ', name_format)
        #         col += 1
        #         sheet.write(row, col, attendance_sheet.employee_id.contract_id.attend_police_id.name or ' ', name_format)
        #
        #         row += 1
        #
        #
        #     # row += 1
        #     no += 1
        #     num += 1
        #
        #

        
        
        
        
        
        
        
        
        
        
        
        
        
        

        