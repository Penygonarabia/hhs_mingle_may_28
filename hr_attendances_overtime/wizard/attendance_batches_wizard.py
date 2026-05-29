from odoo import api,fields,models,_
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, time
import pandas as pd
from odoo.exceptions import ValidationError



class AttendanceBatchWizard(models.Model):
    
    _name = 'attendance.sheet.batch'
    
    _inherit = ["mail.thread", "mail.activity.mixin"]
    
    _description = 'Attendance Sheet Batch'
    
    
    
    name = fields.Char('Name',required = True,tracking = True)
    
    date_from = fields.Date('Period From',required = True, tracking = True, default = lambda self: fields.Date.to_string(date.today().replace(day=1)))
    
    date_to = fields.Date('Period To', required= True, tracking = True, default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    
    
    attendance_batch_line_ids = fields.One2many('attendance.sheet.batch.line','attendance_id',string="Employee attendance")
    
    state = fields.Selection([('draft','Draft'),('in_progress','In Progress'),('confirm','Confirm'),('validate','Validated')],default='draft',tracking = True)
    
    day_check = fields.Boolean(string="Day Check",default=False)
   
   
    @api.constrains('date_from', 'date_to')
    def _check_date_from(self):
        if self.filtered(lambda c: c.date_to and c.date_from > c.date_to):
            raise ValidationError(_('Period From must be less than Period To.'))
  
  
    # @api.constrains('date_from', 'date_to')
    # def _validate_attendance_sheet_batch(self):
    #     """Method to set constrains for attendance sheet."""
    #     for batch in self:
    #         attendance__batch_ids = batch.search([
    #             ('date_from', '>=', batch.date_from),
    #             ('date_to', '<=', batch.date_to),
    #             ('id', '!=', batch.id),
    #         ])
    #         if attendance__batch_ids:
    #             raise ValidationError(
    #                 _("Another Batch already exists with in this Date range from %s -  to %s !!!") % (
    #                     self.date_from.strftime("%d-%m-%Y"),self.date_to.strftime("%d-%m-%Y")))
    #

    def get_employee_data(self):
        for rec in self:
            today = fields.Date.today()
            current_month_start = today.replace(day=1)
            # employee_search = self.env['hr.employee'].search([('contract_warning', '=', False)])
        #     employee_search = self.env['hr.employee'].search([
        #     ('contract_warning', '=', False),
        #     ('contract_id', '!=', False),
        #     ('contract_id.date_start', '<=', current_month_start)
        # ])     
            employee_search = self.env['hr.employee'].search([
               ('state', '=', 'draft'), ('contract_id.attendance_required_bool', 'in', [True,False])
            ])         

        #     employee_search = self.env['hr.employee'].search([
        #     ('contract_warning', '=', False),
        #     ('contract_id', '!=', False),
        #     ('contract_id.date_start', '<=', current_month_start)
        # ])    
            employee_lst = [(5, 0, 0)]
            for employee in employee_search:
                # if employee.contract_id.date_start.strftime("%m-%Y")  <= fields.date.today().strftime("%m-%Y"):
                vals = {
                    'employee_no': employee.employee_no,
                    'employee_id': employee.id,
                    'period_from': rec.date_from,
                    'period_to': rec.date_to
                    }
                employee_lst.append((0, 0, vals))
                rec.write({'attendance_batch_line_ids': employee_lst})
    
            rec.write({'state': 'in_progress'})
                
            
    def write_attendance_sheet(self):
        for rec in self:
            attendance_sheet = self.env['hr.attendance.sheet']
            sheet_lst = []
            for line in rec.attendance_batch_line_ids:
                vals = {
                    'employee_number': line.employee_no,
                    'employee_id': line.employee_id.id,
                    'request_date_from': line.period_from,
                    'request_date_to': line.period_to,
                    }
                # sheet_lst.append(vals)
                attendance_create = attendance_sheet.create(vals)
                attendance_create.get_attendance()
                # attendance_create.compute_attendance_data()
                attendance_create.write({'attendance_sheet_batch_id': rec.id})
                line.write({'attendance_sheet_id': attendance_create.id})
            rec.write({'state': 'confirm'})

    def update_attendance(self):
        today = fields.Date.today()
        is_month_end = pd.Timestamp(today).is_month_end
        is_month_start = today.day == 1
    
        # Define date ranges for the current and previous months
        current_month_start = today.replace(day=1)
        previous_month_end = current_month_start - relativedelta(days=1)
        previous_month_start = previous_month_end.replace(day=1)
    
        # print(f"Previous Month Start: {previous_month_start}, Previous Month End: {previous_month_end}")
    
        # Fetch batches within the previous month date range that are not validated
        attendance_batches = self.env['attendance.sheet.batch'].search([
            ('date_from', '>=', previous_month_start),
            ('date_to', '<=', previous_month_end),
            ('state', '!=', 'validate')
        ])
    
        for batch in attendance_batches:
            # print(f"Processing attendance batch: {batch.date_from} to {batch.date_to}")
    
            # Process lines that have not been marked as processed
            for line in batch.attendance_batch_line_ids:
                if not line.process_bool:

                    # Check if the attendance sheet has not been exported
                    if not line.attendance_sheet_id or batch.state == 'validate':
                        continue

                    try:
                        for att_sheet in line.attendance_sheet_id.attendance_sheet_ids:
                            if att_sheet.export == 'no' and att_sheet.export_bool== False:
                                # print(f"Processing attendance sheet: {att_sheet}")
                                line.attendance_sheet_id.get_attendance()
                                # line.attendance_sheet_id._calc_current_attendance()
                                line.process_bool = True
                    except Exception as e:
                        print(f"Error processing attendance sheet: {e}")

        # Process for the current month
        for rec in self:
            attendance_sheet_model = self.env['hr.attendance.sheet']
            attendance_sheet_batches = self.env['attendance.sheet.batch'].search([('state', '!=', 'validate'),
                                                                            ('date_from', '!=', previous_month_start),
                                                                            ('date_to', '!=', previous_month_end)])
        
            for attend_batch in attendance_sheet_batches:
                attend_batch.date_to = today
                if attend_batch.date_from.strftime("%m-%Y") ==attend_batch.date_to.strftime("%m-%Y") and not rec.day_check:
                    # print(f"...........Processing current month batch: {attend_batch.date_from} to {attend_batch.date_to}")
        
                    for line in rec.attendance_batch_line_ids:
                      
                            # Process new employees
                        employees = self.env['hr.employee'].search([
                            ('contract_id.date_start', '>=', rec.date_from),
                            ('contract_id.date_start', '<=', rec.date_to),
                            ('contract_id.attendance_required_bool', '=', True)
                        ])
        
                        for employee in employees:
                            vals = {
                                'employee_no': employee.employee_no,
                                'employee_id': employee.id,
                                'period_from': employee.contract_id.date_start,
                                'period_to': rec.date_to
                            }
        
                            # Check if attendance line exists; if not, create it
                            existing_line = self.env['attendance.sheet.batch.line'].search([
                                ('employee_id', '=', employee.id),
                                ('attendance_id', '=', line.attendance_id.id)
                            ])
        
                            if not existing_line:
                                new_line = self.env['attendance.sheet.batch.line'].create(vals)
                                rec.write({'attendance_batch_line_ids': [(4, new_line.id)]})
        
                                # Create attendance sheet for new employee
                                sheet_vals = {
                                    'employee_number': new_line.employee_id.employee_no,
                                    'employee_id': new_line.employee_id.id,
                                    'request_date_from': new_line.period_from,
                                    'request_date_to': new_line.period_to,
                                }
                                sheet = attendance_sheet_model.create(sheet_vals)
                                sheet.get_attendance()
                                # sheet._calc_current_attendance()
                                sheet.write({'attendance_sheet_batch_id': rec.id})
                                new_line.write({'new_employee': True, 'attendance_sheet_id': sheet.id})
        
                        # Update attendance period for non-exit employees
                        if not line.exit_employee:
                            line.write({'period_to': rec.date_to,'process_bool':True})
        
                        # Handle employee exit in the middle of the month
                        if line.contract_end_date and rec.date_from <= line.contract_end_date <= rec.date_to:
                            line.write({'exit_employee': True, 'period_to': line.contract_end_date})
                            if line.exit_employee:
                                attendance_sheet = attendance_sheet_model.search([
                                    ('id', '=', line.attendance_sheet_id.id),
                                    ('state', '=', 'draft')
                                ])
                                if attendance_sheet:
                                    attendance_sheet.write({'request_date_to': line.contract_end_date})
                                    attendance_sheet.get_attendance()
                                    # attendance_sheet._calc_current_attendance()
        
                        # Update attendance sheet for current employees
                        if line.attendance_sheet_id and not line.exit_employee:
                            attendance_sheet = attendance_sheet_model.search([
                                ('id', '=', line.attendance_sheet_id.id),
                                ('state', '=', 'draft')
                            ])
                            attendance_sheet.write({'request_date_to': line.period_to})
                            attendance_sheet.get_attendance()
                            # attendance_sheet._calc_current_attendance()
        
                    if is_month_end:
                        next_month_start = today + timedelta(days=1)

                        existing_batch = self.env['attendance.sheet.batch'].search([
                            ('date_from', '=', next_month_start),
                            ('date_to', '=', next_month_start)
                        ], limit=1)
                
                        if not existing_batch:
                            new_batch = self.env['attendance.sheet.batch'].create({
                                'name': f'Attendance sheet batch - {next_month_start.strftime("%m - %Y")}',
                                'date_from': next_month_start,
                                'date_to': next_month_start
                            })
                            new_batch.get_employee_data()
                            new_batch.write_attendance_sheet()
                
                    elif is_month_start:
                       
                        current_month_start = today.replace(day=1)
                        previous_month_end = current_month_start - timedelta(days=1)
                        previous_month_start = previous_month_end.replace(day=1)
                
                        attendance_batches = self.env['attendance.sheet.batch'].search([
                            ('date_from', '>=', previous_month_start),
                            ('date_to', '<=', previous_month_end),
                            ('state', '!=', 'validate')
                        ])
                
                        for batch in attendance_batches:
                            batch.write({'state': 'validate', 'day_check': True})

    ''' New on 4th November'''
    @api.model                    
    def attendance_sheet(self):
        today = fields.Date.today()
        last_date_check = pd.Timestamp(today)
        is_month_end = last_date_check.is_month_end
        is_month_start = today.day == 1

        # Define date ranges for the current and previous months
        # current_month_start = today.replace(day=1)
        # previous_month_end = current_month_start - timedelta(days=1)
        # previous_month_start = previous_month_end.replace(day=1)
        #
        # # Fetch attendance batches in the previous month that aren't validated
        # query = """
        #     SELECT id FROM attendance_sheet_batch
        #     WHERE date_from >= %s AND date_to <= %s AND state != 'validate'
        # """
        # # print("Executing query for previous month's non-validated attendance batches:", query % (previous_month_start, previous_month_end))
        # self.env.cr.execute(query, (previous_month_start, previous_month_end))
        # attendance_batch_ids = [row[0] for row in self.env.cr.fetchall()]
        # print("query", query, attendance_batch_ids)
        #
        # # Process each attendance batch
        # for batch_id in attendance_batch_ids:
        #     # Fetch lines in the batch where `process_bool` is False
        #     query = """
        #         SELECT id, employee_id, attendance_sheet_id
        #         FROM attendance_sheet_batch_line
        #         WHERE attendance_id = %s AND NOT process_bool
        #     """
        #     self.env.cr.execute(query, (batch_id,))
        #     print("query", query)
        #     lines = self.env.cr.dictfetchall()
        #     print("lines", lines)
        #
        #     for line in lines:
        #         if line['attendance_sheet_id']:
        #             try:
        #                 # Fetch attendance sheets that are not yet exported
        #                 query = """
        #                     SELECT id, export, export_bool
        #                     FROM hr_attendance_sheet_line
        #                     WHERE name_id = %s AND export = 'no' AND NOT export_bool
        #                 """
        #                 # print("Executing query for non-exported attendance sheet:", query % line['attendance_sheet_id'])
        #                 self.env.cr.execute(query, (line['attendance_sheet_id'],))
        #                 attendance_sheet = self.env.cr.fetchone()
        #                 print("attendance_sheet", attendance_sheet)
        #
        #                 if attendance_sheet:
        #                     self.env['hr.attendance.sheet'].browse(attendance_sheet[0]).get_attendance()
        #                     query = "UPDATE attendance_sheet_batch_line SET process_bool = TRUE WHERE id = %s"
        #                     print("Executing update for setting process_bool to TRUE in batch line:", query % line['id'])
        #                     self.env.cr.execute(query, (line['id'],))
        #             except Exception as e:
        #                 print("Error processing attendance sheet for line:", line['id'], "| Error:", e)

        current_month_start = today.replace(day=1)
        previous_month_end = current_month_start - relativedelta(days=1)
        previous_month_start = previous_month_end.replace(day=1)

        # print(f"Previous Month Start: {previous_month_start}, Previous Month End: {previous_month_end}")

        # Fetch batches within the previous month date range that are not validated
        attendance_batches = self.env['attendance.sheet.batch'].search([
            ('date_from', '>=', previous_month_start),
            ('date_to', '<=', previous_month_end),
            ('state', '!=', 'validate')
        ])

        for batch in attendance_batches:
            # print(f"Processing attendance batch: {batch.date_from} to {batch.date_to}")

            # Process lines that have not been marked as processed
            for line in batch.attendance_batch_line_ids:
                if not line.process_bool:
                    # Check if the attendance sheet has not been exported
                    if not line.attendance_sheet_id or batch.state == 'validate':
                        continue

                    try:
                        for att_sheet in line.attendance_sheet_id.attendance_sheet_ids:
                            if att_sheet.export == 'no' and att_sheet.export_bool == False:
                                # print(f"Processing attendance sheet: {att_sheet}")
                                line.attendance_sheet_id.get_attendance()
                                line.process_bool = True
                    except Exception as e:
                        print(f"Error processing attendance sheet: {e}")

        # Process attendance batches for the current month
        query = "SELECT id FROM attendance_sheet_batch WHERE state = 'confirm'"
        # print("Executing query for attendance sheet batches with state = 'confirm':", query)
        self.env.cr.execute(query)
        attend_swift_ids = [row[0] for row in self.env.cr.fetchall()]
        current_month_start = today.replace(day=1)
        current_month_end = today.replace(day=1) + relativedelta(months=1, days=-1)
        for rec_id in attend_swift_ids:
            # Find attendance sheet batches that need updating for the current month
            query = """
                SELECT id, date_from, date_to 
                FROM attendance_sheet_batch 
                WHERE state != 'validate' AND date_from >= %s AND date_to <= %s
            """
            self.env.cr.execute(query, (current_month_start, current_month_end))
            current_batches = self.env.cr.dictfetchall()

            for batch in current_batches:
                query = """
                    UPDATE attendance_sheet_batch 
                    SET date_to = %s 
                    WHERE id = %s AND date_from >= %s AND date_from <= %s
                """
                # print("Executing update to set date_to for batch with id:", batch['id'])
                self.env.cr.execute(query, (today, batch['id'], current_month_start, current_month_end))

                if batch['date_from'].strftime("%m-%Y") == today.strftime("%m-%Y"):
                    query = """
                        SELECT id,attendance_sheet_id,attendance_id
                        FROM attendance_sheet_batch_line 
                        WHERE attendance_id = %s 
                    """
                    # print("Executing query for batch lines with process_bool = False in current month:", query % batch['id'])
                    self.env.cr.execute(query, (batch['id'],))
                    lines = self.env.cr.dictfetchall()

                    for line in lines:
                        
                        query ="""
                    SELECT emp.employee_no, emp.id FROM hr_employee emp
                    JOIN hr_contract contract ON emp.contract_id = contract.id
                    WHERE contract.date_start BETWEEN %s AND %s
                """
                       
                        self.env.cr.execute(query, (batch['date_from'], batch['date_to']))
                        employees = self.env.cr.dictfetchall()

                        for employee in employees:
                            # Check if line already exists for this employee
                            query = """
                                SELECT id 
                                FROM attendance_sheet_batch_line 
                                WHERE employee_id = %s AND attendance_id = %s
                            """
                            # print("Executing query to check if line exists for employee in batch:", query % (employee['id'], line['attendance_id']))
                            self.env.cr.execute(query, (employee['id'], line['attendance_id']))
                            existing_line = self.env.cr.fetchone()

                            if not existing_line:
                                # Insert a new line
                                query = """
                                    INSERT INTO attendance_sheet_batch_line (employee_no, employee_id, period_from, period_to, attendance_id) 
                                    VALUES (%s, %s, %s, %s, %s)
                                """
                                # print("Executing insert for new batch line:", query % (employee['employee_no'], employee['id'], batch['date_from'], batch['date_to'], batch['id']))
                                self.env.cr.execute(query, (employee['employee_no'], employee['id'], batch['date_from'], batch['date_to'], batch['id']))

                                # Create an attendance sheet for the employee
                                sheet_vals = {
                                    'employee_number': employee['employee_no'],
                                    'employee_id': employee['id'],
                                    'request_date_from': batch['date_from'],
                                    'request_date_to': batch['date_to'],
                                }
                                new_sheet = self.env['hr.attendance.sheet'].create(sheet_vals)
                                new_sheet.get_attendance()
                                new_sheet.write({'attendance_sheet_batch_id': batch['id']})

                                # Update the line for new employee
                                query = """
                                    UPDATE attendance_sheet_batch_line 
                                    SET new_employee = TRUE, attendance_sheet_id = %s 
                                    WHERE employee_id = %s
                                """
                                # print("Executing update to set new_employee and attendance_sheet_id in batch line:", query % (new_sheet.id, employee['id']))
                                self.env.cr.execute(query, (new_sheet.id, employee['id']))

                        # Update non-exit employees
                       # Update non-exit employees
                        query = """
                            UPDATE attendance_sheet_batch_line 
                            SET period_to = %s, process_bool = TRUE 
                            WHERE attendance_id = %s AND exit_employee = FALSE
                        """
                        # print("Executing update for non-exit employees in batch line:", query % (today, batch['id']))
                        self.env.cr.execute(query, (today, batch['id']))

                        # Handle employee exit if applicable
                        if line['attendance_sheet_id']:
                            attendance_sheet = self.env['hr.attendance.sheet'].search([
                                ('id', '=', line['attendance_sheet_id']),
                                ('state', '=', 'draft')
                            ])
                            if attendance_sheet:
                                attendance_sheet.write({'request_date_to': today})
                                attendance_sheet.get_attendance()
                                
            #### currently working on commented by Vijaya bhaskar on April 11 2025
            # If it's the end of the month, finalize the batch and prepare for next month
            # if is_month_end:
            #     # query = "UPDATE attendance_sheet_batch SET day_check = TRUE, state = 'validate' WHERE id = %s"
            #     query = "UPDATE attendance_sheet_batch SET day_check = TRUE, state = 'validate' WHERE id = %s and date_to = %s"
            #
            #     # print("Executing update to finalize batch at month end:", query % rec_id)
            #     # self.env.cr.execute(query, (rec_id,))
            #     self.env.cr.execute(query, (rec_id, today))
            #
            #     # Create attendance sheet batch for the next month
            #     next_month_start = today + timedelta(days=1)
            #     existing_batch = self.env['attendance.sheet.batch'].search([
            #                 ('date_from', '=', next_month_start),
            #                 ('date_to', '=', next_month_start)
            #             ], limit=1)
            #
            #     if not existing_batch:
            #
            #     # print("Creating new attendance sheet batch for next month")
            #         new_batch = self.env['attendance.sheet.batch'].create({
            #             'name': f'Attendance sheet batch - {next_month_start.strftime("%m - %Y")}',
            #             'date_from': next_month_start,
            #             'date_to': next_month_start
            #         })
            #         new_batch.get_employee_data()
            #         new_batch.write_attendance_sheet()
            #     break
            
            ''' New Code is added by Vijaya bhaskar for month end is new batch created if a new month previous will be vaildate on april 11 2025'''
            if is_month_end:
                next_month_start = today + timedelta(days=1)

                existing_batch = self.env['attendance.sheet.batch'].search([
                    ('date_from', '=', next_month_start),
                    ('date_to', '=', next_month_start)
                ], limit=1)
        
                if not existing_batch:
                    new_batch = self.env['attendance.sheet.batch'].create({
                        'name': f'Attendance sheet batch - {next_month_start.strftime("%m - %Y")}',
                        'date_from': next_month_start,
                        'date_to': next_month_start
                    })
                    new_batch.get_employee_data()
                    new_batch.write_attendance_sheet()
        
            elif is_month_start:
               
                current_month_start = today.replace(day=1)
                previous_month_end = current_month_start - timedelta(days=1)
                previous_month_start = previous_month_end.replace(day=1)
        
                attendance_batches = self.env['attendance.sheet.batch'].search([
                    ('date_from', '>=', previous_month_start),
                    ('date_to', '<=', previous_month_end),
                    ('state', '!=', 'validate')
                ])
        
                for batch in attendance_batches:
                    batch.write({'state': 'validate', 'day_check': True})

            # if is_month_end:
            #     rec.day_check = True
            #     rec.state = 'validate'
            #     next_month_start = today + relativedelta(days=1)
            #     attendance_sheet_batch = self.env['attendance.sheet.batch'].create({
            #         'name': 'Attendence sheet batch - ' + next_month_start.strftime("%m - %Y"),
            #         'date_from': next_month_start,
            #         'date_to': next_month_start
            #     })
            #     attendance_sheet_batch.get_employee_data()
            #     attendance_sheet_batch.write_attendance_sheet()
            #     break

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft', 'in_progress']:
                raise ValidationError("You Can't Delete the attendance Batch.Because Already Attendance Sheet Created")
            else:
                attendance_sheet = self.env['hr.attendance.sheet'].search([('attendance_sheet_batch_id', '=', rec.id)])
                attendance_sheet.unlink()
        return super(AttendanceBatchWizard, self).unlink()
  
class AttendanceBatchLinbeWizard(models.Model):
    
    _name = 'attendance.sheet.batch.line'
    _description = 'Attendance Sheet Batch Line'

    attendance_id = fields.Many2one('attendance.sheet.batch',string="Attendance",store = True)
    
    employee_id = fields.Many2one("hr.employee", string="Employee",
                        domain="[('contract_warning','=',False), ('contract_id.attendance_required_bool', 'in', [True,False])]")
    period_from = fields.Date(string="Date From")
    period_to = fields.Date(string="Date To")
    attendance_sheet_id = fields.Many2one('hr.attendance.sheet',
                                          string="Attendance Sheet Id",
                                          store=True, index=True)
    employee_contract_id = fields.Many2one('hr.contract', string="Running Contract", related="employee_id.contract_id")
    contract_start_date = fields.Date(string="Contract Start Date", related="employee_id.contract_id.date_start")
    contract_end_date = fields.Date(string="Contract End Date", related="employee_id.contract_id.date_end")
    new_employee = fields.Boolean(string="New Employee", default=False)
    exit_employee = fields.Boolean(string="Exit Employee", default=False)
    employee_no = fields.Char(string="Employee Number")
    process_bool = fields.Boolean(string="Process Bool", default=False)

    def unlink(self):
        for rec in self:
            attendance_sheet = self.env['hr.attendance.sheet'].search([('id', '=', rec.attendance_sheet_id.id)])
            attendance_sheet.unlink()
        return super(AttendanceBatchLinbeWizard, self).unlink()