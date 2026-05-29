# See LICENSE file for full copyright and licensing details
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
import calendar
import pytz
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import ValidationError
from calendar import weekday
from collections import defaultdict
import time
from dateutil.relativedelta import relativedelta


class Attendancesheet(models.Model):
    """Attendance Sheet."""

    _name = 'hr.attendance.sheet'
    _description = 'Attendance Sheet'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "employee_id"

    employee_id = fields.Many2one("hr.employee", string="Employee", tracking=True)
    date_from = fields.Date("Date from")
    date_to = fields.Date("Date to")
    state = fields.Selection([('draft', 'Draft'),
                              ('confirm', 'Confirm'),
                              ('approved', 'Approved'),
                              ('export','Export')
                              ],
                             default="draft",tracking = True)
    request_date_from = fields.Date("request_date_from",tracking = True)
    request_date_to = fields.Date("request_date_to",tracking = True)
    attendance_policy = fields.Many2one(
        "hr.attendance.policies", string="Attendance Policy")
    attendance_sheet_ids = fields.One2many(
        "hr.attendance.sheet.line", "name_id")
    no_latein = fields.Integer("No Of Lates")
    total_latein = fields.Float("Total Late in")
    no_overtime = fields.Integer("No Of Overtime")
    total_overtime = fields.Float("Total Overtime")
    no_difftime = fields.Integer("No Of Diff Times")
    total_difftime = fields.Float("Total Diff Times Hours")
    no_absence = fields.Integer("No Of Absence")
    total_absence = fields.Float("Total Absence Hours")

    latein = fields.Float(string='Late In', default='00')

    overtime = fields.Float(string='Overtime', default="00")

    time_different = fields.Float(string='Time Different', default="00")
    absent = fields.Float(string='Absence', default="00")
    
    no_latein_more_1hour = fields.Integer("No Of Lates more than 1 hour")
    total_latein_more_1hour = fields.Float("Total Late in More than 1 hour")
    final_total_late_more_1hour = fields.Float(string="Final total late more than 1 hour",default="00")
    
    no_latein_30_min = fields.Integer("No Of lates more than 30 min")
    total_late_30min = fields.Float("Total Late in morethan 30 min")
    final_total_late_30min = fields.Float(string="Final total late 30 min",default='00')
    
    
    
    
    no_latein_15min = fields.Integer("No of lates lessthan 15 min")
    total_latein_15min = fields.Float("Total late lessthan 15 min")
    final_total_late_15min = fields.Float(string="Final total late 15 min",default="00")
    
    
    
    no_early_out_15min = fields.Integer("No.of Early out in 15min to  30 min")
    total_early_out_15min = fields.Float("Total Early out in 15 min to 30 min")
    final_total_early_out_15min = fields.Float(string="Final Total Early out 15 min", default='00')
    
    
    no_early_out_30min = fields.Integer("No of Early out in 30 min to 60 min")
    total_early_checkout_30min = fields.Float("Total Early out in 30 min to 60 min")
    final_total_early_out_30min = fields.Float(string="Final Total Early out 30 min", default="00")
    
    
    no_early_out_60min = fields.Integer("No of Early out in more than 60 min")
    total_early_out_60min = fields.Float("Total Early out in more than 60 min")
    final_total_early_out_60min = fields.Float(string = "Final Total Early out 60 min", default="00")
    
    
    no_early_checkout = fields.Integer(string="No. of Early Checkout")
    total_early_checkout = fields.Float(string="Total Early checkout")
    
    early_check_out_amount = fields.Float(string="Early Checkout" , default="00")
    
    
    attendance_sheet_batch_id = fields.Many2one('attendance.sheet.batch',string="Attendance Batch Id")

    employee_number = fields.Char(string='Employee No', store = True)
    
    employee_policy_id = fields.Many2one('hr.attendance.policies' , string = "Employee Policy")
    
    '''This code is used for Execute Employee is not going to give the attendance  but they want entry record in attendance sheet.so it will added '''
    atte_required = fields.Boolean('Attendance Required(Y/N)',default=False,readonly=True,compute="_compute_attendance_required",store = True)
    
    
    '''this code is used for export attendance for odoo to hhs for exporting on nov 23 2024'''
    export_sheet = fields.Selection(
        [('no', 'No'), ('yes', 'Yes')],
        string="Export",
        default='no'
    ) 
    
    
    
    late_in_calculation_bool = fields.Boolean(
        string="Late In Calculation",
        compute='_compute_config_values',
        inverse='_inverse_config_values',
        default=lambda self: self._default_late_in_calculation_bool(),
        help="Reflects system parameter 'hr_attendances_overtime.late_in_calculation'",
    )

    early_out_calculation_bool = fields.Boolean(
        string="Early Out Calculation",
        compute='_compute_config_values',
        inverse='_inverse_config_values',
        default=lambda self: self._default_early_out_calculation_bool(),
        help="Reflects system parameter 'hr_attendances_overtime.early_out_calculation'",
    )

    overtime_calculation_bool = fields.Boolean(
        string="Overtime Calculation",
        compute='_compute_config_values',
        inverse='_inverse_config_values',
        default=lambda self: self._default_overtime_calculation_bool(),
        help="Reflects system parameter 'hr_attendances_overtime.overtime_calculation'",
    )

    absence_calculation_bool = fields.Boolean(
        string="Absence Calculation",
        compute='_compute_config_values',
        inverse='_inverse_config_values',
        default=lambda self: self._default_absence_calculation_bool(),
        help="Reflects system parameter 'hr_attendances_overtime.absence_calculation'",
    )
    
    '''Email Scheduler for Early out Employee  on July 28 - 2025 by Vijaya Bhaskar'''

    @api.model
    def _email_for_late_in_employee(self):
        yesterday = fields.Date.today() - relativedelta(days = 1)
        today = fields.Date.today()
        yesterday_str = yesterday.strftime('%d-%m-%Y')
        
        attendance_search = self.env['hr.attendance.sheet'].search([
                ('atte_required','=',True),('employee_id.state','=','draft'),
                ('request_date_from','<=',yesterday),
                ('request_date_to','>=',yesterday),
                ('employee_id.contract_id.mail_required_bool','=',True),
                ('employee_id.contract_id.state','=','open')
                ])
        
        for attendance in attendance_search:
            for line in attendance.attendance_sheet_ids:
                if line.date and line.date == yesterday:
                    if line.status == 'weekday':
                        if line.latein > 0.0:
                            late_in_hr = int(line.latein)
                            late_in_min = int((line.latein - late_in_hr)*60)
                            total_late_in = "{:02d}:{:02d}".format(late_in_hr,late_in_min)
                            # Compose and send mail
                            subject = f"Late in Notification - {attendance.employee_id.name} At  {yesterday_str}"
                            body_html = f"""
                                <p style="color:#0000FF;font-size:20px">Dear {attendance.employee_id.name},</p>
                                <p style="color:#0000FF;font-size:20px">Our attendance records indicate that you were late in on <strong>{yesterday_str}</strong> by <strong>{total_late_in}</strong> hours.</p>
                                <p style="color:#0000FF;font-size:20px">If this is incorrect or if you have a valid reason for this late in, please inform your Direct manager or the HR team immediately with supporting details.</p>
                                <br/>
                                <b style="color:#0000FF;font-size:20px">Best Regards</b><br/>
                                <b style="color:#0000FF;font-size:20px">Human Resource Dept</b><br/>
                                 <b style="color:#0000FF;font-size:20px">HH-Shaker</b>
                            """
         
                            self.env['mail.mail'].create({
                                'subject': subject,
                                'body_html': body_html,
                                'email_to': attendance.employee_id.work_email,
                                'email_cc':attendance.employee_id.parent_id.work_email,
                                'email_from': self.env.user.email or 'noreply@example.com',
                            }).send()
                            # template = self.env.ref('hr_attendances_overtime.email_template_for_latein_employee')
                            # if template :
                            #     template.with_context(yesterday_str=yesterday_str, total_late_in = str(total_late_in)).send_mail(attendance.id, force_send=True)
                            #

    '''Email Scheduler for Early out Employee  on July 28 - 2025 by Vijaya Bhaskar'''
    @api.model
    def _email_for_early_out_employee(self):
        yesterday = fields.Date.today() - relativedelta(days = 1)
        today = fields.Date.today()
        yesterday_str = yesterday.strftime('%d-%m-%Y')
        
        attendance_search = self.env['hr.attendance.sheet'].search([
                        ('atte_required','=',True),('employee_id.state','=','draft'),
                        ('request_date_from','<=',yesterday),
                        ('request_date_to','>=',yesterday),
                        ('employee_id.contract_id.mail_required_bool','=',True),
                        ('employee_id.contract_id.state','=','open')
                        ])        
        for attendance in attendance_search:
            for line in attendance.attendance_sheet_ids:
                if line.date and line.date == yesterday:
                    if line.status == 'weekday':
                        if line.early_out_line > 0.0:
                            early_out_hr = int(line.early_out_line)
                            early_out_min = int((line.early_out_line - early_out_hr)*60)
                            total_early_out = "{:02d}:{:02d}".format(early_out_hr,early_out_min)
                            subject = f"Early Out Notification -{attendance.employee_id.name} At {yesterday_str}"
                            body_html = f"""
                                <p style="color:#0000FF;font-size:20px">Dear {attendance.employee_id.name},</p>
                                <p style="color:#0000FF;font-size:20px">Our attendance records indicate that you were Early out on <strong>{yesterday_str}</strong> by <strong>{total_early_out}</strong> hours.</p>
                                <p style="color:#0000FF;font-size:20px">If this is incorrect or if you have a valid reason for this Early out, please inform your Direct manager or the HR team immediately with supporting details.</p>
                                <br/>
                                <b style="color:#0000FF;font-size:20px">Best Regards</b><br/>
                                <b style="color:#0000FF;font-size:20px">Human Resource Dept</b><br/>
                                 <b style="color:#0000FF;font-size:20px">HH-Shaker</b>
                            """
         
                            self.env['mail.mail'].create({
                                'subject': subject,
                                'body_html': body_html,
                                'email_to': attendance.employee_id.work_email,
                                'email_cc':attendance.employee_id.parent_id.work_email,
                                'email_from': self.env.user.email or 'noreply@example.com',
                            }).send()
                            # template = self.env.ref('hr_attendances_overtime.email_template_for_earlyout_employee')
                            # if template :
                            #     template.with_context(yesterday_str=yesterday_str,total_early_out = total_early_out).send_mail(attendance.id, force_send=True)
                            #

    

   
    ''' Currently working it was commented by Vijaya Bhaskar on Sep - 20-2025 due to attendance sheet employee check in not properly inserted due to any failure.so email scheduler for absent employee is not sent 
    @api.model
    def _email_for_absence_employees(self):
        yesterday = fields.Date.today() - relativedelta(days = 1)
        today = fields.Date.today()
        yesterday_str = yesterday.strftime('%d-%m-%Y')
        
        attendance_search = self.env['hr.attendance.sheet'].search([
                        ('atte_required','=',True),('employee_id.state','=','draft'),
                        ('request_date_from','<=',yesterday),
                        ('request_date_to','>=',yesterday),
                        ('employee_id.contract_id.mail_required_bool','=',True),
                        ('employee_id.contract_id.state','=','open')
                        ])        
        for attendance in attendance_search:
            for line in attendance.attendance_sheet_ids:
                if line.date and line.date == yesterday:
                    if line.status == 'absence':
                       
                        subject = f"Absence Notification -{attendance.employee_id.name} At {yesterday_str}"
                        body_html = f"""
                            <p style="color:#0000FF;font-size:20px">Dear {attendance.employee_id.name},</p>
                            <p style="color:#0000FF;font-size:20px">Our attendance records indicate that you were absent on <strong>{yesterday_str}</strong>.</p>
                            <br/>
                            <p style="color:#0000FF;font-size:20px">If this is incorrect or if you have a valid reason for the absence, please inform your Direct manager or the HR team immediately with supporting details.</p>
                            <br/>
                            <b style="color:#0000FF;font-size:20px">Best Regards</b><br/>
                            <b style="color:#0000FF;font-size:20px">Human Resource Dept</b><br/>
                             <b style="color:#0000FF;font-size:20px">HH-Shaker</b>
                        """
     
                        self.env['mail.mail'].create({
                            'subject': subject,
                            'body_html': body_html,
                            'email_to': attendance.employee_id.work_email,
                            'email_cc':attendance.employee_id.parent_id.work_email,
                            'email_from': self.env.user.email or 'noreply@example.com',
                        }).send()
                        # template = self.env.ref('hr_attendances_overtime.email_template_for_earlyout_employee')
                        # if template :
                        #     template.with_context(yesterday_str=yesterday_str,total_early_out = total_early_out).send_mail(attendance.id, force_send=True)
                        #
        '''
    
    '''Email Scheduler for Absent Employee  on July 29 - 2025 by Vijaya Bhaskar'''
    '''New Code is added on Sep 20 2025'''                        
    
    @api.model
    def _email_for_absence_employees(self):
        yesterday = fields.Date.today() - relativedelta(days = 1)
        today = fields.Date.today()
        yesterday_str = yesterday.strftime('%d-%m-%Y')
        
        total_required_employees = self.env['hr.attendance.sheet'].search_count([
        ('atte_required', '=', True),
        ('employee_id.state', '=', 'draft'),
        ('request_date_from', '<=', yesterday),
        ('request_date_to', '>=', yesterday),
        ('employee_id.contract_id.mail_required_bool', '=', True),
        ('employee_id.contract_id.state', '=', 'open')
        ])
        
        attendance_search = self.env['hr.attendance.sheet'].search([
                        ('atte_required','=',True),('employee_id.state','=','draft'),
                        ('request_date_from','<=',yesterday),
                        ('request_date_to','>=',yesterday),
                        ('employee_id.contract_id.mail_required_bool','=',True),
                        ('employee_id.contract_id.state','=','open')
                        ]) 
       
        checked_in_count = 0
        for attendance in attendance_search:
            for line in attendance.attendance_sheet_ids:
                if line.date == yesterday and line.status != 'absence':
                    checked_in_count += 1
        
        check_in_percentage = False            
        if total_required_employees > 0:  
            check_in_percentage = (checked_in_count / total_required_employees) * 100
        else:
            check_in_percentage = 0            
        
        if check_in_percentage >= 80:
            for attendance in attendance_search:
                for line in attendance.attendance_sheet_ids:
                    if line.date and line.date == yesterday:
                        if line.status == 'absence':
                           
                            subject = f"Absence Notification -{attendance.employee_id.name} At {yesterday_str}"
                            body_html = f"""
                                <p style="color:#0000FF;font-size:20px">Dear {attendance.employee_id.name},</p>
                                <p style="color:#0000FF;font-size:20px">Our attendance records indicate that you were absent on <strong>{yesterday_str}</strong>.</p>
                                <br/>
                                <p style="color:#0000FF;font-size:20px">If this is incorrect or if you have a valid reason for the absence, please inform your Direct manager or the HR team immediately with supporting details.</p>
                                <br/>
                                <b style="color:#0000FF;font-size:20px">Best Regards</b><br/>
                                <b style="color:#0000FF;font-size:20px">Human Resource Dept</b><br/>
                                 <b style="color:#0000FF;font-size:20px">HH-Shaker</b>
                            """
         
                            self.env['mail.mail'].create({
                                'subject': subject,
                                'body_html': body_html,
                                'email_to': attendance.employee_id.work_email,
                                'email_cc':attendance.employee_id.parent_id.work_email,
                                'email_from': self.env.user.email or 'noreply@example.com',
                            }).send()
                            # template = self.env.ref('hr_attendances_overtime.email_template_for_earlyout_employee')
                            # if template :
                            #     template.with_context(yesterday_str=yesterday_str,total_early_out = total_early_out).send_mail(attendance.id, force_send=True)
                            #
        

    # Default value methods
    @api.model
    def _default_late_in_calculation_bool(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'hr_attendances_overtime.late_in_calculation') == 'True'

    @api.model
    def _default_early_out_calculation_bool(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'hr_attendances_overtime.early_out_calculation') == 'True'

    @api.model
    def _default_overtime_calculation_bool(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'hr_attendances_overtime.overtime_calculation') == 'True'

    @api.model
    def _default_absence_calculation_bool(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'hr_attendances_overtime.absence_calculation') == 'True'

    # Compute method for all records
    @api.depends()
    def _compute_config_values(self):
        """Always show current system parameter values"""
        params = self.env['ir.config_parameter'].sudo()
        for record in self:
            record.late_in_calculation_bool = params.get_param('hr_attendances_overtime.late_in_calculation') == 'True'
            record.early_out_calculation_bool = params.get_param('hr_attendances_overtime.early_out_calculation') == 'True'
            record.overtime_calculation_bool = params.get_param('hr_attendances_overtime.overtime_calculation') == 'True'
            record.absence_calculation_bool = params.get_param('hr_attendances_overtime.absence_calculation') == 'True'

    # Inverse method to handle manual edits (if needed)
    def _inverse_config_values(self):
        """If someone edits these fields, update system parameters"""
        params = self.env['ir.config_parameter'].sudo()
        for record in self:
            params.set_param('hr_attendances_overtime.late_in_calculation', str(record.late_in_calculation_bool))
            params.set_param('hr_attendances_overtime.early_out_calculation', str(record.early_out_calculation_bool))
            params.set_param('hr_attendances_overtime.overtime_calculation', str(record.overtime_calculation_bool))
            params.set_param('hr_attendances_overtime.absence_calculation', str(record.absence_calculation_bool))

    # Override create to ensure proper initialization
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            for field in ['late_in_calculation_bool', 'early_out_calculation_bool', 
                         'overtime_calculation_bool', 'absence_calculation_bool']:
                if field not in vals:
                    vals[field] = getattr(self, f'_default_{field}')()
        return super().create(vals_list)

    
    
    
    # late_in_calculation_bool = fields.Boolean(
    #     string="Late In Calculation Bool", compute="_compute_config_values", store=True)
    # early_out_calculation_bool = fields.Boolean(
    #     string="Early Out Calculation Bool", compute="_compute_config_values", store=True)
    # overtime_calculation_bool = fields.Boolean(
    #     string="Overtime Calculation Bool", compute="_compute_config_values", store=True)
    # absence_calculation_bool = fields.Boolean(
    #     string="Absence Calculation Bool", compute="_compute_config_values", store=True)
    #
    # def _compute_config_values(self):
    #     IrConfig = self.env['ir.config_parameter'].sudo()
    #     late_in = IrConfig.get_param('hr_attendances_overtime.late_in_calculation') == 'True'
    #     early_out = IrConfig.get_param('hr_attendances_overtime.early_out_calculation') == 'True'
    #     overtime = IrConfig.get_param('hr_attendances_overtime.overtime_calculation') == 'True'
    #     absence = IrConfig.get_param('hr_attendances_overtime.absence_calculation') == 'True'
    #
    #     for rec in self:
    #         rec.late_in_calculation_bool = late_in
    #         rec.early_out_calculation_bool = early_out
    #         rec.overtime_calculation_bool = overtime
    #         rec.absence_calculation_bool = absence


    
    # @api.model
    # def _default_late_in_calculation_bool(self):
    #     late_in_calculation_search = self.env['ir.config_parameter'].sudo().get_param('hr_attendances_overtime.late_in_calculation')
    #     print("///////////////latein",late_in_calculation_search)
    #     return late_in_calculation_search
    #
    # @api.model
    # def _default_early_out_calculation_bool(self):
    #     early_out_calculation_search = self.env['ir.config_parameter'].sudo().get_param('hr_attendances_overtime.early_out_calculation')
    #     print(".....early_out_calculation_search.......",early_out_calculation_search)
    #     return early_out_calculation_search
    #
    # @api.model
    # def _default_overtime_calculation_bool(self):
    #     overtime_calculation_search = self.env['ir.config_parameter'].sudo().get_param('hr_attendances_overtime.overtime_calculation')
    #     print("///////overtime_calculation_search///",overtime_calculation_search)
    #     return overtime_calculation_search
    #
    # @api.model
    # def _default_absence_calculation_bool(self):
    #     absence_calculation_search = self.env['ir.config_parameter'].sudo().get_param('hr_attendances_overtime.absence_calculation')
    #     print(".....absence_calculation_search.....",absence_calculation_search)
    #     return absence_calculation_search
    #
    #
    # late_in_calculation_bool = fields.Boolean(string = "late in calculation bool", default = _default_late_in_calculation_bool)
    #
    # early_out_calculation_bool = fields.Boolean(string = "Early out calculation Bool", default = _default_early_out_calculation_bool)
    #
    # overtime_calculation_bool = fields.Boolean(string = "Overtime Calculation Bool", default = _default_overtime_calculation_bool)
    #
    # absence_calculation_bool = fields.Boolean (string = "Absence calculation Bool", default = _default_absence_calculation_bool)
    #


    @api.onchange('employee_id')
    def _onchange_employee(self):
        for rec in self:
            rec.employee_number = False
            if rec.employee_id:
                rec.employee_number = rec.employee_id.employee_no
                rec.employee_policy_id = rec.employee_id.contract_id.attend_police_id.id or False
                rec.atte_required = rec.employee_id.contract_id.attendance_required_bool
                
                
    @api.depends('employee_id') 
    def _compute_attendance_required(self):
        for rec in self:
            rec.atte_required = False
            if rec.employee_id:
                rec.atte_required = rec.employee_id.contract_id.attendance_required_bool
                
            
                       

    # @api.constrains('employee_id', 'request_date_from', 'request_date_to')
    # def validation_attendance_sheet(self):
    #     """Method to set constrains for attendance sheet."""
    #     for sheet in self:
    #         attendance_ids = sheet.search([
    #             ('employee_id', '=', sheet.employee_id.id),
    #             ('request_date_from', '>=', sheet.request_date_from),
    #             ('request_date_to', '<=', sheet.request_date_to),
    #             ('id', '!=', sheet.id),
    #         ])
    #         if attendance_ids:
    #             raise ValidationError(
    #                 _("Record already exists with name %s !!!") % (
    #                     self.employee_id.name))

    # @api.model_create_multi
    # def create(self, vals_list):
    #     res = super(Attendancesheet, self).create(vals_list)
    #     res.message_post(body=_("record created"))
    #     return res
    

    
    
    def unlink(self):
        """Method to set validation for attendance sheet."""
        for sheet in self:
            if sheet.state in ['approved', 'export']:
                raise ValidationError(_("You can't delete record"
                                        " which is approved."))
            else:    
                payroll_transaction_search = self.env['salary.allowance.detection'].search([('attendance_sheet_id', '=',sheet.id)])
                for transaction in payroll_transaction_search:
                    transaction.unlink()
                # for line in sheet.attendance_sheet_ids:
                #     line.unlink() 
        return super(Attendancesheet, self).unlink()

    @api.constrains('request_date_from')
    def check_start_date(self):
        """Method to check start date."""
        for sheet in self:
            if sheet.request_date_from > sheet.request_date_to:
                raise ValidationError(_("Start date must be "
                                        "less than end date."))
                
    def compute_attendance_data(self):
        absence_count = defaultdict(int)
       
        for record in self:
            for line in record.attendance_sheet_ids:
                line.compute_attendance()
                if record.absence_calculation_bool:
                    if line.status == 'absence' and line.absent_bool:
                        # Ensure employee_id is fetched from the current record
                        employee_id = record.employee_id.id  
                        absence_count[employee_id] += 1
                        current_count = absence_count[employee_id]
        
                        line.insert_absence_transaction(current_count)
            
     ##### currently working on march 26           
    # def compute_attendance_data(self):
    #     absence_count = defaultdict(int)
    #
    #     for line in self.attendance_sheet_ids:
    #         line.compute_attendance()
    #
    #          # This is worked if absence count is added on nov 26
    #         if line.status == 'absence' and line.absent_bool:
    #              # Increment absence count for the specific employee
    #             employee_id = self.employee_id.id
    #             absence_count[employee_id] += 1
    #             current_count = absence_count[employee_id]
    #
    #             line.insert_absence_transaction(current_count)
        # for line in self.attendance_sheet_ids: 
        #     line.compute_attendance()  
            # line.insert_absence_transaction()

    # def compute_attendance_data(self):
    #     """Compute Data."""
    #     for rec in self:
    #         overtime = 0
    #         rec.latein = 0
    #         rec.final_total_late_30min = 0
    #         rec.final_total_late_more_1hour = 0
    #         rec.final_total_late_15min = 0
    #         no_of_times_30min = 0
    #         no_of_times_1hour = 0
    #         no_of_times_15min = 0
    #
    #         rec.early_check_out_amount = 0
    #
    #         # total_wages = 0
    #         #
    #         # total_wages = rec.employee_id.contract_id.wage + rec.employee_id.contract_id.house_allowance + rec.employee_id.contract_id.transport_allowance + \
    #         #             rec.employee_id.contract_id.school_allowance + rec.employee_id.contract_id.food_allowance + rec.employee_id.contract_id.fuel_allowance + \
    #         #             rec.employee_id.contract_id.ticket_allowance + rec.employee_id.contract_id.fixed_allowance + \
    #         #             rec.employee_id.contract_id.mobile_allowance + rec.employee_id.contract_id.work_allowance + rec.employee_id.contract_id.housing_allowance
    #         #
    #
    #         # print(".........total",rec.employee_id.contract_id.total,total_wages)
    #         rec._onchange_attendance_sheet_ids()
    #         contract_id = self.env['hr.contract'].search([
    #             ('employee_id', '=', rec.employee_id.id),
    #             ('state', '=', 'open')])
    #         policies_id = contract_id.attend_police_id or False
    #         if policies_id:
    #             # Calculated the letin amount if time different is not present.
    #             if rec.no_latein and policies_id.late_id and\
    #                     rec.total_latein:
    #                 latein = policies_id.late_id
    #                 weekday_ids = self.env['hr.attendance.sheet.line'].search([
    #                     ('name_id', '=', rec.id), ('status', '=', 'weekday')])
    #                 for weekday in weekday_ids:
    #                      if weekday.latein:
    #                         latein_minutes = weekday.latein * 60  # Convert to minutes for easier comparison
    #
    #                         if 15 <= latein_minutes < 30:
    #                             no_of_times_15min += 1
    #                             for line in latein.attendance_line_ids:
    #                                 # print("................loop",line)
    #                                 # If more than 4 occurrences, apply the 4th policy for subsequent occurrences
    #                                 if no_of_times_15min > 4 and line.num_of_times == '4':
    #                                     if line.time < (30 / 60):  # Ensure line.time matches the 15min condition
    #                                         if line.amount_type == "rate":
    #                                             rec.final_total_late_15min += (line.rate / 100) * (rec.employee_id.contract_id.total / 30)
    #                                             # self.attendance_sheet_ids.insert_latein_transaction()
    #
    #                                         else:
    #                                             rec.final_total_late_15min += line.amount
    #                                     continue  
    #
    #                                 # Apply the specific policy for the current occurrence
    #                                 if line.num_of_times == str(no_of_times_15min) and line.time < (30 / 60):
    #                                     if line.amount_type == "rate":
    #                                         rec.final_total_late_15min += (line.rate / 100) * (rec.employee_id.contract_id.total / 30)
    #                                         # if rec.latein_bool == True:
    #                                         # for sheet_line in self.attendance_sheet_ids:
    #                                         #     if sheet_line.latein_bool == True:
    #                                         #         if sheet_line.latein_transaction_id:
    #                                         #             latein_transaction = self.env['salary.allowance.detection']
    #                                         #
    #                                         #             vals = {
    #                                         #                  'employee_number':  rec.name_id.employee_id.employee_no,
    #                                         #                 'employee_id': rec.name_id.employee_id.id,
    #                                         #                 'department': rec.name_id.employee_id.department_id.id or False,
    #                                         #                 'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
    #                                         #                 'date':rec.date,
    #                                         #                 'hr_transaction_id': rec.latein_transaction_id.id or False,
    #                                         #                 'transaction_type_id': rec.latein_transaction_id.transaction_type_id.id or False,
    #                                         #                 'days': 0.0,
    #                                         #                 'attendance_sheet_id': rec.name_id.id,
    #                                         #                 'type': rec.latein_transaction_id.rule_type,
    #                                         #                 'reason': 'Late in Transaction'
    #                                         #             }
    #                                         #             transaction = latein_transaction.create(vals)
    #                                         #             transaction.onchange_transaction_type()
    #                                         #             if transaction.hr_transaction_id.unit_type == 'days':
    #                                         #                 transaction.days = 1
    #                                         #             return transaction,transaction.date  
    #                                         #
    #                                         # # transaction_search = self.env['salary.allowance.detection'].search([])
    #                                         # # for transaction in transaction_search:
    #                                         # #     for sheet in self.attendance_sheet_ids:
    #                                         # #         if (sheet.date == transaction.date) and (transaction.hr_transaction_id==line.latein_transaction_id):
    #                                         # #             transaction.amount = (line.rate * transaction.amount)/100
    #                                         # #             print(".........transaction",transaction.amount)
    #                                         # # transaction = self.attendance_sheet_ids.insert_latein_transaction()
    #                                         # # for attendance in self.attendance_sheet_ids.insert_latein_transaction():
    #                                         # #     print("......attendance",attendance)
    #                                         # # for attend in rec.attendance_sheet_ids:
    #                                         # #     print("..........22222222222222222222222222",attend)
    #                                         # #
    #                                         # #     insert_latein_transaction():
    #                                         # #         print("..........trans",trans)
    #                                         # #         if trans.date == attend.date:
    #                                         # #                 # if attend.date == transaction.date:
    #                                         # #                 # transaction = trans.date
    #                                         # #             trans.amount = (line.rate * trans.amount)/100
    #                                         # # transaction.amount = line.rate * transaction.amount
    #                                     else:
    #                                         rec.final_total_late_15min += line.amount
    #                                     break  
    #
    #                         elif 30 <= latein_minutes < 60:
    #                             no_of_times_30min += 1
    #                             for line in latein.attendance_line_ids:
    #                                 # Apply the 4th occurrence policy for further lateness
    #              # def compute_attendance_data(self):
    #     """Compute Data."""
    #     for rec in self:
    #         overtime = 0
    #         rec.latein = 0
    #         rec.final_total_late_30min = 0
    #         rec.final_total_late_more_1hour = 0
    #         rec.final_total_late_15min = 0
    #         no_of_times_30min = 0
    #         no_of_times_1hour = 0
    #         no_of_times_15min = 0
    #
    #         rec.early_check_out_amount = 0
    #
    #         # total_wages = 0
    #         #
    #         # total_wages = rec.employee_id.contract_id.wage + rec.employee_id.contract_id.house_allowance + rec.employee_id.contract_id.transport_allowance + \
    #         #             rec.employee_id.contract_id.school_allowance + rec.employee_id.contract_id.food_allowance + rec.employee_id.contract_id.fuel_allowance + \
    #         #             rec.employee_id.contract_id.ticket_allowance + rec.employee_id.contract_id.fixed_allowance + \
    #         #             rec.employee_id.contract_id.mobile_allowance + rec.employee_id.contract_id.work_allowance + rec.employee_id.contract_id.housing_allowance
    #         #
    #
    #         # print(".........total",rec.employee_id.contract_id.total,total_wages)
    #         rec._onchange_attendance_sheet_ids()
    #         contract_id = self.env['hr.contract'].search([
    #             ('employee_id', '=', rec.employee_id.id),
    #             ('state', '=', 'open')])
    #         policies_id = contract_id.attend_police_id or False
    #         if policies_id:
    #             # Calculated the letin amount if time different is not present.
    #             if rec.no_latein and policies_id.late_id and\
    #                     rec.total_latein:
    #                 latein = policies_id.late_id
    #                 weekday_ids = self.env['hr.attendance.sheet.line'].search([
    #                     ('name_id', '=', rec.id), ('status', '=', 'weekday')])
    #                 for weekday in weekday_icompute_attendanceds:
    #                      if weekday.latein:
    #                         latein_minutes = weekday.latein * 60  # Convert to minutes for easier comparison
    #
    #                         if 15 <= latein_minutes < 30:
    #                             no_of_times_15min += 1
    #                             for line in latein.attendance_line_ids:
    #                                 # print("................loop",line)
    #                                 # If more than 4 occurrences, apply the 4th policy for subsequent occurrences
    #                                 if no_of_times_15min > 4 and line.num_of_times == '4':
    #                                     if line.time < (30 / 60):  # Ensure line.time matches the 15min condition
    #                                         if line.amount_type == "rate":
    #                                             rec.final_total_late_15min += (line.rate / 100) * (rec.employee_id.contract_id.total / 30)
    #                                             # self.attendance_sheet_ids.insert_latein_transaction()
    #
    #                                         else:
    #                                             rec.final_total_late_15min += line.amount
    #                                     continue  
    #
    #                                 # Apply the specific policy for the current occurrence
    #                                 if line.num_of_times == str(no_of_times_15min) and line.time < (30 / 60):
    #                                     if line.amount_type == "rate":
    #                                         rec.final_total_late_15min += (line.rate / 100) * (rec.employee_id.contract_id.total / 30)
    #                                         # if rec.latein_bool == True:
    #                                         # for sheet_line in self.attendance_sheet_ids:
    #                                         #     if sheet_line.latein_bool == True:
    #                                         #         if sheet_line.latein_transaction_id:
    #                                         #             latein_transaction = self.env['salary.allowance.detection']
    #                                         #
    #                                         #             vals = {
    #                                         #                  'employee_number':  rec.name_id.employee_id.employee_no,
    #                                         #                 'employee_id': rec.name_id.employee_id.id,
    #                                         #                 'department': rec.name_id.employee_id.department_id.id or False,
    #                                         #                 'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
    #                                         #                 'date':rec.date,
    #                                         #                 'hr_transaction_id': rec.latein_transaction_id.id or False,
    #                                         #                 'transaction_type_id': rec.latein_transaction_id.transaction_type_id.id or False,
    #                                         #                 'days': 0.0,
    #                                         #                 'attendance_sheet_id': rec.name_id.id,
    #                                         #                 'type': rec.latein_transaction_id.rule_type,
    #                                         #                 'reason': 'Late in Transaction'
    #                                         #             }
    #                                         #             transaction = latein_transaction.create(vals)
    #                                         #             transaction.onchange_transaction_type()
    #                                         #             if transaction.hr_transaction_id.unit_type == 'days':
    #                                         #                 transaction.days = 1
    #                                         #             return transaction,transaction.date  
    #                                         #
    #                                         # # transaction_search = self.env['salary.allowance.detection'].search([])
    #                                         # # for transaction in transaction_search:
    #                                         # #     for sheet in self.attendance_sheet_ids:
    #                                         # #         if (sheet.date == transaction.date) and (transaction.hr_transaction_id==line.latein_transaction_id):
    #                                         # #             transaction.amount = (line.rate * transaction.amount)/100
    #                                         # #             print(".........transaction",transaction.amount)
    #                                         # # transaction = self.attendance_sheet_ids.insert_latein_transaction()
    #                                         # # for attendance in self.attendance_sheet_ids.insert_latein_transaction():
    #                                         # #     print("......attendance",attendance)
    #                                         # # for attend in rec.attendance_sheet_ids:
    #                                         # #     print("..........22222222222222222222222222",attend)
    #                                         # #
    #                                         # #     insert_latein_transaction():
    #                                         # #         print("..........trans",trans)
    #                                         # #         if trans.date == attend.date:
    #                                         # #                 # if attend.date == transaction.date:
    #                                         # #                 # transaction = trans.date
    #                                         # #             trans.amount = (line.rate * trans.amount)/100
    #                                         # # transaction.amount = line.rate * transaction.amount
    #                                     else:
    #                                         rec.final_total_late_15min += line.amount
    #                                     break  
    #
    #                         elif 30 <= latein_minutes < 60:
    #                             no_of_times_30min += 1
    #                             for line in latein.attendance_line_ids:
    #                                 # Apply the 4th occurrence policy for further lateness
    #                                 if no_of_times_30min > 4 and line.num_of_times == '4':
    #                                     if line.time < (60 / 60):
    #                                         if line.amount_type == "rate":
    #                                             rec.final_total_late_30min += (line.rate / 100) * (rec.employee_id.contract_id.total / 30)
    #                                         else:
    #                                             rec.final_total_late_30min += line.amount
    #                                     continue
    #
    #                                 # Apply the specific policy for the current occurrence
    #                                 if line.num_of_times == str(no_of_times_30min) and line.time < (60 / 60):
    #                                     if line.amount_type == "rate":
    #                                         rec.final_total_late_30min += (line.rate / 100) * (rec.employee_id.contract_id.total / 30)
    #                                     else:
    #                                         rec.final_total_late_30min += line.amount
    #                                     break
    #
    #                         elif latein_minutes >= 60:
    #                             no_of_times_1hour += 1
    #                             for line in latein.attendance_line_ids:
    #                                 if no_of_times_1hour > 4 and line.num_of_times == '4':
    #                                     if line.time >= (60 / 60):
    #                                         if line.amount_type == "rate":
    #                                             rec.final_total_late_more_1hour += (line.rate / 100) * (rec.employee_id.contract_id.total / 30)
    #                                         else:
    #                                             rec.final_total_late_more_1hour += line.amount
    #                                     continue
    #
    #                                 if line.num_of_times == str(no_of_times_1hour) and line.time >= (60 / 60):
    #                                     if line.amount_type == "rate":
    #                                         rec.final_total_late_more_1hour += (line.rate / 100) * (rec.employee_id.contract_id.total / 30)
    #                                     else:
    #                                         rec.final_total_late_more_1hour += line.amount
    #                                     break
    #
    #                 # Sum up the total late deductions
    #                 rec.latein = rec.final_total_late_30min + rec.final_total_late_more_1hour + rec.final_total_late_15min
    #
    #
    #
    #                             ######## working correctly
    #                             # if str(rec.no_latein) == line.num_of_times:
    #                             #     # if weekday.latein >= line.time:
    #                             #     if line.time >= weekday.latein:
    #                             #
    #                             #         if line.amount_type == "rate":
    #                             #             rec.latein = rec.latein + (weekday.latein * (line.rate/100) * (rec.employee_id.contract_id.wage/(30*int(rec.employee_id.resource_calendar_id.hours_per_day))))
    #                             #             # rec.latein = rec.latein + (weekday.latein * line.rate)
    #                             #             break
    #                             #         else:
    #                             #             rec.latein = rec.latein + line.amount
    #                             #             break
    #                             # if str(rec.no_latein) != line.num_of_times:
    #                             #     if line.num_of_times == '4':
    #                             #         if weekday.latein >= line.time:
    #                             #             if line.amount_type == "rate":
    #                             #                 rec.latein = rec.latein + (weekday.latein * (line.rate/100) * (rec.employee_id.contract_id.wage/(30*int(rec.employee_id.resource_calendar_id.hours_per_day))))
    #                             #                 # rec.latein = rec.latein + (weekday.latein * line.rate)
    #                             #                 break
    #                             #             else:
    #                             #                 rec.latein = rec.latein + line.amount
    #                             #                 break   
    #
    #             # Calculated the overtime
    #             if rec.no_overtime and rec.total_overtime and\
    #                     policies_id.overtime_id:
    #                 weekend_id = self.env['hr.attendance.sheet.line'].search([
    #                     ('name_id', '=', rec.id), ('status', '=', 'weekend')])
    #                 weekday_id = self.env['hr.attendance.sheet.line'].search([
    #                     ('name_id', '=', rec.id), ('status', '=', 'weekday')])
    #                 for weekend in weekend_id:
    #
    #                     for line in\
    #                             policies_id.overtime_id.overtime_line_ids:
    #                         if line.policie_type == 'week_end' and\
    #                                 weekend.overtime >= line.apply_after:
    #                         # if line.policie_type == 'week_end':
    #                             ''' overtime is calculated based on the wage amount and rate of overtime rule.That wage amount is calculated based on one day and 8 hours working for single day'''
    #                             overtime = overtime + \
    #                                 (weekend.overtime * (line.rate/100) * (rec.employee_id.contract_id.wage/(30*int(rec.employee_id.resource_calendar_id.hours_per_day))))
    #
    #                             # overtime = overtime + \
    #                             #     (weekend.overtime * line.rate)    
    #                             break
    #                 overtime_amount = 0        
    #                 for weekday in weekday_id:
    #                     for line in\
    #                             policies_id.overtime_id.overtime_line_ids:
    #
    #                         if line.policie_type == 'working_days' and\
    #                                 weekday.overtime >= line.apply_after:
    #                             overtime = overtime + \
    #                                 (weekday.overtime * (line.rate/100) * (rec.employee_id.contract_id.total/(30*int(rec.employee_id.resource_calendar_id.hours_per_day))))
    #                             # overtime = overtime + \
    #                             #      (weekday.overtime * line.rate)     
    #                             break
    #
    #             rec.overtime = overtime
    #
    #             # calculating the time Different
    #             if rec.no_difftime and policies_id.diff_rule_id and\
    #                     rec.total_difftime:
    #                 difftime = policies_id.diff_rule_id
    #                 for line in difftime.diff_line_ids:
    #                     if rec.total_difftime >= line.time:
    #                         rec.time_different = rec.total_difftime * (line.rate/100) * (rec.employee_id.contract_id.total/(30*int(rec.employee_id.resource_calendar_id.hours_per_day)))
    #                         # rec.time_different = rec.total_difftime * line.rate
    #                         break
    #
    #             if rec.no_absence and policies_id.absent_id:
    #                 absent = policies_id.absent_id
    #                 for line in absent.absence_line_ids:
    #                     if str(rec.no_absence) == line.time:
    #                         rec.absent = (line.rate/100) * (rec.employee_id.contract_id.total/(30*int(rec.employee_id.resource_calendar_id.hours_per_day)))
    #                         rec.absent = rec.absent * rec.total_absence
    #                         # rec.absent = line.rate
    #                         break
    #                     if str(rec.no_absence) != line.time:
    #                         if line.time == '3':
    #                             rec.absent = (line.rate/100) * (rec.employee_id.contract_id.total/(30*int(rec.employee_id.resource_calendar_id.hours_per_day)))
    #                             rec.absent = rec.absent * rec.total_absence
    #                             # rec.absent = line.rate
    #                             break
    #             if rec.no_early_checkout and policies_id.early_checkout_id:
    #                 early_out = policies_id.early_checkout_id
    #                 for i in range(1, rec.no_early_checkout + 1):
    #                     for line in early_out.early_checkout_line_ids:
    #                         if i > 4 and line.early_time == '4':
    #                             rec.early_check_out_amount += (line.early_rate / 100) * (rec.employee_id.contract_id.total / 30)
    #                             continue
    #                         if str(i) == line.early_time:
    #                             rec.early_check_out_amount += (line.early_rate / 100) * (rec.employee_id.contract_id.total / 30)
    #                             break
    #                 # for line in early_out.early_checkout_line_ids:
    #                 #     if str(rec.no_early_checkout)==line.early_time: 
    #                 #         rec.early_check_out_amount += (line.early_rate/100) * (rec.employee_id.contract_id.total/30) 
    #                 #         early_checkout_applied = True
    #                 #         break
    #                 # # if str(rec.no_early_checkout) != line.early_time:
    #                 #         if line.early_time=='4':
    #                 #             rec.early_check_out_amount = (line.early_rate/100) * (rec.employee_id.contract_id.total/30) 
    #                 #             break
    #     for line in self.attendance_sheet_ids:
    #         line.insert_overtime_transaction()
    #         line.insert_absence_transaction()
    #         line.insert_earlyout_transaction()
    #         line.insert_latein_transaction()                       if no_of_times_30min > 4 and line.num_of_times == '4':
    #                                     if line.time < (60 / 60):
    #                                         if line.amount_type == "rate":
    #                                             rec.final_total_late_30min += (line.rate / 100) * (rec.employee_id.contract_id.total / 30)
    #                                         else:
    #                                             rec.final_total_late_30min += line.amount
    #                                     continue
    #
    #                                 # Apply the specific policy for the current occurrence
    #                                 if line.num_of_times == str(no_of_times_30min) and line.time < (60 / 60):
    #                                     if line.amount_type == "rate":
    #                                         rec.final_total_late_30min += (line.rate / 100) * (rec.employee_id.contract_id.total / 30)
    #                                     else:
    #                                         rec.final_total_late_30min += line.amount
    #                                     break
    #
    #                         elif latein_minutes >= 60:
    #                             no_of_times_1hour += 1
    #                             for line in latein.attendance_line_ids:
    #                                 if no_of_times_1hour > 4 and line.num_of_times == '4':
    #                                     if line.time >= (60 / 60):
    #                                         if line.amount_type == "rate":
    #                                             rec.final_total_late_more_1hour += (line.rate / 100) * (rec.employee_id.contract_id.total / 30)
    #                                         else:
    #                                             rec.final_total_late_more_1hour += line.amount
    #                                     continue
    #
    #                                 if line.num_of_times == str(no_of_times_1hour) and line.time >= (60 / 60):
    #                                     if line.amount_type == "rate":
    #                                         rec.final_total_late_more_1hour += (line.rate / 100) * (rec.employee_id.contract_id.total / 30)
    #                                     else:
    #                                         rec.final_total_late_more_1hour += line.amount
    #                                     break
    #
    #                 # Sum up the total late deductions
    #                 rec.latein = rec.final_total_late_30min + rec.final_total_late_more_1hour + rec.final_total_late_15min
    #
    #
    #
    #                             ######## working correctly
    #                             # if str(rec.no_latein) == line.num_of_times:
    #                             #     # if weekday.latein >= line.time:
    #                             #     if line.time >= weekday.latein:
    #                             #
    #                             #         if line.amount_type == "rate":
    #                             #             rec.latein = rec.latein + (weekday.latein * (line.rate/100) * (rec.employee_id.contract_id.wage/(30*int(rec.employee_id.resource_calendar_id.hours_per_day))))
    #                             #             # rec.latein = rec.latein + (weekday.latein * line.rate)
    #                             #             break
    #                             #         else:
    #                             #             rec.latein = rec.latein + line.amount
    #                             #             break
    #                             # if str(rec.no_latein) != line.num_of_times:
    #                             #     if line.num_of_times == '4':
    #                             #         if weekday.latein >= line.time:
    #                             #             if line.amount_type == "rate":
    #                             #                 rec.latein = rec.latein + (weekday.latein * (line.rate/100) * (rec.employee_id.contract_id.wage/(30*int(rec.employee_id.resource_calendar_id.hours_per_day))))
    #                             #                 # rec.latein = rec.latein + (weekday.latein * line.rate)
    #                             #                 break
    #                             #             else:
    #                             #                 rec.latein = rec.latein + line.amount
    #                             #                 break   
    #
    #             # Calculated the overtime
    #             if rec.no_overtime and rec.total_overtime and\
    #                     policies_id.overtime_id:
    #                 weekend_id = self.env['hr.attendance.sheet.line'].search([
    #                     ('name_id', '=', rec.id), ('status', '=', 'weekend')])
    #                 weekday_id = self.env['hr.attendance.sheet.line'].search([
    #                     ('name_id', '=', rec.id), ('status', '=', 'weekday')])
    #                 for weekend in weekend_id:
    #
    #                     for line in\
    #                             policies_id.overtime_id.overtime_line_ids:
    #                         if line.policie_type == 'week_end' and\
    #                                 weekend.overtime >= line.apply_after:
    #                         # if line.policie_type == 'week_end':
    #                             ''' overtime is calculated based on the wage amount and rate of overtime rule.That wage amount is calculated based on one day and 8 hours working for single day'''
    #                             overtime = overtime + \
    #                                 (weekend.overtime * (line.rate/100) * (rec.employee_id.contract_id.wage/(30*int(rec.employee_id.resource_calendar_id.hours_per_day))))
    #
    #                             # overtime = overtime + \
    #                             #     (weekend.overtime * line.rate)    
    #                             break
    #                 overtime_amount = 0        
    #                 for weekday in weekday_id:
    #                     for line in\
    #                             policies_id.overtime_id.overtime_line_ids:
    #
    #                         if line.policie_type == 'working_days' and\
    #                                 weekday.overtime >= line.apply_after:
    #                             overtime = overtime + \
    #                                 (weekday.overtime * (line.rate/100) * (rec.employee_id.contract_id.total/(30*int(rec.employee_id.resource_calendar_id.hours_per_day))))
    #                             # overtime = overtime + \
    #                             #      (weekday.overtime * line.rate)     
    #                             break
    #
    #             rec.overtime = overtime
    #
    #             # calculating the time Different
    #             if rec.no_difftime and policies_id.diff_rule_id and\
    #                     rec.total_difftime:
    #                 difftime = policies_id.diff_rule_id
    #                 for line in difftime.diff_line_ids:
    #                     if rec.total_difftime >= line.time:
    #                         rec.time_different = rec.total_difftime * (line.rate/100) * (rec.employee_id.contract_id.total/(30*int(rec.employee_id.resource_calendar_id.hours_per_day)))
    #                         # rec.time_different = rec.total_difftime * line.rate
    #                         break
    #
    #             if rec.no_absence and policies_id.absent_id:
    #                 absent = policies_id.absent_id
    #                 for line in absent.absence_line_ids:
    #                     if str(rec.no_absence) == line.time:
    #                         rec.absent = (line.rate/100) * (rec.employee_id.contract_id.total/(30*int(rec.employee_id.resource_calendar_id.hours_per_day)))
    #                         rec.absent = rec.absent * rec.total_absence
    #                         # rec.absent = line.rate
    #                         break
    #                     if str(rec.no_absence) != line.time:
    #                         if line.time == '3':
    #                             rec.absent = (line.rate/100) * (rec.employee_id.contract_id.total/(30*int(rec.employee_id.resource_calendar_id.hours_per_day)))
    #                             rec.absent = rec.absent * rec.total_absence
    #                             # rec.absent = line.rate
    #                             break
    #             if rec.no_early_checkout and policies_id.early_checkout_id:
    #                 early_out = policies_id.early_checkout_id
    #                 for i in range(1, rec.no_early_checkout + 1):
    #                     for line in early_out.early_checkout_line_ids:
    #                         if i > 4 and line.early_time == '4':
    #                             rec.early_check_out_amount += (line.early_rate / 100) * (rec.employee_id.contract_id.total / 30)
    #                             continue
    #                         if str(i) == line.early_time:
    #                             rec.early_check_out_amount += (line.early_rate / 100) * (rec.employee_id.contract_id.total / 30)
    #                             break
    #                 # for line in early_out.early_checkout_line_ids:
    #                 #     if str(rec.no_early_checkout)==line.early_time: 
    #                 #         rec.early_check_out_amount += (line.early_rate/100) * (rec.employee_id.contract_id.total/30) 
    #                 #         early_checkout_applied = True
    #                 #         break
    #                 # # if str(rec.no_early_checkout) != line.early_time:
    #                 #         if line.early_time=='4':
    #                 #             rec.early_check_out_amount = (line.early_rate/100) * (rec.employee_id.contract_id.total/30) 
    #                 #             break
    #     for line in self.attendance_sheet_ids:
    #         line.insert_overtime_transaction()
    #         line.insert_absence_transaction()
    #         line.insert_earlyout_transaction()
    #         line.insert_latein_transaction()


    def _get_planned_checkin(self, curr_date):
        cr = self._cr
        user = self.env.user
        check_in_dt = datetime.strptime(str(curr_date),
                                        DEFAULT_SERVER_DATE_FORMAT)
        local_tz = pytz.timezone(user.tz or 'UTC')
        ci_dt = check_in_dt.replace(tzinfo=pytz.utc
                                    ).astimezone(local_tz)
        hour_from = 0.0
        for rec in self:
            qry = '''select hour_from
                            from resource_calendar rc, \
                            resource_calendar_attendance rca
                            where rc.id = rca.calendar_id and
                            rc.id = %s and \
                            dayofweek=%s'''
            qry1 = qry + " and %s between date_from and date_to order by \
            hour_from limit 1"
            params1 = (rec.employee_id.resource_calendar_id.id,
                       str(ci_dt.weekday()),
                       curr_date)
            cr.execute(qry1, params1)
            res = cr.fetchone()
            # If specific dates are not given then fetch the records that do
            # not have dates
            if not res:
                qry2 = qry + " order by hour_from limit 1"
                params2 = (rec.employee_id.resource_calendar_id.id,
                           str(ci_dt.weekday()))
                cr.execute(qry2, params2)
                res = cr.fetchone()
            hour_from = res and res[0]
        return hour_from

    def _get_planned_checkout(self, curr_date):
        cr = self._cr
        user = self.env.user
        employee = self.employee_id

        check_in_dt = datetime.strptime(str(curr_date),
                                        DEFAULT_SERVER_DATE_FORMAT)
        local_tz = pytz.timezone(user.tz or 'UTC')
        co_dt = check_in_dt.replace(tzinfo=pytz.utc
                                    ).astimezone(local_tz)
        hour_to = 0.0
        for rec in self:
            qry = '''select hour_to,rca.id as rca_id
                        from resource_calendar rc, \
                        resource_calendar_attendance rca
                        where rc.id = rca.calendar_id and
                        rc.id = %s and \
                        dayofweek=%s'''
            qry1 = qry + "and %s between date_from and date_to order by \
               hour_to desc limit 1"
            params1 = (employee.resource_calendar_id.id,
                       str(co_dt.weekday()), curr_date)
            cr.execute(qry1, params1)
            res = cr.fetchone()
            # If specific dates are not given then fetch the records that do
            # not have dates
            if not res:
                qry2 = qry + " order by hour_to desc limit 1"
                params2 = (employee.resource_calendar_id.id,
                           str(co_dt.weekday()))
                cr.execute(qry2, params2)
                res = cr.fetchone()
            hour_to = res and res[0]
        return hour_to

    


    def _calc_current_attendance(self, attendances_ids, curr_date):
        """Method is used to calculate total attendance."""
        user = self.env.user
        local_tz = pytz.timezone(user.tz or 'UTC')
        curr_dt = curr_date
        vals = {'total_attendance': 0.0,
                'psignin': False,
                'psignout': False,
                'day': False,
                'asignin': False,
                'asignout': False,
                'export_bool': False,
                'early_out_line': False,
                'work_type': False
                }
        for atten in self:
            ttl_diff = 0.0
            converted_time = 0.0
            last_in = []
            last_out = []
            vals = {}
            lastin = 0.0
            lastout = 0.0
            employee_work_type = False

            for attends in attendances_ids:


                # attends.process = 'yes'
                if attends.check_in:
                    
                    
                    
                    ci_dt = attends.check_in.replace(tzinfo=pytz.utc
                                                      ).astimezone(local_tz)
                    # check_in_adjusted = (attends.check_in + timedelta(hours=5, minutes=30)) if attends.check_in else ''
                    # check_out_adjusted = (attends.check_out + timedelta(hours=5, minutes=30)) if attends.check_out else ''
                    # ci_dt = check_in_adjusted
                    ci_dt1 = ci_dt.date()
                    if curr_dt == ci_dt1:
                        employee_work_type = attends.work_type
                        ''' this is for when the year is 1900 then time is put in zero'''
                        if ci_dt.year == 1900:
                            ci_dt = False
                            if ci_dt:
                                last_in.append(ci_dt.time())
                            
                        else:    
                            last_in.append(ci_dt.time())
                        # last_in.append(ci_dt.time())
                        if attends.check_out:
                            co_dt = attends.check_out.replace(
                                tzinfo=pytz.utc).astimezone(local_tz)
                            # print(".........originalcout",co_dt)
                            # co_dt = check_out_adjusted
                            co_dt1 = co_dt.date()
                            ''' this is for when the year is 1900 then time is put in zero'''
                            if co_dt.year == 1900:
                                co_dt = False
                                if co_dt:
                                    last_out.append(co_dt.time())
                                
                            else:    
                                last_out.append(co_dt.time())
                            # last_out.append(co_dt.time())    
                            if curr_dt == co_dt1:
                                diff = co_dt - ci_dt
                                ttl_diff = diff.total_seconds() / 60.0 / 60.0
                                converted_time += ttl_diff
                        else:
                            diff = curr_dt - ci_dt.date()
                            ttl_diff = diff.total_seconds() / 60.0 / 60.0
                            converted_time += ttl_diff

            curr_ttl_attendance = converted_time
            # print("curr_ttl_attendance",curr_ttl_attendance)
            last_in.sort()
            last_out.sort(reverse=True)

            # if last_in:
            #     actual_signin_time = last_in[0]
            #     lastin = actual_signin_time.hour + (actual_signin_time.minute * 100 / 60) / 100.0
            # if last_out:
            #     actual_signout_time = last_out[0]
            #     lastout = actual_signout_time.hour + (actual_signout_time.minute * 100 / 60) / 100.0

            for date in last_in:
                lastin = date.hour + (date.minute * 100 / 60) / 100.0
                break
            for date in last_out:
                lastout = date.hour + (date.minute * 100 / 60) / 100.0
                break

            vals.update({'total_attendance': curr_ttl_attendance,
                         'psignin': atten._get_planned_checkin(
                             curr_date) or False,
                         'psignout': atten._get_planned_checkout(
                             curr_date) or False,
                         'day': calendar.day_name[curr_dt.weekday() or False],
                         'asignin': lastin or False,
                         'asignout': lastout or False,
                         'export_bool': False,
                         'early_out_line': False,
                         'work_type': employee_work_type or False
                         
                         })

        return vals

    # def time_to_float(t):
    #     if isinstance(t, time):
    #         return t.hour + t.minute / 60 + t.second / 3600
    #     elif isinstance(t, str):
    #         h, m, s = map(int, t.split(':'))
    #         return h + m / 60 + s / 3600
    #     else:
    #         raise ValueError("Unsupported time format")

    # def get_attendance(self, batch_size=5):
    #     """Get Attendance History Of Employee with batch processing to avoid long polling."""
    #     for record in self:
    #         record.ensure_one()  # Ensure singleton for each record in the loop
    #
    #         # Define the date range
    #         all_dates = [record.request_date_from + timedelta(days=x) for x in range(
    #             (record.request_date_to - record.request_date_from).days + 1)]
    #
    #         # Fetch attendance records and holiday dates once
    #         attendance_ids = self.env['hr.attendance'].search([
    #             ('employee_id', '=', record.employee_id.id),
    #             ('check_in', '>=', record.request_date_from),
    #             ('check_in', '<=', record.request_date_to),
    #         ])
    #
    #         national_holidays = self.env['resource.calendar.leaves'].search([
    #             ('resource_id', '=', False)
    #         ])
    #
    #         # Collect holiday dates for the range
    #         holiday_dates = []
    #         for holiday in national_holidays:
    #             holiday_start = max(holiday.date_from.date(), record.request_date_from)
    #             holiday_end = min(holiday.date_to.date(), record.request_date_to)
    #             if holiday_start <= holiday_end:
    #                 holiday_date = holiday_start
    #                 while holiday_date <= holiday.date_to.date():
    #                     holiday_dates.append(holiday_date)
    #                     holiday_date += timedelta(days=1)
    #
    #         # Process dates in batches
    #         date_batches = [all_dates[i:i + batch_size] for i in range(0, len(all_dates), batch_size)]
    #
    #         for batch_dates in date_batches:
    #             for date in batch_dates:
    #                 vals = {}
    #                 vals = record._calc_current_attendance(attendance_ids, date)
    #                 vals.update({'name_id': record.id, 'date': date, 'status': 'weekday'})
    #
    #                 if vals['psignin'] == 0.0 and vals['psignout'] == 0.0:
    #                     vals.update({'status': 'weekend'})
    #
    #                 if date in holiday_dates:
    #                     holiday_records = self.env['resource.calendar.leaves'].search([
    #                         ('resource_id', '=', False),
    #                         ('date_from', '<=', date),
    #                         ('date_to', '>=', date),
    #                     ])
    #                     if holiday_records:
    #                         vals.update({'status': 'holiday', 'holiday_status': holiday_records.name})
    #                     else:
    #                         vals.update({'status': 'holiday', 'holiday_status': 'Public Holiday'})
    #                 else:
    #                     leave = self.env['hr.leave'].search([
    #                         ('employee_id', '=', record.employee_id.id),
    #                         ('state', '=', 'validate'),
    #                         ('request_date_from', '<=', date),
    #                         ('request_date_to', '>=', date)
    #                     ])
    #                     if leave:
    #                         vals.update({'status': 'leave', 'holiday_status': leave.holiday_status_id.code or False + ' - ' + leave.holiday_status_id.name})
    #                     if not leave:
    #                         vals.update({'status': 'absence'})
    #
    #                 # Early checkout, late-in, overtime, and difftime logic goes here...
    #
    #                 # Check if an attendance line already exists for this date
    #                 existing_line = self.env['hr.attendance.sheet.line'].search([
    #                     ('name_id', '=', record.id), 
    #                     ('date', '=', date),
    #                     ('export_bool', '=', True)
    #                 ], limit=1)
    #
    #                 # Update if it exists; create if it doesn’t
    #                 if existing_line:
    #                     existing_line.write(vals)
    #                 else:
    #                     self.env['hr.attendance.sheet.line'].create(vals)
    #
    #             # Commit after processing each batch to reduce transaction size
    #             self.env.cr.commit()
    #
    #         # Set the attendance sheet ID for the employee
    #         record.employee_id.attendance_sheet_id = record.id or False

    
    def get_attendance(self, batch_size=10):
        """Get Attendance History of Employees in Batches to Avoid Long Polling Issues."""
        records = self
        while records:
            # Limit the number of records processed in each batch to avoid long polling
            batch_records = records[:batch_size]
            records = records[batch_size:]  # Update the remaining records

            for record in batch_records:
                record.ensure_one()  # Ensure singleton for each record
                
                attendance_ids = self.env['hr.attendance'].search([
                    ('employee_id', '=', record.employee_id.id),
                    ('check_in', '>=', record.request_date_from),
                    ('check_in', '<=', record.request_date_to),
                    
                ])
                
                lst = []
                vals = {}
                dates = [record.request_date_from + timedelta(days=x) for x in range(
                    (record.request_date_to - record.request_date_from).days + 1)]
                
                # Fetch holiday dates
                national_holidays = self.env['resource.calendar.leaves'].search([
                    ('resource_id', '=', False)
                ])
                
                holiday_dates = []
                for holiday in national_holidays:
                    holiday_start = max(holiday.date_from.date(), record.request_date_from)
                    holiday_end = min(holiday.date_to.date(), record.request_date_to)
                    if holiday_start <= holiday_end:
                        holiday_date = holiday_start
                        while holiday_date <= holiday.date_to.date():
                            holiday_dates.append(holiday_date)
                            holiday_date += timedelta(days=1)
                
                # Remove lines if export_bool is False
                for line in record.attendance_sheet_ids:
                    for li in attendance_ids:
                        if li.check_in.date() == line.date and li.process == 'no':
                            line.export_bool = False
                            line.export = 'no'
                            li.process = 'yes'
                    if not line.export_bool:
                        line.unlink()
                early_out = 0.00 
                

                # Process attendance entries
                for date in dates:
                    if date not in lst:

                        lst.append(date)
                        vals = record._calc_current_attendance(attendance_ids, date)

                        vals.update({'name_id': record.id, 'date': date, 'status': 'weekday'})
                        
                        if vals['psignin'] == 0.0 and vals['psignout'] == 0.0:
                            vals.update({'status': 'weekend'})
                        
                        # Set holiday or absence status
                        if vals['psignin'] and vals['psignout']:
                            if vals['asignin'] == 0.0 and vals['asignout'] == 0.0:
                                if date in holiday_dates:
                                    holiday_records = self.env['resource.calendar.leaves'].search([
                                        ('resource_id', '=', False),
                                        ('date_from', '<=', date),
                                        ('date_to', '>=', date),
                                    ])
                                    vals.update({
                                        'status': 'holiday',
                                        'holiday_status': holiday_records.name if holiday_records else 'Public Holiday'
                                    })
                                else:
                                    leave = self.env['hr.leave'].search([
                                        ('employee_id', '=', record.employee_id.id),
                                        ('state', '=', 'validate'),
                                        ('request_date_from', '<=', date),
                                        ('request_date_to', '>=', date)
                                    ])
                                    if leave:
                                        vals.update({
                                            'status': 'leave',
                                            'holiday_status': f"{leave.holiday_status_id.code or ''} - {leave.holiday_status_id.name}"
                                        })
                                    else:
                                        # vals.update({'status': 'absence'})
                                        '''This code is used for Execute Employee is not going to give the attendance  but they want entry record in attendance sheet.so it will added '''
                                        if record.atte_required:
                                            vals.update({'status': 'absence'})
                                        if not record.atte_required:
                                            vals.update({'status': 'weekday'})
                                            
                                            # vals.update({'asignin':vals['psignin'],'asignout':vals['psignout']})   
                            
                        # Early checkout handling
                        if attendance_ids.employee_id.contract_id.attend_police_id:
                            for early_out_rule in attendance_ids.employee_id.contract_id.attend_police_id.early_checkout_id.early_checkout_line_ids:
                                if vals['psignin'] !=0.0 and vals['psignout'] !=0.0:
                                    if vals['asignin'] != 0.0 and vals['asignout'] != 0.0:
                                        if vals['status'] == 'weekday':
                                            if early_out_rule.early_rate > 0:
                                                early_out = vals['asignout'] - vals['psignout']
                                                vals.update({'early_out_line': abs(early_out) if early_out < 0.0 else 0.00})
                                                if early_out_rule.time <= vals['early_out_line']:
                                                    vals.update({'early_out_line': abs(early_out)})
                                                else:
                                                    vals.update({'early_out_line': 0.0})
                                                    
                                    
                        # Late-in handling
                        if attendance_ids.employee_id.contract_id.attend_police_id:
                            for attendance_rule in attendance_ids.employee_id.contract_id.attend_police_id.late_id.attendance_line_ids:
                                if (attendance_rule.rate > 0 or attendance_rule.amount > 0) and vals['asignin'] > vals['psignin'] and vals['status'] == 'weekday':
                                    late = vals['asignin'] - vals['psignin']
                                    if attendance_ids.employee_id.contract_id.attend_police_id.attendance_grace_time:
                                        late_in = late - attendance_ids.employee_id.contract_id.attend_police_id.attendance_grace_time
                                        # print("late_in", late_in)
                                        if late_in > 0:
                                            # vals.update({'latein': late if late >= attendance_rule.time else 0.00})
                                            vals.update({'latein': late_in})
                                    else:
                                        vals.update({'latein': late if late >= attendance_rule.time else 0.00})
                                        # print("else latein", vals)


                        # Calculate overtime
                        avg_hours = record.employee_id.resource_calendar_id.hours_per_day if record.employee_id and record.employee_id.resource_calendar_id else False
                        resource_calendar_id = record.employee_id.resource_calendar_id
                        
                        for line in resource_calendar_id.attendance_ids:
                            # print("line, line.date_from, line.date_to, date", line, line.date_from, line.date_to, date)
                            if line.date_from == date or line.date_to == date:
                                avg_hours = line.hour_to - line.hour_from
                                # print("avg_hours = line.hour_to - line.hour_from",line.hour_to, line.hour_from,avg_hours)
                        
                        # Apply overtime rules
                        if attendance_ids.employee_id.contract_id.attend_police_id:
                            for overtime_rule in attendance_ids.employee_id.contract_id.attend_police_id.overtime_id.overtime_line_ids:
                                # if overtime_rule.rate > 0 and vals['psignin'] and vals['psignout']:
                                if overtime_rule.rate > 0:
                                    if vals['asignin'] != 0.0 and vals['asignout'] != 0.0:
                                        if vals['status'] == 'weekday' and vals['total_attendance'] > avg_hours and overtime_rule.policie_type == 'working_days' and vals['psignin'] and vals['psignout']:
                                            #Working Code
                                            # overtime_week_day = vals['total_attendance'] - avg_hours - 1
                                            overtime_week_day = vals['asignout'] - vals['psignout']
                                            # print("overtime_week_day111122222222,vals['asignin'],vals['psignout'] ",overtime_week_day, vals['asignin'],vals['psignout'])

                                            # overtime_week_day = vals['total_attendance'] - avg_hours
                                            # print("overtime_week_day,vals['total_attendance'],avg_hours ",overtime_week_day, vals['total_attendance'], avg_hours)
                                            vals.update({'overtime': overtime_week_day if overtime_week_day >= overtime_rule.apply_after else 0.0})
                                        if vals['status'] == 'weekend' and vals['total_attendance'] and overtime_rule.policie_type == 'week_end':
                                            # print("vals['total_attendance']3333333333", vals['total_attendance'])
                                            vals.update({'overtime': vals['total_attendance'] if vals['total_attendance'] >= overtime_rule.apply_after else 0.0})
                            
                        # Time difference ru    avg_hours = record.employee_id.resource_calendar_id.hours_per_day if record.employee_id and record.employee_id.resource_calendar_id else False
                        
                     
                        if attendance_ids.employee_id.contract_id.attend_police_id:
                            for difference_rule in attendance_ids.employee_id.contract_id.attend_police_id.diff_rule_id.diff_line_ids:
                                if difference_rule.rate > 0 and vals['total_attendance'] < avg_hours and vals['psignin'] > 0.0 and vals['psignout'] > 0.0 and vals['status'] == 'weekday':
                                    vals.update({'difftime': avg_hours - vals['total_attendance']})
                        
                        
                        # flage = True
                        # if vals['status'] == 'weekend' and\
                        #         vals.get('overtime', False) <= 0.0:
                        #     continue
                        # if vals['status'] == 'absence':
                        #     for line in resource_calendar_id.attendance_ids:
                        #
                        #         if int(date.weekday()) == int(line.dayofweek) and\
                        #                 line.date_from and line.date_to:
                        #             if not line.date_to == date or\
                        #                     line.date_from == date:
                        #                 vals = {}
                        #

                        # if flage and vals:
                        #     self.env['hr.attendance.sheet.line'].create(vals)
                        
                        
                        # Check if line already exists; update or create accordingly
                        existing_line = self.env['hr.attendance.sheet.line'].search([
                            ('name_id', '=', record.id), ('date', '=', date), ('export_bool', '=', True)
                        ])
                        if existing_line:
                            vals.update({'export_bool': True})
                            existing_line.write(vals)
                        else:
                       
                            self.env['hr.attendance.sheet.line'].create(vals)  
                record.employee_id.attendance_sheet_id = record.id or False
            # Pause briefly between batches to avoid long polling issues
            if records:
                time.sleep(2)  # Pauses execution for 2 seconds to help avoid server timeouts

    '''This is for scheduler because get attendance is not worked for current utc time'''
    @api.model            
    def get_attendance_schedule(self):
        
        """Get Attendance Sheet for scheduler for time difference."""
        
        attendance_sheet_search = self.env['hr.attendance.sheet'].search([])
        
        for attendance in attendance_sheet_search:
            if attendance.request_date_from.strftime("%m-%Y") == fields.Date.today().strftime("%m-%Y"):
                curr_date = fields.Date.today()

                # Get attendance records within the date range of the attendance sheet
                attendances_ids = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_in', '>=', attendance.request_date_from),
                    ('check_out', '<=', attendance.request_date_to)
                ])
                
                attendance._calc_current_attendance(attendances_ids, curr_date)
                
                attendance.get_attendance()
    
    '''Currently working on nov 7th'''
    # def get_attendance(self):
    #     """Get Attendance History Of Employee."""
    #     for record in self:
    #         record.ensure_one()  # Ensure singleton for each record in the loop
    #
    #         attendance_ids = self.env['hr.attendance'].search([
    #             ('employee_id', '=', record.employee_id.id),
    #             ('check_in', '>=', record.request_date_from),
    #             ('check_in', '<=', record.request_date_to),
    #         ])
    #
    #         lst = []
    #         vals = {}
    #         dates = [record.request_date_from + timedelta(days=x) for x in range(
    #             (record.request_date_to - record.request_date_from).days + 1)]
    #
    #         # Fetch holiday dates
    #         national_holidays = self.env['resource.calendar.leaves'].search([
    #             ('resource_id', '=', False)
    #         ])
    #
    #         holiday_dates = []
    #         for holiday in national_holidays:
    #             holiday_start = max(holiday.date_from.date(), record.request_date_from)
    #             holiday_end = min(holiday.date_to.date(), record.request_date_to)
    #             if holiday_start <= holiday_end:
    #                 holiday_date = holiday_start
    #                 while holiday_date <= holiday.date_to.date():
    #                     holiday_dates.append(holiday_date)
    #                     holiday_date += timedelta(days=1)
    #
    #         # Remove lines if export_bool is False
    #         for line in record.attendance_sheet_ids:
    #             for li in attendance_ids:
    #                 if li.check_in.date() == line.date:
    #                     if li.process == 'no':
    #                         line.export_bool = False
    #                         line.export = 'no'
    #                         li.process = 'yes'
    #             if not line.export_bool:
    #                 line.unlink()
    #
    #         # Process attendance entries
    #         early_out = 0.00 
    #         for date in dates:
    #             vals = {}
    #             if date not in lst:
    #                 lst.append(date)
    #                 vals = record._calc_current_attendance(attendance_ids, date)
    #                 vals.update({'name_id': record.id, 'date': date, 'status': 'weekday'})
    #
    #                 if vals['psignin'] == 0.0 and vals['psignout'] == 0.0:
    #                     vals.update({'status': 'weekend'})
    #
    #                 if vals['psignin'] and vals['psignout']:
    #                     if vals['asignin'] == 0.0 and vals['asignout'] == 0.0:
    #                         if date in holiday_dates:
    #                             holiday_records = self.env['resource.calendar.leaves'].search([
    #                                 ('resource_id', '=', False),
    #                                 ('date_from', '<=', date),
    #                                 ('date_to', '>=', date),
    #                             ])
    #                             if holiday_records:
    #                                 vals.update({'status': 'holiday', 'holiday_status': holiday_records.name})
    #                             else:
    #                                 vals.update({'status': 'holiday', 'holiday_status': 'Public Holiday'})
    #                         else:
    #                             leave = self.env['hr.leave'].search([
    #                                 ('employee_id', '=', record.employee_id.id),
    #                                 ('state', '=', 'validate'),
    #                                 ('request_date_from', '<=', date),
    #                                 ('request_date_to', '>=', date)
    #                             ])
    #                             if leave:
    #                                 vals.update({'status': 'leave', 'holiday_status': leave.holiday_status_id.code or False + ' - ' + leave.holiday_status_id.name})
    #                             if not leave:
    #                                 vals.update({'status': 'absence'})
    #
    #                 # Early checkout handling
    #                 if attendance_ids.employee_id.contract_id.attend_police_id:
    #                     for early_out_rule in attendance_ids.employee_id.contract_id.attend_police_id.early_checkout_id.early_checkout_line_ids:
    #                         if early_out_rule.early_rate > 0 and vals['psignin'] and vals['psignout'] and vals['status'] == 'weekday':
    #                             if vals['asignin'] != 0.0 and vals['asignout'] != 0.0:
    #                                 early_out = vals['asignout'] - vals['psignout']
    #                                 vals.update({'early_out_line': abs(early_out) if early_out < 0.0 else 0.00})
    #
    #                 # Late-in handling
    #                 if attendance_ids.employee_id.contract_id.attend_police_id:
    #                     for attendance_rule in attendance_ids.employee_id.contract_id.attend_police_id.late_id.attendance_line_ids:
    #                         if (attendance_rule.rate > 0 or attendance_rule.amount > 0) and vals['asignin'] > vals['psignin'] and vals['status'] == 'weekday':
    #                             late = vals['asignin'] - vals['psignin']
    #                             vals.update({'latein': late if late >= attendance_rule.time else 0.00})
    #
    #                 # Calculate overtime
    #                 avg_hours = record.employee_id.resource_calendar_id.hours_per_day if record.employee_id and record.employee_id.resource_calendar_id else False
    #                 resource_calendar_id = record.employee_id.resource_calendar_id
    #
    #                 for line in resource_calendar_id.attendance_ids:
    #                     if line.date_from == date or line.date_to == date:
    #                         avg_hours = line.hour_to - line.hour_from
    #
    #                 # Apply overtime rules
    #                 if attendance_ids.employee_id.contract_id.attend_police_id:
    #                     for overtime_rule in attendance_ids.employee_id.contract_id.attend_police_id.overtime_id.overtime_line_ids:
    #                         if overtime_rule.rate > 0:
    #                             if vals['status'] == 'weekday' and vals['total_attendance'] > avg_hours and overtime_rule.policie_type == 'working_days':
    #                                 overtime_week_day = vals['total_attendance'] - avg_hours
    #                                 vals.update({'overtime': overtime_week_day if overtime_week_day >= overtime_rule.apply_after else 0.0})
    #                             elif vals['status'] == 'weekend' and vals['total_attendance'] and overtime_rule.policie_type == 'week_end':
    #                                 vals.update({'overtime': vals['total_attendance'] if vals['total_attendance'] >= overtime_rule.apply_after else 0.0})
    #
    #                 # Time difference rule handling
    #                 if attendance_ids.employee_id.contract_id.attend_police_id:
    #                     for difference_rule in attendance_ids.employee_id.contract_id.attend_police_id.diff_rule_id.diff_line_ids:
    #                         if difference_rule.rate > 0 and vals['total_attendance'] < avg_hours and vals['psignin'] > 0.0 and vals['psignout'] > 0.0 and vals['status'] == 'weekday':
    #                             vals.update({'difftime': avg_hours - vals['total_attendance']})
    #
    #                 # Check if line already exists; update or create accordingly
    #                 existing_line = self.env['hr.attendance.sheet.line'].search([
    #                     ('name_id', '=', record.id), ('date', '=', date), ('export_bool', '=', True)
    #                 ])
    #                 if existing_line:
    #                     vals.update({'export_bool': True})
    #                     existing_line.write(vals)
    #                 elif vals:
    #                     self.env['hr.attendance.sheet.line'].create(vals)
    #
    #         record.employee_id.attendance_sheet_id = record.id or False
            # '''extra for not getting user based time'''
            # for date in dates:  
            #     record._calc_current_attendance(attendance_ids, date)


    # def get_attendance(self):
    #     """Get Attendance History Of Employee."""
    #     self.ensure_one()
    #     attendance_ids = self.env['hr.attendance'].search([
    #         ('employee_id', '=', self.employee_id.id),
    #         ('check_in', '>=', self.request_date_from),
    #         ('check_in', '<=', self.request_date_to),
    #         ])
    #     lst = []
    #     vals = {}
    #     dates = [self.request_date_from + timedelta(days=x) for x in range(
    #         (self.request_date_to - self.request_date_from).days + 1)]
    #
    #     national_holidays = self.env['resource.calendar.leaves'].search([
    #                        ('resource_id', '=', False)
    #                     ])
    #
    #                     # Convert the records to a list of dates
    #     holiday_dates = []
    #     for holiday in national_holidays:
    #         holiday_start = max(holiday.date_from.date(), self.request_date_from)
    #         holiday_end = min(holiday.date_to.date(), self.request_date_to)
    #
    #         # Check if holiday_start <= holiday_end
    #         if holiday_start <= holiday_end:
    #         # Generate a list of dates for each holiday range
    #             holiday_date = holiday_start
    #             while holiday_date <= holiday.date_to.date():
    #                 holiday_dates.append(holiday_date)
    #                 holiday_date += timedelta(days=1)
    #
    #     for line in self.attendance_sheet_ids:
    #         for li in attendance_ids:
    #             if li.check_in.date() == line.date:
    #                 if li.process == 'no':
    #                     line.export_bool = False
    #                     line.export = 'no'
    #                     li.process = 'yes'
    #         if line.export_bool == False:
    #             line.unlink()
    #
    #     # self.attendance_sheet_ids.unlink()
    #     early_out = 0.00 
    #     for date in dates:
    #         vals = {}
    #         if date not in lst:
    #             lst.append(date)
    #             vals = self._calc_current_attendance(attendance_ids, date)
    #             vals.update({'name_id': self.id, 'date': date})
    #             vals.update({'status': 'weekday'})
    #
    #             if vals['psignin'] == 0.0 and vals['psignout'] == 0.0:
    #                 vals.update({'status': 'weekend'})
    #
    #             if vals['psignin'] and vals['psignout']:
    #                 if vals['asignin'] == 0.0 and vals['asignout'] == 0.0:
    #
    #                     if date in holiday_dates :
    #                         holiday_records = self.env['resource.calendar.leaves'].search([
    #                             ('resource_id', '=', False),
    #                             ('date_from', '<=', date),
    #                             ('date_to', '>=', date),
    #                         ])
    #                         if holiday_records:
    #                             vals.update({'status': 'holiday', 'holiday_status': holiday_records.name})
    #                         else:
    #                             vals.update({'status': 'holiday', 'holiday_status': 'Public Holiday'}) 
    #                     else:    
    #                         leave = self.env['hr.leave'].search(
    #                             [('employee_id', '=', self.employee_id.id),
    #                              ('state', '=', 'validate'),
    #                              ('request_date_from', '<=', date),
    #                              ('request_date_to', '>=', date)
    #                              ])
    #                         if leave:
    #                             vals.update({'status': 'leave','holiday_status':leave.holiday_status_id.code or  False + ' - '+leave.holiday_status_id.name})
    #                         if not leave:
    #                             vals.update({'status': 'absence'})
    #
    #
    #
    #
    #             if  attendance_ids.employee_id.contract_id.attend_police_id:
    #                 for early_out in attendance_ids.employee_id.contract_id.attend_police_id.early_checkout_id.early_checkout_line_ids:
    #                     if early_out.early_rate > 0:
    #                         if vals['psignin'] and vals['psignout'] and vals['status'] == 'weekday':
    #                             if vals['asignin'] != 0.0 and vals['asignout'] != 0.0:
    #                                 early_out = vals['asignout'] - vals['psignout']
    #                                 if early_out < 0.0:
    #                                     vals.update({'early_out_line':abs(early_out)})
    #                                 else:
    #                                     vals.update({'early_out_line':0.00})    
    #
    #             if  attendance_ids.employee_id.contract_id.attend_police_id:           
    #                 for attendance in attendance_ids.employee_id.contract_id.attend_police_id.late_id.attendance_line_ids:
    #                     if (attendance.rate > 0) or (attendance.amount >0):
    #                         if vals['asignin'] > vals['psignin'] and vals['status'] == 'weekday':
    #                             late = vals['asignin'] - vals['psignin']
    #
    #                             # Assuming both `late` and `attendance.time` are in float time format
    #                             if late >= attendance.time:
    #                                 vals.update({'latein': late})
    #                             else:
    #                                 vals.update({'latein': 0.00})
    #
    #
    #             # if vals['asignin'] > vals['psignin'] and\
    #             #         vals['status'] == 'weekday':
    #             #     late = vals['asignin'] - vals['psignin']
    #             #     vals.update({'latein': late})
    #
    #
    #             avg_hours = self.employee_id and \
    #                 self.employee_id.resource_calendar_id and \
    #                 self.employee_id.resource_calendar_id.hours_per_day or\
    #                 False
    #
    #             resource_calendar_id = self.employee_id and\
    #                 self.employee_id.resource_calendar_id
    #
    #             for line in resource_calendar_id.attendance_ids:
    #                 if line.date_from == date or line.date_to == date:
    #                     avg_hours = line.hour_to - line.hour_from
    #
    #             if  attendance_ids.employee_id.contract_id.attend_police_id:           
    #                 for overtime in attendance_ids.employee_id.contract_id.attend_police_id.overtime_id.overtime_line_ids:
    #                     if overtime.rate > 0:       
    #                         overtime_week_day = 0
    #                         overtime_week_end = 0
    #                         if vals['status']=='weekday':
    #                             if overtime.policie_type =='working_days':
    #                                 if vals['total_attendance'] > avg_hours:
    #                                     overtime_week_day = vals['total_attendance'] - avg_hours
    #                                     if overtime_week_day >= overtime.apply_after:
    #                                         vals.update({'overtime':
    #                                                      overtime_week_day or False},
    #                                                         )
    #                                     # else:
    #                                     #     vals.update({'overtime':0.0})  
    #
    #                         if vals['status'] == 'weekend' and vals['total_attendance']:
    #                             if overtime.policie_type =='week_end':
    #                                 overtime_week_end = vals['total_attendance']
    #                                 if overtime_week_end >= overtime.apply_after:
    #                                     vals.update({'overtime':
    #                                                  vals['total_attendance'] or False},
    #                                                     )
    #                             # else:
    #                             #     vals.update({'overtime':0.0})    
    #                             # vals.update(
    #                             #     {'overtime': vals['total_attendance'] or False})
    #
    #             if  attendance_ids.employee_id.contract_id.attend_police_id:           
    #                 for difference_time in attendance_ids.employee_id.contract_id.attend_police_id.diff_rule_id.diff_line_ids:
    #                     if difference_time.rate > 0:     
    #                         if vals['total_attendance'] < avg_hours and\
    #                                 vals['psignin'] > 0.0 and vals['psignout'] > 0.0:
    #                             if vals.get('status') == 'weekday':
    #                                 vals.update({'difftime': avg_hours -
    #                                              vals['total_attendance'] or False})
    #             flage = True
    #             if vals['status'] == 'weekend' and\
    #                     vals.get('overtime', False) <= 0.0:
    #                 continue
    #             if vals['status'] == 'absence':
    #                 for line in resource_calendar_id.attendance_ids:
    #
    #                     if int(date.weekday()) == int(line.dayofweek) and\
    #                             line.date_from and line.date_to:
    #                         if not line.date_to == date or\
    #                                 line.date_from == date:
    #                             vals = {}
    #             # Ensure only new lines are created or existing lines are updated
    #             existing_line = self.env['hr.attendance.sheet.line'].search(
    #                 [('name_id', '=', self.id), ('date', '=', date), ('export_bool', '=', True)])
    #             if existing_line:
    #                 vals.update({'export_bool': True})
    #                 existing_line.write(vals)
    #             else:
    #                 if flage and vals:
    #                     self.env['hr.attendance.sheet.line'].create(vals)                
    #             # if flage and vals:
    #             #     self.env['hr.attendance.sheet.line'].create(vals)
    #     self.employee_id.attendance_sheet_id = self.id or False
    #

        
        

    def name_get(self):
        """Name Get."""
        result = []
        for record in self:
            user_lang = self.env.user.lang
            lang = self.env['res.lang'].search(
                [('code', '=', user_lang)])
            cust_name = ''
            if lang:
                cust_name = 'Attendance Sheet of ' +\
                    str(record.employee_id.name) \
                    + ' From ' +\
                    record.request_date_from.strftime(lang.date_format) +\
                    ' To ' + \
                    record.request_date_to.strftime(lang.date_format)
            result.append((record.id, cust_name))
        return result

    def execute_send_to_manager(self):
        """State Confirm."""
        self.write({'state': 'confirm'})
        payroll_transaction_search = self.env['salary.allowance.detection'].search([('attendance_sheet_id', '=', self.id)])
        for transaction in payroll_transaction_search:
            # transaction.action_progress()
            # transaction.action_progress2()
            transaction.action_progress3()
            
        return True

    def execute_set_to_draft(self):
        """State to draft."""
        self.write({'state': 'draft'})
        return True

    def execute_set_to_approve(self):
        """State To Approved."""
        for rec in self:
            if rec.state == 'confirm':
                # if rec.employee_id.user_id and \
                #             rec.employee_id.user_id.id == self.env.user.id:
                #         raise ValidationError(_(
                #             "You can not approve your own Sheet !!!"))
                self.write({'state': 'approved'})
                payroll_transaction_search = self.env['salary.allowance.detection'].search([('attendance_sheet_id','=',self.id)])
                for transaction in payroll_transaction_search:
                    transaction.action_progress3()
            else:
                raise ValidationError(_("Please Confirm Attendance sheet with Manager before approve button clicked"))
                    
        return True
    
    def execute_set_to_export(self):
        self.write({'state': 'export'})
        return True
    
    @api.model
    def _execute_full_approve(self): 
        for rec in self:
            rec.compute_attendance_data()
            rec.execute_send_to_manager()
            rec.execute_set_to_approve()
            

