from odoo import models, fields, api, _
from datetime import datetime, date
import calendar
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round
from dateutil.relativedelta import relativedelta
import time

# _logger = logging.getLogger(__name__)


class EmployeeAccrual(models.Model):
    _name = 'employee.accrual'
    _description = 'Employee Accrual'

    # name = fields.Char(string='Accrual Name', required=True)
    name = fields.Char(string='Reference', readonly=True, copy=False)
    date_from = fields.Date(
        string='Date From',
        default=lambda self: datetime.today().replace(day=1)
    )

    # Date to: end of the current month
    date_to = fields.Date(
        string='Date To',
        default=lambda self: datetime.today().replace(
            day=calendar.monthrange(datetime.today().year, datetime.today().month)[1]
        )
    )

    accrual_type = fields.Selection([
        ('annual_leave', 'Annual Leave'),
        ('annual_tickets', 'Annual Tickets'),
        ('gratuity', 'EOS Accruals'),
    ], string='Accrual Type', required=True)

    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft')

    accrual_line_ids = fields.One2many('employee.accrual.line', 'accrual_id', string='Accrual Lines')
    gratuity_line_ids = fields.One2many('mih.auh.gratuity.line', 'gratuity_id', string='Gratuity Lines')

    accrual_calculation = fields.Selection(string="Calculate Based On",
                                         selection=[('wage', 'Wage'),
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
                                                    ('hr_tr_wk', 'HRA + Transport + Work'), ('all', 'All')])

    accrual_calculation_id = fields.Many2one(
        'hr.transaction.entry',
        string="Transaction Definition",
        default=lambda self: self.env['hr.transaction.entry'].search([('code', '=', 'ACL')], limit=1)
    )

    @api.onchange('accrual_calculation_id')
    def _onchange_accrual_calculation(self):
        for rec in self:
            rec.accrual_calculation = False
            if rec.accrual_calculation_id:
                # Get the selection field's key from the related 'calculate_based_on_allowance' field
                selection_field_value = rec.accrual_calculation_id.calculate_based_on_allowance
                rec.accrual_calculation = selection_field_value

    def unlink(self):
        for record in self:
            if record.status == 'approved':
                raise ValidationError(_('You cannot delete an approved record.'))
            if record.status in ['draft', 'confirmed']:
                # for line in record.accrual_line_ids:
                #     line.unlink()
                if record.accrual_line_ids:
                    print("record", record.accrual_line_ids)
                    record.accrual_line_ids.unlink()
                if record.gratuity_line_ids:
                    record.gratuity_line_ids.unlink()
        return super(EmployeeAccrual, self).unlink()

    @api.constrains('date_from', 'date_to', 'accrual_type')
    def _check_unique_accrual_record(self):
        for record in self:
            # Search for existing records with the same date range and accrual type
            existing_record = self.search_count([
                ('id', '!=', record.id),  # Exclude the current record (for updates)
                ('date_from', '=', record.date_from),
                ('date_to', '=', record.date_to),
                ('accrual_type', '=', record.accrual_type),
            ])
            if existing_record:
                raise UserError("A record with the same date range and accrual type already exists.")

    def action_generate_monthly_accrual(self):
        """Logic to generate monthly accruals for selected employees."""
        for accrual in self:
            if accrual.accrual_type in ['annual_leave', 'annual_tickets']:
                if not accrual.date_from or not accrual.date_to:
                    raise UserError(_('Please select both the date_from and date_to for the accrual period.'))
                if accrual.accrual_line_ids:
                    accrual.accrual_line_ids.unlink()
                if accrual.gratuity_line_ids:
                    accrual.gratuity_line_ids.unlink()
                    print(" accrual.gratuity_line_ids",  accrual.gratuity_line_ids)
                # for employee in self.env['hr.employee'].search([('exit_date', '=', False), ('contract_warning', '=', False),('joining_date', '<=', accrual.date_to)]):
                for employee in self.env['hr.employee'].search([('contract_warning', '=', False),('joining_date', '<=', accrual.date_to)]):
                    if employee.entitlement > 0 or employee.entitlement_ticket > 0:
                        self.env['employee.accrual.line'].create({
                            'accrual_id': accrual.id,
                            'employee_id': employee.id,
                            'contract_id': employee.contract_id.id,
                            'ticket_entitlement': employee.entitlement_ticket,
                            'ticket_entitlement_amount': employee.air_ticket_unit_price * employee.entitlement_ticket,
                            'status': accrual.status,
                            'accrual_type': accrual.accrual_type,
                        })
            else:
                if accrual.accrual_line_ids:
                    accrual.accrual_line_ids.unlink()
                if accrual.gratuity_line_ids:
                    accrual.gratuity_line_ids.unlink()
                # accrual.gratuity_line_ids.unlink()
                # def create_auh_gratuity_sheet(self):
                employee_ids = self.env['hr.employee'].search(
                    [('custom_gratuity_generate', '=', True), ('joining_date', '<=', self.date_to)])
                # journal_id = self.env['account.journal'].search([('custom_is_gratuity_journal', '=', True)],
                #                                                 limit=1)
                # if not journal_id:
                #     raise ValidationError(
                #         _('Configure Gratuity Journal on Accounting journals, Click on checkbox "Is Gratuity Journal?" to create.'))

                dates = date.today()
                previous_month = dates + relativedelta(day=1, months=-1)
                previous_month_last = dates + relativedelta(day=1, months=-1, days=-1)
                first_day = dates + relativedelta(day=1)
                last_day = dates + relativedelta(day=1, months=+1, days=-1)
                next_month_first = self.date_to.replace(day=1)
                next_month_last = dates + relativedelta(day=1, months=+2, days=-1)
                if (self.date_to >= first_day) and (self.date_to < last_day):
                    raise ValidationError(_('Already gratuity has been created for the employees on the date %s')
                                          % (self.date_to.strftime("%d-%m-%Y")))

                ### working code just commanded for validation perpose - 13/11/2024
                # if self.date_to < first_day:
                #     raise ValidationError(
                #         _('Previous Month Date should not be allowed. Only Current month alone can be allowed'))
                if self.date_to > last_day:
                    raise ValidationError(
                        _('Future Month Date should not be allowed. Only Current month alone can be allowed'))
                # move_pool = self.env['account.move']
                #
                # move = {
                #     'date': last_day,
                #     'journal_id': journal_id.id,
                #
                # }
                # custom_move = move_pool.create(move)
                for empl in employee_ids:
                    contracts = empl._get_contracts(first_day, last_day)
                    if not contracts:
                        continue
                    # custom_gratuity = self.env['mih.auh.gratuity.sheet'].search(
                    #     [('custom_date_of_join', '=', empl.joining_date)])
                    sheet_vals = {
                        'custom_employee_id': empl.id,
                        ### working code just commanded for validation perpose - 13/11/2024
                        # 'custom_date_of_join': empl.joining_date if self.date_to == last_day else next_month_first,
                        'custom_date_of_join': empl.joining_date,
                        'custom_late_working_day': self.date_to,
                        'custom_contract_id': contracts.id,
                        'custom_basic_salary': contracts.wage,
                        'custom_allowance': contracts.custom_allowance,
                        'gratuity_id': accrual.id
                    }
                    # print("sheet_vals", sheet_vals)
                    custom_gratuity_id = self.env['mih.auh.gratuity.line'].create(sheet_vals)
                    custom_gratuity_id.write({'custom_type': 'less_than_five_year' if custom_gratuity_id.no_of_days <= 1825 else 'greater_than_five_year'})

                    # deb_interest_line = (0, 0, {
                    #     'name': empl.name,
                    #     'date': last_day,
                    #     'partner_id': empl.address_home_id.id,
                    #     'account_id': journal_id.default_debit_account_id.id,
                    #     'journal_id': journal_id.id,
                    #     # 'analytic_tag_ids' : [(6, 0, empl.contract_id.x_analytic_tag_ids.ids)],
                    #     'analytic_account_id': empl.contract_id.analytic_account_id.id,
                    #     'debit': custom_gratuity_id.custom_esob_amounts,
                    #     'credit': 0.0
                    # })
                    # cred_interest_line = (0, 0, {
                    #     'name': empl.name,
                    #     'date': last_day,
                    #     'partner_id': empl.address_home_id.id,
                    #     'account_id': journal_id.default_credit_account_id.id,
                    #     'journal_id': journal_id.id,
                    #     #                'analytic_tag_ids' : [(6, 0, empl.contract_id.x_analytic_tag_ids.ids)],
                    #     'analytic_account_id': empl.contract_id.analytic_account_id.id,
                    #     'debit': 0.0,
                    #     'credit': custom_gratuity_id.custom_esob_amounts
                    # })
                    # custom_move.write({
                    #     'line_ids': [deb_interest_line, cred_interest_line],
                    # })
                    # custom_gratuity_id.write({
                    #     'custom_move_id': custom_move.id,
                    #     'custom_type': 'less_than_five_year' if custom_gratuity_id.no_of_days <= 1825 else 'greater_than_five_year',
                    #
                    # })

                    dupl_empl = self.env['mih.auh.gratuity.line'].search([('id', '!=', custom_gratuity_id.id),
                                                                           ('custom_employee_id', '=',
                                                                            custom_gratuity_id.custom_employee_id.id),
                                                                           ('custom_late_working_day', '=',
                                                                            custom_gratuity_id.custom_late_working_day)])

                    if self.date_to == dupl_empl.custom_late_working_day:
                        raise ValidationError(
                            _('Already gratuity has been created for the employees on the date %s')
                            % (self.date_to.strftime("%d-%m-%Y")))

                # auh_action = self.env.ref("hr_gratuity.action_auh_gratuity_custom").read()[0]
                # try:
                #     auh_action['domain'] = [('id', 'in', custom_gratuity_id.ids)]
                # except Exception as e:
                #     se = _serialize_exception(e)
                #     error = {
                #         'code': 200,
                #         'message': 'Not available any running employee contract.',
                #         'data': se
                #     }
                #
                # return auh_action


    def action_create_eos_journal_entry(self):
        for rec in self:
            journal_id = self.env['account.journal'].search([('custom_is_gratuity_journal', '=', True)],
                                                            limit=1)
            if not journal_id:
                raise ValidationError(
                    _('Configure Gratuity Journal on Accounting journals, Click on checkbox "Is Gratuity Journal?" to create.'))

            dates = date.today()
            previous_month = dates + relativedelta(day=1, months=-1)
            previous_month_last = dates + relativedelta(day=1, months=-1, days=-1)
            first_day = dates + relativedelta(day=1)
            last_day = dates + relativedelta(day=1, months=+1, days=-1)
            acc_date = self.date_to
            next_month_first = self.date_to.replace(day=1)
            next_month_last = dates + relativedelta(day=1, months=+2, days=-1)
            move_pool = self.env['account.move']

            move = {
                'date': acc_date,
                'journal_id': journal_id.id,
                'ref': _('Accrual for %s') % rec.name,
            }
            custom_move = move_pool.create(move)
            print("custom_move", custom_move)
            for eos_line in rec.gratuity_line_ids:
                print("eos_line", eos_line)
                # if eos_line.custom_esob_amounts > 0:
                if eos_line.current_month_amt > 0:
                    deb_interest_line = (0, 0, {
                        'name': eos_line.custom_employee_id.name,
                        'date': acc_date,
                        'partner_id': eos_line.custom_employee_id.address_home_id.id,
                        'account_id': journal_id.default_debit_account_id.id,
                        'journal_id': journal_id.id,
                        # 'analytic_tag_ids' : [(6, 0, empl.contract_id.x_analytic_tag_ids.ids)],
                        # 'analytic_account_id': eos_line.custom_employee_id.contract_id.analytic_account_id.id,
                        'analytic_distribution': {
                            eos_line.custom_employee_id.contract_id.analytic_account_id.id: 100} if eos_line.custom_employee_id.contract_id.analytic_account_id else {},
                        'debit': eos_line.current_month_amt,
                        'credit': 0.0
                    })
                    cred_interest_line = (0, 0, {
                        'name': eos_line.custom_employee_id.name,
                        'date': acc_date,
                        'partner_id': eos_line.custom_employee_id.address_home_id.id,
                        'account_id': journal_id.default_credit_account_id.id,
                        'journal_id': journal_id.id,
                        #                'analytic_tag_ids' : [(6, 0, empl.contract_id.x_analytic_tag_ids.ids)],
                        # 'analytic_account_id': eos_line.custom_employee_id.contract_id.analytic_account_id.id,
                        'analytic_distribution': {
                            eos_line.custom_employee_id.contract_id.analytic_account_id.id: 100} if eos_line.custom_employee_id.contract_id.analytic_account_id else {},
                        'debit': 0.0,
                        'credit': eos_line.current_month_amt
                    })
                    custom_move.write({
                        'line_ids': [deb_interest_line, cred_interest_line],
                    })
                    eos_line.write({
                        'custom_move_id': custom_move.id,
                        'custom_type': 'less_than_five_year' if eos_line.no_of_days <= 1825 else 'greater_than_five_year',

                    })

    def action_approve_accrual(self):
        """Approve the accrual and generate journal entries."""
        self.write({'status': 'approved'})
        # self.accrual_line_ids.action_create_accrual_journal_entry()
        if self.accrual_type in ['annual_leave', 'annual_tickets']:
            self.action_create_accrual_journal_entry()
        if self.accrual_type == 'gratuity':
            self.action_create_eos_journal_entry()
        # for record in self:
        #     record.status = 'approved'
        #     # Generate reference when changing state to approved
        #     if not record.name:
        #         if record.accrual_type == 'annual_leave':
        #             record.name = self.env['ir.sequence'].next_by_code('accrual.type.annual.leave') or '/'
        #         elif record.accrual_type == 'annual_tickets':
        #             record.name = self.env['ir.sequence'].next_by_code('accrual.type.annual.tickets') or '/'

    def action_confirm_accrual(self):
        """Confirm the accrual."""
        self.write({'status': 'confirmed'})
        for record in self:
            record.status = 'confirmed'
            if record.accrual_type in ['annual_leave', 'annual_tickets']:
                if len(record.accrual_line_ids) < 1:
                    raise ValidationError("Employee Accrual Sheet must have at least one line.")
            if record.accrual_type == 'gratuity':
                if len(record.gratuity_line_ids) < 1:
                    raise ValidationError("EOS Accruals must have at least one line.")
            # Generate reference when changing state to approved
            if not record.name:
                if record.accrual_type == 'annual_leave':
                    record.name = self.env['ir.sequence'].next_by_code('accrual.type.annual.leave') or '/'
                elif record.accrual_type == 'annual_tickets':
                    record.name = self.env['ir.sequence'].next_by_code('accrual.type.annual.tickets') or '/'
                elif record.accrual_type == 'gratuity':
                    record.name = self.env['ir.sequence'].next_by_code('accrual.type.gratuity') or '/'

    def action_reject_accrual(self):
        """Reject the accrual and reset status to draft."""
        self.write({'status': 'draft'})

    def action_create_accrual_journal_entry(self):
        """Create a single journal entry for multiple employee accrual lines."""
        for accrual in self:
            move_vals = {
                'journal_id': self._get_journal_id(accrual.accrual_type),
                'date': accrual.date_to or fields.Date.today(),
                'ref': _('Accrual for %s') % accrual.name,
                'line_ids': []
            }

            for line in accrual.accrual_line_ids:
                # Debit and Credit amounts
                debit_amount = line.accrual_amount + line.ticket_accrual_amount
                credit_amount = line.accrual_amount + line.ticket_accrual_amount

                # Only process lines with valid amounts
                if debit_amount > 0:
                    # Get the debit and credit account IDs
                    debit_account_id = line._get_debit_account_id()
                    credit_account_id = line._get_credit_account_id()

                    if not debit_account_id or not credit_account_id:
                        raise UserError(_('Please configure both debit and credit accounts for accruals.'))

                    # Create debit line
                    move_vals['line_ids'].append((0, 0, {
                        'account_id': debit_account_id,
                        'name': _('Accrual Debit for %s') % line.employee_id.name,
                        'partner_id': line.employee_id.address_home_id.id,
                        'debit': debit_amount,
                        'credit': 0.0,
                        # 'analytic_account_id': line.analytical_code.id or False,
                        'analytic_distribution': {
                            line.analytical_code.id: 100} if line.analytical_code else {},
                    }))

                    # Create credit line
                    move_vals['line_ids'].append((0, 0, {
                        'account_id': credit_account_id,
                        'name': _('Accrual Credit for %s') % line.employee_id.name,
                        'partner_id': line.employee_id.address_home_id.id,
                        'debit': 0.0,
                        'credit': credit_amount,
                        # 'analytic_account_id': line.analytical_code.id or False,
                        'analytic_distribution': {
                            line.analytical_code.id: 100} if line.analytical_code else {},
                    }))

            # Only create the journal entry if there are lines to process
            if move_vals['line_ids']:
                move = self.env['account.move'].create(move_vals)
                accrual.accrual_line_ids.write({'account_move_id': move.id})

    def _get_journal_id(self, accrual_type):
        """Return the journal ID based on the accrual type."""
        journal = False
        if accrual_type == 'annual_leave':
            journal = self.env['account.journal'].search([('show_accrual_leave_accounts', '=', True)], limit=1)
        elif accrual_type == 'annual_tickets':
            journal = self.env['account.journal'].search([('show_accrual_ticket_accounts', '=', True)], limit=1)
        return journal.id if journal else False


