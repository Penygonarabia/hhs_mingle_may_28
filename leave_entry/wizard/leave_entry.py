from odoo import fields, models, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, time
import calendar


class LeaveEntry(models.Model):
    
    _name = "leave.entry.analysis"
    
    _description = "Leave Entry Analysis"
    
    
    s_no = fields.Char(string="S.no")
    
    employee_code = fields.Char(string="Employee Code")
    
    employee_name = fields.Char(string ="Employee Name")
    
    emp_dept_name = fields.Char(string="Department")
    
    emp_designation = fields.Char(string="Designation")
    
    date_no_1 = fields.Char(string="01")
    date_no_2 = fields.Char(string="02")
    date_no_3 = fields.Char(string="03")
    date_no_4 = fields.Char(string="04")
    date_no_5 = fields.Char(string="05")
    date_no_6 = fields.Char(string="06")
    date_no_7 = fields.Char(string="07")
    date_no_8 = fields.Char(string="08")
   
    date_no_9 = fields.Char(string="09")
    date_no_10 = fields.Char(string="10")
     
    date_no_11 = fields.Char(string="11") 
    date_no_12 = fields.Char(string="12")
      
    date_no_13 = fields.Char(string="13")
       
    date_no_14 = fields.Char(string="14")
    date_no_15 = fields.Char(string="15")
    date_no_16 = fields.Char(string="16")
    
    
    date_no_17 = fields.Char(string="17")
    date_no_18 = fields.Char(string="18")
    date_no_19 = fields.Char(string="19")
    date_no_20 = fields.Char(string="20")
    date_no_21 = fields.Char(string="21")
    date_no_22 = fields.Char(string="22")
    date_no_23 = fields.Char(string="23")
    date_no_24 = fields.Char(string="24")
   
    date_no_25 = fields.Char(string="25")
    date_no_26 = fields.Char(string="26")
     
    date_no_27 = fields.Char(string="27") 
    date_no_28 = fields.Char(string="28")
      
    date_no_29 = fields.Char(string="29")
       
    date_no_30 = fields.Char(string="30")
    date_no_31 = fields.Char(string="31")
   
              
    leave_reference_id = fields.Many2one('hr.leave', string="Leave Reference")
    
    
    