# calculate the attendance data

    @api.onchange('attendance_sheet_ids')
    def _onchange_attendance_sheet_ids(self):
        # existing_transaction = self.env['salary.allowance.detection'].search([
        #                                         ('employee_id', '=', self.employee_id.id),
        #                                         ('attendance_sheet_id', '=', self.id), ('state', '=', 'draft')])
        # if existing_transaction:
        #     existing_transaction.unlink()
       
        no_ot = 0
        no_dt = 0
        no_lt = 0
        total_ot = 0.0
        
        no_lt_1hour = 0.0 
        total_late_more1hour = 0.0
        no_lt_lessthan_1hour = 0.0
        total_late_lessthan_1hour = 0.0
        
        no_lt_15min = 0.0
        total_late_15min = 0.0
        
        no_early_out = 0.0
        total_early_out = 0.0
        
        
        no_early_out_15min = 0.0
        total_early_out_15min = 0.0
        
        no_early_out_30min = 0.0
        total_early_out_30min = 0.0
        
        no_early_out_60min = 0.0
        total_early_out_60min = 0.0
        
        
        total_lt = 0.0
        total_dt = 0.0
        total_abs = 0.0
        for lines in self.attendance_sheet_ids:
            '''self.atte_required because employee have executive they don't give the attendance so they don't want attendance calculation'''
            if self.atte_required:
                if lines.overtime != 0.0:
                    no_ot += 1
                    total_ot += round(lines.overtime, 2)
                    lines.overtime_bool = True
                    if self.employee_id.contract_id.attend_police_id.overtime_id:
                        for overtime_rule in self.employee_id.contract_id.attend_police_id.overtime_id.overtime_line_ids:
                            if lines.status == 'weekday':
                                if overtime_rule.policie_type == 'working_days':
                                    lines.overtime_transaction_id = overtime_rule.payroll_transaction_id.id
                                    lines.insert_overtime_transaction()
                            if lines.status == 'weekend':
                                if overtime_rule.policie_type == 'week_end':
                                    lines.overtime_transaction_id = overtime_rule.payroll_transaction_id.id
                                    lines.insert_overtime_transaction()
                    
                if lines.difftime != 0.0:
                    no_dt += 1
                    total_dt += round(lines.difftime,2)
                if lines.latein != 0.0:
                    lines.latein_bool = True
                    # no_lt += 1
                    # total_lt += round(lines.latein, 2)
                    if self.employee_id.contract_id.attend_police_id.late_id:
                        for latein_rule in self.employee_id.contract_id.attend_police_id.late_id.attendance_line_ids:
                            if lines.latein !=0.0:
                                lines.latein_transaction_id = latein_rule.latein_transaction_id.id
                                
                        # print("lines.latein", lines.latein)
                        # Newly Added in 24-12-2024
                        if (1/60) < lines.latein <= (30/60) and self.employee_id.contract_id.attend_police_id.attendance_grace_time:
                            # print("lines.latein 11111111", lines.latein, lines.date)
                            no_lt_15min += 1
                            total_late_15min += round(lines.latein, 2)

                        if (15/60) < lines.latein <= (30/60) and not self.employee_id.contract_id.attend_police_id.attendance_grace_time:
                            # print("lines.latein 11111111", lines.latein)
                            no_lt_15min += 1
                            total_late_15min += round(lines.latein, 2)
                        if (30/60) < lines.latein:
                            if (30/60) < lines.latein < (60/60):
                                no_lt_lessthan_1hour += 1
                                total_late_lessthan_1hour += round(lines.latein, 2)
                                # no_lt += 1
                                # total_lt += round(lines.latein, 2)
                                #
        
                            elif lines.latein > (60/60):
                                no_lt_1hour += 1
                                total_late_more1hour += round(lines.latein,2)
                    
    
                if lines.status == 'absence':
                    total_abs += 1
                    lines.absent_bool = True
                    # lines.insert_absence_transaction()
                if lines.early_out_line != 0.0:
                    lines.early_out_bool = True
                    no_early_out += 1
                    total_early_out += round(lines.early_out_line,2)
                    if self.employee_id.contract_id.attend_police_id.early_checkout_id:
                        for early_out_rule in self.employee_id.contract_id.attend_police_id.early_checkout_id.early_checkout_line_ids:
                            if lines.early_out_line != 0.0:
                                lines.early_out_transaction_id = early_out_rule.earlyout_transaction_id.id
                                
                        if (15/60) < lines.early_out_line <= (30/60):
                            no_early_out_15min += 1
                            total_early_out_15min += round(lines.early_out_line,2)
                        
                        if (30/60) < lines.early_out_line:
                            if (30/60) < lines.early_out_line <= (60/60):
                                no_early_out_30min += 1
                                total_early_out_30min += round(lines.early_out_line,2)
                                    
                            elif lines.early_out_line > (60/60):
                                no_early_out_60min += 1
                                total_early_out_60min += round(lines.early_out_line,2)    
                        
                        
                    
            # count = 0 
            # if self.employee_id.contract_id.attend_police_id.late_id:
            #     for late in self.employee_id.contract_id.attend_police_id.late_id.attendance_line_ids:
            #         count += 1
            #         if lines.latein:
            #             print("...........count",count) 
                    # print("////////////////line",late.time,count,lines.latein)
                    
                    # if lines.latein >= late.time:
                    #     count +=1
                    #     print("......count",count)
                    #     lines.late_times = count
                    #

        if self.atte_required:
            self.no_latein_more_1hour = no_lt_1hour
            self.total_latein_more_1hour = total_late_more1hour
            
            self.no_latein_30_min = no_lt_lessthan_1hour
            self.total_late_30min = total_late_lessthan_1hour
            
            self.no_latein_15min = no_lt_15min
            self.total_latein_15min = total_late_15min
    
            self.no_latein = self.no_latein_more_1hour + self.no_latein_30_min + self.no_latein_15min
            self.total_latein = self.total_latein_more_1hour + self.total_late_30min + self.total_latein_15min
            # self.no_latein = no_lt
            # self.total_latein = total_lt
         
         
         
            # self.no_early_checkout = no_early_out
            # self.total_early_checkout = total_early_out
            #
            
            self.no_early_out_15min = no_early_out_15min
            self.total_early_out_15min = total_early_out_15min
            
            self.no_early_out_30min = no_early_out_30min
            self.total_early_checkout_30min = total_early_out_30min
            
            self.no_early_out_60min = no_early_out_60min
            self.total_early_out_60min = total_early_out_60min
            
            self.no_early_checkout = self.no_early_out_15min + self.no_early_out_30min + self.no_early_out_60min
            self.total_early_checkout = self.total_early_out_15min + self.total_early_checkout_30min + self.total_early_out_60min
            
    
            self.no_overtime = no_ot
            self.total_overtime = total_ot
            self.no_difftime = no_dt
            self.total_difftime = total_dt
            self.no_absence = total_abs
            self.total_absence = total_abs * \
                self.employee_id.resource_calendar_id.hours_per_day or False
                
        if not self.atte_required:
            self.no_latein_more_1hour = False
            self.total_latein_more_1hour = False
            
            self.no_latein_30_min = False
            self.total_late_30min = False
            
            self.no_latein_15min = False
            self.total_latein_15min = False
    
            self.no_latein = self.no_latein_more_1hour + self.no_latein_30_min + self.no_latein_15min
            self.total_latein = self.total_latein_more_1hour + self.total_late_30min + self.total_latein_15min
            # self.no_latein = no_lt
            # self.total_latein = total_lt
         
         
         
            # self.no_early_checkout = no_early_out
            # self.total_early_checkout = total_early_out
            #
            
            self.no_early_out_15min = False
            self.total_early_out_15min = False
            
            self.no_early_out_30min = False
            self.total_early_checkout_30min = False
            
            self.no_early_out_60min = False
            self.total_early_out_60min = False
            
            self.no_early_checkout = self.no_early_out_15min + self.no_early_out_30min + self.no_early_out_60min
            self.total_early_checkout = self.total_early_out_15min + self.total_early_checkout_30min + self.total_early_out_60min
            
    
            self.no_overtime = False
            self.total_overtime = False
            self.no_difftime = False
            self.total_difftime = False
            self.no_absence = 0.0
            # self.total_absence = total_abs * \
            #     self.employee_id.resource_calendar_id.hours_per_day or False

            self.total_absence = 0.0

