from odoo import api, fields, models, _
from datetime import date, time, datetime, timedelta
import base64
import io
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

class DailyAttendanceReport(models.TransientModel):
    
    _name = "daily.attendance.report"
    
    _description = "Daily Attendance Report"
    
    # @api.model
    # def default_get(self, default_fields):
    #     res = super(DailyAttendanceReport, self).default_get(default_fields)
    #     today = fields.date.today()
    #     first = today.replace(day=1)
    #     today_month_first = first
    #     last_day_month = today_month_first 
    #
    #     # last_month_first = (today - timedelta(days=today.day)).replace(day=1)
    #     # last_month = first - timedelta(days=1)
    #     res.update({
    #         'from_date': today_month_first or False,
    #         'to_date': last_month or False
    #     })
    #     return res
    
    
    employee_ids = fields.Many2many('hr.employee', string="Employee")
    
    department_ids = fields.Many2many('hr.department', string = "Department")
    
    from_date = fields.Date(string = "From Date", default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    
    to_date = fields.Date(string = "To Date", default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    
    sort_by = fields.Selection ([('department', 'Department'),('employee','Employee') ,('date','Date')],string="Sort by")
    
    attendance_policy_ids = fields.Many2many('hr.attendance.policies',string="Policy")
    
    status_filter = fields.Selection(
                    [('weekend', 'Week End'),
                     ('absence', 'Absence'),
                     ('leave', 'Leave'),
                     ('weekday', 'WeekDay'),
                     ('holiday','Public Holiday'),
                     ],  string="Status")
    
    summary_based_report = fields.Boolean('Summary Based')
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,required=True)

    report_for_option = fields.Selection([('all','All'),('overtime','Overtime Only'),('latein','Late In only'),('early_out','Early Out Only')],default='all',string="Report For")
    
    logo = fields.Binary("Company Logo")
    
    
    @api.constrains('from_date', 'to_date')
    def _check_from_date(self):
        if self.filtered(lambda c: c.to_date and c.from_date > c.to_date):
            raise ValidationError(_('From Date must be less than To  Date.'))
    
    
    def daily_attendance_excel(self):
        company = self.company_id
        
        # Decode the company logo
        logo = base64.b64decode(company.logo) if company.logo else False
        
        data ={
            
            'form_data' :self.read()[0],
             'model' : 'daily.attendance.report',
               'logo': logo,
            }
        
        return self.env.ref('daily_attendance_report.report_daily_attendance_report_xlsx').report_action(self, data = data)
    
    
    def daily_attendance_pdf(self):
        
        attendance_lst = []
        
        domain = []
        
        employee_ids = False
        
        department_ids = False
        
        attendance_policy_ids = False
        
        employee_ids = self.employee_ids
        
        department_ids = self.department_ids
        
        attendance_policy_ids = self.attendance_policy_ids
        
        
        if self.employee_ids :
            
            domain += [('employee_id' ,'in' , self.employee_ids.ids)]
            
        else :
            
            domain += [('employee_id' , 'in', self.env['hr.employee'].search([]).ids)]
            
            
        if self.department_ids :
             
            domain += [('employee_id.department_id', 'in' , self.department_ids.ids)]
            
            
        if self.from_date :
            
            domain += [('request_date_from' ,'>=' , self.from_date)]
            
        if self.to_date : 
            
            domain += [('request_date_to' ,'<=' , self.to_date)]  
         
        attendance_sheet_total = False 
        
        if self.summary_based_report:
            attendance_sheet_total = self.env['hr.attendance.sheet'].search(domain,order="employee_number asc") 
            
        if self.attendance_policy_ids:
            domain += [('employee_id.contract_id.attend_police_id','in', self.attendance_policy_ids.ids)]
        
        attendance_sheet_search = self.env['hr.attendance.sheet'].search(domain,order="employee_number asc") 
        
        attendance_lines = self.env['hr.attendance.sheet.line'].search([('name_id', 'in', attendance_sheet_search.ids)],order="date ASC")
        
        attendance_sheet_lines = attendance_sheet_search.attendance_sheet_ids
        # attendance_sheet_lines = sorted(
        #     attendance_lines, 
        #     key=lambda line: (line.date, line.name_id.employee_id.employee_no)
        # )
        
        
        
        if self.sort_by:
            if self.sort_by =='department':
                attendance_sheet_search = attendance_sheet_search.filtered(lambda c:c.employee_id.department_id)
                attendance_sheet_search = attendance_sheet_search.sorted(key=lambda c:c.employee_id.department_id.name.lower())
                attendance_sheet_lines = attendance_sheet_search.attendance_sheet_ids
                
            elif self.sort_by == 'employee':
                attendance_sheet_search = attendance_sheet_search.filtered(lambda c:c.employee_id)
                attendance_sheet_search = attendance_sheet_search.sorted(key = lambda c:c.employee_id.name.lower())
                attendance_sheet_lines = attendance_sheet_search.attendance_sheet_ids

            elif self.sort_by == 'date':
                
                # Sort by date, and we will display all employees under each date
                attendance_sheet_search = attendance_sheet_search.sorted(key=lambda c: min([line.date for line in c.attendance_sheet_ids]))            #

        if self.report_for_option =='overtime' :
            attendance_sheet_lines = attendance_sheet_search.mapped('attendance_sheet_ids').filtered(
        lambda line: line.overtime > 0.0 and line.date >= self.from_date and line.date <= self.to_date
        )
            
        if self.report_for_option =='latein' :
            attendance_sheet_lines = attendance_sheet_search.mapped('attendance_sheet_ids').filtered(
        lambda line: line.latein > 0.0 and line.date >= self.from_date and line.date <= self.to_date
        ) 
        if self.report_for_option =='early_out' :
            attendance_sheet_lines = attendance_sheet_search.mapped('attendance_sheet_ids').filtered(
        lambda line: line.early_out_line > 0.0 and line.date >= self.from_date and line.date <= self.to_date
        )  
        if  self.report_for_option =='all':
            attendance_sheet_lines = attendance_sheet_search.mapped('attendance_sheet_ids').filtered(
        lambda line: line.date >= self.from_date and line.date <= self.to_date)

        if self.status_filter:            
            if self.status_filter=='weekday':
                attendance_sheet_lines = attendance_sheet_search.mapped('attendance_sheet_ids').filtered(
            lambda line: (
                (line.status=='weekday') 
                and line.date >= self.from_date and line.date <= self.to_date))
                
            if self.status_filter=='weekend':
                attendance_sheet_lines = attendance_sheet_search.mapped('attendance_sheet_ids').filtered(
            lambda line: (
                (line.status=='weekend') 
                and line.date >= self.from_date and line.date <= self.to_date))   
                
            if self.status_filter=='absence':
                attendance_sheet_lines = attendance_sheet_search.mapped('attendance_sheet_ids').filtered(
            lambda line: (
                (line.status=='absence') 
                and line.date >= self.from_date and line.date <= self.to_date))
            
            if self.status_filter == 'leave': 
                attendance_sheet_lines = attendance_sheet_search.mapped('attendance_sheet_ids').filtered(
            lambda line: (
                (line.status=='leave') 
                and line.date >= self.from_date and line.date <= self.to_date))  
            
            if self.status_filter == 'holiday': 
                attendance_sheet_lines = attendance_sheet_search.mapped('attendance_sheet_ids').filtered(
            lambda line: (
                (line.status=='holiday') 
                and line.date >= self.from_date and line.date <= self.to_date))  
                
                
        attendance_by_date = {}

        # Group attendance lines by date
        for line in attendance_lines:
            attendance_date = line.date
            if attendance_date not in attendance_by_date:
                attendance_by_date[attendance_date] = []
            attendance_by_date[attendance_date].append(line)
        
        # Sort dates for ordered display
        sorted_dates = sorted(attendance_by_date.keys())
        
       
        
        if self.sort_by == 'date':
            date_lst = []
            for attendance_date in sorted_dates:
              
                for line in attendance_by_date[attendance_date]:
                    
                    hours_psign = int(line.psignin)
                    min_psign = int((line.psignin - hours_psign) * 60)
                    
                    hours_psignout = int(line.psignout)
                    min_psignout = int((line.psignout - hours_psignout) * 60)
                    
                    hours_asignin = int(line.asignin)
                    min_asignin = int((line.asignin - hours_asignin) * 60)
                
                        
                    hours_asignout = int(line.asignout)
                    min_asignout = int((line.asignout - hours_asignout) * 60)
                
                    hours_latein = int(line.latein)
                    min_latein = int((line.latein - hours_latein) * 60)
                   
                    hours_earlyout = int(line.early_out_line)
                    min_earlyout = int((line.early_out_line - hours_earlyout)* 60)
                  
                    hours_overtime = int(line.overtime)
                    min_overtime = int((line.overtime - hours_overtime) * 60)
                
                   
                    date_lst.append({
                            
                        'emp_no': line.name_id.employee_number or ' ',
                        'emp_name' : line.name_id.employee_id.name or ' ',
                        'dept_name' : line.name_id.employee_id.department_id.name or '',
                        'date' : line.date.strftime('%d-%m-%Y') or ' ',
                        'day' : line.day or ' ',
                        'clock_in' : "{:02d}:{:02d}".format(hours_psign,min_psign) or ' ',
                        'clock_out' :  "{:02d}:{:02d}".format(hours_psignout,min_psignout) or ' ',
                        'check_in' : "{:02d}:{:02d}".format(hours_asignin,min_asignin) or ' ',
                        'check_out' :"{:02d}:{:02d}".format(hours_asignout,min_asignout ) or '',
                        'late_in' :"{:02d}:{:02d}".format(hours_latein,min_latein) or ' ',
                        'early_out' :"{:02d}:{:02d}".format(hours_earlyout, min_earlyout) or ' ',
                        'overtime' :"{:02d}:{:02d}".format(hours_overtime,min_overtime) or '',
                        'status' : line.status.capitalize() or ' ',
                        'work_type' : line.work_type or ' '
                        
                        })
                
                   
                 
                
            if len(date_lst)==0:
                raise ValidationError("Attendance is not there for that particular Period") 
            

            
            data ={
                
                'form_data': self.read()[0],
                'date_attendance_employee' : date_lst,
                'from_date' : self.from_date.strftime("%d-%m-%Y"),
                'to_date' : self.to_date.strftime("%d-%m-%Y")
                
                }   
            
            
            return self.env.ref('daily_attendance_report.action_report_daily_attendance_pdf').with_context(landscape=True).report_action(self, data = data) 
        
                    
         
           
                            
        else:
            if not self.summary_based_report:
                attendance_lst = []
                
                for line in sorted(attendance_sheet_lines, key=lambda l: (l.name_id.employee_id.employee_no, l.date)):

                # for line in attendance_sheet_lines:
                    
                    hours_psign = int(line.psignin)
                    min_psign = int((line.psignin - hours_psign)* 60)
                    
                    hours_psignout = int(line.psignout)
                    min_psignout = int((line.psignout - hours_psignout)*60)
                    
                    hours_asignin = int(line.asignin)
                    min_asignin = int((line.asignin - hours_asignin) * 60)
                
                    hours_asignout = int(line.asignout)
                    min_asignout = int((line.asignout - hours_asignout) * 60)
                    
                    hours_latein = int(line.latein)
                    min_latein = int((line.latein - hours_latein) * 60)
                    
                    hours_earlyout = int(line.early_out_line)
                    min_earlyout = int((line.early_out_line - hours_earlyout)* 60)
                    
                    hours_overtime = int(line.overtime)
                    min_overtime = int((line.overtime - hours_overtime) * 60)
                    
                    attendance_lst.append({
                            
                        'emp_no': line.name_id.employee_number or ' ',
                        'emp_name' : line.name_id.employee_id.name or ' ',
                        'dept_name' : line.name_id.employee_id.department_id.name or '',
                        'date' : line.date.strftime('%d-%m-%Y') or ' ',
                        'day' : line.day or ' ',
                        'clock_in' : "{:02d}:{:02d}".format(hours_psign,min_psign) or ' ',
                        'clock_out' :  "{:02d}:{:02d}".format(hours_psignout,min_psignout) or ' ',
                        'check_in' : "{:02d}:{:02d}".format(hours_asignin,min_asignin) or ' ',
                        'check_out' :"{:02d}:{:02d}".format(hours_asignout,min_asignout ) or '',
                        'late_in' :"{:02d}:{:02d}".format(hours_latein,min_latein) or ' ',
                        'early_out' :"{:02d}:{:02d}".format(hours_earlyout, min_earlyout) or ' ',
                        'overtime' :"{:02d}:{:02d}".format(hours_overtime,min_overtime) or '',
                        'status' : line.status.capitalize() or ' ',
                        'work_type' : line.work_type or ' '
                        
                        })
                
                   
                 
                
                if len(attendance_lst)==0:
                    raise ValidationError("Attendance is not there for that particular Period") 
                
    
                
                data ={
                    
                    'form_data': self.read()[0],
                    'attendance_employee' : attendance_lst,
                    'from_date' : self.from_date.strftime("%d-%m-%Y"),
                    'to_date' : self.to_date.strftime("%d-%m-%Y")
                    
                    }   
                
                
                return self.env.ref('daily_attendance_report.action_report_daily_attendance_pdf').with_context(landscape=True).report_action(self, data = data) 
        
        
        
        
            if self.summary_based_report:
                
                summary_lst = []
                
                for line in attendance_sheet_total: 
                    
                    total_late_in = 0.0
                    total_early_out = 0.0
                    total_overtime = 0.0
                    
                    late_in_count = 0
                    early_out_count = 0
                    overtime_count = 0
                    
                    
                    
                    
                    for total in line.attendance_sheet_ids:
                        
                        if total.latein > 0.0:
                            late_in_count += 1
                            
                        if total.early_out_line > 0.0:
                            early_out_count  += 1
                            
                        if total.overtime > 0.0:
                            overtime_count += 1
                        
                        total_late_in += round(total.latein,2)
                        hours_latein_total = int(total_late_in)
                        min_latein_total = int((total_late_in - hours_latein_total)*60)
                    
                      
                    
                        total_early_out += round(total.early_out_line,2)
                        hours_earlyout = int(total_early_out)
                        min_earlyout = int((total_early_out - hours_earlyout) * 60)
                    
                        
                        total_overtime += round(total.overtime,2)
                        hours_overtime = int(total_overtime)
                        min_overtime = int((total_overtime - hours_overtime)* 60)
                    
                        
                    # summary_lst.append(line.employee_id.name)
                    
                    summary_lst.append({
                            
                        'emp_no': line.employee_id.employee_no or ' ',
                        'emp_name' : line.employee_id.name or ' ',
                        'dept_name' : line.employee_id.department_id.name or '',
                         
                        'late_in_count' : late_in_count or ' ',
                        
                        'late_in' :"{:02d}:{:02d}".format(hours_latein_total,min_latein_total) or ' ',
                        
                        'early_out_count' : early_out_count or ' ',
                        
                        'early_out' :"{:02d}:{:02d}".format(hours_earlyout,min_earlyout) or ' ',
                        
                        'overtime_count' : overtime_count or ' ',
                         
                        'overtime' :"{:02d}:{:02d}".format(hours_overtime,min_overtime) or ' ',
                       
                        
                        })
                
                if len(summary_lst)==0:
                    raise ValidationError("Attendance Summary is not there for that particular Period") 
                
                
                data ={
                    
                    'form_data': self.read()[0],
                    'total_attendance_employee' : summary_lst,
                    'from_date' : self.from_date.strftime("%d-%m-%Y"),
                    'to_date' : self.to_date.strftime("%d-%m-%Y")
                    
                    }   
                
                
                return self.env.ref('daily_attendance_report.action_report_daily_attendance_pdf').with_context(landscape=True).report_action(self, data = data) 
        
        
        
        
        
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    




