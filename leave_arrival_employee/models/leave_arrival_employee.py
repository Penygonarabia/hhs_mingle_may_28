from odoo import api, fields, models
from datetime import timedelta
from odoo.exceptions import UserError,ValidationError
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
import calendar

class LeaveArrivalEmployee(models.Model):
    _name = "employee.arrival"
    _description = "Employee Arrival"
    _auto = False

    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    employee_number = fields.Char(string="Employee Number",readonly=True)
    leave_date = fields.Date(string="Leave Date", readonly=True)
    expected_return_date = fields.Date(string="Expected Return Date", readonly=True)
    arrived_bool = fields.Boolean(string="Arrived")
    actual_return_date = fields.Date(string="Actual Return Date")
    leave_id = fields.Many2one('hr.leave', string="Leave", readonly=True)
    serial_no = fields.Char('S.no',readonly = True)  
    
    
    @api.model
    def get_number_of_days(self):
        no_days = int(self.env['ir.config_parameter'].sudo().get_param('hr.number_of_days'))
        return no_days

    ''' this code is working correctly they want the employee arrival is based on the expected leave return date'''
    @api.model
    def create_arrival_records(self):
        # Drop the existing employee_arrival table if it exists
        self._cr.execute("""
            DROP TABLE IF EXISTS employee_arrival CASCADE;
        """)

        # Create the employee_arrival table with audit fields
        self._cr.execute("""
            CREATE TABLE employee_arrival (
                id SERIAL PRIMARY KEY,
                employee_id INTEGER REFERENCES hr_employee(id),
                serial_no VARCHAR(50),
                leave_date DATE,
                employee_number VARCHAR(50),
                expected_return_date DATE,
                actual_return_date DATE,  
                arrived_bool BOOLEAN,
                leave_id INTEGER REFERENCES hr_leave(id),
                create_uid INTEGER REFERENCES res_users(id),
                create_date TIMESTAMP WITH TIME ZONE DEFAULT now(),
                write_uid INTEGER REFERENCES res_users(id),
                write_date TIMESTAMP WITH TIME ZONE
            );
        """)

        # Calculate the relevant date range
        today = fields.Date.today()
        ####working
        '''expected return days - arrival'''
        # checking_date = today - timedelta(days = self.get_number_of_days())
        checking_date = today + timedelta(days = self.get_number_of_days())
        # checking_date = today + timedelta(days=7)

        # Find relevant leaves
        leave_search = self.env['hr.leave'].search([
            # ('request_date_to', '<=', checking_date),
            # ('request_date_to', '>=', today),
            ('state', '=', 'validate'),
            ('actual_return_date','=',False),
            ('holiday_status_id.code', '=', 'AV')
        ])
        # leave_search = self.env['hr.leave'].search([
        #     ('request_date_to', '>=', checking_date),
        #     ('request_date_to', '<=', today),
        #     ('state', '=', 'validate'),
        #     ('actual_return_date','=',False),
        #     ('holiday_status_id.code', '=', 'AV')
        # ])

        # Prepare data for insertion
        employee_lst = []
        count = 0
        for leave in leave_search:
            count += 1
            val = {
                'serial_no' : count,
                'employee_id': leave.employee_id.id,
                'leave_date': leave.request_date_from,
                'expected_return_date': leave.request_date_to,
                'leave_id': leave.id,
                'employee_number':leave.employee_id.employee_no
            }
            employee_lst.append(val)

        # Insert new records into the employee_arrival table
        insert_query = """
            INSERT INTO employee_arrival (serial_no, employee_id, employee_number,leave_date, expected_return_date, leave_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        for record in employee_lst:
            self._cr.execute(insert_query, (
                record['serial_no'],
                record['employee_id'],
                record['employee_number'],
                record['leave_date'],
                record['expected_return_date'],
                record['leave_id'],
            ))
    

    # @api.model
    # def create_arrival_records(self):
    #     # Drop the existing employee_arrival table if it exists
    #     self._cr.execute("""
    #         DROP TABLE IF EXISTS employee_arrival CASCADE;
    #     """)
    #
    #     # Create the employee_arrival table with audit fields
    #     self._cr.execute("""
    #         CREATE TABLE employee_arrival (
    #             id SERIAL PRIMARY KEY,
    #             employee_id INTEGER REFERENCES hr_employee(id),
    #             serial_no VARCHAR(50),
    #             leave_date DATE,
    #             employee_number VARCHAR(50),
    #             expected_return_date DATE,
    #             actual_return_date DATE,  
    #             arrived_bool BOOLEAN,
    #             leave_id INTEGER REFERENCES hr_leave(id),
    #             create_uid INTEGER REFERENCES res_users(id),
    #             create_date TIMESTAMP WITH TIME ZONE DEFAULT now(),
    #             write_uid INTEGER REFERENCES res_users(id),
    #             write_date TIMESTAMP WITH TIME ZONE
    #         );
    #     """)
    #
    #     # Calculate the relevant date range
    #
    #     search_leave = self.env['hr.leave'].search([('state', '=', 'validate'),
    #         ('actual_return_date','=',False),
    #         ('holiday_status_id.code', '=', 'AV')])
    #
    #     checking_date = False
    #     for check_leave in search_leave:
    #         today = fields.Date.today()
    #         checking_date = check_leave.request_date_to + timedelta(days = self.get_number_of_days())
    #         # checking_date = today + timedelta(days = self.get_number_of_days())
    #
    #         # checking_date = today + timedelta(days=7)
    #
    #
    #         # Find relevant leaves
    #         leave_search = self.env['hr.leave'].search([
    #             ('request_date_to', '<=', checking_date),
    #             ('request_date_to', '>=', check_leave.request_date_to),
    #             ('state', '=', 'validate'),
    #             ('actual_return_date','=',False),
    #             ('holiday_status_id.code', '=', 'AV')
    #         ])
    #
    #         # Prepare data for insertion
    #         employee_lst = []
    #         count = 0
    #         for leave in leave_search:
    #             count += 1  
    #             val = {
    #                 'serial_no' : count,
    #                 'employee_id': leave.employee_id.id,
    #                 'leave_date': leave.request_date_from,
    #                 'expected_return_date': leave.request_date_to,
    #                 'leave_id': leave.id,
    #                 'employee_number':leave.employee_id.employee_no
    #             }
    #             employee_lst.append(val)
    #
    #     # Insert new records into the employee_arrival table
    #     insert_query = """
    #         INSERT INTO employee_arrival (serial_no, employee_id, employee_number,leave_date, expected_return_date, leave_id)
    #         VALUES (%s, %s, %s, %s, %s, %s)
    #     """
    #     for record in employee_lst:
    #         self._cr.execute(insert_query, (
    #             record['serial_no'],
    #             record['employee_id'],
    #             record['employee_number'],
    #             record['leave_date'],
    #             record['expected_return_date'],
    #             record['leave_id'],
    #         ))
    
    @api.model
    def search_fetch(self,  args, field_names, offset=0, limit=None, order=None):
        # Populate records when the menu is accessed
        self.create_arrival_records()

        return super(LeaveArrivalEmployee, self).search_fetch(args, field_names, offset=offset, limit=limit, order=order)

    def confirm_leave_arrival(self):
        for rec in self:
            if rec.arrived_bool and rec.actual_return_date:               
                rec._update_leave_records()
    
    def write(self, vals):
        """Override the write method to include logic for updating hr.leave records."""
        self.ensure_one()

        actual_return_date = vals.get('actual_return_date')
        if not actual_return_date:
            actual_return_date = self.actual_return_date

        leave_date = vals.get('leave_date')
        if not leave_date:
            leave_date = self.read(['leave_date'])[0]['leave_date']
            
        if isinstance(actual_return_date, str):
            actual_return_date = datetime.strptime(actual_return_date, "%Y-%m-%d").date()

        if isinstance(leave_date, str):
            leave_date = datetime.strptime(leave_date, "%Y-%m-%d").date()
        if actual_return_date:    
            if actual_return_date < leave_date:
                raise ValidationError("Actual return date must be greater than or equal to the leave date.")
        
        result = super(LeaveArrivalEmployee, self).write(vals)   
       

        return result

    
    ''' this is working correct they want confirm button for each line without update the employee record using save button so we use confirm button'''
    # def write(self, vals):
    #     """Override the write method to include logic for updating hr.leave records."""
    #     if 'actual_return_date' in vals:
    #         actual_return_date = vals.get('actual_return_date')
    #     else:
    #         actual_return_date = self.actual_return_date
    #     if 'leave_date' in vals:
    #         leave_date = vals.get('leave_date')
    #     else:
    #         leave_date = self.leave_date
    #
    #     if actual_return_date < leave_date.strftime("%Y-%m-%d"):
    #         raise ValidationError("Actual return date must be greater than leave date.")
    #
    #     result = super(LeaveArrivalEmployee, self).write(vals)
    #
    #     # Check if arrived_bool or actual_return_date is updated
    #     # if 'arrived_bool' in vals or 'actual_return_date' in vals:
    #     #
    #     #     self._update_leave_records()
    #
    #     return result

    def _update_leave_records(self):
        """Update hr.leave records based on the employee_arrival table."""
        # try:
            # Fetch records from employee_arrival where arrived_bool is True
        # arrival_records = self.env['employee.arrival'].search([('arrived_bool', '=', True)])
        no_of_days = 0
        for rec in self:
            if rec.arrived_bool:
                leave = self.env['hr.leave'].browse(rec.leave_id.id)
                if leave:
                    leave.write({'actual_return_date': rec.actual_return_date})
                    rec.employee_id.write({'accrued_leave': rec.actual_return_date})
                    if leave.request_date_from.month == leave.request_date_to.month:
                        leave.write({'actual_return_date': rec.actual_return_date})
                        paid_leave = leave.paid_leave
                        unpaid_leave = leave.unpaid_leave
                        paid_leave_last_date = leave.request_date_from + timedelta(days=paid_leave)
                        if paid_leave_last_date == rec.actual_return_date:
                            leave.write({'actual_return_date': rec.actual_return_date})
                            # print("paid_leave_last_date == rec.actual_return_date", leave)

                        if leave.request_date_from < rec.actual_return_date < paid_leave_last_date:
                            # print("leave.request_date_from < rec.actual_return_date < paid_leave_last_date 2222222", leave.request_date_from, rec.actual_return_date, paid_leave_last_date, leave.id)
                            days = (rec.actual_return_date - leave.request_date_from).days
                            arrival_paid_leave = days
                            arrival_unpaid_leave = 0
                            leave.paid_leave = arrival_paid_leave
                            leave.unpaid_leave = arrival_unpaid_leave

                            public_holiday_model = self.env['resource.calendar.leaves']
                            public_holidays = public_holiday_model.search([
                                ('resource_id', '=', False)  # Global public holidays
                            ])

                            # Loop through each public holiday and check overlap with leave dates
                            num_of_days = 0.00
                            for holiday in public_holidays:
                                # Find the overlapping range between the public holiday and leave request
                                holiday_start = max(holiday.date_from.date(), leave.request_date_from)
                                holiday_end = min(holiday.date_to.date(), rec.actual_return_date)

                                # Calculate number of days of overlap if within the range
                                if holiday_start <= holiday_end:  # Only count if there's an overlap
                                    num_of_days += (holiday_end - holiday_start).days + 1

                            # Add 1 extra day if needed
                            num_of_days = num_of_days
                            # Update the national_holiday field in the record
                            if num_of_days > 0:
                                leave.vacation_utilised = days - num_of_days

                                # rec.write({'national_holiday': num_of_days})
                            else:
                                leave.vacation_utilised = days

                            transaction = self.env['salary.allowance.detection'].search([
                                ('leave_id', '=', leave.id), ('employee_id', '=', leave.employee_id.id)
                            ])
                            for trans in transaction:
                                trans.days = days
                                # print(" trans.days",  trans.days)
                                # print("trans iddddddddd 2222222222222222222", trans)
                                # if rec.actual_return_date.month == trans.date.month:
                                #     return_date = rec.actual_return_date
                                #     print("return_date", return_date)
                                #     next_month = return_date.replace(day=28) + timedelta(
                                #         days=4)
                                #     print("next_month", next_month)
                                #     month_end_date = next_month - timedelta(
                                #         days=next_month.day)
                                #     print("month_end_date", month_end_date)
                                #     no_of_days = (month_end_date - return_date).days + 2
                                #     print("no_of_days", no_of_days)
                                #     month_num_of_days = calendar.monthrange(return_date.year, return_date.month)[1]
                                #     print("month_num_of_days", month_num_of_days)
                                #     days_trans = 0.00
                                #     # if no_of_days > trans.days:
                                #     days_trans = month_num_of_days - no_of_days
                                #     print("days_trans", days_trans)
                                #     trans.days = days_trans
                                #     print("trans.days", trans.days)
                                #     check_date = return_date
                                #     print("check_date", check_date)

                        if leave.request_date_to < rec.actual_return_date:
                            date_diff = (rec.actual_return_date - leave.request_date_to).days
                            # print("date_diff  (rec.actual_return_date - leave.request_date_to).days 333333333333", date_diff, rec.actual_return_date, leave.request_date_to)

                            if rec.employee_id.accrued_leave_num_of_days >= date_diff:
                                leave.vacation_utilised = leave.vacation_utilised + date_diff
                                leave.paid_leave = paid_leave + date_diff
                                transaction = self.env['salary.allowance.detection'].search([
                                    ('leave_id', '=', leave.id), ('employee_id', '=', leave.employee_id.id)
                                ])
                                for trans in transaction:
                                    trans_days = 0.00
                                    if rec.actual_return_date.month == trans.date.month:
                                        trans_days = trans.days + date_diff
                                        trans.days = trans_days
                            # else:
                            #     leave.vacation_utilised = leave.vacation_utilised
                            #     leave.paid_leave = paid_leave
                            #     leave.unpaid_leave = unpaid_leave + date_diff
                            else:

                                transaction = self.env['salary.allowance.detection'].search([
                                    ('leave_id', '=', leave.id), ('employee_id', '=', leave.employee_id.id)
                                ])
                                if transaction:
                                    for trans in transaction:
                                        trans_days = 0.00
                                        # if rec.actual_return_date.month == trans.date.month:
                                        #     trans_days = trans.days + date_diff
                                        #     trans.days = trans_days
                                        #     leave.vacation_utilised = leave.vacation_utilised + date_diff
                                        #     leave.paid_leave = paid_leave + date_diff
                                        #     leave.unpaid_leave = unpaid_leave - date_diff
                                        #     if leave.unpaid_leave < 0:
                                        #         leave.unpaid_leave = 0
                                        if rec.actual_return_date.month == trans.date.month:
                                            trans_days = trans.days + rec.employee_id.accrued_leave_num_of_days
                                            trans.days = int(trans_days)
                                            leave.vacation_utilised = int(leave.vacation_utilised + rec.employee_id.accrued_leave_num_of_days)
                                            leave.paid_leave = int(paid_leave + rec.employee_id.accrued_leave_num_of_days)
                                            leave.unpaid_leave = int(unpaid_leave - rec.employee_id.accrued_leave_num_of_days + date_diff)
                                            # print("unpaid_leave - rec.employee_id.accrued_leave_num_of_days + date_diff", unpaid_leave, rec.employee_id.accrued_leave_num_of_days, date_diff)
                                            # if leave.unpaid_leave < 0:
                                            #     leave.unpaid_leave = 0

                                else:
                                    leave.vacation_utilised = leave.vacation_utilised
                                    leave.paid_leave = paid_leave
                                    leave.unpaid_leave = unpaid_leave + date_diff
                                    # print("else leave.vacation_utilised, leave.paid_leave, leave.unpaid_leave", leave.vacation_utilised, leave.paid_leave, leave.unpaid_leave)

                    else:
                        paid_leave = leave.paid_leave
                        unpaid_leave = leave.unpaid_leave
                        paid_leave_last_date = leave.request_date_from + timedelta(days=paid_leave)
                        if leave.request_date_from <= rec.actual_return_date <= paid_leave_last_date:
                            # print("111111111111111 leave.request_date_from <= rec.actual_return_date <= paid_leave_last_date", leave.request_date_from, rec.actual_return_date, paid_leave_last_date )
                            days = (rec.actual_return_date - leave.request_date_from).days
                            arrival_paid_leave = days
                            arrival_unpaid_leave = 0
                            leave.paid_leave = arrival_paid_leave
                            leave.unpaid_leave = arrival_unpaid_leave


                            public_holiday_model = self.env['resource.calendar.leaves']
                            public_holidays = public_holiday_model.search([
                                ('resource_id', '=', False)  # Global public holidays
                            ])

                            # Loop through each public holiday and check overlap with leave dates
                            num_of_days = 0.00
                            for holiday in public_holidays:
                                # Find the overlapping range between the public holiday and leave request
                                holiday_start = max(holiday.date_from.date(), leave.request_date_from)
                                holiday_end = min(holiday.date_to.date(), rec.actual_return_date)

                                # Calculate number of days of overlap if within the range
                                if holiday_start <= holiday_end:  # Only count if there's an overlap
                                    num_of_days += (holiday_end - holiday_start).days + 1

                            # Add 1 extra day if needed
                            num_of_days = num_of_days
                            # Update the national_holiday field in the record
                            if num_of_days > 0:
                                leave.vacation_utilised = days - num_of_days

                                # rec.write({'national_holiday': num_of_days})
                            else:
                                leave.vacation_utilised = days

                            transaction = self.env['salary.allowance.detection'].search([
                                ('leave_id', '=', leave.id), ('employee_id', '=', leave.employee_id.id)
                            ])
                            for trans in transaction:
                                if rec.actual_return_date.month == trans.date.month:
                                    return_date = rec.actual_return_date
                                    next_month = return_date.replace(day=28) + timedelta(
                                        days=4)
                                    month_end_date = next_month - timedelta(
                                        days=next_month.day)
                                    no_of_days = (month_end_date - return_date).days + 1
                                    month_num_of_days = calendar.monthrange(return_date.year, return_date.month)[1]
                                    days_trans = 0.00
                                    # if no_of_days > trans.days:
                                    days_trans = month_num_of_days - no_of_days
                                    trans.days = days_trans
                                    check_date = return_date
                                    # print("days_trans 11111111111", days_trans, paid_leave)
                                    self.env.cr.execute("""
                                                               DELETE FROM salary_allowance_detection
                                                               WHERE employee_id = %s
                                                               AND date > %s
                                                               AND transaction_type_id = %s
                                                               AND leave_id = %s
                                                           """, (
                                        leave.employee_id.id,
                                        check_date,
                                        leave.holiday_status_id.transact_code_accrd_leave.transaction_type_id.id,
                                        leave.id
                                    ))


                        if paid_leave_last_date <= rec.actual_return_date <= leave.request_date_to:
                            # print(" paid_leave_last_date <= rec.actual_return_date <= leave.request_date_to",  paid_leave_last_date, rec.actual_return_date, leave.request_date_to)
                            date_diff = (leave.request_date_to - rec.actual_return_date).days
                            leave.unpaid_leave = unpaid_leave - date_diff
                            # print("leave.unpaid_leave, date_diff", leave.unpaid_leave, date_diff)

                        if leave.request_date_to <= rec.actual_return_date:
                            # print("leave.request_date_to <= rec.actual_return_date", leave.request_date_to, rec.actual_return_date)
                            date_diff = (rec.actual_return_date - leave.request_date_to).days
                            # print("date_diff 55555555", date_diff)
                            # print("rec.employee_id.accrued_leave_num_of_days 223232",
                            #       rec.employee_id.accrued_leave_num_of_days, date_diff)

                            if rec.employee_id.accrued_leave_num_of_days >= date_diff:
                                # print("rec.employee_id.accrued_leave_num_of_days", rec.employee_id.accrued_leave_num_of_days, date_diff)

                                # leave.vacation_utilised = leave.vacation_utilised + date_diff
                                # leave.paid_leave = paid_leave + date_diff
                                # leave.unpaid_leave = unpaid_leave

                                transaction = self.env['salary.allowance.detection'].search([
                                    ('leave_id', '=', leave.id), ('employee_id', '=', leave.employee_id.id)
                                ])
                                for trans in transaction:
                                    trans_days = 0.00
                                    if rec.actual_return_date.month == trans.date.month:
                                        trans_days = trans.days + date_diff
                                        trans.days = trans_days
                                        leave.vacation_utilised = leave.vacation_utilised + date_diff
                                        leave.paid_leave = paid_leave + date_diff
                                        leave.unpaid_leave = unpaid_leave - date_diff
                                        if leave.unpaid_leave < 0:
                                            leave.unpaid_leave = 0

                            else:

                                transaction = self.env['salary.allowance.detection'].search([
                                    ('leave_id', '=', leave.id), ('employee_id', '=', leave.employee_id.id)
                                ])
                                if transaction:
                                    for trans in transaction:
                                        trans_days = 0.00
                                        # if rec.actual_return_date.month == trans.date.month:
                                        #     trans_days = trans.days + date_diff
                                        #     trans.days = trans_days
                                        #     leave.vacation_utilised = leave.vacation_utilised + date_diff
                                        #     leave.paid_leave = paid_leave + date_diff
                                        #     leave.unpaid_leave = unpaid_leave - date_diff
                                        #     if leave.unpaid_leave < 0:
                                        #         leave.unpaid_leave = 0
                                        if rec.actual_return_date.month == trans.date.month:
                                            trans_days = trans.days + rec.employee_id.accrued_leave_num_of_days
                                            trans.days = int(trans_days)
                                            leave.vacation_utilised = int(leave.vacation_utilised + rec.employee_id.accrued_leave_num_of_days)
                                            leave.paid_leave = int(paid_leave + rec.employee_id.accrued_leave_num_of_days)
                                            leave.unpaid_leave = int(unpaid_leave - rec.employee_id.accrued_leave_num_of_days + date_diff)
                                            # print("unpaid_leave - rec.employee_id.accrued_leave_num_of_days + date_diff", unpaid_leave, rec.employee_id.accrued_leave_num_of_days, date_diff)
                                            # if leave.unpaid_leave < 0:
                                            #     leave.unpaid_leave = 0

                                else:
                                    leave.vacation_utilised = leave.vacation_utilised
                                    leave.paid_leave = paid_leave
                                    leave.unpaid_leave = unpaid_leave + date_diff
                                    # print("else leave.vacation_utilised, leave.paid_leave, leave.unpaid_leave", leave.vacation_utilised, leave.paid_leave, leave.unpaid_leave)


                rec.employee_id.last_return_date = rec.actual_return_date
                if leave.request_date_from.month == leave.request_date_to.month:
                    if rec.employee_id.emp_on_vacation:
                        rec.employee_id.emp_on_vacation = False

                else:
                    if rec.employee_id.slip_ids:
                        if rec.employee_id.emp_on_vacation:
                            rec.employee_id.emp_on_vacation = False
                        check_date = rec.actual_return_date
                        relevant_slip = rec.employee_id.slip_ids.filtered(
                            lambda slip: slip.date_from <= check_date <= slip.date_to and slip.state == 'draft'
                        )

                        if relevant_slip:
                            relevant_slip.write({'actual_arrival_date': check_date})
                            relevant_slip.onchange_employee()
                            relevant_slip.compute_sheet()