class Attendancesheetline(models.Model):
    """Attendance Sheet Line."""

    _name = 'hr.attendance.sheet.line'
    _description = "Attendance Sheet Line"

    date = fields.Date("Date")
    day = fields.Char("Day")
    psignin = fields.Float("Planned Signin")
    psignout = fields.Float("Planned Signout")
    asignin = fields.Float("Actual Signin")
    asignout = fields.Float("Actual Signout")
    latein = fields.Float("Late in")
    overtime = fields.Float("Overtime")
    difftime = fields.Float("Diff Time")
    status = fields.Selection(
        [('weekend', 'Week End'),
         ('absence', 'Absence'),
         ('leave', 'Leave'),
         ('weekday', 'WeekDay'),
         ('holiday','Public Holiday'),
         ], default='weekday')
    note = fields.Text("Note")
    name_id = fields.Many2one("hr.attendance.sheet", string="name")
    d_asignin = fields.Datetime("actual sign in for date")
    d_asignout = fields.Datetime("actual signout for time")
    total_attendance = fields.Float(string="Total Attendance")
    
    holiday_status = fields.Char(string="Status Reason")
    
    overtime_transaction_id = fields.Many2one('hr.transaction.entry', string="Overtime Transaction Entry")

    overtime_bool = fields.Boolean(string='Overtime Boolean', default=False)
    
    absence_transaction_id = fields.Many2one('hr.transaction.entry', string="Absence Transaction Entry")
    
    early_out_transaction_id = fields.Many2one('hr.transaction.entry', string="Earlyout Transaction Entry")
    
    latein_transaction_id = fields.Many2one('hr.transaction.entry', string="Latein Transaction Entry")
    
    absent_bool = fields.Boolean(string="Absence Boolean", default=False)
    
    export_bool = fields.Boolean(string="Export", default=False)
    
    early_out_bool = fields.Boolean(string="Earlyout Boolean", default=False)
    
    latein_bool = fields.Boolean(string = "Latein Boolean", default=False)
    
    trans_bool = fields.Boolean(string="Trans Bool", default=False)
    
    early_out_count = fields.Integer(string="Early Out Count", compute="_compute_early_out_count")

    export = fields.Selection(
        [('no', 'No'), ('yes', 'Yes')],
        string="export",
        default='no'
    )
    
    
    late_times = fields.Char(string="Late Times",store=True)
    
    early_out_line = fields.Float(string="Early Out")
    
    work_type = fields.Selection(
        [("wfo", "Office Work"), ("wfh", "Remote Work")],
        string="Work Type",
    )
    
    
    
     # attendance_ids = self.env['hr.attendance'].search([
     #        ('employee_id', '=', self.employee_id.id),
     #        ('check_in', '>=', self.request_date_from),
     #        ('check_in', '<=', self.request_date_to),
     #        ])
    
    # @api.depends('name_id')
    # def _compute_export_bool_selection(self):
    #     for rec in self:
    #         rec.export = False
    #         attendance_search = self.env['hr.attendance'].search([('employee_id','=',rec.name_id.employee_id.id),('process','=','no')])
    #         for attendance in attendance_search:
    #             if attendance:
    #                 rec.export_bool = False
    #                 rec.export = 'no'
    #

    
    # @api.depends('early_out_bool')
    # def _compute_early_out_count(self):
    #     count = 0  # Initialize the cumulative count
    #     for rec in self:
    #
    #         if rec.early_out_bool:
    #             count += 1  # Increment the cumulative count for True early_out_bool
    #         else:
    #             count = 0  # Reset the count if early_out_bool is False
    #
    #         rec.early_out_count = count  # Assign the cumulative count to the current record
    #
    #         # Print statement for debugging
    #         print(f"Record ID: {rec.id}, Early Out Bool: {rec.early_out_bool}, Early Out Count: {rec.early_out_count}")

    
    @api.depends('early_out_bool')
    def _compute_early_out_count(self):
        cumulative_count = 0  # Initialize the cumulative count across all records
        for rec in self:
            if rec.early_out_bool:
                cumulative_count += 1  # Increment the cumulative count for True early_out_bool
            rec.early_out_count = cumulative_count  # Assign the cumulative count to the current record
    
            # Print statement for debugging
            # print(f"Record ID: {rec.id}, Early Out Bool: {rec.early_out_bool}, Early Out Count: {rec.early_out_count}")
                
    
    def open_wizard(self):
        """Method to open wizard."""
        vals = {'default_overtime': self.overtime,
                'default_latein': self.latein,
                'default_difftime': self.difftime,
                'default_reason': self.note
                }
        view_id = self.env.ref(
            'hr_attendances_overtime.change_attendance_data_wizard_view')
        return {
            'name': 'change attendance data',
            'type': 'ir.actions.act_window',
            'view_id': view_id.id,
            'view_mode': 'form',
            'res_model': 'hr.change.attendance',
            'target': 'new',
            'context': vals,
        }
     
    # @api.depends('latein')   
    # def _compute_late_times(self):
    #     for rec in self:
    #         rec.late_times = False
    #         if rec.name_id.employee_id.contract_id.attend_police_id.late_id:
    #             for line in rec.name_id.employee_id.contract_id.attend_police_id.late_id.attendance_line_ids:
    #                 rec.late_times = line.num_of_times
    #
    #
    #

        
   
    def insert_overtime_transaction(self):
        for rec in self:
            if rec.overtime_bool == True:
                if rec.overtime_transaction_id:
                    payroll_transaction = self.env['salary.allowance.detection']
                    # existing_transaction = payroll_transaction.search([
                    #     ('employee_id', '=', rec.name_id.employee_id.id),
                    #     ('attendance_sheet_id', '=', rec.name_id.id),
                    #     ('date', '=', rec.date),
                    #     ('hr_transaction_id', '=', rec.overtime_transaction_id.id)
                    # ])
                    # if existing_transaction:
                    #     existing_transaction.update({'hours':rec.overtime})
                    #
                    # if not existing_transaction:
                    vals = {
                        'employee_number':  rec.name_id.employee_id.employee_no,
                        'employee_id': rec.name_id.employee_id.id,
                        'department': rec.name_id.employee_id.department_id.id or False,
                        'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                        'date': rec.date,
                        'hr_transaction_id': rec.overtime_transaction_id.id or False,
                        'transaction_type_id': rec.overtime_transaction_id.transaction_type_id.id or False,
                        'days': 0.0,
                        'attendance_sheet_id': rec.name_id.id,
                        'type': rec.overtime_transaction_id.rule_type,
                        'reason': 'Allowance for Overtime'
                    }
                    transaction = payroll_transaction.create(vals)
                    transaction.onchange_transaction_type()
                    if transaction.hr_transaction_id.unit_type == 'hours':
                        transaction.hours = round(rec.overtime, 2)
                        rate = transaction.hr_transaction_id.rate
                        # print("rate, transaction.amount", rate, transaction.amount)

                        if rec.name_id.employee_id.contract_id.attend_police_id.additional_overtime:
                            first_tran_amount = round(transaction.amount, 2)
                            amount = round((first_tran_amount * 100) / rate, 2)
                            # print("amount", amount, first_tran_amount)
                            wage_cul = rec.name_id.employee_id.contract_id.wage / (30 * 8)
                            # amt = wage_cul * 0.5
                            amt = wage_cul * (rec.overtime_transaction_id.rate - 100)/100
                            rate_ra = rec.overtime_transaction_id.rate - 100
                            hours_mul = round(transaction.hours, 2) * round(amt, 2)
                            # print("rate_ra,wage_cul,amt", hours_mul, amt)

                            # print("transaction.hours", transaction.hours, amt)
                            transaction.amount = amount + hours_mul
                            # print("rate_ra,wage_cul,amt", rate_ra, wage_cul, amt, amount, hours_mul)


                            # print("transaction.hours, transaction.amount", transaction.hours, transaction.amount)

                        # transaction.amount = transaction.amount + (rec.name_id.employee_id.contract_id.wage / 50)
                
        
    def insert_absence_transaction(self, current_count):
        for rec in self:
            if rec.status == 'absence' and rec.absent_bool:
                absence_lines = rec.name_id.employee_id.contract_id.attend_police_id.absent_id.absence_line_ids if rec.name_id.employee_id.contract_id.attend_police_id.absent_id else []
                
                # Find the absence line matching the current count
                matched_line = next((line for line in absence_lines if line.time == str(current_count)), None)
    
                # If no exact match, use the last available absence line rate
                if not matched_line and absence_lines:
                    matched_line = max(absence_lines, key=lambda line: int(line.time))
    
                if matched_line:
                    # Get the rate from the matched line
                    rate = matched_line.rate
    
                    # Create the payroll transaction
                    payroll_transaction = self.env['salary.allowance.detection']
                    vals = {
                        'employee_number': rec.name_id.employee_id.employee_no,
                        'employee_id': rec.name_id.employee_id.id,
                        'department': rec.name_id.employee_id.department_id.id or False,
                        'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                        'date': rec.date,
                        'hr_transaction_id': matched_line.absent_payroll_transaction_id.id or False,
                        'transaction_type_id': matched_line.absent_payroll_transaction_id.transaction_type_id.id or False,
                        'days': 0.0,
                        'attendance_sheet_id': rec.name_id.id,
                        'type': matched_line.absent_payroll_transaction_id.rule_type,
                        'reason': f'Absent for the day (Count: {current_count}, Rate: {rate}%)',
                    }
                    transaction = payroll_transaction.create(vals)
                    transaction.onchange_transaction_type()
    
                    # Set days and calculate the amount based on the rate
                    if transaction.hr_transaction_id and transaction.hr_transaction_id.unit_type == 'days':
                        transaction.days = 1
                    transaction.amount = (rate * transaction.amount) / 100


    
    # def insert_absence_transaction(self):
    #     for rec in self:
    #         absence_lines = False
    #         if rec.status=='absence' and rec.absent_bool == True:
    #             if rec.name_id.employee_id.contract_id.attend_police_id.absent_id:
    #                 absence_lines = rec.name_id.employee_id.contract_id.attend_police_id.absent_id.absence_line_ids
    #             # Initialize a dictionary to count absences per employee
    #             absence_count = defaultdict(int)
    #
    #
    #             for rec in self:
    #                 if rec.status == 'absence':
    #
    #                     absence_count[rec.status=='absence'] += 1
    #                     current_count = absence_count[rec.status=='absence']
    #                     if current_count == 1:
    #                         if absence_lines:
    #                             for line in absence_lines:
    #                                 if line.time == '1':
    #                                     rec.absence_transaction_id = line.absent_payroll_transaction_id.id
    #                                     if rec.absence_transaction_id:
    #                                         payroll_transaction = self.env['salary.allowance.detection']
    #
    #                                         vals = {
    #                                             'employee_number':  rec.name_id.employee_id.employee_no,
    #                                             'employee_id': rec.name_id.employee_id.id,
    #                                             'department': rec.name_id.employee_id.department_id.id or False,
    #                                             'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
    #                                             'date': rec.date,
    #                                             'hr_transaction_id': rec.absence_transaction_id.id or False,
    #                                             'transaction_type_id': rec.absence_transaction_id.transaction_type_id.id or False,
    #                                             'days': 0.0,
    #                                             'attendance_sheet_id': rec.name_id.id,
    #                                             'type':rec.absence_transaction_id.rule_type,
    #                                             'reason':'Absent for the day'
    #                                         }
    #                                         transaction = payroll_transaction.create(vals)
    #                                         transaction.onchange_transaction_type()
    #                                         if transaction.hr_transaction_id.unit_type == 'days':
    #                                             transaction.days = 1
    #                                     break
    #                     elif current_count == 2:
    #                         if absence_lines:
    #                             for line in absence_lines:
    #                                 if line.time == '2':
    #                                     rec.absence_transaction_id = line.absent_payroll_transaction_id.id
    #                                     if rec.absence_transaction_id:
    #                                         payroll_transaction = self.env['salary.allowance.detection']
    #                                         vals = {
    #                                              'employee_number':  rec.name_id.employee_id.employee_no,
    #                                             'employee_id': rec.name_id.employee_id.id,
    #                                             'department': rec.name_id.employee_id.department_id.id or False,
    #                                             'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
    #                                             'date': rec.date,
    #                                             'hr_transaction_id': rec.absence_transaction_id.id or False,
    #                                             'transaction_type_id': rec.absence_transaction_id.transaction_type_id.id or False,
    #                                             'days': 0.0,
    #                                             'attendance_sheet_id': rec.name_id.id,
    #                                             'type':rec.absence_transaction_id.rule_type,
    #                                             'reason':'Absent for the day'
    #                                         }
    #                                         transaction = payroll_transaction.create(vals)
    #                                         transaction.onchange_transaction_type()
    #                                         if transaction.hr_transaction_id.unit_type == 'days':
    #                                             transaction.days = 1
    #                                     break
    #                     elif current_count >= 3:
    #                         if absence_lines:
    #                             for line in absence_lines:
    #                                 if line.time == '3':
    #                                     rec.absence_transaction_id = line.absent_payroll_transaction_id.id
    #                                     if rec.absence_transaction_id:
    #                                         payroll_transaction = self.env['salary.allowance.detection']
    #                                         vals = {
    #                                              'employee_number':  rec.name_id.employee_id.employee_no,
    #                                             'employee_id': rec.name_id.employee_id.id,
    #                                             'department': rec.name_id.employee_id.department_id.id or False,
    #                                             'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
    #                                             'date': rec.date,
    #                                             'hr_transaction_id': rec.absence_transaction_id.id or False,
    #                                             'transaction_type_id': rec.absence_transaction_id.transaction_type_id.id or False,
    #                                             'days': 0.0,
    #                                             'attendance_sheet_id': rec.name_id.id,
    #                                             'type':rec.absence_transaction_id.rule_type,
    #                                             'reason':'Absent for the day'
    #                                         }
    #                                         transaction = payroll_transaction.create(vals)
    #                                         transaction.onchange_transaction_type()
    #                                         if transaction.hr_transaction_id.unit_type == 'days':
    #                                             transaction.days = 1
    #                                     break
        
        
    def insert_earlyout_transaction(self):
        for rec in self:
            if rec.early_out_bool == True:
                if rec.early_out_transaction_id:
                    early_out_transaction = self.env['salary.allowance.detection']
                    # existing_transaction = payroll_transaction.search([
                    #     ('employee_id', '=', rec.name_id.employee_id.id),
                    #     ('attendance_sheet_id', '=', rec.name_id.id),
                    #     ('date', '=', rec.date),
                    #     ('hr_transaction_id', '=', rec.overtime_transaction_id.id)
                    # ])
                    # if existing_transaction:
                    #     existing_transaction.update({'hours':rec.overtime})
                    #
                    # if not existing_transaction:
                    vals = {
                         'employee_number':  rec.name_id.employee_id.employee_no,
                        'employee_id': rec.name_id.employee_id.id,
                        'department': rec.name_id.employee_id.department_id.id or False,
                        'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                        'date': rec.date,
                        'hr_transaction_id': rec.early_out_transaction_id.id or False,
                        'transaction_type_id': rec.early_out_transaction_id.transaction_type_id.id or False,
                        'days': 0.0,
                        'attendance_sheet_id': rec.name_id.id,
                        'type': rec.early_out_transaction_id.rule_type,
                        'reason': 'Early out Transaction'
                    }
                    transaction = early_out_transaction.create(vals)
                    transaction.onchange_transaction_type()
                    if transaction.hr_transaction_id.unit_type == 'days':
                        transaction.days = 1
            
        
    def insert_latein_transaction(self):
        for rec in self:
            if rec.latein_bool == True:
                if rec.latein_transaction_id:
                    latein_transaction = self.env['salary.allowance.detection']
            
                    vals = {
                         'employee_number':  rec.name_id.employee_id.employee_no,
                        'employee_id': rec.name_id.employee_id.id,
                        'department': rec.name_id.employee_id.department_id.id or False,
                        'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                        'date': rec.date,
                        'hr_transaction_id': rec.latein_transaction_id.id or False,
                        'transaction_type_id': rec.latein_transaction_id.transaction_type_id.id or False,
                        'days': 0.0,
                        'attendance_sheet_id': rec.name_id.id,
                        'type': rec.latein_transaction_id.rule_type,
                        'reason': 'Late in Transaction'
                    }
                    transaction = latein_transaction.create(vals)
                    transaction.onchange_transaction_type()
                    if transaction.hr_transaction_id.unit_type == 'days':
                        transaction.days = 1
                    # return transaction,transaction.date  
            




    def compute_attendance(self):
        """Compute Data."""
        for rec in self:
           
            overtime = 0
            rec.name_id.latein = 0
            rec.name_id.final_total_late_30min = 0
            rec.name_id.final_total_late_more_1hour = 0
            rec.name_id.final_total_late_15min = 0
            
            rec.name_id.final_total_early_out_15min = 0
            rec.name_id.final_total_early_out_30min = 0
            rec.name_id.final_total_early_out_60min = 0
            
            no_of_times_30min = 0
            no_of_times_1hour = 0
            no_of_times_15min = 0
            
            no_of_times_early_out_15min = 0
            no_of_times_early_out_30min = 0
            no_of_times_60min = 0
            
            
            rec.name_id.early_check_out_amount = 0
            # total_wages = 0
            #
            # total_wages = rec.employee_id.contract_id.wage + rec.employee_id.contract_id.house_allowance + rec.employee_id.contract_id.transport_allowance + \
            #             rec.employee_id.contract_id.school_allowance + rec.employee_id.contract_id.food_allowance + rec.employee_id.contract_id.fuel_allowance + \
            #             rec.employee_id.contract_id.ticket_allowance + rec.employee_id.contract_id.fixed_allowance + \
            #             rec.employee_id.contract_id.mobile_allowance + rec.employee_id.contract_id.work_allowance + rec.employee_id.contract_id.housing_allowance
            #

            # print(".........total",rec.employee_id.contract_id.total,total_wages)
            rec.name_id._onchange_attendance_sheet_ids()
            contract_id = self.env['hr.contract'].search([
                ('employee_id', '=', rec.name_id.employee_id.id),
                ('state', '=', 'open'),
                ('attendance_required_bool', '=', True)
                ])
            policies_id = contract_id.attend_police_id or False
            if policies_id:
                # Calculated the letin amount if time different is not present.
                if rec.name_id.late_in_calculation_bool:
                    if rec.name_id.no_latein and policies_id.late_id and\
                            rec.name_id.total_latein:
                        latein = policies_id.late_id
                        weekday_ids = self.env['hr.attendance.sheet.line'].search([
                            ('name_id', '=', rec.name_id.id), ('status', '=', 'weekday')])
                        for weekday in weekday_ids:
                             if weekday.latein:
                                latein_minutes = weekday.latein * 60  # Convert to minutes for easier comparison
                                
                                if 1 <= latein_minutes < 30 and policies_id.attendance_grace_time:
                                    # print("latein_minutes 522222222222", latein_minutes)
                                    no_of_times_15min += 1
                                    for line in latein.attendance_line_ids:
                                        # print("................loop",line)
                                        # If more than 4 occurrences, apply the 4th policy for subsequent occurrences
                                        if no_of_times_15min > 4 and line.num_of_times == '4':
                                            if line.time < (30 / 60):  # Ensure line.time matches the 15min condition
                                                if line.amount_type == "rate":
                                                    rec.name_id.final_total_late_15min += (line.rate / 100) * (rec.name_id.employee_id.contract_id.total / 30)
                                                    # self.attendance_sheet_ids.insert_latein_transaction()
                                                    if rec.latein_transaction_id:
                                                        latein_transaction = self.env['salary.allowance.detection']
                                                        reason = f"Late in Transaction - {no_of_times_15min} Time @ Rate: {line.rate}%"
                                                        if line.rate > 0:
                                                            vals = {
                                                                 'employee_number':  rec.name_id.employee_id.employee_no,
                                                                'employee_id': rec.name_id.employee_id.id,
                                                                'department': rec.name_id.employee_id.department_id.id or False,
                                                                'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                                                                'date': weekday.date,
                                                                'hr_transaction_id': rec.latein_transaction_id.id or False,
                                                                'transaction_type_id': rec.latein_transaction_id.transaction_type_id.id or False,
                                                                'days': 0.0,
                                                                'attendance_sheet_id': rec.name_id.id,
                                                                'type': rec.latein_transaction_id.rule_type,
                                                                'reason': reason
                                                            }
                                                            transaction = latein_transaction.create(vals)
                                                            transaction.onchange_transaction_type()
                                                            if transaction.hr_transaction_id.unit_type == 'days':
                                                                transaction.days = 1
                                                            transaction.amount = (line.rate * transaction.amount)/100
                                                            
                                                else:
                                                    rec.name_id.final_total_late_15min += line.amount
                                            continue  
                                            
                                        # Apply the specific policy for the current occurrence
                                        if line.num_of_times == str(no_of_times_15min) and line.time < (30 / 60):
                                         
                                            if line.amount_type == "rate":
                                                rec.name_id.final_total_late_15min += (line.rate / 100) * (rec.name_id.employee_id.contract_id.total / 30)
                                                # date = rec.date
                                                if rec.latein_transaction_id:
                                                    latein_transaction = self.env['salary.allowance.detection']
                                                    reason = f"Late in Transaction -{no_of_times_15min} Time @ Rate: {line.rate}%"
                                                    if line.rate > 0:
                                                        vals = {
                                                             'employee_number':  rec.name_id.employee_id.employee_no,
                                                             'employee_id': rec.name_id.employee_id.id,
                                                             'department': rec.name_id.employee_id.department_id.id or False,
                                                             'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                                                             'date': weekday.date,
                                                             'hr_transaction_id': rec.latein_transaction_id.id or False,
                                                             'transaction_type_id': rec.latein_transaction_id.transaction_type_id.id or False,
                                                             'days': 0.0,
                                                             'attendance_sheet_id': rec.name_id.id,
                                                             'type': rec.latein_transaction_id.rule_type,
                                                             'reason': reason
                                                        }
                                                        transaction = latein_transaction.create(vals)
                                                        transaction.onchange_transaction_type()
                                                        if transaction.hr_transaction_id.unit_type == 'days':
                                                            transaction.days = 1
                                                        transaction.amount = (line.rate * transaction.amount)/100
                                                    
                                                    # transaction.date = rec.date
                                            
                                            else:
                                                rec.name_id.final_total_late_15min += line.amount
                                            break
    
                                elif 15 <= latein_minutes < 30 and not policies_id.attendance_grace_time:
                                    # print("latein_minutes 2222222222666666", latein_minutes)
                                    no_of_times_15min += 1
                                    for line in latein.attendance_line_ids:
                                        # print("................loop",line)
                                        # If more than 4 occurrences, apply the 4th policy for subsequent occurrences
                                        if no_of_times_15min > 4 and line.num_of_times == '4':
                                            if line.time < (30 / 60):  # Ensure line.time matches the 15min condition
                                                if line.amount_type == "rate":
                                                    rec.name_id.final_total_late_15min += (line.rate / 100) * (
                                                                rec.name_id.employee_id.contract_id.total / 30)
                                                    # self.attendance_sheet_ids.insert_latein_transaction()
                                                    if rec.latein_transaction_id:
                                                        latein_transaction = self.env['salary.allowance.detection']
                                                        reason = f"Late in Transaction - {no_of_times_15min} Time @ Rate: {line.rate}%"
                                                        if line.rate > 0:
                                                            vals = {
                                                                'employee_number': rec.name_id.employee_id.employee_no,
                                                                'employee_id': rec.name_id.employee_id.id,
                                                                'department': rec.name_id.employee_id.department_id.id or False,
                                                                'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                                                                'date': weekday.date,
                                                                'hr_transaction_id': rec.latein_transaction_id.id or False,
                                                                'transaction_type_id': rec.latein_transaction_id.transaction_type_id.id or False,
                                                                'days': 0.0,
                                                                'attendance_sheet_id': rec.name_id.id,
                                                                'type': rec.latein_transaction_id.rule_type,
                                                                'reason': reason
                                                            }
                                                            transaction = latein_transaction.create(vals)
                                                            transaction.onchange_transaction_type()
                                                            if transaction.hr_transaction_id.unit_type == 'days':
                                                                transaction.days = 1
                                                            transaction.amount = (line.rate * transaction.amount) / 100
    
                                                else:
                                                    rec.name_id.final_total_late_15min += line.amount
                                            continue
    
                                            # Apply the specific policy for the current occurrence
                                        if line.num_of_times == str(no_of_times_15min) and line.time < (30 / 60):
    
                                            if line.amount_type == "rate":
                                                rec.name_id.final_total_late_15min += (line.rate / 100) * (
                                                            rec.name_id.employee_id.contract_id.total / 30)
                                                # date = rec.date
                                                if rec.latein_transaction_id:
                                                    latein_transaction = self.env['salary.allowance.detection']
                                                    reason = f"Late in Transaction -{no_of_times_15min} Time @ Rate: {line.rate}%"
                                                    if line.rate > 0:
                                                        vals = {
                                                            'employee_number': rec.name_id.employee_id.employee_no,
                                                            'employee_id': rec.name_id.employee_id.id,
                                                            'department': rec.name_id.employee_id.department_id.id or False,
                                                            'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                                                            'date': weekday.date,
                                                            'hr_transaction_id': rec.latein_transaction_id.id or False,
                                                            'transaction_type_id': rec.latein_transaction_id.transaction_type_id.id or False,
                                                            'days': 0.0,
                                                            'attendance_sheet_id': rec.name_id.id,
                                                            'type': rec.latein_transaction_id.rule_type,
                                                            'reason': reason
                                                        }
                                                        transaction = latein_transaction.create(vals)
                                                        transaction.onchange_transaction_type()
                                                        if transaction.hr_transaction_id.unit_type == 'days':
                                                            transaction.days = 1
                                                        transaction.amount = (line.rate * transaction.amount) / 100
    
                                                    # transaction.date = rec.date
    
                                            else:
                                                rec.name_id.final_total_late_15min += line.amount
                                            break
                                            
                                elif 30 <= latein_minutes < 60:
                                    no_of_times_30min += 1
                                    for line in latein.attendance_line_ids:
                                        # Apply the 4th occurrence policy for further lateness
                                        if no_of_times_30min > 4 and line.num_of_times == '4':
                                            if line.time < (60 / 60):
                                                if line.amount_type == "rate":
                                                    rec.name_id.final_total_late_30min += (line.rate / 100) * (rec.name_id.employee_id.contract_id.total / 30)
                                                    if rec.latein_transaction_id:
                                                        latein_transaction = self.env['salary.allowance.detection']
                                                        reason = f"Late in Transaction - {no_of_times_30min} Time @ Rate: {line.rate}%"
                                                        if line.rate > 0:
                                                            vals = {
                                                                 'employee_number':  rec.name_id.employee_id.employee_no,
                                                                 'employee_id': rec.name_id.employee_id.id,
                                                                 'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                                                                 'date': weekday.date,
                                                                 'hr_transaction_id': rec.latein_transaction_id.id or False,
                                                                 'transaction_type_id': rec.latein_transaction_id.transaction_type_id.id or False,
                                                                 'days': 0.0,
                                                                 'attendance_sheet_id': rec.name_id.id,
                                                                 'type': rec.latein_transaction_id.rule_type,
                                                                 'reason': reason
                                                            }
                                                            transaction = latein_transaction.create(vals)
                                                            transaction.onchange_transaction_type()
                                                            if transaction.hr_transaction_id.unit_type == 'days':
                                                                transaction.days = 1
                                                            transaction.amount = (line.rate * transaction.amount)/100
                                                else:
                                                    rec.name_id.final_total_late_30min += line.amount
                                            continue
                                
                                        # Apply the specific policy for the current occurrence
                                        if line.num_of_times == str(no_of_times_30min) and line.time < (60 / 60):
                                            if line.amount_type == "rate":
                                                rec.name_id.final_total_late_30min += (line.rate / 100) * (rec.name_id.employee_id.contract_id.total / 30)
                                                if rec.latein_transaction_id:
                                                    latein_transaction = self.env['salary.allowance.detection']
                                                    reason = f"Late in Transaction - {no_of_times_30min} Time @ Rate: {line.rate}%"
                                                    if line.rate > 0:
                                                        vals = {
                                                             'employee_number':  rec.name_id.employee_id.employee_no,
                                                             'employee_id': rec.name_id.employee_id.id,
                                                             'department': rec.name_id.employee_id.department_id.id or False,
                                                             'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                                                             'date': weekday.date,
                                                             'hr_transaction_id': rec.latein_transaction_id.id or False,
                                                             'transaction_type_id': rec.latein_transaction_id.transaction_type_id.id or False,
                                                             'days': 0.0,
                                                             'attendance_sheet_id': rec.name_id.id,
                                                             'type': rec.latein_transaction_id.rule_type,
                                                             'reason': reason
                                                        }
                                                        transaction = latein_transaction.create(vals)
                                                        transaction.onchange_transaction_type()
                                                        if transaction.hr_transaction_id.unit_type == 'days':
                                                            transaction.days = 1
                                                        transaction.amount = (line.rate * transaction.amount)/100
                                            else:
                                                rec.name_id.final_total_late_30min += line.amount
                                            break
                                
                                elif latein_minutes >= 60:
                                    no_of_times_1hour += 1
                                    for line in latein.attendance_line_ids:
                                        transaction_hours = 0
                                        temp_reason = False
                                        one_day_amount = False
    
                                        if no_of_times_1hour > 4 and line.num_of_times == '4':
                                            if line.time >= (60 / 60):
                                                if line.amount_type == "rate":
                                                    rec.name_id.final_total_late_more_1hour += (line.rate / 100) * (rec.name_id.employee_id.contract_id.total / 30)
                                                    if rec.latein_transaction_id:
                                                        latein_transaction = self.env['salary.allowance.detection']
                                                        reason = f"Late in Penalty - {no_of_times_1hour} Time @ Rate: {line.rate}%: Amount:"
                                                        if line.rate > 0:
                                                            vals = {
                                                                 'employee_number':  rec.name_id.employee_id.employee_no,
                                                                 'employee_id': rec.name_id.employee_id.id,
                                                                 'department': rec.name_id.employee_id.department_id.id or False,
                                                                 'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                                                                 'date': weekday.date,
                                                                 'hr_transaction_id': rec.latein_transaction_id.id or False,
                                                                 'transaction_type_id': rec.latein_transaction_id.transaction_type_id.id or False,
                                                                 'days': 0.0,
                                                                 'attendance_sheet_id': rec.name_id.id,
                                                                 'type': rec.latein_transaction_id.rule_type,
                                                                 'reason': reason
                                                            }
                                                            transaction = latein_transaction.create(vals)
                                                            transaction.onchange_transaction_type()
                                                            if transaction.hr_transaction_id.unit_type == 'days':
                                                                transaction.days = 1
                                                          
                                                            # transaction.amount =  (line.rate * transaction.amount)/100
                                                            transaction_total = (line.rate * transaction.amount)/100
                                                            temp_transaction_amount = round(transaction_total, 2)
                                                            one_day_amount = transaction.amount/int(rec.name_id.employee_id.resource_calendar_id.hours_per_day)
    
                                                            total_worked_hours_amt = (weekday.latein * (transaction.amount/int(rec.name_id.employee_id.resource_calendar_id.hours_per_day)))
                                                            transaction.amount = transaction_total + total_worked_hours_amt
                                                            
                                                             
                                                            latein_hours = int(weekday.latein)
                                                            latein_minutes = round((weekday.latein - latein_hours) * 60)
                                                            latein_formatted = f"{latein_hours} H : {latein_minutes} min"
                                                            
                                                            # temp_reason = (f"{temp_transaction_amount} SR) + (Absent Amount: {hours_late_in:02d}:{min_late_in:02d} hours * "
                                                            #                f"{round(one_day_amount, 2)} SR = {round(total_worked_hours_amt, 2)} SR)")
                                                            
                                                            temp_reason = (f"{temp_transaction_amount} SR) + (Absent Amount: {latein_formatted} * "
                                                                           f"{round(one_day_amount, 2)} SR = {round(total_worked_hours_amt, 2)} SR)")
    
                                                            # hours_late_in = int(weekday.latein)
                                                            # min_late_in = int((round(weekday.latein, 2) - hours_late_in) * 60 )
                                                            #
                                                            # temp_reason = (f"{temp_transaction_amount} SR) + (Absent Amount: {hours_late_in:02d}:{min_late_in:02d} hours * "
                                                            #                f"{round(one_day_amount, 2)} SR = {round(total_worked_hours_amt, 2)} SR)")
                                                        
                                                            # temp_reason = (f"{temp_transaction_amount} SR) + (Absent Amount: {round(weekday.latein, 2)} hours * "
                                                            #            f"{round(one_day_amount, 2)} SR = {round(total_worked_hours_amt, 2)} SR)")
                                                            transaction.reason = transaction.reason + temp_reason
        
                                                             
                                                            
                                                else:
                                                    rec.name_id.final_total_late_more_1hour += line.amount
                                            continue
                                
                                        if line.num_of_times == str(no_of_times_1hour) and line.time >= (60 / 60):
                                            transaction_hours = 0
                                            temp_reason = False
                                            one_day_amount = False
                                            if line.amount_type == "rate":
                                                rec.name_id.final_total_late_more_1hour += (line.rate / 100) * (rec.name_id.employee_id.contract_id.total / 30)
                                                if rec.latein_transaction_id:
                                                    latein_transaction = self.env['salary.allowance.detection']
                                                    reason = f"(Late in Penalty  - {no_of_times_1hour} Time @ Rate: {line.rate}% : Amount: "
                                                    if line.rate > 0:    
                                                        vals = {
                                                             'employee_number':  rec.name_id.employee_id.employee_no,
                                                             'employee_id': rec.name_id.employee_id.id,
                                                             'department': rec.name_id.employee_id.department_id.id or False,
                                                             'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                                                             'date': weekday.date,
                                                             'hr_transaction_id': rec.latein_transaction_id.id or False,
                                                             'transaction_type_id': rec.latein_transaction_id.transaction_type_id.id or False,
                                                             'days': 0.0,
                                                             'attendance_sheet_id': rec.name_id.id,
                                                             'type': rec.latein_transaction_id.rule_type,
                                                             'reason': reason
                                                        }
                                                        transaction = latein_transaction.create(vals)
                                                        transaction.onchange_transaction_type()
                                                        if transaction.hr_transaction_id.unit_type == 'days':
                                                            transaction.days = 1
                                                            
                                                        # transaction.amount =  (line.rate * transaction.amount)/100    
                                                        transaction_total = (line.rate * transaction.amount)/100
                                                        temp_transaction_amount = round(transaction_total, 2)
                                                        # temp_reason = str(transaction.amount) +" - " + 'Additional Penalty ' + str(weekday.latein) + " Penalty Amount" 
                                                        one_day_amount = transaction.amount/int(rec.name_id.employee_id.resource_calendar_id.hours_per_day)
                                                        total_worked_hours_amt = (weekday.latein * (transaction.amount/int(rec.name_id.employee_id.resource_calendar_id.hours_per_day)))
                                                        transaction.amount = transaction_total + total_worked_hours_amt
                                                        # temp_reason = str(temp_transaction_amount) +" SR) + (Absent Amount :" + str(round(weekday.latein,2)) +" hours * " + str(round(one_day_amount,2)) +" SR = " + str(round(total_worked_hours_amt,2)) + " SR)"
                                                         
                                                        latein_hours = int(weekday.latein)
                                                        latein_minutes = round((weekday.latein - latein_hours) * 60)
                                                        latein_formatted = f"{latein_hours} H : {latein_minutes} min"
                                                        
                                                        # temp_reason = (f"{temp_transaction_amount} SR) + (Absent Amount: {hours_late_in:02d}:{min_late_in:02d} hours * "
                                                        #                f"{round(one_day_amount, 2)} SR = {round(total_worked_hours_amt, 2)} SR)")
                                                        
                                                        temp_reason = (f"{temp_transaction_amount} SR) + (Absent Amount: {latein_formatted} * "
                                                                       f"{round(one_day_amount, 2)} SR = {round(total_worked_hours_amt, 2)} SR)")
    
                                                        
                                                        # hours_late_in = int(weekday.latein)
                                                        # min_late_in = int((round(weekday.latein, 2) - hours_late_in) * 60 )
                                                        #
                                                        # temp_reason = (f"{temp_transaction_amount} SR) + (Absent Amount: {hours_late_in:02d}:{min_late_in:02d} hours * "
                                                        #                    f"{round(one_day_amount, 2)} SR = {round(total_worked_hours_amt, 2)} SR)")
                                                        
                                                        # temp_reason = (f"{temp_transaction_amount} SR) + (Absent Amount: {round(weekday.latein, 2)} hours * "
                                                        #                f"{round(one_day_amount, 2)} SR = {round(total_worked_hours_amt, 2)} SR)")
                                                        
                                                        transaction.reason = transaction.reason + temp_reason
    
    
                                            else:
                                                rec.name_id.final_total_late_more_1hour += line.amount
                                            break
                                
    
                        # Sum up the total late deductions
                        rec.name_id.latein = rec.name_id.final_total_late_30min + rec.name_id.final_total_late_more_1hour + rec.name_id.final_total_late_15min

             

                                ######## working correctly
                                # if str(rec.no_latein) == line.num_of_times:
                                #     # if weekday.latein >= line.time:
                                #     if line.time >= weekday.latein:
                                #
                                #         if line.amount_type == "rate":
                                #             rec.latein = rec.latein + (weekday.latein * (line.rate/100) * (rec.employee_id.contract_id.wage/(30*int(rec.employee_id.resource_calendar_id.hours_per_day))))
                                #             # rec.latein = rec.latein + (weekday.latein * line.rate)
                                #             break
                                #         else:
                                #             rec.latein = rec.latein + line.amount
                                #             break
                                # if str(rec.no_latein) != line.num_of_times:
                                #     if line.num_of_times == '4':
                                #         if weekday.latein >= line.time:
                                #             if line.amount_type == "rate":
                                #                 rec.latein = rec.latein + (weekday.latein * (line.rate/100) * (rec.employee_id.contract_id.wage/(30*int(rec.employee_id.resource_calendar_id.hours_per_day))))
                                #                 # rec.latein = rec.latein + (weekday.latein * line.rate)
                                #                 break
                                #             else:
                                #                 rec.latein = rec.latein + line.amount
                                #                 break   
                '''Overtime'''                            
                # Calculated the overtime
                if rec.name_id.overtime_calculation_bool:
                    if rec.name_id.no_overtime and rec.name_id.total_overtime and\
                            policies_id.overtime_id:
                        weekend_id = self.env['hr.attendance.sheet.line'].search([
                            ('name_id', '=', rec.name_id.id), ('status', '=', 'weekend')])
                        weekday_id = self.env['hr.attendance.sheet.line'].search([
                            ('name_id', '=', rec.name_id.id), ('status', '=', 'weekday')])
                        for weekend in weekend_id:
                    
                            for line in\
                                    policies_id.overtime_id.overtime_line_ids:
                                if line.policie_type == 'week_end' and\
                                        weekend.overtime >= line.apply_after:
                                # if line.policie_type == 'week_end':
                                    ''' overtime is calculated based on the wage amount and rate of overtime rule.That wage amount is calculated based on one day and 8 hours working for single day'''
                                    overtime = overtime + \
                                        (weekend.overtime * (line.rate/100) * (rec.name_id.employee_id.contract_id.wage/(30*int(rec.name_id.employee_id.resource_calendar_id.hours_per_day))))
                    
                                    # overtime = overtime + \
                                    #     (weekend.overtime * line.rate)    
                                    break
                        overtime_amount = 0        
                        for weekday in weekday_id:
                            for line in\
                                    policies_id.overtime_id.overtime_line_ids:
                    
                                if line.policie_type == 'working_days' and\
                                        weekday.overtime >= line.apply_after:
                                    overtime = overtime + \
                                        (weekday.overtime * (line.rate/100) * (rec.name_id.employee_id.contract_id.total/(30*int(rec.name_id.employee_id.resource_calendar_id.hours_per_day))))
                                    # overtime = overtime + \
                                    #      (weekday.overtime * line.rate)     
                                    break
                    
                    rec.name_id.overtime = overtime
                ''' Difference times'''
                # calculating the time Different
                if rec.name_id.no_difftime and policies_id.diff_rule_id and\
                        rec.name_id.total_difftime:
                    difftime = policies_id.diff_rule_id
                    for line in difftime.diff_line_ids:
                        if rec.name_id.total_difftime >= line.time:
                            rec.name_id.time_different = rec.name_id.total_difftime * (line.rate/100) * (rec.name_id.employee_id.contract_id.total/(30*int(rec.name_id.employee_id.resource_calendar_id.hours_per_day)))
                            # rec.time_different = rec.total_difftime * line.rate
                            break
                '''Absence lines'''
                if rec.name_id.absence_calculation_bool == True:   
                    if rec.name_id.no_absence and policies_id.absent_id:
                        absent = policies_id.absent_id
                        for line in absent.absence_line_ids:
                            if str(rec.name_id.no_absence) == line.time:
                                rec.name_id.absent = (line.rate/100) * (rec.name_id.employee_id.contract_id.total/(30*int(rec.name_id.employee_id.resource_calendar_id.hours_per_day)))
                                rec.name_id.absent = rec.name_id.absent * rec.name_id.total_absence
                                # rec.absent = line.rate
                                break
                            if str(rec.name_id.no_absence) != line.time:
                                if line.time == '3':
                                    rec.name_id.absent = (line.rate/100) * (rec.name_id.employee_id.contract_id.total/(30*int(rec.name_id.employee_id.resource_calendar_id.hours_per_day)))
                                    rec.name_id.absent = rec.name_id.absent * rec.name_id.total_absence
                                    # rec.absent = line.rate
                                    break
                    

                '''Early out '''   
                if rec.name_id.early_out_calculation_bool:
                    if rec.name_id.no_early_checkout and policies_id.early_checkout_id:
                        early_out = policies_id.early_checkout_id
                        weekday_ids = self.env['hr.attendance.sheet.line'].search([
                            ('name_id', '=', rec.name_id.id), ('status', '=', 'weekday')
                        ])
                    
                        for weekday in weekday_ids:
                            if weekday.early_out_line != 0.0:
                                early_out_min = weekday.early_out_line * 60
                                if 15 <= early_out_min < 30:
                                    no_of_times_early_out_15min += 1
                                    for early in early_out.early_checkout_line_ids:
                                        
                                        if no_of_times_early_out_15min > 4 and early.early_time == '4':
                                            if early.time < (30/60):
                                                rec.name_id.final_total_early_out_15min += (early.early_rate / 100) * (rec.name_id.employee_id.contract_id.total / 30)
                                                if weekday.early_out_transaction_id:
                                                    early_out_transaction = self.env['salary.allowance.detection']
                                                    reason = f"Early Out Transaction - {no_of_times_early_out_15min} Time @ Rate: {early.early_rate}%"
                                                    if early.early_rate > 0:
                                                        vals = {
                                                             'employee_number': rec.name_id.employee_id.employee_no,
                                                             'employee_id': rec.name_id.employee_id.id,
                                                             'department': rec.name_id.employee_id.department_id.id or False,
                                                             'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                                                             'date': weekday.date,  # Use the specific attendance date
                                                             'hr_transaction_id': weekday.early_out_transaction_id.id or False,
                                                             'transaction_type_id': weekday.early_out_transaction_id.transaction_type_id.id or False,
                                                             'days': 0.0,
                                                             'attendance_sheet_id': rec.name_id.id,
                                                             'type': weekday.early_out_transaction_id.rule_type,
                                                             'reason': reason
                                                         }
                            
                                                         # Create the transaction and handle onchange behavior
                                                        transaction = early_out_transaction.create(vals)
                                                        transaction.onchange_transaction_type()
                            
                                                        if transaction.hr_transaction_id.unit_type == 'days':
                                                            transaction.days = 1
                            
                                                         # Calculate amount based on early checkout rate
                                                        transaction.amount = (early.early_rate * transaction.amount) / 100
                                                    
                                                continue
                                                
                                        if early.early_time == str(no_of_times_early_out_15min) and early.time < (30/60):
                                            rec.name_id.final_total_early_out_15min += (early.early_rate / 100) * (rec.name_id.employee_id.contract_id.total / 30)
                                            if weekday.early_out_transaction_id:
                                                early_out_transaction = self.env['salary.allowance.detection']
                                                reason = f"Early Out Transaction - {no_of_times_early_out_15min} Time @  Rate: {early.early_rate}%"
                                                if early.early_rate > 0:
                                                    vals = {
                                                         'employee_number': rec.name_id.employee_id.employee_no,
                                                         'employee_id': rec.name_id.employee_id.id,
                                                         'department': rec.name_id.employee_id.department_id.id or False,
                                                         'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                                                         'date': weekday.date,  # Use the specific attendance date
                                                         'hr_transaction_id': weekday.early_out_transaction_id.id or False,
                                                         'transaction_type_id': weekday.early_out_transaction_id.transaction_type_id.id or False,
                                                         'days': 0.0,
                                                         'attendance_sheet_id': rec.name_id.id,
                                                         'type': weekday.early_out_transaction_id.rule_type,
                                                         'reason': reason
                                                     }
                        
                                                     # Create the transaction and handle onchange behavior
                                                    transaction = early_out_transaction.create(vals)
                                                    transaction.onchange_transaction_type()
                        
                                                    if transaction.hr_transaction_id.unit_type == 'days':
                                                        transaction.days = 1
                        
                                                     # Calculate amount based on early checkout rate
                                                    transaction.amount = (early.early_rate * transaction.amount) / 100
                                    
                                                break                    
                                
                                elif 30 <= early_out_min < 60:
                                    no_of_times_early_out_30min += 1
                                    for early in early_out.early_checkout_line_ids:
                                        if no_of_times_early_out_30min > 4 and early.early_time =='4':
                                            if early.time < (60/60):
                                                rec.name_id.final_total_early_out_30min +=  (early.early_rate / 100) * (rec.name_id.employee_id.contract_id.total / 30)
                                                if weekday.early_out_transaction_id:
                                                    early_out_transaction = self.env['salary.allowance.detection']
                                                    reason = f"Early Out Transaction - {no_of_times_early_out_30min} Time @ Rate: {early.early_rate}%"
                                                    
                                                    if early.early_rate > 0:
                                                        vals = {
                                                             'employee_number': rec.name_id.employee_id.employee_no,
                                                             'employee_id': rec.name_id.employee_id.id,
                                                             'department': rec.name_id.employee_id.department_id.id or False,
                                                             'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                                                             'date': weekday.date,  # Use the specific attendance date
                                                             'hr_transaction_id': weekday.early_out_transaction_id.id or False,
                                                             'transaction_type_id': weekday.early_out_transaction_id.transaction_type_id.id or False,
                                                             'days': 0.0,
                                                             'attendance_sheet_id': rec.name_id.id,
                                                             'type': weekday.early_out_transaction_id.rule_type,
                                                             'reason': reason
                                                         }
                            
                                                         # Create the transaction and handle onchange behavior
                                                        transaction = early_out_transaction.create(vals)
                                                        transaction.onchange_transaction_type()
                            
                                                        if transaction.hr_transaction_id.unit_type == 'days':
                                                            transaction.days = 1
                            
                                                         # Calculate amount based on early checkout rate
                                                        transaction.amount = (early.early_rate * transaction.amount) / 100
                                            continue
                                        
                                        if early.early_time == str(no_of_times_early_out_30min) and early.time <(60/60):
                                            rec.name_id.final_total_early_out_30min +=  (early.early_rate / 100) * (rec.name_id.employee_id.contract_id.total / 30)
                                            if weekday.early_out_transaction_id:
                                                early_out_transaction = self.env['salary.allowance.detection']
                                                reason = f"Early Out Transaction - {no_of_times_early_out_30min} Time @  Rate: {early.early_rate}%"
                                                
                                                if early.early_rate > 0:
                                                    vals = {
                                                         'employee_number': rec.name_id.employee_id.employee_no,
                                                         'employee_id': rec.name_id.employee_id.id,
                                                         'department': rec.name_id.employee_id.department_id.id or False,
                                                         'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                                                         'date': weekday.date,  # Use the specific attendance date
                                                         'hr_transaction_id': weekday.early_out_transaction_id.id or False,
                                                         'transaction_type_id': weekday.early_out_transaction_id.transaction_type_id.id or False,
                                                         'days': 0.0,
                                                         'attendance_sheet_id': rec.name_id.id,
                                                         'type': weekday.early_out_transaction_id.rule_type,
                                                         'reason': reason
                                                     }
                        
                                                     # Create the transaction and handle onchange behavior
                                                    transaction = early_out_transaction.create(vals)
                                                    transaction.onchange_transaction_type()
                        
                                                    if transaction.hr_transaction_id.unit_type == 'days':
                                                        transaction.days = 1
                        
                                                     # Calculate amount based on early checkout rate
                                                    transaction.amount = (early.early_rate * transaction.amount) / 100
                                    
                                                break
                                                
                                
                                elif  early_out_min >= 60:
                                    no_of_times_60min += 1
                                    for early in early_out.early_checkout_line_ids:
                                        if no_of_times_60min > 4 and early.early_time =='4':
                                            transaction_hours = 0
                                            temp_reason = False
                                            one_day_amount = False
                                            if early.time >= (60/60):
                                                rec.name_id.final_total_early_out_60min +=  (early.early_rate / 100) * (rec.name_id.employee_id.contract_id.total / 30)
                                                if weekday.early_out_transaction_id:
                                                    early_out_transaction = self.env['salary.allowance.detection']
                                                    reason = f"(Early Out Penalty - {no_of_times_60min} Time @  Rate: {early.early_rate}%: Amount: "
                                                    
                                                    if early.early_rate > 0:
                                                        vals = {
                                                             'employee_number': rec.name_id.employee_id.employee_no,
                                                             'employee_id': rec.name_id.employee_id.id,
                                                             'department': rec.name_id.employee_id.department_id.id or False,
                                                             'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                                                             'date': weekday.date,  # Use the specific attendance date
                                                             'hr_transaction_id': weekday.early_out_transaction_id.id or False,
                                                             'transaction_type_id': weekday.early_out_transaction_id.transaction_type_id.id or False,
                                                             'days': 0.0,
                                                             'attendance_sheet_id': rec.name_id.id,
                                                             'type': weekday.early_out_transaction_id.rule_type,
                                                             'reason': reason
                                                         }
                            
                                                         # Create the transaction and handle onchange behavior
                                                        transaction = early_out_transaction.create(vals)
                                                        transaction.onchange_transaction_type()
                            
                                                        if transaction.hr_transaction_id.unit_type == 'days':
                                                            transaction.days = 1
                            
                                                         # Calculate amount based on early checkout rate
                                                        # transaction.amount = (early.early_rate * transaction.amount) / 100
                                                        transaction_total = (early.early_rate * transaction.amount)/100
                                                        temp_transaction_amount = round(transaction_total,2)
                                                        one_day_amount = transaction.amount/int(rec.name_id.employee_id.resource_calendar_id.hours_per_day)
                                                        total_worked_hours_amt = (weekday.early_out_line  * (transaction.amount/int(rec.name_id.employee_id.resource_calendar_id.hours_per_day)))
                                                        transaction.amount = transaction_total + total_worked_hours_amt
                                                        
                                                        # hours_early_out = int(weekday.early_out_line)
                                                        # min_early_out = int((round(weekday.early_out_line,2) - hours_early_out) * 60 )
                                                        #
                                                        # temp_reason = (f"{temp_transaction_amount} SR) + (Absent Amount: {hours_early_out:02d}:{min_early_out:02d} hours * "
                                                        #                f"{round(one_day_amount, 2)} SR = {round(total_worked_hours_amt, 2)} SR)")
                                                        
                                                        earlyout_hours = int(weekday.early_out_line)
                                                        earlyout_minutes = round((weekday.early_out_line - earlyout_hours) * 60)
                                                        earlyout_formatted = f"{earlyout_hours} H : {earlyout_minutes} min"
                                                            
                                                        temp_reason = (f"{temp_transaction_amount} SR) + (Absent Amount: {earlyout_formatted} * "
                                                                          f"{round(one_day_amount, 2)} SR = {round(total_worked_hours_amt, 2)} SR)")
                                                        
                                                        # temp_reason = (f"{temp_transaction_amount} SR) + (Absent Amount: {round(weekday.early_out_line, 2)} hours * "
                                                        #                f"{round(one_day_amount, 2)} SR = {round(total_worked_hours_amt, 2)} SR)")
                                                        #
    
                                                        
                                                        # temp_reason = str(temp_transaction_amount) +" - " + 'Additional Penalty for ' + str(round(weekday.early_out_line,2)) + " hours Penalty Amount :"  + str(round(total_worked_hours_amt,2))
                                                        transaction.reason = transaction.reason + temp_reason
                                                        
                                            continue
                                        
                                        if early.early_time == str(no_of_times_60min) and early.time >= (60/60):
                                            rec.name_id.final_total_early_out_60min += (early.early_rate / 100) * (rec.name_id.employee_id.contract_id.total / 30)
                                            transaction_hours = 0
                                            temp_reason = False
                                            one_day_amount = False
                                            if weekday.early_out_transaction_id:
                                                early_out_transaction = self.env['salary.allowance.detection']
                                                reason = f"(Early Out Penalty - {no_of_times_60min} Time @  Rate: {early.early_rate}%: Amount: "
                                                
                                                if early.early_rate > 0:
                                                    vals = {
                                                         'employee_number': rec.name_id.employee_id.employee_no,
                                                         'employee_id': rec.name_id.employee_id.id,
                                                         'department': rec.name_id.employee_id.department_id.id or False,
                                                         'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                                                         'date': weekday.date,  # Use the specific attendance date
                                                         'hr_transaction_id': weekday.early_out_transaction_id.id or False,
                                                         'transaction_type_id': weekday.early_out_transaction_id.transaction_type_id.id or False,
                                                         'days': 0.0,
                                                         'attendance_sheet_id': rec.name_id.id,
                                                         'type': weekday.early_out_transaction_id.rule_type,
                                                         'reason': reason
                                                     }
                        
                                                     # Create the transaction and handle onchange behavior
                                                    transaction = early_out_transaction.create(vals)
                                                    transaction.onchange_transaction_type()
                        
                                                    if transaction.hr_transaction_id.unit_type == 'days':
                                                        transaction.days = 1
                        
                                                     # Calculate amount based on early checkout rate
                                                    # transaction.amount = (early.early_rate * transaction.amount) / 100
                                                    transaction_total = (early.early_rate * transaction.amount)/100
                                                    temp_transaction_amount = round(transaction_total,2)
                                                    one_day_amount = transaction.amount/int(rec.name_id.employee_id.resource_calendar_id.hours_per_day)
    
                                                    total_worked_hours_amt = (weekday.early_out_line * (transaction.amount/int(rec.name_id.employee_id.resource_calendar_id.hours_per_day)))
                                                    transaction.amount = transaction_total + total_worked_hours_amt
                                                     
                                                     
                                                    # hours_early_out = int(weekday.early_out_line)
                                                    # min_early_out = int((round(weekday.early_out_line,2) - hours_early_out) * 60 )
                                                    #
                                                    # temp_reason = (f"{temp_transaction_amount} SR) + (Absent Amount: {hours_early_out:02d}:{min_early_out:02d} hours * "
                                                    #                    f"{round(one_day_amount, 2)} SR = {round(total_worked_hours_amt, 2)} SR)")
                                                    #
    
                                                    earlyout_hours = int(weekday.early_out_line)
                                                    earlyout_minutes = round((weekday.early_out_line - earlyout_hours) * 60)
                                                    earlyout_formatted = f"{earlyout_hours} H : {earlyout_minutes} min"
                                                        
                                                    temp_reason = (f"{temp_transaction_amount} SR) + (Absent Amount: {earlyout_formatted} * "
                                                                      f"{round(one_day_amount, 2)} SR = {round(total_worked_hours_amt, 2)} SR)")
                                                    
                                                    # temp_reason = (f"{temp_transaction_amount} SR) + (Absent Amount: {round(weekday.early_out_line, 2)} hours * "
                                                    #                    f"{round(one_day_amount, 2)} SR = {round(total_worked_hours_amt, 2)} SR)")
                                                        
                                                    # temp_reason = str(temp_transaction_amount) +" - " + 'Additional Penalty for ' + str(round(weekday.early_out_line,2)) + " hours Penalty Amount :"  + str(round(total_worked_hours_amt,2))
                                                    transaction.reason = transaction.reason + temp_reason
                            
                                                break
                                                    
                                                    
                        
                        rec.name_id.early_check_out_amount =  rec.name_id.final_total_early_out_15min  +   rec.name_id.final_total_early_out_30min + rec.name_id.final_total_early_out_60min 
                    
                '''Currently working'''  
                                                                
                # if rec.name_id.no_early_checkout and policies_id.early_checkout_id:
                #     early_out = policies_id.early_checkout_id
                #     weekday_ids = self.env['hr.attendance.sheet.line'].search([
                #         ('name_id', '=', rec.name_id.id), ('status', '=', 'weekday')
                #     ])
                #
                #     for weekday in weekday_ids:
                #     # for i in range(1, rec.name_id.no_early_checkout + 1):
                #         for line in early_out.early_checkout_line_ids:
                #             if weekday.early_out_count > 4 and line.early_time == '4':
                #
                #             # if i > 4 and line.early_time == '4':
                #                 rec.name_id.early_check_out_amount += (line.early_rate / 100) * (rec.name_id.employee_id.contract_id.total / 30)
                #                 if weekday.early_out_bool:
                #                     if weekday.early_out_transaction_id:
                #                         early_out_transaction = self.env['salary.allowance.detection']
                #                         reason = f"Early out Transaction - Rate: {line.early_rate}%"
                #                         if line.early_rate > 0 :
                #                             vals = {
                #                                  'employee_number': rec.name_id.employee_id.employee_no,
                #                                  'employee_id': rec.name_id.employee_id.id,
                #                                  'department': rec.name_id.employee_id.department_id.id or False,
                #                                  'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                #                                  'date': weekday.date,  # Use the specific attendance date
                #                                  'hr_transaction_id': weekday.early_out_transaction_id.id or False,
                #                                  'transaction_type_id': weekday.early_out_transaction_id.transaction_type_id.id or False,
                #                                  'days': 0.0,
                #                                  'attendance_sheet_id': rec.name_id.id,
                #                                  'type': weekday.early_out_transaction_id.rule_type,
                #                                  'reason': reason
                #                              }
                #
                #                              # Create the transaction and handle onchange behavior
                #                             transaction = early_out_transaction.create(vals)
                #                             transaction.onchange_transaction_type()
                #
                #                             if transaction.hr_transaction_id.unit_type == 'days':
                #                                 transaction.days = 1
                #
                #                              # Calculate amount based on early checkout rate
                #                             transaction.amount = (line.early_rate * transaction.amount) / 100
                #                 continue
                #             if str(weekday.early_out_count) == line.early_time:
                #                 rec.name_id.early_check_out_amount += (line.early_rate / 100) * (rec.name_id.employee_id.contract_id.total / 30)
                #                 if weekday.early_out_bool:
                #                     if weekday.early_out_transaction_id:
                #                         early_out_transaction = self.env['salary.allowance.detection']
                #                         reason = f"Early out Transaction - Rate: {line.early_rate}%"
                #                         if line.early_rate > 0:
                #                             vals = {
                #                                  'employee_number': rec.name_id.employee_id.employee_no,
                #                                  'employee_id': rec.name_id.employee_id.id,
                #                                  'department': rec.name_id.employee_id.department_id.id or False,
                #                                  'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
                #                                  'date': weekday.date,  # Use the specific attendance date
                #                                  'hr_transaction_id': weekday.early_out_transaction_id.id or False,
                #                                  'transaction_type_id': weekday.early_out_transaction_id.transaction_type_id.id or False,
                #                                  'days': 0.0,
                #                                  'attendance_sheet_id': rec.name_id.id,
                #                                  'type': weekday.early_out_transaction_id.rule_type,
                #                                  'reason': reason
                #                              }
                #
                #                              # Create the transaction and handle onchange behavior
                #                             transaction = early_out_transaction.create(vals)
                #                             transaction.onchange_transaction_type()
                #
                #                             if transaction.hr_transaction_id.unit_type == 'days':
                #                                 transaction.days = 1
                #
                #                              # Calculate amount based on early checkout rate
                #                             transaction.amount = (line.early_rate * transaction.amount) / 100
                #
                #                 break
                #

        
         
     #############currently working   
    # @api.depends('date')
    # def _compute_payroll_overtime(self):
    #     for rec in self:
    #         rec.overtime_transaction_id  = False
    #         if rec.overtime > 0.0:
    #             if rec.name_id.employee_id.contract_id.attend_police_id.overtime_id:
    #                 for line in rec.name_id.employee_id.contract_id.attend_police_id.overtime_id.overtime_line_ids:
    #                     if rec.status=='weekday':
    #                         if line.policie_type=='working_days':
    #                             rec.overtime_transaction_id  = line.payroll_transaction_id.id
    #                             if rec.overtime_transaction_id:
    #                                 payroll_transaction = self.env['salary.allowance.detection']
    #                                 existing_transaction = payroll_transaction.search([
    #                                     ('employee_id', '=', rec.name_id.employee_id.id),
    #                                     ('attendance_sheet_id', '=', rec.name_id.id),
    #                                     ('date', '=', rec.date),
    #                                     ('hr_transaction_id', '=', rec.overtime_transaction_id.id)
    #                                 ])
    #                                 if existing_transaction:
    #                                     existing_transaction.update({'hours':rec.overtime})
    #
    #                                 if not existing_transaction:
    #                                     vals = {
    #                                         'employee_id': rec.name_id.employee_id.id,
    #                                         'department': rec.name_id.employee_id.department_id.id or False,
    #                                         'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
    #                                         'date': rec.date,
    #                                         'hr_transaction_id': rec.overtime_transaction_id.id or False,
    #                                         'transaction_type_id': rec.overtime_transaction_id.id or False,
    #                                         'days': 0.0,
    #                                         'attendance_sheet_id': rec.name_id.id,
    #                                         'reason':'Allowance for Overtime'
    #                                     }
    #                                     transaction = payroll_transaction.create(vals)
    #                                     transaction.onchange_transaction_type()
    #                                     if transaction.hr_transaction_id.unit_type == 'hours':
    #                                         transaction.hours = rec.overtime
    #                                 break    
    #                     if rec.status=='weekend':            
    #                         if line.policie_type=='week_end':
    #                             rec.overtime_transaction_id  = line.payroll_transaction_id.id 
    #                             if rec.overtime_transaction_id:
    #                                 payroll_transaction = self.env['salary.allowance.detection']
    #                                 existing_transaction = payroll_transaction.search([
    #                                     ('employee_id', '=', rec.name_id.employee_id.id),
    #                                     ('attendance_sheet_id', '=', rec.name_id.id),
    #                                     ('date', '=', rec.date),
    #                                     ('hr_transaction_id', '=', rec.overtime_transaction_id.id)
    #                                 ])
    #                                 if existing_transaction:
    #                                     existing_transaction.update({'hours':rec.overtime})
    #                                 if not existing_transaction:
    #                                     vals = {
    #                                         'employee_id': rec.name_id.employee_id.id,
    #                                         'department': rec.name_id.employee_id.department_id.id or False,
    #                                         'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
    #                                         'date': rec.date,
    #                                         'hr_transaction_id': rec.overtime_transaction_id.id or False,
    #                                         'transaction_type_id': rec.overtime_transaction_id.id or False,
    #                                         'days': 0,
    #                                         'attendance_sheet_id': rec.name_id.id,
    #                                         'reason':'Allowance for Overtime'
    #                                     }
    #                                     transaction = payroll_transaction.create(vals)
    #                                     transaction.onchange_transaction_type()
    #                                     if transaction.hr_transaction_id.unit_type == 'hours':
    #                                         transaction.hours = rec.overtime
    #                                 break 
    #
    #
    #
    # @api.depends('date')
    # def _compute_payroll_absence(self):
    #     for rec in self:
    #         rec.absence_transaction_id = False
    #         absence_lines = False
    #         if rec.status=='absence':
    #             if rec.name_id.employee_id.contract_id.attend_police_id.absent_id:
    #                 absence_lines = rec.name_id.employee_id.contract_id.attend_police_id.absent_id.absence_line_ids
    #             # Initialize a dictionary to count absences per employee
    #             absence_count = defaultdict(int)
    #
    #
    #             for rec in self:
    #                 if rec.status == 'absence':
    #
    #                     absence_count[rec.status=='absence'] += 1
    #                     current_count = absence_count[rec.status=='absence']
    #                     if current_count == 1:
    #                         if absence_lines:
    #                             for line in absence_lines:
    #                                 if line.time == '1':
    #                                     rec.absence_transaction_id = line.absent_payroll_transaction_id.id
    #                                     if rec.absence_transaction_id:
    #                                         payroll_transaction = self.env['salary.allowance.detection']
    #
    #                                         existing_transaction = payroll_transaction.search([
    #                                             ('employee_id', '=', rec.name_id.employee_id.id),
    #                                             ('attendance_sheet_id', '=', rec.name_id.id),
    #                                             ('date', '=', rec.date),
    #                                             ('hr_transaction_id', '=', rec.absence_transaction_id.id)
    #                                         ])
    #                                         # if existing_transaction:
    #                                         #     existing_transaction.update({'days':1})
    #                                         if not existing_transaction:
    #                                             vals = {
    #                                                 'employee_id': rec.name_id.employee_id.id,
    #                                                 'department': rec.name_id.employee_id.department_id.id or False,
    #                                                 'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
    #                                                 'date': rec.date,
    #                                                 'hr_transaction_id': rec.absence_transaction_id.id or False,
    #                                                 'transaction_type_id': rec.absence_transaction_id.id or False,
    #                                                 'days': 0.0,
    #                                                 'attendance_sheet_id': rec.name_id.id,
    #                                                 'reason':'Absent for the day'
    #                                             }
    #                                             transaction = payroll_transaction.create(vals)
    #                                             transaction.onchange_transaction_type()
    #                                             if transaction.hr_transaction_id.unit_type == 'days':
    #                                                 transaction.days = 1
    #                                     break
    #                     elif current_count == 2:
    #                         if absence_lines:
    #                             for line in absence_lines:
    #                                 if line.time == '2':
    #                                     rec.absence_transaction_id = line.absent_payroll_transaction_id.id
    #                                     if rec.absence_transaction_id:
    #                                         payroll_transaction = self.env['salary.allowance.detection']
    #                                         existing_transaction = payroll_transaction.search([
    #                                             ('employee_id', '=', rec.name_id.employee_id.id),
    #                                             ('attendance_sheet_id', '=', rec.name_id.id),
    #                                             ('date', '=', rec.date),
    #                                             ('hr_transaction_id', '=', rec.absence_transaction_id.id)
    #                                         ])
    #                                         if not existing_transaction:
    #                                             vals = {
    #                                                 'employee_id': rec.name_id.employee_id.id,
    #                                                 'department': rec.name_id.employee_id.department_id.id or False,
    #                                                 'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
    #                                                 'date': rec.date,
    #                                                 'hr_transaction_id': rec.absence_transaction_id.id or False,
    #                                                 'transaction_type_id': rec.absence_transaction_id.id or False,
    #                                                 'days': 0.0,
    #                                                 'attendance_sheet_id': rec.name_id.id,
    #                                                 'reason':'Absent for the day'
    #                                             }
    #                                             transaction = payroll_transaction.create(vals)
    #                                             transaction.onchange_transaction_type()
    #                                             if transaction.hr_transaction_id.unit_type == 'days':
    #                                                 transaction.days = 1
    #                                     break
    #                     elif current_count >= 3:
    #                         if absence_lines:
    #                             for line in absence_lines:
    #                                 if line.time == '3':
    #                                     rec.absence_transaction_id = line.absent_payroll_transaction_id.id
    #                                     if rec.absence_transaction_id:
    #                                         payroll_transaction = self.env['salary.allowance.detection']
    #                                         existing_transaction = payroll_transaction.search([
    #                                             ('employee_id', '=', rec.name_id.employee_id.id),
    #                                             ('attendance_sheet_id', '=', rec.name_id.id),
    #                                             ('date', '=', rec.date),
    #                                             ('hr_transaction_id', '=', rec.absence_transaction_id.id)
    #                                         ])
    #                                         if not existing_transaction:
    #                                             vals = {
    #                                                 'employee_id': rec.name_id.employee_id.id,
    #                                                 'department': rec.name_id.employee_id.department_id.id or False,
    #                                                 'employee_contract_id': rec.name_id.employee_id.contract_id.id or False,
    #                                                 'date': rec.date,
    #                                                 'hr_transaction_id': rec.absence_transaction_id.id or False,
    #                                                 'transaction_type_id': rec.absence_transaction_id.id or False,
    #                                                 'days': 0.0,
    #                                                 'attendance_sheet_id': rec.name_id.id,
    #                                                 'reason':'Absent for the day'
    #                                             }
    #                                             transaction = payroll_transaction.create(vals)
    #                                             transaction.onchange_transaction_type()
    #                                             if transaction.hr_transaction_id.unit_type == 'days':
    #                                                 transaction.days = 1
    #                                     break
    #
    #


    
   
   