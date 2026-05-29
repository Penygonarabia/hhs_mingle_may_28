from collections import defaultdict
from datetime import datetime, timedelta,date,time
from operator import itemgetter

import pytz
from odoo import models, fields, api, exceptions, _
from odoo.tools import format_datetime
from odoo.osv.expression import AND, OR
from odoo.tools.float_utils import float_is_zero
from dateutil.relativedelta import relativedelta


import logging

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    
    _inherit = "hr.attendance"
    

    
    process = fields.Selection([('yes','Yes'),('no','No')],default="no",string="Processed")
    
    worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_hours', store=True, readonly=True)

    att_date = fields.Date(string="Attendance date")
    
    year_1900_bool = fields.Boolean(string="Year-1900", default=False, compute="_compute_year_bool")
    
    year_1900_chekout_bool = fields.Boolean(string="Year 1900 Check out ", default=False, compute="_compute_year_bool")
    
    employee_no = fields.Char(string="Employee No", compute="_onchange_employee_id",store=True)
    
    @api.depends('check_in', 'check_out')
    def _compute_year_bool(self):
        for rec in self:
            rec.year_1900_bool = False
            rec.year_1900_chekout_bool = False
            if rec.employee_id:
                if rec.check_in and rec.check_in.year == 1900:
                    rec.year_1900_bool = True
                    '''for time being it will be commented because the when the year is 1900 it will be empty'''
                    # if rec.year_1900_bool:
                    #     rec.check_in = False
                    
                if rec.check_out and rec.check_out.year == 1900:
                    rec.year_1900_chekout_bool = True
                    # if rec.year_1900_chekout_bool:
                    #     rec.check_out = False
                    
                        
    
    @api.depends('employee_id')
    def _onchange_employee_id(self):
        for rec in self:
            rec.employee_no = rec.employee_id.employee_no or False
     
    '''Code is added on Nov 04 - 2025 by Vijaya Bhaskar Attendance Count Mail -- '''            
    @api.model
    def _email_remainder_check_in_count(self):
        
        today = fields.Date.today()
        
        yesterday = fields.Date.today() - relativedelta(days = 1)
        
        # start_date = datetime.combine(today,datetime.min.time())
        # end_date = datetime.combine(today,datetime.max.time())
        
        '''because Scheduling is run after mid night so employee sign out was untill 11 pm.so that we take yesterday time '''
        start_date = datetime.combine(yesterday,datetime.min.time())
        end_date = datetime.combine(yesterday,datetime.max.time())
        
        
        company = self.env.company
        calendar = company.resource_calendar_id

        # -----------------------------------------
        # STEP 1: Determine if today is working day
        # -----------------------------------------
        is_working_day = True
        is_public_holiday = False

        if calendar:
            # attendance_today = calendar.attendance_ids.filtered(
            #     lambda att: int(att.dayofweek) == today.weekday()
            # )
            attendance_today = calendar.attendance_ids.filtered(
                lambda att: int(att.dayofweek) == yesterday.weekday()
             )
            if not attendance_today:
                is_working_day = False

            # Check if today falls within a public holiday
            public_leaves = calendar.global_leave_ids.filtered(
                lambda leave: leave.date_from.date() <= yesterday <= leave.date_to.date()
            )
            # public_leaves = calendar.global_leave_ids.filtered(
            #     lambda leave: leave.date_from.date() <= today <= leave.date_to.date()
            # )
            if public_leaves:
                is_public_holiday = True

        # -----------------------------------------
        # STEP 2: Skip execution if non-working day
        # -----------------------------------------
        if not is_working_day or is_public_holiday:
            reason = "non-working day" if not is_working_day else "public holiday"
            _logger.info(
                f"⏸️ Skipping attendance email for {yesterday.strftime('%A %d-%m-%Y')} — {reason} "
                f"based on company calendar '{calendar.name if calendar else 'N/A'}'."
            )
            return
        
        
        
        domain = [('check_in','>=',start_date),('check_out','<=',end_date)]
        
        domain_check_in_count = [('check_in','>=',start_date),('check_in', '<=', end_date)]
        
        # domain_check_in_count = [('check_in','>=',start_date),('check_in', '<=', end_date),('check_out','=',False)]
        '''Both Check in and Check Out'''
        attendance_search = self.env['hr.attendance'].search([
                    ('check_in', '>=', start_date),
                    ('check_in', '<=', end_date),
                    ('check_out', '!=', False),
                    ('check_out', '<=', end_date),
                ])    
        '''Only Check In Count'''    
        attendance_check_in_count_search = self.env['hr.attendance'].search(domain_check_in_count)
        
        '''Total No.of Employee entered in the attendance'''
        attendance_record = self.env['hr.attendance'].search([
            ('check_in','>=',start_date),
            ('check_in','<=',end_date)
            
            ])
        
        
        
        attendance_count  = 0
        
        attendance_check_in_count = 0
        
        total_attendance_count = 0
        
               
        valid_attendance_checkin_checkout = attendance_search.filtered(
            lambda att: att.check_out and att.check_out.year != 1900
        )
        
        unique_employee_search = valid_attendance_checkin_checkout.mapped('employee_id.id')
        
        attendance_count = len(set(unique_employee_search))
        
        
        valid_attendance_checkIn = attendance_check_in_count_search.filtered(
            lambda att: not att.check_out or att.check_out.year == 1900
            )
        
        unique_employee_check_in = valid_attendance_checkIn.mapped('employee_id.id')
        
        attendance_check_in_count = len(set(unique_employee_check_in))
        
        
        valid_total_attendance = attendance_record.mapped('employee_id.id')
        
        total_attendance_count = len(set(valid_total_attendance))
        
        
        
       
        if attendance_count > 0 or attendance_check_in_count > 0  or total_attendance_count > 0:
            subject = f"Attendance Count For HHS Employee at {yesterday.strftime('%d-%m-%Y')} ({yesterday.strftime('%A')})"
            # body_html = f""" 
            #     <p>Attendance Check in  & Checkout Count</p>
            #     <table border="1" cellpadding="4" cellspacing="0">
            #         <tr><th>Total Check-ins</th></tr>
            #         <tr><td align="center"><b>{attendance_count}</b></td></tr>
            #     </table>
            #     <br/>
            #     <p>Attendance Check In Count Only</p>
            #      <table border="1" cellpadding="4" cellspacing="0">
            #         <tr><th>Total Check-ins Only</th></tr>
            #         <tr><td aligntoday="center"><b>{attendance_check_in_count}</b></td></tr>
            #     </table>
            #
            # """
            
            body_html = f"""
                <p><b>Attendance Summary for {yesterday.strftime('%d-%m-%Y')} ({yesterday.strftime('%A')})</b></p>

                <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
                    <tr style="background-color:#f2f2f2;"><th>Description</th><th align="center">Count</th></tr>
                    <tr><td>Total No.of Employees Count </td><td align ="center"><b>{total_attendance_count}</b></td></tr>
                    <tr><td>No. of Employees Check in and Check Out</td><td align="center"><b style="color:red;">{attendance_count}</b></td></tr>
                    <tr><td>No. of Employees Only Check In (Not Checkout)</td><td align="center"><b>{attendance_check_in_count}</b></td></tr>
                </table>

                <br/>
                <p style="color:gray;">This is an automated attendance summary generated.</p>
            """
            
            self.env['mail.mail'].sudo().create({
                'subject' : subject,
                'body_html' : body_html,
                'email_from' : self.env.user.email,
                'email_to':'baskar@penygonarabia.com',
                'email_cc':'iraju@penygonarabia.com,cieloerpsupport@penygonarabia.com,saravanan@penygonarabia.com'
                
                }).send()
                
         
                
                
        
    
    #
    # @api.model_create_multi
    # def create(self, vals_list):
    #     ''' because they need when the year starts with 1900 then it will be empty'''
    #     for vals in vals_list:
    #
    #         if 'check_out' in vals and vals['check_out']:
    #             check_out = vals['check_out']
    #
    #             if isinstance(check_out, str) and check_out.startswith('1900'):
    #                 vals.update({'check_out': False})  
    #
    #         if 'check_in' in vals and vals['check_in']:
    #             check_in = vals['check_in']
    #             if isinstance(check_in, str):
    #                 if check_in.startswith('1900'):
    #                     vals.update({'check_in': False})           
    #
    #     res = super().create(vals_list)
    #
    #     res._update_overtime()
    #
    #     return res
    #
    #
    # def write(self, vals):
    #     ''' because they need when the year starts with 1900 then it will be empty'''
    #     if 'check_out' in vals and vals['check_out']:
    #         check_out = vals['check_out']
    #         if isinstance(check_out, str):
    #             if check_out.startswith('1900'):
    #                 vals.update({'check_out': False}) 
    #     if 'check_in' in vals and vals['check_in']:
    #         check_in = vals['check_in']
    #         if isinstance(check_in, str):
    #             if check_in.startswith('1900'):
    #                 vals.update({'check_in': False})               
    #     return super(HrAttendance, self).write(vals)
  
    @api.onchange('check_in','check_out')
    def _onchange_check(self):
        for rec in self:
            if rec.check_in:
                rec.write({'process': 'no'})
                
                attendance_ids = self.env['hr.attendance.sheet'].search([
            ('employee_id', '=', rec.employee_id.id),
            ('request_date_from', '<=', rec.check_in.date()),
            ('request_date_to', '>=', rec.check_in.date()),
            ])
                for attendance in attendance_ids.attendance_sheet_ids:
                    if attendance:
                        if attendance.date == rec.check_in.date():
                            attendance.export_bool = False
                            attendance.export='no'
                            
                            
                attendance_batch_ids = self.env['attendance.sheet.batch.line'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('period_from', '<=', rec.check_in.date()),
                ('period_to', '>=', rec.check_in.date()),
                ])  
                
                for batch in attendance_batch_ids:
                    if batch:
                        batch.process_bool = False            
                        
            if rec.check_out:
                rec.write({'process': 'no'})
                attendance_ids = self.env['hr.attendance.sheet'].search([
            ('employee_id', '=', rec.employee_id.id),
            ('request_date_from', '<=', rec.check_out.date()),
            ('request_date_to', '>=', rec.check_out.date()),
            ])
                for attendance in attendance_ids.attendance_sheet_ids:
                    if attendance:
                        if attendance.date == rec.check_out.date():
                            attendance.export_bool = False
                            attendance.export='no'
                
                
                            
                attendance_batch_ids = self.env['attendance.sheet.batch.line'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('period_from', '<=', rec.check_out.date()),
                ('period_to', '>=', rec.check_out.date()),
                ])  
                
                for batch in attendance_batch_ids:
                    if batch:
                        batch.process_bool = False

                
    
    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """ Verifies the validity of the attendance record compared to the others from the same employee.
            For the same employee we must have :
                * maximum 1 "open" attendance record (without check_out)
                * no overlapping time slices with previous employee records
        """
        for attendance in self:
            # we take the latest attendance before our check_in time and check it doesn't overlap with ours
            last_attendance_before_check_in = self.env['hr.attendance'].search([
                ('employee_id', '=', attendance.employee_id.id),
                ('check_in', '<=', attendance.check_in),
                ('id', '!=', attendance.id),
            ], order='check_in desc', limit=1)
            if last_attendance_before_check_in and last_attendance_before_check_in.check_out and last_attendance_before_check_in.check_out > attendance.check_in:
                pass
                # raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s") % {
                #     'empl_name': attendance.employee_id.name,
                #     'datetime': format_datetime(self.env, attendance.check_in, dt_format=False),
                # })

            if not attendance.check_out:
                # if our attendance is "open" (no check_out), we verify there is no other "open" attendance
                no_check_out_attendances = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_out', '=', False),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if no_check_out_attendances:
                    pass
                    # raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee hasn't checked out since %(datetime)s") % {
                    #     'empl_name': attendance.employee_id.name,
                    #     'datetime': format_datetime(self.env, no_check_out_attendances.check_in, dt_format=False),
                    # })
            else:
                # we verify that the latest attendance with check_in time before our check_out time
                # is the same as the one before our check_in time computed before, otherwise it overlaps
                last_attendance_before_check_out = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_in', '<', attendance.check_out),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if last_attendance_before_check_out and last_attendance_before_check_in != last_attendance_before_check_out:
                    pass
                    # raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s") % {
                    #     'empl_name': attendance.employee_id.name,
                    #     'datetime': format_datetime(self.env, last_attendance_before_check_out.check_in, dt_format=False),
                    # })

    
          
    ''' this is for checking if the check in time less than check out time then validation error will be removed on october 9 '''        
    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for attendance in self:
            if attendance.check_out and attendance.check_in:
                delta = attendance.check_out - attendance.check_in
                attendance.worked_hours = delta.total_seconds() / 3600.0
                if attendance.worked_hours < 0:
                    attendance.worked_hours = 0
            else:
                attendance.worked_hours = False
   
    ''' this is for checking if the check in time less than check out time then validation error will be removed on october 9 '''  
    @api.constrains('check_in', 'check_out')
    def _check_validity_check_in_check_out(self):
        """ verifies if check_in is earlier than check_out. """
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                pass
                # if attendance.check_out < attendance.check_in:
                #     raise exceptions.ValidationError(_('"Check Out" time cannot be earlier than "Check In" time.'))
                
                
   