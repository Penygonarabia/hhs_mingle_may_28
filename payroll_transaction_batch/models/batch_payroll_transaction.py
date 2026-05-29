from odoo import api, fields, models, _
from odoo.exceptions import UserError,ValidationError

class PayrollTransactionBatch(models.Model):

    _name = "payroll.transaction.batch"
    _description = "Payroll Transaction Batch"
    
    name = fields.Char(string="Reference")

    batch_transaction_type_id = fields.Many2one('hr.transaction.rule', string='Transaction Type',
                                    domain="[('rule_type', 'in', ['transaction_allowance','transaction_detection'])]")

    batch_hr_transaction_id = fields.Many2one('hr.transaction.entry', 'Transaction Entry')

    batch_type = fields.Selection([('transaction_allowance', 'Transaction Allowance'),
                                   ('transaction_detection', 'Transaction Deduction')
                                   ], string='Type', readonly="1")
    
    transaction_date = fields.Date(string='Date',
                                   required=True,
                                   default=lambda self: fields.Date.today(),
                                   help="Submit date")
    
    state = fields.Selection([('draft', 'Draft'), ('approve', 'Approve')], default="draft", string="State")
    
    batch_payroll_transaction_ids = fields.One2many('payroll.transaction.batch.line', 'payroll_batch_id',
                                                    string="Batch Payroll Transaction")
    
    transact_code = fields.Char(string='Code')

    batch_units = fields.Selection([('days', 'Days'), ('hours', 'Hours'), ('amount', 'Amount')],
                                   string='Units', readonly=True, store=True, default='amount')

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('batch.payroll.transaction')
        return super(PayrollTransactionBatch, self).create(vals)
    
    @api.onchange('batch_hr_transaction_id')
    def _onchange_batch_transaction_type(self):
        for rec in self:
            if rec.batch_hr_transaction_id:
                rec.transact_code = rec.batch_hr_transaction_id.code
                rec.batch_type = rec.batch_hr_transaction_id.rule_type
                # rec.units = rec.hr_transaction_id.unit_type
                rec.batch_transaction_type_id = rec.batch_hr_transaction_id.transaction_type_id.id
                rec.batch_units = rec.batch_hr_transaction_id.unit_type
                if rec.batch_payroll_transaction_ids:
                    for record in rec.batch_payroll_transaction_ids:
                        record.batch_days = False
                        record.batch_amount = False
                        record.batch_fixed_amount = False
                        record.batch_hours = False
  
    def generate_payroll_batch(self):
        for rec in self:
            if not rec.batch_payroll_transaction_ids:
                raise ValidationError(_("Please ensure at least one line is added to the batch payroll transactions before proceeding."))
            # domain = []
            for line in self.batch_payroll_transaction_ids:
                payroll_transaction = self.env['salary.allowance.detection']
                vals = {
                    'employee_id': line.employee_id.id,
                    'date': line.date_line,
                    'employee_number': line.employee_id.employee_no,
                    'department': line.employee_id.department_id.id or False,
                    'employee_contract_id': line.employee_id.contract_id.id or False,
                    'hr_transaction_id': rec.batch_hr_transaction_id.id or False,
                    'transaction_type_id': line.batch_transaction_type_line_id.id or False,
                    'type': line.batch_line_type,
                    'reason': line.line_reason,
                    'code': rec.transact_code,
                    'payroll_transaction_batch_id': rec.id,
                    'days': 0,
                    }
                transaction = payroll_transaction.create(vals)
                transaction.onchange_transaction_type()
                if transaction.hr_transaction_id.unit_type == 'days':
                    if line.batch_days > 0.0:
                        transaction.days = line.batch_days
                if transaction.hr_transaction_id.unit_type == 'hours':
                    if line.batch_hours > 0.0:
                        transaction.hours = line.batch_hours
                if transaction.hr_transaction_id.unit_type == 'amount':
                    if line.batch_fixed_amount > 0.0:
                        transaction.fixed_amount = line.batch_fixed_amount
                        transaction.amount = line.batch_fixed_amount
            self.write({'state': 'approve'})

    # def unlink(self):
    #     for rec in self:
    #         if rec.state == 'draft':
    #            if rec.batch_payroll_transaction_ids:
    #                rec.batch_payroll_transaction_ids.unlink()
    #            rec.unlink()
    #         else:
    #             if rec.state == 'approve':

    def unlink(self):
        # Separate records into those that can be deleted and those that cannot
        records_to_delete = self.filtered(lambda rec: rec.state == 'draft')
        records_not_deletable = self.filtered(lambda rec: rec.state == 'approve')

        if records_not_deletable:
            raise ValidationError(_("Approved records cannot be deleted."))

        # Unlink related lines for draft records
        for rec in records_to_delete:
            if rec.batch_payroll_transaction_ids:
                rec.batch_payroll_transaction_ids.unlink()

        # Proceed with deleting draft records
        return super(PayrollTransactionBatch, records_to_delete).unlink()