class LeaveEntryAnalysis(models.TransientModel): 
    
    _name = "leave.analysis.employee" 
    
    _inherit = 'leave.entry.analysis' 
    
    _description = "Leave Analysis Employee"
    
    @api.model
    def default_get(self, default_fields):
        res = super(LeaveEntryAnalysis, self).default_get(default_fields)
        today = fields.date.today()
        first = today.replace(day=1)
        last_month_first = (today - timedelta(days=today.day)).replace(day=1)
        last_month = first - timedelta(days=1)
        res.update({
            'start_date': last_month_first or False,
            'end_date': last_month or False
        })
        return res

    
    
    
    dept_ids = fields.Many2many('hr.department', string ='Department Wise')
    employee_ids = fields.Many2many('hr.employee', string='Employee Wise')
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)
    leave_type_id = fields.Many2one('hr.leave.type',string="Leave") 
    leave_boolean =  fields.Boolean(default=False)
    leave_reference_bool =fields.Boolean(default = False)
    
    twenty_28_bool = fields.Boolean(default = False)
    twenty_29_days_bool = fields.Boolean(default = False)
    thirty_30_bool = fields.Boolean(default = False)
    thirty_one_31_bool = fields.Boolean(default = False)
    
    max_days_in_month = fields.Integer(string="Max Days in Month", compute="_compute_max_days_in_month", store=True)

    leave_reference_id_day_1 = fields.Many2one('hr.leave', string='Leave Reference Day 1')
    leave_reference_id_day_2 = fields.Many2one('hr.leave', string='Leave Reference Day 2')

    @api.depends('start_date' )  # Replace 'some_date_field' with the field determining the month
    def _compute_max_days_in_month(self):
        for record in self:
            if record.start_date:
                # Get the month and year from the date field
                year = record.start_date.year
                month = record.start_date.month
                # Get the maximum number of days in the month
               
                record.max_days_in_month = calendar.monthrange(year, month)[1]
                record.twenty_28_bool = False
                record.twenty_29_days_bool = False
                record.thirty_30_bool = False
                record.thirty_one_31_bool = False

                # Update booleans based on max days
                if record.max_days_in_month == 28:
                    record.twenty_28_bool = True
                elif record.max_days_in_month == 29:
                    record.twenty_28_bool = True
                    record.twenty_29_days_bool = True
                elif record.max_days_in_month == 30:
                    record.twenty_28_bool = True
                    record.twenty_29_days_bool = True
                    record.thirty_30_bool = True
                elif record.max_days_in_month == 31:
                    record.twenty_28_bool = True
                    record.twenty_29_days_bool = True
                    record.thirty_30_bool = True
                    record.thirty_one_31_bool = True
            else:
                record.max_days_in_month = 0  # 
    
    def attendance_view(self):
        for rec in self:
            attendance_search = self.env['hr.attendance.sheet'].search([('employee_id.employee_no','=', self.employee_code),
                                                                        ('request_date_from','>=', self.start_date),
                                                                        ('request_date_to','<=',self.end_date)],limit=1)
            for attendance in attendance_search:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Attendance Sheet',
                    'res_model': 'hr.attendance.sheet',
                    'res_id': attendance.id,
                    'view_mode': 'form',
                    'view_type': 'form',
                    'target': 'current',  
                }
                
                
    def show_leave(self):
        if self.leave_type_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Leave Type',
                'res_model': 'hr.leave',
                'view_mode': 'form',
                'view_id': self.env.ref('hr_holidays.hr_leave_view_form_manager').id,
                'res_id': self.leave_reference_id.id,
                'target': 'current',
            }
    
    
    def generate_leave_entry(self):
    
        start_date = self.start_date
    
        end_date = self.end_date
        
        employee_ids = False
        
        dept_id = False
        
        employee_ids = self.employee_ids
        
        dept_ids = self.dept_ids
        
    
        no_of_days = (end_date - start_date).days
        self._cr.execute('delete from leave_analysis_employee;')  
    
        domain = []
    
     
        domain += [('id' ,'in', self.employee_ids.ids if self.employee_ids else self.env['hr.employee'].search([]).ids),
                   "|",('exit_date','=',False),
                   ('exit_date','>=',start_date)
                   ]
        

        if self.dept_ids:
            domain += [('department_id', 'in', self.dept_ids.ids)]
            
        domain += [('contract_warning','=',False)] 
        employees = self.env['hr.employee'].search(domain, order='employee_no asc')
        national_holidays = self.env['resource.calendar.leaves'].search([
           ('resource_id', '=', False)
        ])
    
        # Convert the records to a list of dates
        holiday_dates = []
        for holiday in national_holidays:
            holiday_start = max(holiday.date_from.date(), self.start_date)
            holiday_end = min(holiday.date_to.date(), self.end_date)
    
            # Check if holiday_start <= holiday_end
            if holiday_start <= holiday_end:
            # Generate a list of dates for each holiday range
                holiday_date = holiday_start
                while holiday_date <= holiday.date_to.date():
                    holiday_dates.append(holiday_date)
                    holiday_date += timedelta(days=1)
    
    
        no = 1            
        for employee in employees:        
            leave_data = {
            's_no': no,
            'employee_code': employee.employee_no,
            'employee_name': employee.name,
            'emp_dept_name': employee.department_id.name,
            'emp_designation': employee.job_id.name,
            'start_date' : self.start_date,
            'end_date' :self.end_date
            }
            working_calendar = employee.resource_calendar_id
    
            if working_calendar:
                attendance_lines = self.env['resource.calendar.attendance'].search([
                    ('calendar_id', '=', working_calendar.id)
                ])
            else:
                attendance_lines = []
    
            for day in range(1, no_of_days + 2):  
                current_day = start_date + timedelta(days=day - 1)
                weekday = current_day.weekday()  
    
                is_working_day = False
                for line in attendance_lines:
                    if int(line.dayofweek) == weekday:
                        is_working_day = True
                        break
                if employee.exit_date and current_day >= employee.exit_date:
                    day_status = 'T'   
                elif current_day in holiday_dates:
                    day_status = 'HO'  # Set the status as Holiday
                elif not is_working_day:
                    day_status = 'WK'
                else:
                    attendance = self.env['hr.attendance'].search([
                        ('employee_id', '=', employee.id),
                        ('check_in', '>=', current_day),
                        ('check_in', '<', current_day + timedelta(days=1))
                    ])
                    leave = self.env['hr.leave'].search([
                    ('employee_id', '=', employee.id),
                    ('date_from', '<=', current_day),
                    ('date_to', '>=', current_day),
                    ('state', '=', 'validate')  # Assuming 'validate' is the approved state
                ], limit=1)
    
                    if leave:
                        leave_data['leave_boolean'] = True
                        leave_data['leave_reference_bool'] = True
                        leave_data['leave_reference_id'] = leave.id 
                        # leave_data['leave_type_id'] = leave.holiday_status_id.id
    
                        # leave_data[f'leave_reference_id_day_{day}'] = leave.id  # Store leave reference for the specific day
                        # leave_data[f'date_no_{day}'] = leave.holiday_status_id.code 
    
    
                        day_status = leave.holiday_status_id.code  
                    else:
                        day_status = '✔' if attendance else 'AB'
                        # leave_data[f'date_no_{day}'] = day_status
                        leave_data['leave_boolean'] = True
    
    
                # Dynamically assign the status to the correct date field
                field_name = f'date_no_{day}'
                if hasattr(self, field_name):
                    leave_data[field_name] = day_status
            self.create(leave_data)
            no += 1
    
    
        action = self.sudo().env.ref('leave_entry.leave_action_entry_window').read()[0]
        return action
    