class EmployeeAccrualLine(models.Model):
    _name = 'employee.accrual.line'
    _description = 'Employee Accrual Line'

    accrual_id = fields.Many2one('employee.accrual', string='Accrual Reference')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    contract_id = fields.Many2one('hr.contract', string='Contract')
    accrual_type = fields.Selection([
        ('annual_leave', 'Annual Leave'),
        ('annual_tickets', 'Annual Tickets'),
    ], related='accrual_id.accrual_type', string='Accrual Type', store=True)
    accrual_calculation = fields.Selection(string="Calculate Based On",
                                           selection=[('wage', 'Wage'),
                                                      ('hra', 'HRA'),
                                                      ('wage_trv', 'Basic + Transport'),
                                                      ('hra_trv', 'HRA + Transport'),
                                                      ('wage_tr_fd','Basic + Transport + Food'),
                                                      ('hr_tr_sch', 'HRA + Transport + School'),
                                                      ('hr_tr_fd', 'HRA + Transport + Food'),
                                                      ('hr_tr_fl', 'HRA + Transport + Fuel'),
                                                      ('hr_tr_tk', 'HRA + Transport + Ticket'),
                                                      ('hr_tr_fx', 'HRA + Transport + Fixed'),
                                                      ('hr_tr_mb', 'HRA + Transport + Mobile'),
                                                      ('hr_tr_oth', 'HRA + Transport + Other'),
                                                      ('hr_tr_wk', 'HRA + Transport + Work'), ('all', 'All')],
                                           related='accrual_id.accrual_calculation', store=True)

    accrual_days = fields.Float(string='Accrual Days', compute='_compute_accrual_days')
    entitlement_days = fields.Float(string='Entitlement', compute='_compute_accrual_days')
    entitlement_amount = fields.Float(string='Entitlement Amount', compute='_compute_accrual_amount')
    accrual_amount = fields.Float(string='Accrual Amount', compute='_compute_accrual_amount')
    ticket_entitlement = fields.Float(string='Ticket Entitlement')
    ticket_accrual = fields.Float(string='Ticket Accrual', compute='_compute_ticket_accrual')
    ticket_entitlement_amount = fields.Float(string='Ticket Entitlement Amount')
    ticket_accrual_amount = fields.Float(string='Ticket Accrual amount', compute='_compute_ticket_accrual')
    analytical_code = fields.Many2one('account.analytic.account', string='Analytical Code', compute='_compute_analytical_code')
    status = fields.Selection(related='accrual_id.status', string='Status')
    account_move_id = fields.Many2one('account.move', string='Account Moves')

    # @api.depends('employee_id', 'accrual_type', 'accrual_id')
    # def _compute_accrual_days(self):
    #     for line in self:
    #         # Initialize the accrual days and entitlement days to 0.0
    #         line.accrual_days = 0.0
    #         line.entitlement_days = 0.0
    #
    #         # Get the employee's entitlement if the employee exists
    #         entitlement = line.employee_id.entitlement if line.employee_id else 0.00
    #
    #         if line.accrual_id and line.employee_id and line.employee_id.joining_date:
    #             # Check if employee's joining_date is within the accrual period
    #             # hr_leave_allocation = self.env['hr.leave.allocation'].search('employee_id', '=', line.employee_id)
    #
    #             accrual_plans = self.env['hr.leave.accrual.plan'].search([])
    #             added_value = 0.00
    #             for plan in accrual_plans:
    #                 for leave in plan.level_ids[0]:
    #                     added_value = leave.added_value
    #             if line.accrual_id.date_from <= line.employee_id.joining_date <= line.accrual_id.date_to:
    #                 # Calculate the accrual days as the difference between date_to and joining_date
    #                 accrual_days = (line.accrual_id.date_to - line.employee_id.joining_date).days + 1
    #                 month_end_date = line.accrual_id.date_to.day
    #                 print("accrual_days", accrual_days, month_end_date)
    #                 # line.accrual_days = accrual_days / entitlement
    #                 line.accrual_days = (accrual_days * added_value) / month_end_date
    #                 line.entitlement_days = entitlement
    #             else:
    #                 # Normal accrual calculation if joining date is outside the range
    #                 if line.accrual_type == 'annual_leave' and entitlement:
    #                     line.accrual_days = (entitlement / 12)
    #                 line.entitlement_days = entitlement
    #
    #             if line.accrual_id.date_from <= line.employee_id.exit_date <= line.accrual_id.date_to:
    #                 # Calculate the accrual days as the difference between date_to and joining_date
    #                 accrual_days = (line.employee_id.exit_date - line.accrual_id.date_from).days + 1
    #                 month_end_date = line.accrual_id.date_to.day
    #                 print("accrual_days", accrual_days, month_end_date)
    #                 # line.accrual_days = accrual_days / entitlement
    #                 line.accrual_days = (accrual_days * added_value) / month_end_date
    #                 line.entitlement_days = entitlement
    #
    #             else:
    #                 # Normal accrual calculation if joining date is outside the range
    #                 if line.accrual_type == 'annual_leave' and entitlement:
    #                     line.accrual_days = (entitlement / 12)
    #                 line.entitlement_days = entitlement
    #
    #         else:
    #             # Normal accrual calculation if joining date condition isn't met
    #             if line.accrual_type == 'annual_leave' and entitlement:
    #                 line.accrual_days = (entitlement / 12)
    #             line.entitlement_days = entitlement

    @api.depends('employee_id', 'accrual_type', 'accrual_id')
    def _compute_accrual_days(self):
        for line in self:
            # Initialize the accrual days and entitlement days to 0.0
            line.accrual_days = 0.0
            line.entitlement_days = 0.0

            # Get the employee's entitlement if the employee exists
            entitlement = line.employee_id.entitlement if line.employee_id else 0.00

            # Ensure we have accrual, employee, and joining_date to proceed
            if line.accrual_id and line.employee_id and line.employee_id.joining_date:

                # Search for the accrual plans
                accrual_plans = self.env['hr.leave.accrual.plan'].search([])
                added_value = 0.00

                # Get the added value from the first level of accrual plans
                for plan in accrual_plans:
                    for leave in plan.level_ids[:1]:
                        added_value = leave.added_value  # Assuming you want the first record's added value

                # If the joining date is within the accrual date range
                if line.accrual_id.date_from <= line.employee_id.joining_date <= line.accrual_id.date_to:
                    # Calculate accrual days as the difference between date_to and joining_date
                    accrual_days = (line.accrual_id.date_to - line.employee_id.joining_date).days + 1
                    month_end_date = line.accrual_id.date_to.day
                    # Accrual calculation based on added value
                    line.accrual_days = (accrual_days * added_value) / month_end_date
                    line.entitlement_days = entitlement
                else:
                    # Normal accrual calculation if joining date is outside the range
                    if line.accrual_type == 'annual_leave' and entitlement:
                        line.accrual_days = entitlement / 12
                    line.entitlement_days = entitlement

                # If exit date is within the accrual period
                if line.employee_id.exit_date and line.accrual_id.date_from <= line.employee_id.exit_date <= line.accrual_id.date_to:
                    # Calculate accrual days as the difference between exit_date and date_from
                    accrual_days = (line.employee_id.exit_date - line.accrual_id.date_from).days + 1
                    month_end_date = line.accrual_id.date_to.day
                    # Accrual calculation based on added value
                    line.accrual_days = (accrual_days * added_value) / month_end_date
                    line.entitlement_days = entitlement

            # Normal accrual calculation if joining date or exit date conditions aren't met
            else:
                if line.accrual_type == 'annual_leave' and entitlement:
                    line.accrual_days = entitlement / 12
                line.entitlement_days = entitlement

    # @api.depends('employee_id', 'accrual_type')
    # def _compute_accrual_days(self):
    #     for line in self:
    #         # Initialize values
    #         line.accrual_days = 0.0
    #         line.entitlement_days = 0.0
    #
    #         # Get the employee's entitlement
    #         entitlement = line.employee_id.entitlement if line.employee_id else 0.00
    #
    #         # Different accrual days based on accrual_type
    #         if line.accrual_type == 'annual_leave':
    #             line.accrual_days = (entitlement / 12) if entitlement else 0.00
    #             line.entitlement_days = entitlement
    #         else:
    #             line.accrual_days = 0.0
    #             line.entitlement_days = 0.0

    # @api.depends('employee_id', 'accrual_type')
    # def _compute_accrual_amount(self):
    #     for line in self:
    #         line.entitlement_amount = 0.00
    #         line.accrual_amount = 0.00
    #         allowance = 0.00
    #         if line.employee_id.contract_id:
    #             allowance = line.employee_id.contract_id.wage + line.employee_id.contract_id.transport_allowance
    #         if line.accrual_type == 'annual_leave':
    #             line.entitlement_amount = (line.employee_id.entitlement * allowance) / 30
    #             line.accrual_amount = (line.accrual_days * allowance) / 30 if line.accrual_days and allowance else 0.00
    #         else:
    #             line.entitlement_amount = 0.00
    #             line.accrual_amount = 0.00

    @api.depends('employee_id', 'accrual_type')
    def _compute_accrual_amount(self):
        for line in self:
            line.entitlement_amount = 0.00
            line.accrual_amount = 0.00
            allowance = 0.00
            entitlement_amount = 0.00
            no_of_days = 30

            if line.employee_id.contract_id:
                # Base calculations depending on the accrual type
                base_salary = line.employee_id.contract_id.wage
                transport_allowance = line.employee_id.contract_id.transport_allowance or 0.00
                house_allowance = line.employee_id.contract_id.house_allowance or 0.00
                school_allowance = line.employee_id.contract_id.school_allowance or 0.00
                food_allowance = line.employee_id.contract_id.food_allowance or 0.00
                fuel_allowance = line.employee_id.contract_id.fuel_allowance or 0.00
                ticket_allowance = line.employee_id.contract_id.ticket_allowance or 0.00
                fixed_allowance = line.employee_id.contract_id.fixed_allowance or 0.00
                mobile_allowance = line.employee_id.contract_id.mobile_allowance or 0.00
                work_allowance = line.employee_id.contract_id.work_allowance or 0.00
                housing_allowance = line.employee_id.contract_id.housing_allowance or 0.00

                rate = line.accrual_id.accrual_calculation_id.rate / 100
                accrual_days = line.accrual_days or 0.00
                entitlement_days = line.employee_id.entitlement or 0.00

                # Determine the allowance based on accrual calculation type
                if line.accrual_calculation == 'wage':
                    allowance = (base_salary * accrual_days / no_of_days * rate)
                    entitlement_amount = (base_salary * entitlement_days / no_of_days * rate)
                elif line.accrual_calculation == 'wage_trv':
                    allowance = ((base_salary + transport_allowance) * accrual_days / no_of_days * rate)
                    entitlement_amount = ((base_salary + transport_allowance) * entitlement_days / no_of_days * rate)
                elif line.accrual_calculation == 'hra':
                    allowance = ((base_salary + house_allowance) * accrual_days / no_of_days * rate)
                    entitlement_amount = ((base_salary + house_allowance) * entitlement_days / no_of_days * rate)
                elif line.accrual_calculation == 'hra_trv':
                    allowance = ((
                                             base_salary + house_allowance + transport_allowance) * accrual_days / no_of_days * rate)
                    entitlement_amount = ((
                                                      base_salary + house_allowance + transport_allowance) * entitlement_days / no_of_days * rate)
                elif line.accrual_calculation == 'hr_tr_sch':
                    allowance = ((
                                             base_salary + house_allowance + transport_allowance + school_allowance) * accrual_days / no_of_days * rate)
                    entitlement_amount = ((
                                                      base_salary + house_allowance + transport_allowance + school_allowance) * entitlement_days / no_of_days * rate)
                
                elif line.accrual_calculation == 'wage_tr_fd':
                    allowance = ((
                                             base_salary + food_allowance + transport_allowance ) * accrual_days / no_of_days * rate)
                    entitlement_amount = ((
                                                      base_salary + food_allowance + transport_allowance ) * entitlement_days / no_of_days * rate)
                
                
                elif line.accrual_calculation == 'hr_tr_fd':
                    allowance = ((
                                             base_salary + house_allowance + transport_allowance + food_allowance) * accrual_days / no_of_days * rate)
                    entitlement_amount = ((
                                                      base_salary + house_allowance + transport_allowance + food_allowance) * entitlement_days / no_of_days * rate)
                elif line.accrual_calculation == 'hr_tr_fl':
                    allowance = ((
                                             base_salary + house_allowance + transport_allowance + fuel_allowance) * accrual_days / no_of_days * rate)
                    entitlement_amount = ((
                                                      base_salary + house_allowance + transport_allowance + fuel_allowance) * entitlement_days / no_of_days * rate)
                elif line.accrual_calculation == 'hr_tr_tk':
                    allowance = ((
                                             base_salary + house_allowance + transport_allowance + ticket_allowance) * accrual_days / no_of_days * rate)
                    entitlement_amount = ((
                                                      base_salary + house_allowance + transport_allowance + ticket_allowance) * entitlement_days / no_of_days * rate)
                elif line.accrual_calculation == 'hr_tr_fx':
                    allowance = ((
                                             base_salary + house_allowance + transport_allowance + fixed_allowance) * accrual_days / no_of_days * rate)
                    entitlement_amount = ((
                                                      base_salary + house_allowance + transport_allowance + fixed_allowance) * entitlement_days / no_of_days * rate)
                elif line.accrual_calculation == 'hr_tr_mb':
                    allowance = ((
                                             base_salary + house_allowance + transport_allowance + mobile_allowance) * accrual_days / no_of_days * rate)
                    entitlement_amount = ((
                                                      base_salary + house_allowance + transport_allowance + mobile_allowance) * entitlement_days / no_of_days * rate)
                elif line.accrual_calculation == 'hr_tr_wk':
                    allowance = ((
                                             base_salary + house_allowance + transport_allowance + work_allowance) * accrual_days / no_of_days * rate)
                    entitlement_amount = ((
                                                      base_salary + house_allowance + transport_allowance + work_allowance) * entitlement_days / no_of_days * rate)
                elif line.accrual_calculation == 'hr_tr_oth':
                    allowance = ((
                                             base_salary + house_allowance + transport_allowance + housing_allowance) * accrual_days / no_of_days * rate)
                    entitlement_amount = ((
                                                      base_salary + house_allowance + transport_allowance + housing_allowance) * entitlement_days / no_of_days * rate)
                elif line.accrual_calculation == 'all':
                    allowance = (
                            (base_salary + house_allowance + transport_allowance + school_allowance +
                             food_allowance + fuel_allowance + ticket_allowance + fixed_allowance +
                             mobile_allowance + work_allowance + housing_allowance)
                            * accrual_days / no_of_days * rate
                    )
                    entitlement_amount = (
                            (base_salary + house_allowance + transport_allowance + school_allowance +
                             food_allowance + fuel_allowance + ticket_allowance + fixed_allowance +
                             mobile_allowance + work_allowance + housing_allowance)
                            * entitlement_days / no_of_days * rate
                    )

                # Assign allowance and entitlement_amount directly
                # line.accrual_amount = allowance
                # line.entitlement_amount = entitlement_amount

                # Calculate entitlement amount if accrual type is 'annual_leave'
            if line.accrual_type == 'annual_leave':
                line.accrual_amount = allowance
                line.entitlement_amount = entitlement_amount
            else:
                line.entitlement_amount = 0.00
                line.accrual_amount = 0.00

    @api.depends('ticket_entitlement', 'accrual_type')
    def _compute_ticket_accrual(self):
        for line in self:
            line.ticket_accrual = 0.0
            line.ticket_accrual_amount = 0.0
            if line.accrual_type == 'annual_tickets':
                line.ticket_accrual = (line.ticket_entitlement * 1) / 12 if line.ticket_entitlement else 0.0
                line.ticket_accrual_amount = (line.ticket_entitlement_amount * 1) / 12 if line.ticket_entitlement_amount else 0.0

    @api.depends('employee_id')
    def _compute_analytical_code(self):
        for line in self:
            line.analytical_code = line.employee_id.contract_id.analytic_account_id.id if line.employee_id.contract_id else False

    # def action_create_accrual_journal_entry(self):
    #     """Create a journal entry for the accrual line based on accrual type."""
    #     for line in self:
    #         accrual_type_display = 'Unknown Type'
    #         credit_account_id = line._get_credit_account_id()  # Ensure this returns an ID
    #         debit_account_id = line._get_debit_account_id()
    #         print("credit_account_id,debit_account_id",credit_account_id,debit_account_id)
    #         # Check if line.accrual_type is set and valid
    #         if line.accrual_type:
    #             # Safely get the display value for accrual_type using the class method
    #             accrual_type_selection = self.fields_get(['accrual_type'])['accrual_type']['selection']
    #             accrual_type_dict = dict(accrual_type_selection)
    #             accrual_type_display = accrual_type_dict.get(line.accrual_type, 'Unknown Type')
    #
    #         amount = 0.00
    #         if line.accrual_type == 'annual_leave':
    #             amount = line.accrual_amount
    #         elif line.accrual_type == 'annual_tickets':
    #             amount = line.ticket_accrual_amount
    #
    #         move_vals = {
    #             'journal_id': self._get_journal_id(line.accrual_type),
    #             'date': line.accrual_id.date_to or fields.Date.today(),
    #             'ref': _('Accrual for %s - %s') % (accrual_type_display, line.employee_id.name),
    #             'line_ids': [(0, 0, {
    #                 'account_id': debit_account_id,
    #                 'name': _('Accrual Debit for %s') % (accrual_type_display),
    #                 'debit': amount,
    #                 'credit': 0.0,
    #             }), (0, 0, {
    #                 'account_id': credit_account_id,
    #                 'name': _('Accrual Credit for %s') % (accrual_type_display),
    #                 'debit': 0.0,
    #                 'credit': amount,
    #             })]
    #         }
    #         print("move_vals", move_vals)
    #
    #         # Create the journal entry
    #         move_id = self.env['account.move'].create(move_vals)
    #         print("move_id", move_id)
    #         line.account_move_id = move_id.id

    # def action_create_accrual_journal_entry(self):
    #     """Create separate journal entries for each employee's accrual."""
    #     for accrual in self.mapped('accrual_id'):
    #         for line in accrual.accrual_line_ids:
    #             # Create individual journal entries for each employee
    #             debit_account_id = line._get_debit_account_id()
    #             credit_account_id = line._get_credit_account_id()
    #
    #             # Ensure we only create entries for valid amounts
    #             if line.accrual_amount > 0 or line.ticket_accrual_amount > 0:
    #                 move_vals = {
    #                     'journal_id': self._get_journal_id(accrual.accrual_type),
    #                     'date': accrual.date_to or fields.Date.today(),
    #                     'ref': _('Accrual for %s - %s') % (line.employee_id.name, accrual.name),
    #                     'line_ids': [
    #                         (0, 0, {
    #                             'account_id': debit_account_id,
    #                             'name': _('Accrual Debit for %s') % (line.employee_id.name),
    #                             'debit': line.accrual_amount + line.ticket_accrual_amount,
    #                             'credit': 0.0,
    #                         }),
    #                         (0, 0, {
    #                             'account_id': credit_account_id,
    #                             'name': _('Accrual Credit for %s') % (line.employee_id.name),
    #                             'debit': 0.0,
    #                             'credit': line.accrual_amount + line.ticket_accrual_amount,
    #                         }),
    #                     ]
    #                 }
    #
    #                 # Create the journal entry
    #                 move_id = self.env['account.move'].create(move_vals)
    #                 line.write({'account_move_id': move_id.id})

    def _get_credit_account_id(self):
        """Return the credit account based on the accrual type by searching for specific account configurations in account.journal."""
        credit_account = False

        if self.accrual_type == 'annual_leave':
            # Search for the journal where accrual leave credit accounts are configured
            journal = self.env['account.journal'].search([('show_accrual_leave_accounts', '=', True)], limit=1)
            if journal:
                credit_account = journal.accrual_leave_credit_account_id.id  # Assuming you have this field in account.journal

        elif self.accrual_type == 'annual_tickets':
            # Search for the journal where accrual ticket credit accounts are configured
            journal = self.env['account.journal'].search([('show_accrual_ticket_accounts', '=', True)], limit=1)
            if journal:
                credit_account = journal.accrual_ticket_credit_account_id.id
                print("credit_account", credit_account)

        return credit_account

    def _get_debit_account_id(self):
        """Return the debit account based on the accrual type by searching for specific account configurations in account.journal."""
        debit_account = False

        if self.accrual_type == 'annual_leave':
            # Search for the journal where accrual leave debit accounts are configured
            journal = self.env['account.journal'].search([('show_accrual_leave_accounts', '=', True)], limit=1)
            if journal:
                debit_account = journal.accrual_leave_debit_account_id.id

        elif self.accrual_type == 'annual_tickets':
            # Search for the journal where accrual ticket debit accounts are configured
            journal = self.env['account.journal'].search([('show_accrual_ticket_accounts', '=', True)], limit=1)
            if journal:
                debit_account = journal.accrual_ticket_debit_account_id.id

        return debit_account

    # def _get_journal_id(self, accrual_type):
    #     """Return the journal ID based on the accrual type."""
    #     journal = False
    #     if accrual_type == 'annual_leave':
    #         # Search for the journal where accrual leave accounts are defined
    #         journal = self.env['account.journal'].search([
    #             ('show_accrual_leave_accounts', '=', True)
    #         ], limit=1)
    #     elif accrual_type == 'annual_tickets':
    #         # Search for the journal where accrual ticket accounts are defined
    #         journal = self.env['account.journal'].search([
    #             ('show_accrual_ticket_accounts', '=', True)
    #         ], limit=1)
    #
    #     return journal.id if journal else False