class PayrollTransactionBatchLine(models.Model):
    _name = "payroll.transaction.batch.line"
    _description = "Payroll Transaction Batch Line"
    
    payroll_batch_id = fields.Many2one('payroll.transaction.batch', string="Payroll Batch Transaction Id")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    employee_no = fields.Char(string="Employee No")
    date_line = fields.Date(string="Date")
    # date_line = fields.Date(string="Date",compute="_compute_batch_hr_transaction_id",store=True)
    batch_hr_transaction_line_id = fields.Many2one('hr.transaction.entry', 'Transaction Entry',
                                                   compute="_compute_batch_hr_transaction_id", store=True)
    batch_transaction_type_line_id = fields.Many2one('hr.transaction.rule', string='Transaction Type',
                                                     compute="_compute_batch_hr_transaction_id",
                                    domain="[('rule_type', 'in', ['transaction_allowance','transaction_detection'])]",
                                    store=True)
    batch_line_type = fields.Selection([('transaction_allowance', 'Transaction Allowance'),
                                        ('transaction_detection', 'Transaction Deduction')
                                        ], string='Type', readonly="1", compute="_compute_batch_hr_transaction_id",
                                       store=True)
    line_reason = fields.Char(string="Reason")
    batch_days = fields.Float(string='Days')
    batch_hours = fields.Float(string='Hours')
    batch_fixed_amount = fields.Float(string="Fixed Amount")
    batch_amount = fields.Float(string="Amount", compute='compute_hr_allowance_days_hours_amount')
    batch_calculate_based_on_allowance = fields.Selection(string="Calculate Based On",
                                                          selection=[
                                                               ('wage', 'Wage'),
                                                               ('hra', 'HRA'),
                                                               ('wage_trv', 'Basic + Transport'),
                                                               ('wage_tr_fd', 'Basic + Transport + Food'),
                                                               ('hra_trv', 'HRA + Transport'),
                                                               ('hr_tr_sch', 'HRA + Transport + School'),
                                                               ('hr_tr_fd', 'HRA + Transport + Food'),
                                                               ('hr_tr_fl', 'HRA + Transport + Fuel'),
                                                               ('hr_tr_tk', 'HRA + Transport + Ticket'),
                                                               ('hr_tr_fx', 'HRA + Transport + Fixed'),
                                                               ('hr_tr_mb', 'HRA + Transport + Mobile'),
                                                               ('hr_tr_oth', 'HRA + Transport + Other'),
                                                               ('hr_tr_wk', 'HRA + Transport + Work'),
                                                               ('all', 'All')],
                                                          default='hra', required=True)
    # batch_units = fields.Selection([('days', 'Days'), ('hours', 'Hours'), ('amount', 'Amount')],
    #                                string='Units', readonly=True, store=True, default='amount')

    @api.constrains('date_line')
    def _check_date_month(self):
        for rec in self:
            if rec.payroll_batch_id.transaction_date:
                if rec.payroll_batch_id.transaction_date.strftime("%m-%Y") != rec.date_line.strftime("%m-%Y"): 
                    raise ValidationError("Please enter the same month date %s range only" %rec.payroll_batch_id.transaction_date)
                if rec.date_line:
                    existing_employee = self.env['salary.allowance.detection'].search(
                        [('id', '!=', rec.id), ('employee_id', '=', rec.employee_id.id), 
                         ('transaction_type_id', '=', rec.batch_transaction_type_line_id.id),
                         ('date', '=', rec.date_line)])
                    if existing_employee:
                        raise ValidationError(('Already Employee %s is existing on %s day on payroll Transaction' % (rec.employee_id.name,rec.date_line)))

    @api.constrains('employee_no', 'date_line','batch_hr_transaction_line_id')
    def _check_employee_no(self):
        for rec in self:
            # Check if any record exists with the same employee_no and date_line but a different id
            duplicate = self.search([
                ('employee_no', '=', rec.employee_no),
                ('date_line', '=', rec.date_line),
                ('employee_id', '=', rec.employee_id.id),
                ('batch_hr_transaction_line_id','=',rec.batch_hr_transaction_line_id.id),
                ('id', '!=', rec.id)
            ])
            if duplicate:
                raise ValidationError(
                    _("A line with Employee No '%s' and Date '%s' already exists. Please ensure each line is unique.")
                    % (rec.employee_no, rec.date_line)
                )

    @api.constrains('batch_days', 'batch_hours', 'batch_fixed_amount')
    def _check_days(self):
        for rec in self:
            # if rec.payroll_batch_id.batch_units == 'days':
            #     if rec.batch_days == 0.0:
            #         raise ValidationError('Days should not be zero.Please Enter number of Days in the line')
            # if rec.payroll_batch_id.batch_units == 'hours':
            #     if rec.batch_hours == 0.0:
            #         raise ValidationError('Hours should not be zero.Please Enter number of Hours in the line')
            # if rec.payroll_batch_id.batch_units == 'amount':
            #     if rec.batch_fixed_amount == 0.0:
            #         raise ValidationError('Fixed amount should not be zero.Please Enter Amount in the line')

            employee_name = rec.employee_id.name or "Unknown Employee"
            employee_no = rec.employee_no or "Unknown Employee No"
            # if len(rec.employee_no) > 1:
            #     raise ValidationError(
            #         _("A line cannot be assigned to more than one employee. Please ensure each line is linked to a single employee.")
            #     )

            if rec.payroll_batch_id.batch_units == 'days':
                if rec.batch_days == 0.0:
                    raise ValidationError(
                        _("For Employee '%s' (Employee No: %s), Days should not be zero. Please enter the number of days in the line.")
                        % (employee_name, employee_no)
                    )
            if rec.payroll_batch_id.batch_units == 'hours':
                if rec.batch_hours == 0.0:
                    raise ValidationError(
                        _("For Employee '%s' (Employee No: %s), Hours should not be zero. Please enter the number of hours in the line.")
                        % (employee_name, employee_no)
                    )
            if rec.payroll_batch_id.batch_units == 'amount':
                if rec.batch_fixed_amount == 0.0:
                    raise ValidationError(
                        _("For Employee '%s' (Employee No: %s), Fixed amount should not be zero. Please enter the amount in the line.")
                        % (employee_name, employee_no)
                    )

    @api.onchange('employee_no')
    def _onchange_employee_id(self):
        for rec in self:
            if rec.employee_no:
                employee_search = self.env['hr.employee'].search([('employee_no', '=', rec.employee_no)], limit=1)
                rec.employee_id = employee_search.id
                # rec.date_line = rec.payroll_batch_id.transaction_date

    @api.onchange('employee_id')
    def _onchange_employee(self):
        for rec in self:
            if rec.employee_id:
                rec.employee_no = rec.employee_id.employee_no
                rec.date_line = rec.payroll_batch_id.transaction_date
                if rec.payroll_batch_id.batch_units == 'amount':
                    rec.batch_fixed_amount = rec.payroll_batch_id.batch_hr_transaction_id.fixed_amount

    @api.depends('payroll_batch_id.batch_hr_transaction_id') 
    def _compute_batch_hr_transaction_id(self):
        for rec in self: 
            rec.batch_hr_transaction_line_id = False
            rec.batch_line_type = False
            rec.batch_transaction_type_line_id = False
            if rec.payroll_batch_id.batch_hr_transaction_id:
                rec.batch_hr_transaction_line_id = rec.payroll_batch_id.batch_hr_transaction_id.id
                rec.batch_line_type = rec.payroll_batch_id.batch_hr_transaction_id.rule_type
                # rec.units = rec.hr_transaction_id.unit_type
                rec.batch_transaction_type_line_id = rec.payroll_batch_id.batch_hr_transaction_id.transaction_type_id.id
                # rec.batch_units = rec.payroll_batch_id.batch_hr_transaction_id.unit_type
                # rec.date_line = rec.payroll_batch_id.transaction_date
                rec.batch_calculate_based_on_allowance = rec.payroll_batch_id.batch_hr_transaction_id.calculate_based_on_allowance
                if rec.payroll_batch_id.batch_units == 'amount':
                    rec.batch_fixed_amount = rec.payroll_batch_id.batch_hr_transaction_id.fixed_amount
                    rec.batch_amount = rec.batch_fixed_amount

    @api.depends('batch_days', 'payroll_batch_id.batch_units', 'employee_id.contract_id', 'batch_hours', 'batch_calculate_based_on_allowance')
    def compute_hr_allowance_days_hours_amount(self):
        for salary in self:
            salary.batch_amount = 0.00
            for rec in salary.employee_id.contract_id:
                if salary.employee_id:
                    no_of_days = 30
                    hours_per_day = 8
                    if salary.batch_calculate_based_on_allowance == 'wage':
                        if salary.payroll_batch_id.batch_units == 'days':
                            salary.batch_amount = (
                                    rec.wage * salary.batch_days / no_of_days * (
                                        salary.payroll_batch_id.batch_hr_transaction_id.rate / 100))
                        if salary.payroll_batch_id.batch_units == 'hours':
                            salary.batch_amount = (rec.wage / no_of_days / hours_per_day * (
                                    salary.payroll_batch_id.batch_hr_transaction_id.rate / 100)) * salary.batch_hours

                    if salary.batch_calculate_based_on_allowance == 'wage_trv':
                        if salary.payroll_batch_id.batch_units == 'days':
                            salary.batch_amount = ((rec.wage + rec.transport_allowance) * salary.batch_days / no_of_days * (
                                    salary.payroll_batch_id.batch_hr_transaction_id.rate / 100))
                        elif salary.payroll_batch_id.batch_units == 'hours':
                            salary.batch_amount = ((rec.wage + rec.transport_allowance) / no_of_days / hours_per_day * (
                                    salary.payroll_batch_id.batch_hr_transaction_id.rate / 100)) * salary.batch_hours
                        elif salary.payroll_batch_id.batch_units == 'amount':
                            salary.batch_amount = salary.batch_fixed_amount

                    if salary.batch_calculate_based_on_allowance == 'wage_tr_fd':
                        if salary.payroll_batch_id.batch_units == 'days':
                            salary.batch_amount = ((
                                                           rec.wage + rec.food_allowance + rec.transport_allowance) * salary.batch_days / no_of_days * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100))
                        elif salary.payroll_batch_id.batch_units == 'hours':
                            salary.batch_amount = ((
                                                           rec.wage + rec.food_allowance + rec.transport_allowance) / no_of_days / hours_per_day * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100)) * salary.batch_hours
                        elif salary.payroll_batch_id.batch_units == 'amount':
                            salary.batch_amount = salary.batch_fixed_amount

                    if salary.batch_calculate_based_on_allowance == 'hra':
                        if salary.payroll_batch_id.batch_units == 'days':
                            salary.batch_amount = ((rec.wage + rec.house_allowance) * salary.batch_days / no_of_days * (
                                    salary.payroll_batch_id.batch_hr_transaction_id.rate / 100))
                        elif salary.payroll_batch_id.batch_units == 'hours':
                            salary.batch_amount = ((rec.wage + rec.house_allowance) / no_of_days / hours_per_day * (
                                    salary.payroll_batch_id.batch_hr_transaction_id.rate / 100)) * salary.batch_hours
                        elif salary.payroll_batch_id.batch_units == 'amount':
                            salary.batch_amount = salary.batch_fixed_amount

                    if salary.batch_calculate_based_on_allowance == 'hra_trv':
                        if salary.payroll_batch_id.batch_units == 'days':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance) * salary.batch_days / no_of_days * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100))
                        elif salary.payroll_batch_id.batch_units == 'hours':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance) / no_of_days / hours_per_day * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100)) * salary.batch_hours

                    if salary.batch_calculate_based_on_allowance == 'hr_tr_sch':
                        if salary.payroll_batch_id.batch_units == 'days':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance + rec.school_allowance) * salary.batch_days / no_of_days * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100))

                        elif salary.payroll_batch_id.batch_units == 'hours':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance + rec.school_allowance) / no_of_days / hours_per_day * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100)) * salary.batch_hours

                    if salary.batch_calculate_based_on_allowance == 'hr_tr_fd':
                        if salary.payroll_batch_id.batch_units == 'days':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance + rec.food_allowance) * salary.batch_days / no_of_days * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100))
                        elif salary.payroll_batch_id.batch_units == 'hours':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance + rec.food_allowance) / no_of_days / hours_per_day * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100)) * salary.batch_hours

                    if salary.batch_calculate_based_on_allowance == 'hr_tr_fl':
                        if salary.payroll_batch_id.batch_units == 'days':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance + rec.fuel_allowance) * salary.batch_days / no_of_days * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100))
                        elif salary.payroll_batch_id.batch_units == 'hours':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance + rec.fuel_allowance) / no_of_days / hours_per_day * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100)) * salary.batch_hours

                    if salary.batch_calculate_based_on_allowance == 'hr_tr_tk':
                        if salary.payroll_batch_id.batch_units == 'days':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance + rec.ticket_allowance) * salary.batch_days / no_of_days * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100))
                        elif salary.payroll_batch_id.batch_units == 'hours':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance + rec.ticket_allowance) / no_of_days / hours_per_day * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100)) * salary.batch_hours

                    if salary.batch_calculate_based_on_allowance == 'hr_tr_fx':
                        if salary.payroll_batch_id.batch_units == 'days':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance + rec.fixed_allowance) * salary.batch_days / no_of_days * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100))
                        elif salary.payroll_batch_id.batch_units == 'hours':
                            salary.batch_amount = salary.batch_amount = ((
                                                                                 rec.wage + rec.house_allowance + rec.transport_allowance + rec.fixed_allowance) / no_of_days / hours_per_day * (
                                                                                 salary.payroll_batch_id.batch_hr_transaction_id.rate / 100)) * salary.batch_hours

                    if salary.batch_calculate_based_on_allowance == 'hr_tr_mb':
                        if salary.payroll_batch_id.batch_units == 'days':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance + rec.mobile_allowance) * salary.batch_days / no_of_days * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100))
                        elif salary.payroll_batch_id.batch_units == 'hours':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance + rec.mobile_allowance) / no_of_days / hours_per_day * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100)) * salary.batch_hours

                    if salary.batch_calculate_based_on_allowance == 'hr_tr_wk':
                        if salary.payroll_batch_id.batch_units == 'days':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance + rec.work_allowance) * salary.batch_days / no_of_days * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100))
                        elif salary.payroll_batch_id.batch_units == 'hours':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance + rec.work_allowance) / no_of_days / hours_per_day * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100)) * salary.batch_hours

                    if salary.batch_calculate_based_on_allowance == 'hr_tr_oth':
                        if salary.payroll_batch_id.batch_units == 'days':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance + rec.housing_allowance) * salary.batch_days / no_of_days * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100))
                        elif salary.payroll_batch_id.batch_units == 'hours':
                            salary.batch_amount = ((
                                                           rec.wage + rec.house_allowance + rec.transport_allowance + rec.housing_allowance) / no_of_days / hours_per_day * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100)) * salary.batch_hours

                    if salary.batch_calculate_based_on_allowance == 'all':
                        if salary.payroll_batch_id.batch_units == 'days':
                            salary.batch_amount = ((rec.wage + rec.house_allowance + rec.transport_allowance +
                                                    rec.school_allowance + rec.food_allowance + rec.fuel_allowance + rec.ticket_allowance
                                                    + rec.fixed_allowance + rec.mobile_allowance + rec.work_allowance + rec.housing_allowance) * salary.batch_days / no_of_days * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100))
                        elif salary.payroll_batch_id.batch_units == 'hours':
                            salary.batch_amount = ((rec.wage + rec.house_allowance + rec.transport_allowance +
                                                    rec.school_allowance + rec.food_allowance + rec.fuel_allowance + rec.ticket_allowance
                                                    + rec.fixed_allowance + rec.mobile_allowance + rec.work_allowance + rec.housing_allowance) / no_of_days / hours_per_day * (
                                                           salary.payroll_batch_id.batch_hr_transaction_id.rate / 100)) * salary.batch_hours

            if salary.payroll_batch_id.batch_units == 'amount':
                salary.batch_amount = salary.batch_fixed_amount