# class LeaveEntry(models.Model):
#
#     _name = "leave.entry.analysis"
#
#     _description = "Leave Entry Analysis"
#
#
#     s_no = fields.Char(string="S.no")
#
#     employee_code = fields.Char(string="Employee Code")
#
#     employee_name = fields.Char(string ="Employee Name")
#
#     emp_dept_name = fields.Char(string="Department")
#
#     emp_designation = fields.Char(string="Designation")
#
#     date_no_1 = fields.Char(string="01")
#     date_no_2 = fields.Char(string="02")
#     date_no_3 = fields.Char(string="03")
#     date_no_4 = fields.Char(string="04")
#     date_no_5 = fields.Char(string="05")
#     date_no_6 = fields.Char(string="06")
#     date_no_7 = fields.Char(string="07")
#     date_no_8 = fields.Char(string="08")
#
#     date_no_9 = fields.Char(string="09")
#     date_no_10 = fields.Char(string="10")
#
#     date_no_11 = fields.Char(string="11") 
#     date_no_12 = fields.Char(string="12")
#
#     date_no_13 = fields.Char(string="13")
#
#     date_no_14 = fields.Char(string="14")
#     date_no_15 = fields.Char(string="15")
#     date_no_16 = fields.Char(string="16")
#
#
#     date_no_17 = fields.Char(string="17")
#     date_no_18 = fields.Char(string="18")
#     date_no_19 = fields.Char(string="19")
#     date_no_20 = fields.Char(string="20")
#     date_no_21 = fields.Char(string="21")
#     date_no_22 = fields.Char(string="22")
#     date_no_23 = fields.Char(string="23")
#     date_no_24 = fields.Char(string="24")
#
#     date_no_25 = fields.Char(string="25")
#     date_no_26 = fields.Char(string="26")
#
#     date_no_27 = fields.Char(string="27") 
#     date_no_28 = fields.Char(string="28")
#
#     date_no_29 = fields.Char(string="29")
#
#     date_no_30 = fields.Char(string="30")
#     date_no_31 = fields.Char(string="31")
#
#
#     leave_reference_id = fields.Many2one('hr.leave', string="Leave Reference")
#
#
#
# class LeaveEntryAnalysis(models.TransientModel): 
#
#     _name = "leave.analysis.employee" 
#
#     _inherit = 'leave.entry.analysis' 
#
#     _description = "Leave Analysis Employee"
#
#     @api.model
#     def default_get(self, default_fields):
#         res = super(LeaveEntryAnalysis, self).default_get(default_fields)
#         today = fields.date.today()
#         first = today.replace(day=1)
#         last_month_first = (today - timedelta(days=today.day)).replace(day=1)
#         last_month = first - timedelta(days=1)
#         res.update({
#             'start_date': last_month_first or False,
#             'end_date': last_month or False
#         })
#         return res
#
#
#
#
#     dept_ids = fields.Many2many('hr.department', string ='Department Wise')
#     employee_ids = fields.Many2many('hr.employee', string='Employee Wise')
#     start_date = fields.Date('Start Date', required=True)
#     end_date = fields.Date('End Date', required=True)
#     leave_type_id = fields.Many2one('hr.leave.type',string="Leave") 
#     leave_boolean =  fields.Boolean(default=False)
#     leave_reference_bool =fields.Boolean(default = False)
#
#     twenty_28_bool = fields.Boolean(default = False)
#     twenty_29_days_bool = fields.Boolean(default = False)
#     thirty_30_bool = fields.Boolean(default = False)
#     thirty_one_31_bool = fields.Boolean(default = False)
#
#     max_days_in_month = fields.Integer(string="Max Days in Month", compute="_compute_max_days_in_month", store=True)
#
#     leave_reference_id_day_1 = fields.Many2one('hr.leave', string='Leave Reference Day 1')
#     leave_reference_id_day_2 = fields.Many2one('hr.leave', string='Leave Reference Day 2')
#     leave_reference_id_day_3 = fields.Many2one('hr.leave', string='Leave Reference Day 3')
#     leave_reference_id_day_4 = fields.Many2one('hr.leave', string='Leave Reference Day 4')
#     leave_reference_id_day_5 = fields.Many2one('hr.leave', string='Leave Reference Day 5')
#     leave_reference_id_day_6 = fields.Many2one('hr.leave', string='Leave Reference Day 6')
#     leave_reference_id_day_7 = fields.Many2one('hr.leave', string='Leave Reference Day 7')
#     leave_reference_id_day_8 = fields.Many2one('hr.leave', string='Leave Reference Day 8')
#     leave_reference_id_day_9 = fields.Many2one('hr.leave', string='Leave Reference Day 9')
#     leave_reference_id_day_10 = fields.Many2one('hr.leave', string='Leave Reference Day 10')
#     leave_reference_id_day_11 = fields.Many2one('hr.leave', string='Leave Reference Day 11')
#     leave_reference_id_day_12 = fields.Many2one('hr.leave', string='Leave Reference Day 12')
#     leave_reference_id_day_13 = fields.Many2one('hr.leave', string='Leave Reference Day 13')
#     leave_reference_id_day_14 = fields.Many2one('hr.leave', string='Leave Reference Day 14')
#     leave_reference_id_day_15 = fields.Many2one('hr.leave', string='Leave Reference Day 15')
#     leave_reference_id_day_16 = fields.Many2one('hr.leave', string='Leave Reference Day 16')
#     leave_reference_id_day_17 = fields.Many2one('hr.leave', string='Leave Reference Day 17')
#     leave_reference_id_day_18 = fields.Many2one('hr.leave', string='Leave Reference Day 18')
#     leave_reference_id_day_19 = fields.Many2one('hr.leave', string='Leave Reference Day 19')
#     leave_reference_id_day_20 = fields.Many2one('hr.leave', string='Leave Reference Day 20')
#     leave_reference_id_day_21 = fields.Many2one('hr.leave', string='Leave Reference Day 21')
#     leave_reference_id_day_22 = fields.Many2one('hr.leave', string='Leave Reference Day 22')
#     leave_reference_id_day_23 = fields.Many2one('hr.leave', string='Leave Reference Day 23')
#     leave_reference_id_day_24 = fields.Many2one('hr.leave', string='Leave Reference Day 24')
#     leave_reference_id_day_25 = fields.Many2one('hr.leave', string='Leave Reference Day 25')
#     leave_reference_id_day_26 = fields.Many2one('hr.leave', string='Leave Reference Day 26')
#     leave_reference_id_day_27 = fields.Many2one('hr.leave', string='Leave Reference Day 27')
#     leave_reference_id_day_28 = fields.Many2one('hr.leave', string='Leave Reference Day 28')
#     leave_reference_id_day_29 = fields.Many2one('hr.leave', string='Leave Reference Day 29')
#     leave_reference_id_day_30 = fields.Many2one('hr.leave', string='Leave Reference Day 30')
#     leave_reference_id_day_31 = fields.Many2one('hr.leave', string='Leave Reference Day 31')
#
#
#
#     @api.depends('start_date' )  # Replace 'some_date_field' with the field determining the month
#     def _compute_max_days_in_month(self):
#         for record in self:
#             if record.start_date:
#                 # Get the month and year from the date field
#                 year = record.start_date.year
#                 month = record.start_date.month
#                 # Get the maximum number of days in the month
#
#                 record.max_days_in_month = calendar.monthrange(year, month)[1]
#                 record.twenty_28_bool = False
#                 record.twenty_29_days_bool = False
#                 record.thirty_30_bool = False
#                 record.thirty_one_31_bool = False
#
#                 # Update booleans based on max days
#                 if record.max_days_in_month == 28:
#                     record.twenty_28_bool = True
#                 elif record.max_days_in_month == 29:
#                     record.twenty_28_bool = True
#                     record.twenty_29_days_bool = True
#                 elif record.max_days_in_month == 30:
#                     record.twenty_28_bool = True
#                     record.twenty_29_days_bool = True
#                     record.thirty_30_bool = True
#                 elif record.max_days_in_month == 31:
#                     record.twenty_28_bool = True
#                     record.twenty_29_days_bool = True
#                     record.thirty_30_bool = True
#                     record.thirty_one_31_bool = True
#             else:
#                 record.max_days_in_month = 0  # 
#
#     def attendance_view(self):
#         for rec in self:
#             attendance_search = self.env['hr.attendance.sheet'].search([('employee_id.employee_no','=', self.employee_code),
#                                                                         ('request_date_from','>=', self.start_date),
#                                                                         ('request_date_to','<=',self.end_date)],limit=1)
#             for attendance in attendance_search:
#                 return {
#                     'type': 'ir.actions.act_window',
#                     'name': 'Attendance Sheet',
#                     'res_model': 'hr.attendance.sheet',
#                     'res_id': attendance.id,
#                     'view_mode': 'form',
#                     'view_type': 'form',
#                     'target': 'current',  
#                 }
#
#
#     def show_leave(self):
#         if self.leave_type_id:
#             return {
#                 'type': 'ir.actions.act_window',
#                 'name': 'Leave Type',
#                 'res_model': 'hr.leave',
#                 'view_mode': 'form',
#                 'view_id': self.env.ref('hr_holidays.hr_leave_view_form_manager').id,
#                 'res_id': self.leave_reference_id.id,
#                 'target': 'current',
#             }
#
#     def generate_leave_entry(self):
#         start_date = self.start_date
#         end_date = self.end_date
#         no_of_days = (end_date - start_date).days
#         self._cr.execute('delete from leave_analysis_employee;')  # Clear the previous analysis
#         domain =[]
#
#         domain = [('id', 'in', self.employee_ids.ids if self.employee_ids else self.env['hr.employee'].search([]).ids),
#                     '|',  # This ensures either the employee has no exit date or their exit date is after the report start date.
#                     ('exit_date', '=', False),
#                     ('exit_date', '>=', self.start_date)]
#
#         print("")
#         if self.dept_ids:
#             domain += [('department_id', 'in', self.dept_ids.ids)]
#
#         employees = self.env['hr.employee'].search(domain, order='employee_no asc')
#         national_holidays = self.env['resource.calendar.leaves'].search([
#             ('resource_id', '=', False)
#         ])
#
#         # Convert the records to a list of holiday dates
#         holiday_dates = []
#         for holiday in national_holidays:
#             holiday_start = max(holiday.date_from.date(), self.start_date)
#             holiday_end = min(holiday.date_to.date(), self.end_date)
#
#             if holiday_start <= holiday_end:
#                 holiday_date = holiday_start
#                 while holiday_date <= holiday_end:
#                     holiday_dates.append(holiday_date)
#                     holiday_date += timedelta(days=1)
#
#         no = 1
#         # Use a set to store unique leaves for the form view
#         processed_leaves = set()
#
#         for employee in employees:
#             leave_data = {
#                 's_no': no,
#                 'employee_code': employee.employee_no,
#                 'employee_name': employee.name,
#                 'emp_dept_name': employee.department_id.name,
#                 'emp_designation': employee.job_id.name,
#                 'start_date': self.start_date,
#                 'end_date': self.end_date
#             }
#
#             working_calendar = employee.resource_calendar_id
#             attendance_lines = self.env['resource.calendar.attendance'].search([
#                 ('calendar_id', '=', working_calendar.id)
#             ]) if working_calendar else []
#
#             # Get all validated leaves for the employee
#             employee_leaves = self.env['hr.leave'].search([
#                 ('employee_id', '=', employee.id),
#                 ('state', '=', 'validate'),
#                 ('date_from', '<=', self.end_date),
#                 ('date_to', '>=', self.start_date)
#             ])
#
#             for day in range(1, no_of_days + 2):
#                 current_day = start_date + timedelta(days=day - 1)
#                 weekday = current_day.weekday()
#
#                 is_working_day = any(int(line.dayofweek) == weekday for line in attendance_lines)
#
#                 # Check for employee exit
#                 if employee.exit_date and current_day >= employee.exit_date:
#                     day_status = 'T'
#                 # Check if it's a national holiday
#                 elif current_day in holiday_dates:
#                     day_status = 'HO'
#                 # Check if it's a working day
#                 elif not is_working_day:
#                     day_status = 'WK'
#                 else:
#                     # Check if the employee is on leave for the current day
#                     leave = next((l for l in employee_leaves if l.date_from.date() <= current_day <= l.date_to.date()), None)
#
#                     if leave:
#                         leave_data[f'leave_reference_id_day_{day}'] = leave.id
#                         print("/////////////leave if",leave.id,leave_data[f'leave_reference_id_day_{day}'])
#                         day_status = leave.holiday_status_id.code
#                         print(".........daystatys",day_status)
#                         processed_leaves.add((employee.id, leave.id))
#                         print("............processed leaves",processed_leaves)
#                     else:
#                         # Check attendance for the current day
#                         attendance = self.env['hr.attendance'].search([
#                             ('employee_id', '=', employee.id),
#                             ('check_in', '>=', current_day),
#                             ('check_in', '<', current_day + timedelta(days=1))
#                         ])
#                         day_status = '✔' if attendance else 'AB'
#
#                 # Dynamically assign the status to the correct date field
#                 field_name = f'date_no_{day}'
#                 if hasattr(self, field_name):
#                     leave_data[field_name] = day_status
#
#             self.create(leave_data)
#             no += 1
#
#         action = self.sudo().env.ref('leave_entry.leave_action_entry_window').read()[0]
#         return action

    
    # def generate_leave_entry(self):
    #     start_date = self.start_date
    #     end_date = self.end_date
    #     no_of_days = (end_date - start_date).days
    #     self._cr.execute('delete from leave_analysis_employee;')  # Clear the previous analysis
    #
    #     domain = [
    #         ('id', 'in', self.employee_ids.ids if self.employee_ids else self.env['hr.employee'].search([]).ids),
    #         "|", ('exit_date', '=', False),
    #         ('exit_date', '>=', start_date)
    #     ]
    #
    #     if self.dept_ids:
    #         domain += [('department_id', 'in', self.dept_ids.ids)]
    #
    #     employees = self.env['hr.employee'].search(domain, order='employee_no asc')
    #     national_holidays = self.env['resource.calendar.leaves'].search([
    #         ('resource_id', '=', False)
    #     ])
    #
    #     # Convert the records to a list of holiday dates
    #     holiday_dates = []
    #     for holiday in national_holidays:
    #         holiday_start = max(holiday.date_from.date(), self.start_date)
    #         holiday_end = min(holiday.date_to.date(), self.end_date)
    #
    #         if holiday_start <= holiday_end:
    #             holiday_date = holiday_start
    #             while holiday_date <= holiday_end:
    #                 holiday_dates.append(holiday_date)
    #                 holiday_date += timedelta(days=1)
    #
    #     no = 1
    #     for employee in employees:
    #         leave_data = {
    #             's_no': no,
    #             'employee_code': employee.employee_no,
    #             'employee_name': employee.name,
    #             'emp_dept_name': employee.department_id.name,
    #             'emp_designation': employee.job_id.name,
    #             'start_date': self.start_date,
    #             'end_date': self.end_date
    #         }
    #
    #         working_calendar = employee.resource_calendar_id
    #         attendance_lines = self.env['resource.calendar.attendance'].search([
    #             ('calendar_id', '=', working_calendar.id)
    #         ]) if working_calendar else []
    #
    #         # **Define `employee_leaves` for the current employee**
    #         employee_leaves = self.env['hr.leave'].search([
    #             ('employee_id', '=', employee.id),
    #             ('state', '=', 'validate'),
    #             ('date_from', '<=', self.end_date),
    #             ('date_to', '>=', self.start_date)
    #         ])
    #
    #         for day in range(1, no_of_days + 2):
    #             current_day = start_date + timedelta(days=day - 1)
    #             weekday = current_day.weekday()
    #
    #             is_working_day = any(int(line.dayofweek) == weekday for line in attendance_lines)
    #
    #             # Check for employee exit
    #             if employee.exit_date and current_day >= employee.exit_date:
    #                 day_status = 'T'
    #             # Check if it's a national holiday
    #             elif current_day in holiday_dates:
    #                 day_status = 'HO'
    #             # Check if it's a working day
    #             elif not is_working_day:
    #                 day_status = 'WK'
    #             else:
    #                 # Check if the employee is on leave for the current day
    #                 leave = next((l for l in employee_leaves if l.date_from.date() <= current_day <= l.date_to.date()), None)
    #
    #                 if leave:
    #                     leave_data[f'leave_reference_id_day_{day}'] = leave.id
    #                     day_status = leave.holiday_status_id.code
    #                 else:
    #                     # Check attendance for the current day
    #                     attendance = self.env['hr.attendance'].search([
    #                         ('employee_id', '=', employee.id),
    #                         ('check_in', '>=', current_day),
    #                         ('check_in', '<', current_day + timedelta(days=1))
    #                     ])
    #                     day_status = '✔' if attendance else 'AB'
    #
    #             # Dynamically assign the status to the correct date field
    #             field_name = f'date_no_{day}'
    #             if hasattr(self, field_name):
    #                 leave_data[field_name] = day_status
    #
    #         self.create(leave_data)
    #         no += 1
    #
    #     action = self.sudo().env.ref('leave_entry.leave_action_entry_window').read()[0]
    #     return action

    
    # '''working correctly'''
    # def generate_leave_entry(self):
    #
    #     start_date = self.start_date
    #
    #     end_date = self.end_date
    #
    #     no_of_days = (end_date - start_date).days
    #     self._cr.execute('delete from leave_analysis_employee;')  
    #
    #     domain = []
    #
    #     domain += [('id' ,'in', self.employee_ids.ids if self.employee_ids else self.env['hr.employee'].search([]).ids),
    #                "|",('exit_date','=',False),
    #                ('exit_date','>=',start_date)
    #                ]
    #
    #     if self.dept_ids:
    #         domain += [('department_id', 'in', self.dept_ids.ids)]
    #
    #
    #     employees = self.env['hr.employee'].search(domain, order='employee_no asc')
    #     national_holidays = self.env['resource.calendar.leaves'].search([
    #        ('resource_id', '=', False)
    #     ])
    #
    #     # Convert the records to a list of dates
    #     holiday_dates = []
    #     for holiday in national_holidays:
    #         holiday_start = max(holiday.date_from.date(), self.start_date)
    #         holiday_end = min(holiday.date_to.date(), self.end_date)
    #
    #         # Check if holiday_start <= holiday_end
    #         if holiday_start <= holiday_end:
    #         # Generate a list of dates for each holiday range
    #             holiday_date = holiday_start
    #             while holiday_date <= holiday.date_to.date():
    #                 holiday_dates.append(holiday_date)
    #                 holiday_date += timedelta(days=1)
    #
    #
    #     no = 1            
    #     for employee in employees:        
    #         leave_data = {
    #         's_no': no,
    #         'employee_code': employee.employee_no,
    #         'employee_name': employee.name,
    #         'emp_dept_name': employee.department_id.name,
    #         'emp_designation': employee.job_id.name,
    #         'start_date' : self.start_date,
    #         'end_date' :self.end_date
    #         }
    #         working_calendar = employee.resource_calendar_id
    #
    #         if working_calendar:
    #             attendance_lines = self.env['resource.calendar.attendance'].search([
    #                 ('calendar_id', '=', working_calendar.id)
    #             ])
    #         else:
    #             attendance_lines = []
    #
    #         for day in range(1, no_of_days + 2):  
    #             current_day = start_date + timedelta(days=day - 1)
    #             weekday = current_day.weekday()  
    #
    #             is_working_day = False
    #             for line in attendance_lines:
    #                 if int(line.dayofweek) == weekday:
    #                     is_working_day = True
    #                     break
    #             if employee.exit_date and current_day >= employee.exit_date:
    #                 day_status = 'T'   
    #             elif current_day in holiday_dates:
    #                 day_status = 'HO'  # Set the status as Holiday
    #             elif not is_working_day:
    #                 day_status = 'WK'
    #             else:
    #                 attendance = self.env['hr.attendance'].search([
    #                     ('employee_id', '=', employee.id),
    #                     ('check_in', '>=', current_day),
    #                     ('check_in', '<', current_day + timedelta(days=1))
    #                 ])
    #                 leave = self.env['hr.leave'].search([
    #                 ('employee_id', '=', employee.id),
    #                 ('date_from', '<=', current_day),
    #                 ('date_to', '>=', current_day),
    #                 ('state', '=', 'validate')  # Assuming 'validate' is the approved state
    #             ], limit=1)
    #
    #                 if leave:
    #                     leave_data['leave_boolean'] = True
    #                     leave_data['leave_reference_bool'] = True
    #                     leave_data['leave_reference_id'] = leave.id 
    #                     # leave_data['leave_type_id'] = leave.holiday_status_id.id
    #
    #                     # leave_data[f'leave_reference_id_day_{day}'] = leave.id  # Store leave reference for the specific day
    #                     # leave_data[f'date_no_{day}'] = leave.holiday_status_id.code 
    #
    #
    #                     day_status = leave.holiday_status_id.code  
    #                 else:
    #                     day_status = '✔' if attendance else 'AB'
    #                     # leave_data[f'date_no_{day}'] = day_status
    #                     leave_data['leave_boolean'] = True
    #
    #
    #             # Dynamically assign the status to the correct date field
    #             field_name = f'date_no_{day}'
    #             if hasattr(self, field_name):
    #                 leave_data[field_name] = day_status
    #         self.create(leave_data)
    #         no += 1
    #
    #
    #     action = self.sudo().env.ref('leave_entry.leave_action_entry_window').read()[0]
    #     return action
    #

    
    
    # def generate_leave_entry(self):
    #     start_date = self.start_date
    #     end_date = self.end_date
    #     no_of_days = (end_date - start_date).days
    #     self._cr.execute('delete from leave_analysis_employee;')
    #
    #     domain = [
    #         ('id', 'in', self.employee_ids.ids if self.employee_ids else self.env['hr.employee'].search([]).ids),
    #         '|', ('exit_date', '=', False),
    #         ('exit_date', '>=', start_date)
    #     ]
    #
    #     if self.dept_ids:
    #         domain += [('department_id', 'in', self.dept_ids.ids)]
    #
    #     employees = self.env['hr.employee'].search(domain, order='employee_no asc')
    #     national_holidays = self.env['resource.calendar.leaves'].search([
    #         ('resource_id', '=', False)
    #     ])
    #
    #     # Convert holidays to a list of dates
    #     holiday_dates = []
    #     for holiday in national_holidays:
    #         holiday_start = max(holiday.date_from.date(), self.start_date)
    #         holiday_end = min(holiday.date_to.date(), self.end_date)
    #
    #         if holiday_start <= holiday_end:
    #             holiday_date = holiday_start
    #             while holiday_date <= holiday_end:
    #                 holiday_dates.append(holiday_date)
    #                 holiday_date += timedelta(days=1)
    #
    #     no = 1
    #     for employee in employees:
    #         leave_data = {
    #             's_no': no,
    #             'employee_code': employee.employee_no,
    #             'employee_name': employee.name,
    #             'emp_dept_name': employee.department_id.name,
    #             'emp_designation': employee.job_id.name,
    #             'start_date': self.start_date,
    #             'end_date': self.end_date
    #         }
    #
    #         working_calendar = employee.resource_calendar_id
    #         attendance_lines = self.env['resource.calendar.attendance'].search([
    #             ('calendar_id', '=', working_calendar.id)
    #         ]) if working_calendar else []
    #
    #         for day in range(1, no_of_days + 2):  # +2 to include the end date
    #             current_day = start_date + timedelta(days=day - 1)
    #             weekday = current_day.weekday()
    #
    #             is_working_day = any(int(line.dayofweek) == weekday for line in attendance_lines)
    #
    #             if employee.exit_date and current_day >= employee.exit_date:
    #                 day_status = 'T'
    #             elif current_day in holiday_dates:
    #                 day_status = 'HO'
    #             elif not is_working_day:
    #                 day_status = 'WK'
    #             else:
    #                 attendance = self.env['hr.attendance'].search([
    #                     ('employee_id', '=', employee.id),
    #                     ('check_in', '>=', current_day),
    #                     ('check_in', '<', current_day + timedelta(days=1))
    #                 ])
    #                 leave = self.env['hr.leave'].search([
    #                     ('employee_id', '=', employee.id),
    #                     ('date_from', '<=', current_day),
    #                     ('date_to', '>=', current_day),
    #                     ('state', '=', 'validate')
    #                 ], limit=1)
    #
    #                 if leave:
    #                     leave_data[f'leave_reference_id_day_{day}'] = leave.id
    #                     day_status = leave.holiday_status_id.code
    #                 else:
    #                     day_status = '✔' if attendance else 'AB'
    #
    #             leave_data[f'date_no_{day}'] = day_status
    #
    #         self.env['leave.analysis.employee'].create(leave_data)
    #         no += 1
    #
    #     action = self.sudo().env.ref('leave_entry.leave_action_entry_window').read()[0]
    #     return action
    #

    
    # ''' working correctly'''
    # def generate_leave_entry(self):
    #
    #     start_date = self.start_date
    #
    #     end_date = self.end_date
    #
    #     no_of_days = (end_date - start_date).days
    #     self._cr.execute('delete from leave_analysis_employee;')  
    #
    #     domain = []
    #
    #     domain += [('id' ,'in', self.employee_ids.ids if self.employee_ids else self.env['hr.employee'].search([]).ids),
    #                "|",('exit_date','=',False),
    #                ('exit_date','>=',start_date)
    #                ]
    #
    #     if self.dept_ids:
    #         domain += [('department_id', 'in', self.dept_ids.ids)]
    #
    #
    #     employees = self.env['hr.employee'].search(domain, order='employee_no asc')
    #     national_holidays = self.env['resource.calendar.leaves'].search([
    #        ('resource_id', '=', False)
    #     ])
    #
    #     # Convert the records to a list of dates
    #     holiday_dates = []
    #     for holiday in national_holidays:
    #         holiday_start = max(holiday.date_from.date(), self.start_date)
    #         holiday_end = min(holiday.date_to.date(), self.end_date)
    #
    #         # Check if holiday_start <= holiday_end
    #         if holiday_start <= holiday_end:
    #         # Generate a list of dates for each holiday range
    #             holiday_date = holiday_start
    #             while holiday_date <= holiday.date_to.date():
    #                 holiday_dates.append(holiday_date)
    #                 holiday_date += timedelta(days=1)
    #
    #
    #     no = 1            
    #     for employee in employees:        
    #         leave_data = {
    #         's_no': no,
    #         'employee_code': employee.employee_no,
    #         'employee_name': employee.name,
    #         'emp_dept_name': employee.department_id.name,
    #         'emp_designation': employee.job_id.name,
    #         'start_date' : self.start_date,
    #         'end_date' :self.end_date
    #         }
    #         working_calendar = employee.resource_calendar_id
    #
    #         if working_calendar:
    #             attendance_lines = self.env['resource.calendar.attendance'].search([
    #                 ('calendar_id', '=', working_calendar.id)
    #             ])
    #         else:
    #             attendance_lines = []
    #
    #         for day in range(1, no_of_days + 2):  # +2 to include the end date
    #             current_day = start_date + timedelta(days=day - 1)
    #             weekday = current_day.weekday()  # Monday = 0, Sunday = 6
    #
    #             is_working_day = False
    #             for line in attendance_lines:
    #                 if int(line.dayofweek) == weekday:
    #                     is_working_day = True
    #                     break
    #             if employee.exit_date and current_day >= employee.exit_date:
    #                 day_status = 'T'   
    #             elif current_day in holiday_dates:
    #                 day_status = 'HO'  # Set the status as Holiday
    #             elif not is_working_day:
    #                 day_status = 'WK'
    #             else:
    #                 attendance = self.env['hr.attendance'].search([
    #                     ('employee_id', '=', employee.id),
    #                     ('check_in', '>=', current_day),
    #                     ('check_in', '<', current_day + timedelta(days=1))
    #                 ])
    #                 leave = self.env['hr.leave'].search([
    #                 ('employee_id', '=', employee.id),
    #                 ('date_from', '<=', current_day),
    #                 ('date_to', '>=', current_day),
    #                 ('state', '=', 'validate')  # Assuming 'validate' is the approved state
    #             ], limit=1)
    #
    #                 if leave:
    #                     leave_data['leave_boolean'] = True
    #                     leave_data['leave_reference_bool'] = True
    #                     # leave_data['leave_reference_id'] = leave.id 
    #                     # leave_data['leave_type_id'] = leave.holiday_status_id.id
    #
    #                     leave_data[f'leave_reference_id_day_{day}'] = leave.id  # Store leave reference for the specific day
    #                     leave_data[f'date_no_{day}'] = leave.holiday_status_id.code 
    #
    #
    #                     day_status = leave.holiday_status_id.code  
    #                 else:
    #                     day_status = '✔' if attendance else 'AB'
    #                     leave_data[f'date_no_{day}'] = day_status
    #                     leave_data['leave_boolean'] = True
    #
    #
    #             # Dynamically assign the status to the correct date field
    #             field_name = f'date_no_{day}'
    #             if hasattr(self, field_name):
    #                 leave_data[field_name] = day_status
    #         self.create(leave_data)
    #         no += 1
    #
    #
    #     action = self.sudo().env.ref('leave_entry.leave_action_entry_window').read()[0]
    #     return action
    #

    

        
        
        
        
       
    
    
    
    
     
    
    
    