class MihAuhGratuityLine(models.Model):
    _name = 'mih.auh.gratuity.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'id'
    _description = 'Mih Auh Gratuity Sheet'

    gratuity_id = fields.Many2one('employee.accrual', string='Gratuity Reference')

    custom_type = fields.Selection(
        selection=[
            ('less_than_five_year', 'Less Than 5 Year'),
            ('greater_than_five_year', 'Greater Than 5 Year'),
        ],
        string="Type",
        default='less_than_five_year',
    )
    custom_contract_id = fields.Many2one(
        'hr.contract',
        string='Contract',
        readonly=True
    )
    custom_move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        copy=False
    )
    custom_employee_id = fields.Many2one(
        'hr.employee',
        string='Employee'
    )
    custom_date_of_join = fields.Date(
        string="Contract Start Date",
    )
    custom_late_working_day = fields.Date(
        string="Accrual Month Date",
    )
    no_of_days = fields.Float(
        string='No of Days',
        compute='_compute_no_of_days'
    )
    custom_lop = fields.Float(
        string='LOP'
    )
    custom_eligible_days = fields.Float(
        string='Eligible Days',
        compute='_compute_eligible_days'
    )
    eligible_days_f_five_years = fields.Float(
        string='Eligible days for first 5 years',
        compute='_compute_eligible_days_f_five_years'
    )
    eligible_days_a_five_years = fields.Float(
        string='Eligible days for after 5 Years',
        compute='_compute_eligible_days_a_five_years'
    )
    esob_days = fields.Float(
        string='EOSB for 1st 5 year Amount',
        # string='EOSB for 1825 days(for 1st 5 year)',
        compute='_compute_esob_days',
    )
    esob_a_days = fields.Float(
        # string='EOSB for 1825 days(After 5 year)',
        string='EOSB for After 5 year Amount',
        compute='_compute_esob_a_days',
    )
    custom_esob_days_sum = fields.Float(
        # string='EOSB Days',
        string='EOSB Amount',
        compute='_compute_esob_days_sum'
    )
    custom_basic_salary = fields.Float(
        string='Basic Salary'
    )
    custom_allowance = fields.Float(
        string='Allowance', compute='_compute_total_deserved_amount'
    )
    custom_net_salary = fields.Float(
        stirng='Net Salary',
        compute='_compute_custom_net_salary'
    )
    custom_per_day_salary = fields.Float(
        stirng='Per Day Salary',
        compute='_compute_custom_per_day_salary'
    )
    custom_esob_amounts = fields.Float(
        # string='EOSB Amount',
        string='Previous month EOSB Amount',
        compute='_compute_custom_esob_amounts',

    )
    custom_partner_id = fields.Many2one(
        'res.partner',
        string="Partner",
    )
    custom_debit_account_id = fields.Many2one(
        'account.account',
        string='Debit Account',
    )
    custom_credit_account_id = fields.Many2one(
        'account.account',
        string='Credit Account',
    )
    custom_journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        copy=False
    )
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True, copy=False,
    )
    created_date = fields.Date(
        string='Created Date',
        default=fields.Date.today(),
        readonly=True,
    )
    currency_id = fields.Many2one('res.currency',
                                  string='Currency',
                                  default=lambda self: self.env.user.company_id.currency_id,
                                  required=True,
                                  readonly=True,
                                  )
    internal_note = fields.Text(
        string='Internal Notes',
        copy=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('lock', 'Locked'),
    ],
        string="Status",
        default='draft',
        track_visibility='onchange',
        required=True,
        copy=False
    )
    # status = fields.Selection(related='gratuity_id.status', string='Status')
    current_month_amt = fields.Float(string="Current Month Accrual Amount", compute='_compute_current_month_amt')
    total_esob_amount = fields.Float(string="End of Service Award (EOS) Amount",
                                     compute='_compute_total_deserved_amount')
    service_period = fields.Float(string="Service Period In Years", compute='_compute_period', store=True)
    years = fields.Integer(string="Years", compute='_compute_period', store=True, invisible=True)
    months = fields.Integer(string="Months", compute='_compute_period', store=True, invisible=True)
    days = fields.Integer(string="Days", compute='_compute_period', store=True, invisible=True, )
    current_last_amt = fields.Float(string="Current-Last Month Amount",)
    first_5_years = fields.Float(
        string='First Five year',
        compute='_compute_five_years_split_period',

    )
    after_5_years = fields.Float(
        string='Ater Five Years',
        compute='_compute_five_years_split_period',

    )

    @api.depends('service_period')
    def _compute_five_years_split_period(self):
        for record in self:
            record.first_5_years = 0.00
            record.after_5_years = 0.00
            if record.service_period:
                if record.service_period > 5:
                    record.after_5_years = round(record.service_period - 5, 2)
                    record.first_5_years = 5




    @api.depends('custom_esob_amounts', 'custom_employee_id', 'custom_late_working_day')
    def _compute_current_month_amt(self):
        for rec in self:
            rec.current_month_amt = 0.00
            amount = 0.00
            amount = rec.custom_esob_days_sum - rec.custom_esob_amounts
            rec.current_month_amt = amount
            # rec_b = self.env['mih.auh.gratuity.line'].search(
            #     [('id', '!=', rec.id), ('custom_late_working_day', '<', rec.custom_late_working_day),
            #      ('custom_employee_id', '=', rec.custom_employee_id.id)], order='custom_late_working_day desc',
            #     limit=1)  # Another record
            # rec_emp_b = self.env['hr.employee'].search(
            #     [('id', '=', rec.custom_employee_id.id), ('eos_accrued_date', '<', rec.custom_late_working_day)],
            #     order='eos_accrued_date desc', limit=1)
            # rec_emp = self.env['hr.employee'].search([('id', '=', rec.custom_employee_id.id)])
            #
            # rec.current_month_amt = rec.custom_esob_amounts
            # for emp in rec_emp_b:
            #     rec_emp.previous_eos_amount = emp.eos_amount
            #     if rec_b.current_month_amt:
            #         rec_b.current_month_amt = emp.eos_amount - emp.previous_eos_amount
            #         rec.update({'current_month_amt': rec_b.current_month_amt})

    @api.depends('custom_date_of_join', 'custom_late_working_day')
    def _compute_period(self):
        for record in self:
            if record.custom_date_of_join:
                joining_date = record.custom_date_of_join
                # ending_date = record.custom_late_working_day
                period_days = relativedelta(record.custom_late_working_day, joining_date)
                record.years = period_days.years
                record.months = period_days.months
                record.days = period_days.days
                period = period_days.years + (period_days.months / 12.0) + (period_days.days / 365.0)
                record.service_period = period

    @api.depends('custom_employee_id', 'custom_esob_days_sum')
    def _compute_total_deserved_amount(self):
        for record in self:
            record.total_esob_amount = 0.00
            contract_id = self.env['hr.contract'].search(
                [('employee_id', '=', record.custom_employee_id.id)],
                limit=1, order='id desc')

            gosi = 0
            hra = 0
            service_period = round(record.service_period, 2)
            deserved_for_first_five = 5
            deserved_for_half_year = 0.5
            deserved_for_one_year = 1
            deserved_after_five_year_months = 1
            amount_allowance = 0
            # total_ticket=record.total_ticket
            if contract_id:
                wage = contract_id.wage

                record.custom_allowance = contract_id.custom_allowance
                amount_allowance = record.custom_allowance
                if record.custom_employee_id.is_saudi:
                    gosi = (wage + hra) * 0.0975

                total = 0.0

                # if deserved_for_first_five <= service_period:
                residual = service_period
                total_taken_years = 0

                if residual < deserved_for_half_year or residual < deserved_for_one_year:
                    total += round(deserved_for_half_year, 2) * (deserved_for_half_year - total_taken_years) * (
                            wage + amount_allowance - gosi)
                    total_taken_years = deserved_for_first_five
                    residual = service_period - deserved_for_first_five
                elif residual > deserved_for_first_five - total_taken_years or residual > deserved_for_one_year:
                    total += round(deserved_after_five_year_months, 2) * round(residual, 2) * (
                            wage + amount_allowance - gosi)
                    total_taken_years += residual
                    residual = 0.0
                # other_amount = record.other_amount if record.type == 'ending_service' else 0
                record.total_esob_amount = total
                record.update({'total_esob_amount': record.total_esob_amount})

    def show_custom_journal_entries(self):
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['domain'] = [('id', '=', self.custom_move_id.id)]
        return action

    def action_lock(self):
        custom_employee_eos = self.env['hr.employee'].search([('id', '=', self.custom_employee_id.id)])
        rec_emp_b = self.env['hr.employee'].search(
            [('id', '=', self.custom_employee_id.id)],
            order='id desc', limit=1)

        for emp in rec_emp_b:
            custom_employee_eos.previous_eos_amount = emp.eos_amount
            eos_vals = {
                'eos_amount': self.custom_esob_days_sum,
                'eos_accrued_date': self.custom_late_working_day,
                'previous_eos_amount': custom_employee_eos.previous_eos_amount,
            }
            custom_employee_eos.write(eos_vals)
            print("custom_employee_eos, ", custom_employee_eos)

        return self.write({'state': 'lock'})

    def action_unlock(self):
        return self.write({'state': 'draft'})

    def unlink(self):
        for rec in self:
            if rec.state == 'lock':
                raise UserError(_('You can not delete EOS Accruals Line Which is locked.'))
        return super(MihAuhGratuityLine, self).unlink()

    @api.onchange('custom_employee_id')
    def onchange_custom_employee_id(self):
        for rec in self:
            rec.custom_date_of_join = rec.custom_employee_id.joining_date

    @api.depends('custom_type', 'custom_late_working_day', 'custom_date_of_join')
    def _compute_no_of_days(self):
        for rec in self:
            rec.no_of_days = 0
            if rec.custom_type == 'less_than_five_year':
                if rec.custom_late_working_day and rec.custom_date_of_join:
                    rec.no_of_days = (rec.custom_late_working_day - rec.custom_date_of_join).days + 1
                else:
                    pass
            else:
                if rec.custom_late_working_day and rec.custom_date_of_join:
                    rec.no_of_days = (rec.custom_late_working_day - rec.custom_date_of_join).days + 1
                else:
                    pass

    @api.depends('custom_type', 'no_of_days', 'custom_lop')
    def _compute_eligible_days(self):
        for rec in self:
            if rec.custom_type == 'less_than_five_year':
                rec.custom_eligible_days = rec.no_of_days - rec.custom_lop
            else:
                rec.custom_eligible_days = rec.no_of_days - rec.custom_lop

    @api.depends('custom_eligible_days', 'eligible_days_f_five_years', 'custom_type')
    def _compute_eligible_days_f_five_years(self):
        for rec in self:
            if rec.custom_type == 'less_than_five_year':
                if rec.custom_eligible_days >= 1825:
                    rec.eligible_days_f_five_years = 1825

                elif rec.custom_eligible_days < (rec.custom_eligible_days):
                    rec.eligible_days_f_five_years = rec.custom_eligible_days
                else:
                    rec.eligible_days_f_five_years = rec.custom_eligible_days
            else:
                if rec.custom_eligible_days >= 1825:
                    rec.eligible_days_f_five_years = 1825
                else:
                    rec.eligible_days_f_five_years = 0

    @api.depends('custom_eligible_days', 'eligible_days_a_five_years', 'custom_type')
    def _compute_eligible_days_a_five_years(self):
        for rec in self:
            if rec.custom_type == 'less_than_five_year':
                ced = (rec.custom_eligible_days * 5)
                if rec.custom_eligible_days > ced:
                    rec.eligible_days_a_five_years = rec.custom_eligible_days - ced
                else:
                    rec.eligible_days_a_five_years = 0
            else:
                ced = (rec.custom_eligible_days)
                if rec.custom_eligible_days > 1825:
                    rec.eligible_days_a_five_years = rec.custom_eligible_days - 1825
                else:
                    rec.eligible_days_a_five_years = 0

    @api.depends('custom_type', 'custom_eligible_days', 'eligible_days_f_five_years')
    def _compute_esob_days(self):
        for rec in self:
            if rec.custom_type == 'less_than_five_year':
                # esob_days = (rec.custom_eligible_days * 15) / 365
                esob_days = (rec.custom_basic_salary * rec.service_period *0.5)
                rec.esob_days = float_round(esob_days, 2)
            else:
                # esob_days_f = (rec.eligible_days_f_five_years * 15) / 365
                esob_days_f = (rec.custom_basic_salary * rec.first_5_years *0.5)
                rec.esob_days = float_round(esob_days_f, 2)

    @api.depends('custom_type', 'eligible_days_a_five_years')
    def _compute_esob_a_days(self):
        for rec in self:
            if rec.custom_type == 'less_than_five_year':
                rec.esob_a_days = float_round((rec.eligible_days_a_five_years * 30) / 365, 2)
            else:
                # rec.esob_a_days = float_round((rec.eligible_days_a_five_years * 30) / 365, 2)
                rec.esob_a_days = rec.custom_basic_salary * 1 * rec.after_5_years
                print('rec.esob_a_days, ', rec.esob_a_days, rec.custom_basic_salary, rec.after_5_years)

    @api.depends('custom_type', 'esob_days', 'esob_a_days')
    def _compute_esob_days_sum(self):
        for rec in self:
            if rec.custom_type == 'less_than_five_year':
                rec.custom_esob_days_sum = rec.esob_days + rec.esob_a_days
            else:
                rec.custom_esob_days_sum = rec.esob_days + rec.esob_a_days

    @api.depends('custom_type', 'custom_basic_salary', 'custom_allowance')
    def _compute_custom_net_salary(self):
        for rec in self:
            if rec.custom_type == 'less_than_five_year':
                rec.custom_net_salary = rec.custom_basic_salary + rec.custom_allowance
            else:
                rec.custom_net_salary = rec.custom_basic_salary + rec.custom_allowance

    @api.depends('custom_type', 'custom_basic_salary')
    def _compute_custom_per_day_salary(self):
        for rec in self:
            if rec.custom_type == 'less_than_five_year':
                rec.custom_per_day_salary = (rec.custom_basic_salary * 12) / 360
            else:
                rec.custom_per_day_salary = (rec.custom_basic_salary * 12) / 360

    # @api.depends('custom_type', 'custom_per_day_salary', 'custom_esob_days_sum')
    # def _compute_custom_esob_amounts(self):
    #     for rec in self:
    #         if rec.custom_type == 'less_than_five_year':
    #             custom_esob_amounts = rec.custom_per_day_salary * rec.custom_esob_days_sum
    #             rec.custom_esob_amounts = float("{:.2f}".format(custom_esob_amounts))
    #
    #         else:
    #             custom_esob_amounts = rec.custom_per_day_salary * rec.custom_esob_days_sum
    #             rec.custom_esob_amounts = float("{:.2f}".format(custom_esob_amounts))

    @api.depends('custom_type', 'custom_per_day_salary', 'custom_esob_days_sum')
    def _compute_custom_esob_amounts(self):
        for rec in self:
            total_eosb = 0.0  # Initialize total for previous amounts

            if rec.gratuity_id and rec.gratuity_id.date_from:
                # Calculate the first and last days of the previous month
                current_date = rec.gratuity_id.date_from
                previous_month_start = (current_date + relativedelta(day=1, months=-1))
                previous_month_end = (current_date + relativedelta(day=31, months=-1))

                print("Previous month start:", previous_month_start)
                print("Previous month end:", previous_month_end)

                # Fetch approved accrual records within the previous month
                approved_accruals = self.env['employee.accrual'].search([
                    ('status', '=', 'approved'),
                    ('accrual_type', '=', 'gratuity'),
                    ('date_from', '>=', previous_month_start),
                    ('date_from', '<=', previous_month_end)
                ])

                # Sum up the `custom_esob_days_sum` for matching records
                for accrual in approved_accruals:
                    for line in accrual.gratuity_line_ids:
                        if line.custom_employee_id == rec.custom_employee_id:
                            total_eosb += line.custom_esob_days_sum or 0.0

            # Compute the base amount and assign the final total
            if rec.custom_type == 'less_than_five_year':
                rec.custom_esob_amounts = total_eosb
            else:
                # Add any additional calculation logic if needed
                # base_amount = (
                #             rec.custom_per_day_salary * rec.custom_esob_days_sum) if rec.custom_per_day_salary and rec.custom_esob_days_sum else 0.0
                rec.custom_esob_amounts = total_eosb











