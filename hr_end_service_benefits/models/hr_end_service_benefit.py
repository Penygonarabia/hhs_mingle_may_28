# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo import tools, _
import time

class HREndServiceBenifits(models.Model):
    _name = 'hr.end.service.benefit'
    _description = 'Employee End Of Service Benefits'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    @api.constrains('total_taken_amount', 'amount')
    def _check_amounts(self):
        for record in self:
            diff = record.total_deserved_amount - record.total_taken_amount
    
    '''Newly added because gosi is want or not from res config settings they want on sept 11 2024'''
    @api.model 
    def _get_gosi_from_settings(self):
        gosi_bool = self.env['ir.config_parameter'].sudo().get_param('hr_end_service_benefits.gosi_for_exit_bool')       
        return gosi_bool      

    @api.model
    def _get_gosi_amount(self):
        gosi_amount = float(self.env['ir.config_parameter'].sudo().get_param('hr_end_service_benefits.gosi_amount'))
        return gosi_amount
        

    @api.constrains('date')
    def unique_end_service_benefit_date_per_employee(self):
        """Constraint to prevent create 2 end service benefits at the same day for them same employee"""
        for record in self:
            if record.date:
                end_service_benefit_ids = self.env['hr.end.service.benefit'].search(
                    [('employee_id', '=', record.employee_id.id), ('date', '=', record.date),
                     ('state', 'not in', ['cancel'])])
                if len(end_service_benefit_ids) > 1:
                    raise ValidationError(_('Employee has another end service benefit that date'))

    # @api.constrains('total_deserved_amount')
    # def _check_total_deserved_amount(self):
    #     for record in self:
    #         if record.total_deserved_amount == 0:
    #             raise ValidationError(record.end_service_benefit_type_id.zero_message)

    def _default_employee(self):
        """:returns current logged in employee using configured employee"""
        return self.env.context.get('default_employee_id') or self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)

    @api.depends('joining_date', 'date')
    def _compute_period(self):
        for record in self:
            if record.joining_date:
                joining_date = record.joining_date
                period_days = relativedelta(record.date, joining_date)
                record.years = period_days.years
                record.months = period_days.months
                record.days = period_days.days
                period = period_days.years + (period_days.months / 12.0) + (period_days.days / 365.0)
                record.service_period = period

    @api.depends('employee_id', 'service_period', 'end_service_benefit_type_id', 'date',
                 'total_holiday_deserved_amount', 'type', 'payment_type', 'other_amount', 'allowance_line_ids')
    def _compute_total_deserved_amount(self):
        for record in self:
            contract_id = self.env['hr.contract'].search(
                [('employee_id', '=', record.employee_id.id), ('state', '=', 'exit')],
                limit=1, order='id desc')
            gosi = 0
            hra = 0
            # total_ticket=record.total_ticket
            if contract_id:
                wage = contract_id.wage
                amount_allowance = 0
                if record.payment_type == 'wage_allowance':
                    for all in self.allowance_line_ids:
                        amount_allowance = amount_allowance + all.fix_amount
                        if all.allowance_id.code == 'HRA':
                            hra = all.fix_amount
                '''Newly added because gosi is want or not from res config settings they want on sept 11 2024'''
                if self._get_gosi_from_settings() == True:
                    if record.employee_id.is_saudi:
                        # gosi = (wage + hra) * self._get_gosi_amount()
                        gosi = (wage + hra) * 0.0975
                        print("gosiiii", gosi, wage, hra)

                    
                    # if record.employee_id.is_saudi:
                    #     gosi = (wage + hra) * 0.0975    
                total = 0.0

                service_period = record.years + (record.months / 12.0) + (record.days / 365.0)
                print("service_period", service_period)
                if record.end_service_benefit_type_id.deserved_after <= service_period:
                    residual = service_period
                    total_taken_years = 0
                    for line in record.end_service_benefit_type_id.line_ids:
                        if residual > line.deserved_for - total_taken_years:
                            total += round(line.deserved_months, 2) * (line.deserved_for - total_taken_years) * (
                                wage + amount_allowance - gosi)
                            total_taken_years = line.deserved_for
                            residual = service_period - line.deserved_for
                        else:
                            total += round(line.deserved_months, 2) * round(residual, 2) * (wage + amount_allowance - gosi)
                            total_taken_years += residual
                            
                            residual = 0.0
                other_amount = record.other_amount if record.type == 'ending_service' else 0
                # record.total_deserved_amount = (total + (record.total_holiday_deserved_amount or 0) + other_amount)
                record.total_deserved_amount = (total + other_amount)


    @api.depends('employee_id', 'holiday_line_ids', 'holiday_line_ids.remaining_leaves', 'type', 'payment_type','allowance_line_ids')
    def _compute_total_holiday_deserved_amount(self):
        for record in self:
            total = 0.0
            gosi = 0
            hra = 0
            if record.type == 'ending_service':
                contract_id = self.env['hr.contract'].search(
                    [('employee_id', '=', record.employee_id.id), ('state', '=', 'exit')],
                    limit=1, order='id desc')
                if contract_id:
                    # wage = contract_id.wage
                    wage = contract_id.wage
                    #if contract_id.net_payment == 0:
                        # raise("P")
                       # raise ValidationError(_('Please Add Net saalry in Employee'))
                    allowances = 0
                    amount_allowance = 0
                    if record.payment_type == 'wage_allowance':
                        amount_allowance = 0
                        for all in self.allowance_line_ids:
                                amount_allowance = amount_allowance + all.fix_amount
                                if all.allowance_id.code == 'HRA':
                                    hra = all.fix_amount
                        '''Newly added because gosi is want or not from res config settings they want on sept 11 2024'''
                        if self._get_gosi_from_settings() == True:
                            if record.employee_id.is_saudi:
                                gosi = (wage + hra) * 0.0975
                                # gosi = (wage + hra) * self._get_gosi_amount()

                        # if record.employee_id.is_saudi:
                        #     gosi = (wage + hra) * 0.0975            
                    # for line in record.holiday_line_ids:
                    #     if line.pay:
                        # total += record.employee_id.accrued_leave_num_of_days * ((wage + amount_allowance - gosi) / 30)
                        # total += record.employee_id.accrued_leave_num_of_days_end_of_service * ((wage + record.employee_id.contract_id.house_allowance - gosi) / 30)

                            # total += line.remaining_leaves * ((wage + amount_allowance - gosi) / 30)
                # record.total_holiday_deserved_amount = total
                        if record.employee_id.contract_id:
                            # Base calculations depending on the accrual type
                            base_salary = record.employee_id.contract_id.wage
                            transport_allowance = record.employee_id.contract_id.transport_allowance or 0.00
                            house_allowance = record.employee_id.contract_id.house_allowance or 0.00
                            school_allowance = record.employee_id.contract_id.school_allowance or 0.00
                            food_allowance = record.employee_id.contract_id.food_allowance or 0.00
                            fuel_allowance = record.employee_id.contract_id.fuel_allowance or 0.00
                            ticket_allowance = record.employee_id.contract_id.ticket_allowance or 0.00
                            fixed_allowance = record.employee_id.contract_id.fixed_allowance or 0.00
                            mobile_allowance = record.employee_id.contract_id.mobile_allowance or 0.00
                            work_allowance = record.employee_id.contract_id.work_allowance or 0.00
                            housing_allowance = record.employee_id.contract_id.housing_allowance or 0.00

                            # rate = record.accrual_id.accrual_calculation_id.rate / 100
                            # accrual_days = record.accrual_days or 0.00
                            # entitlement_days = record.employee_id.entitlement or 0.00

                            # Determine the allowance based on accrual calculation type
                            if record.accrual_calculation_eos == 'wage':
                                total += record.employee_id.accrued_leave_num_of_days_end_of_service * ((base_salary - gosi) / 30)

                            elif record.accrual_calculation_eos == 'wage_trv':
                                total += record.employee_id.accrued_leave_num_of_days_end_of_service * ((base_salary + transport_allowance - gosi) / 30)

                            elif record.accrual_calculation_eos == 'hra':
                                total += record.employee_id.accrued_leave_num_of_days_end_of_service * ((base_salary + house_allowance - gosi) / 30)

                            elif record.accrual_calculation_eos == 'hra_trv':
                                total += record.employee_id.accrued_leave_num_of_days_end_of_service * ((base_salary + house_allowance + transport_allowance - gosi) / 30)

                            elif record.accrual_calculation_eos == 'hr_tr_sch':
                                total += record.employee_id.accrued_leave_num_of_days_end_of_service * ((base_salary + house_allowance + transport_allowance + school_allowance - gosi) / 30)

                            elif record.accrual_calculation_eos == 'wage_tr_fd':
                                total += record.employee_id.accrued_leave_num_of_days_end_of_service * ((base_salary + food_allowance + transport_allowance - gosi) / 30)

                            elif record.accrual_calculation_eos == 'hr_tr_fd':
                                total += record.employee_id.accrued_leave_num_of_days_end_of_service * ((base_salary + house_allowance + transport_allowance + food_allowance - gosi) / 30)

                            elif record.accrual_calculation_eos == 'hr_tr_fl':
                                total += record.employee_id.accrued_leave_num_of_days_end_of_service * ((base_salary + house_allowance + transport_allowance + fuel_allowance - gosi) / 30)

                            elif record.accrual_calculation_eos == 'hr_tr_tk':
                                total += record.employee_id.accrued_leave_num_of_days_end_of_service * ((base_salary + house_allowance + transport_allowance + ticket_allowance - gosi) / 30)

                            elif record.accrual_calculation_eos == 'hr_tr_fx':
                                total += record.employee_id.accrued_leave_num_of_days_end_of_service * ((base_salary + house_allowance + transport_allowance + fixed_allowance - gosi) / 30)

                            elif record.accrual_calculation_eos == 'hr_tr_mb':
                                total += record.employee_id.accrued_leave_num_of_days_end_of_service * ((base_salary + house_allowance + transport_allowance + mobile_allowance - gosi) / 30)

                            elif record.accrual_calculation_eos == 'hr_tr_wk':
                                total += record.employee_id.accrued_leave_num_of_days_end_of_service * ((base_salary + house_allowance + transport_allowance + work_allowance - gosi) / 30)

                            elif record.accrual_calculation_eos == 'hr_tr_oth':
                                total += record.employee_id.accrued_leave_num_of_days_end_of_service * ((base_salary + house_allowance + transport_allowance + housing_allowance - gosi) / 30)

                            elif record.accrual_calculation_eos == 'all':
                                total += record.employee_id.accrued_leave_num_of_days_end_of_service * ((base_salary + house_allowance + transport_allowance + school_allowance +
                                         food_allowance + fuel_allowance + ticket_allowance + fixed_allowance +
                                         mobile_allowance + work_allowance + housing_allowance - gosi) / 30)

                record.total_holiday_deserved_amount = total

    # @api.depends('employee_id', 'payslip_id', 'days_number', 'type',
    #              'payment_type')
    # def _compute_total_payslip_deserved_amount(self):
    #     category_id = self.env.user.company_id.category_id
    #     for record in self:
    #         payslip_total = 0
    #         total =0
    #         days=0
    #         for line in record.payslip_id.line_ids:
    #             if line.code in ['NET','net']:
    #                 total=line.total
    #             if total:
    #                 days=total/30
    #         record.total_payslip_deserved_amount = record.days_number*days

    @api.onchange('payslip_id', 'employee_id')
    def _compute_payslip_bool(self):
        for rec in self:
            rec.payslip_bool = False
            rec.payroll_draft_amount = False
            rec.total_accured_leave_end_of_days = rec.employee_id.accrued_leave_num_of_days_end_of_service 
            if rec.payslip_id.state == 'draft':
                rec.payroll_draft_amount = rec.total_payslip_deserved_amount
          
            

    @api.depends('employee_id', 'payslip_id', 'days_number', 'type',)
    def _compute_total_payslip_deserved_amount(self):
        category_id = self.env.user.company_id.category_id
        payslip_total = 0
        total = 0
        days = 0
        for record in self:
            record.total_payslip_deserved_amount = False
            for lin in record.payslip_id:
                delta = (lin.date_to - lin.date_from).days + 1
                days_number = delta
                record.days_number = days_number
                for line in lin.line_ids:
                    if line.code == 'GROSS':
                        total = line.total
                    if total:
                        days = total/days_number
                record.total_payslip_deserved_amount = record.days_number*days
                if lin.state == 'done':
                    record.total_payslip_deserved_amount = record.payroll_draft_amount
                    
                    # record.payroll_draft_amount = record.total_payslip_deserved_amount
            
            # if record.payslip_bool:
            #     record.total_payslip_deserved_amount = record.payroll_draft_amount
            #


    @api.depends('employee_id')
    def _compute_total_taken_amount(self):
        for record in self:
            benefits_ids = self.env['hr.end.service.benefit'].search([
                ('employee_id', '=', record.employee_id.id),
                ('state', 'in', ['validated', 'paid']),
            ])
            sum = 0
            for benefits_id in benefits_ids:
                sum += benefits_id.amount
            record.total_taken_amount = sum

    # @api.depends('employee_id')
    # def _compute_ticket(self):
    #     for record in self:
    #         contract_ids = self.env['hr.contract'].search([
    #             ('employee_id', '=', record.employee_id.id),
    #             ('state', 'in', ['open']),
    #         ])
    #         amt,mul_days,duration,days= 0,0,1,''
    #         if contract_ids:
    #             ticket_amount=0
    #             for contract_id in contract_ids:
    #                 ticket_amount=contract_id.per_ticket_amt * contract_id.ticket_count
    #                 try:
    #                     data_days=record.date
    #                     if contract_id.duration:
    #                         duration=int(contract_id.duration[:1])
    #                     if contract_id.date_reneview:
    #                         days=data_days - contract_id.date_reneview
    #                     if str(days).find('days') > -1:
    #                         mul_days=int(str(days).split('days')[0])
    #                 except:
    #                     print('error')
    #
    #
    #             if mul_days == 0:
    #                 mul_days=1
    #             # amount=(ticket_amount / duration)*days(data_days - contract_ids.date_reneview)
    #             amount=(ticket_amount / duration)*mul_days
    #             print("amount",amount)
    #             amt += amount
    #             print('sum',amt)
    #         record.total_ticket = amt
    
    # @api.depends('total_deserved_amount','total_payslip_deserved_amount')
    @api.depends('total_deserved_amount', 'total_taken_amount')
    def _compute_available_amount(self):
        for record in self:
            record.available_amount = record.total_deserved_amount - record.total_taken_amount
            # record.available_amount = record.total_deserved_amount + record.total_payslip_deserved_amount
   
    @api.depends('state')
    def _compute_payment_button_invisible(self):
        for record in self:
            record.payment_button_invisible = True
            if record.state != 'validated':
                record.payment_button_invisible = False
            if record.payment_id:
                record.payment_button_invisible = False

    @api.depends('total_deserved_amount', 'total_payslip_deserved_amount', 'total_holiday_deserved_amount',
                 'accured_ticket_amount', 'outstanding_loan_amount', 'outstanding_advance_amount')
    def _compute_total_reward(self):
        for record in self:
            record.total_reward = (record.total_deserved_amount + record.total_payslip_deserved_amount + record.total_holiday_deserved_amount - 
                                   record.accured_ticket_amount - record.outstanding_loan_amount - record.outstanding_advance_amount)

    # @api.depends('type')
    # def _compute_total_loan_advance(self):
    #     for record in self:
    #         loan_advance_amt = 0.0
    #         if record.employee_id:
    #             loan_amt_ids = self.env['approval.request'].search([
    #                 ('emp_id', '=', record.employee_id.id),
    #                 ('category_id.category_code_id.code', '=', 'HAADV'),
    #                 ('request_status', '=', 'approved')
    #             ])
    #             if loan_amt_ids:
    #                 for loan_id in loan_amt_ids:
    #                     line=loan_id.loan_lines.filtered(lambda p_line: p_line.paid !='True')
    #                     for loan in line:
    #                         loan_advance_amt += loan.amount
    #                     # if loan_id.date <= record.date :
    #                     #     loan_advance_amt+=loan_id.balance_of_advance
    #
    #         record.total_advance_loan = loan_advance_amt

    name = fields.Char(string='Reference', copy=False, default=_('New'),
                       tracking=True)
    state = fields.Selection(string="State", tracking=True,
                             selection=[('draft', 'Draft'),
                                        ('confirmed', 'Confirmed'),
                                        ('validated', 'Validated'),
                                        ('paid', 'Paid'),
                                        ('cancel', 'Cancelled'), ],
                             default='draft', copy=False)
    employee_id = fields.Many2one('hr.employee', string='Employee', index=True, readonly=True,
                                  tracking=True)
    department_id = fields.Many2one(comodel_name="hr.department", string="Department",
                                    related='employee_id.department_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    date = fields.Date(string="Date", default=datetime.now().strftime('%Y-%m-%d'), tracking=True,
                       copy=False)
    
    termination_date = fields.Date(string="Termination Date", related='employee_id.exit_date',
                                   tracking=True,copy=False, readonly=True)
    type = fields.Selection(string="Reward Type",
                            selection=[('replacement', 'Replacement'), ('ending_service', 'Ending Service'), ],
                            default='replacement', )
    payment_type = fields.Selection(string="Payment Type",
                                    selection=[('wage', 'Wage'), ('wage_allowance', 'Wage + Allowances'), ],
                                    default='wage_allowance', required=True)
    end_service_benefit_type_id = fields.Many2one(comodel_name="hr.end.service.benefit.type", string="ES Reason", )
    hiring_date = fields.Date(string="Hiring Date")
    joining_date = fields.Date(string="Joining Date")
    years = fields.Integer(string="Years", compute=_compute_period, store=True)
    months = fields.Integer(string="Months", compute=_compute_period, store=True)
    days = fields.Integer(string="Days", compute=_compute_period, store=True)
    service_period = fields.Float(string="Service Period In Years", compute=_compute_period, store=True)
    notes = fields.Text(string="Notes", tracking=True)
    company_id = fields.Many2one('res.company', string='Company', related='employee_id.company_id', store=True)
    total_holiday_deserved_amount = fields.Float(string='Accrued Leave Amount',digits=(16, 2),
                                                 compute=_compute_total_holiday_deserved_amount, store=True)
    total_payslip_deserved_amount = fields.Float(string="Current Monthly Allowance", digits=(16, 2),
                                                 compute=_compute_total_payslip_deserved_amount)
    other_amount = fields.Float(string="Other Amount", invisible=True)
    total_deserved_amount = fields.Float(string="End of Service Award (EOS) Amount",
                                         compute=_compute_total_deserved_amount, digits=(12, 2),
                                         store=True)
    total_taken_amount = fields.Float(string="Previously Disbursed Amount",
                                      compute=_compute_total_taken_amount,
                                      digits=(12, 2),
                                      store=True)
    available_amount = fields.Float(string="Amount Due", compute=_compute_available_amount, store=True)
    amount = fields.Float(string="Reward Requested Amount", required=False, invisible=True)
    payment_id = fields.Many2one(comodel_name="account.payment", string="Reward Payment", copy=False, )
    payslip_payment_id = fields.Many2one(comodel_name="account.payment", string="Terminal Journa", copy=False, )
    account_move_id = fields.Many2one(comodel_name="account.move", string="Terminal Journal Reference", copy=False, )
    payment_button_invisible = fields.Boolean(compute=_compute_payment_button_invisible)
    holiday_line_ids = fields.One2many(comodel_name="hr.end.benefit.holiday.line", inverse_name="reward_id")
    payslip_id = fields.Many2one(comodel_name="hr.payslip", string="Payslip",required=True)
    days_number = fields.Float(string="Last Month Worked Days Number", default=30)
    total_reward = fields.Float(string="Terminal Pay Amount", compute=_compute_total_reward, store=True)
    # total_advance_loan = fields.Float(string="Total Housing Loan/Advance", store=True)
    total_allowance_new = fields.Float("Total Allowances")
    allowance_line_ids = fields.One2many("hr.end.benefit.allowance.line", 'benefit_type_id', 'Allowances')
    total_days = fields.Integer(string='Total Days', compute='_compute_total_days', store=True)
    termination_id = fields.Many2one('hr.exit', string="Termination")
    
    accured_ticket_amount = fields.Float(string="Accured Ticket Amount")
    outstanding_loan_amount = fields.Float(string="Outstanding Loans Amount")
    outstanding_advance_amount = fields.Float(string="Outstanding Advance Amount")
    
    payslip_bool = fields.Boolean(default=False,)
    payroll_draft_amount = fields.Float(string="Payslip Draft amount")
    
    total_accured_leave_end_of_days = fields.Float("Total Accured leave End Of days", readonly=True)
    
    
    employee_number = fields.Char(string='Employee No', store = True)

    accrual_calculation_eos = fields.Selection(string="Calculate Based On",
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

    accrual_calculation_eos_id = fields.Many2one(
        'hr.transaction.entry',
        string="Transaction Definition",
        default=lambda self: self.env['hr.transaction.entry'].search([('code', '=', 'ACL')], limit=1)
    )

    @api.onchange('accrual_calculation_eos_id')
    def _onchange_accrual_calculation_eos(self):
        for rec in self:
            rec.accrual_calculation_eos = False
            if rec.accrual_calculation_eos_id:
                # Get the selection field's key from the related 'calculate_based_on_allowance' field
                selection_field_value = rec.accrual_calculation_eos_id.calculate_based_on_allowance
                rec.accrual_calculation_eos = selection_field_value
    
    @api.onchange('employee_id')
    def _onchange_employe(self):
        for rec in self:
            rec.employee_number = False
            if rec.employee_id:
                rec.joining_date = rec.employee_id.joining_date or False
                rec.employee_number = rec.employee_id.employee_no or False
                rec.hiring_date = rec.employee_id.hiring_date or False
    # complete_name_accured_leave = fields.Char('Complete name',compute="_compute_complete_name",store=True)
    #
    #
    # @api.depends('total_accured_leave_end_of_days','total_holiday_deserved_amount')
    # def _compute_complete_name(self):
    #     for rec in self:
    #         rec.complete_name_accured_leave = False
    #         if rec.total_accured_leave_end_of_days and rec.total_holiday_deserved_amount:
    #
    #             rec.complete_name_accured_leave = '%s ( %s)' % (rec.total_holiday_deserved_amount, rec.total_accured_leave_end_of_days) 
    #

    # sanction_line_ids = fields.One2many("hr.end.benefit.sanction.line", 'benefit_type_id','Sanctions')
    # total_sanction = fields.Float(string='Total Sanction')
    # total_ticket = fields.Float(string='Total Ticket', store=True)
    # allowance,percentage,fix_amount
    #
    # @api.model
    # def create(self,vals):
    #
    #     name = str(vals['total_holiday_deserved_amount'] or '')+str(vals['total_accured_leave_end_of_days'] or '')
    #     vals['total_holiday_deserved_amount'] = name
    #     print(".............vals",vals)
    #     res = super(HREndServiceBenifits,self).create(vals)
    #     return res
    

    

    @api.depends('years', 'months', 'days')
    def _compute_total_days(self):
        total_days = 0
        for record in self:
            total_days = record.years * 365
            total_days += record.months * 30
            total_days += record.days
            record.total_days = total_days
        return total_days
    # def _get_business_trip_values(self):
    #     business_trip_amt = 0.0
    #     business_trip_values = False
    #     business_trip = self.env['approval.request'].search([
    #         ('emp_id', '=', self.employee_id.id),
    #         ('category_id.category_code_id.code', '=', 'BSTRP'),
    #         ('request_status', '=', 'approved'),
    #         ('is_payslip_req', '=', True),
    #         ('date', '<=', self.date)
    #     ])
    #     if business_trip:
    #         business_trip_amt = sum(business_trip.ticket_ids.mapped('total_dues_amt'))
    #         # business_trip_values = [(6, 0, business_trip.ids)]
    #     print("business_trip_amt",business_trip_amt)
    #     return business_trip_amt

    # def _get_vocation_salary(self):
    #     result = 0
    #     out=0
    #     vocation_salary=0
    #     clearance_ids = self.env['hr_saudi_leave.vocation.clearance'].search([
    #         ('employee_id', '=', self.employee_id.id),
    #         ('state', '=', 'approve'),
    #     ])
    #     for rec in clearance_ids:
    #         if rec.leave_id:
    #             if rec.leave_id.request_date_from >= self.date and rec.leave_id.request_date_to<=self.date:
    #                 difference = (rec.leave_id.request_date_to - rec.leave_id.request_date_from).days + 1
    #                 rec.leave_count=difference
    #                 result = difference*(rec.employee_id.contract_id.wage/30)
    #                 vocation_salary += result
    #                 result=0
    #     return vocation_salary

    @api.onchange('employee_id', 'type')
    def _onchange_employee_id(self):
        if self.type == 'ending_service':
            allocation_ids = self.env['hr.leave.allocation'].search(
                [('employee_id', '=', self.employee_id.id),
                 ('state', 'not in', ['draft', 'cancel', 'refuse']),
                 ('holiday_status_id.code', '=', 'AV')
                 ])
            holiday_status_ids = allocation_ids and allocation_ids.mapped('holiday_status_id')
            for line in self.holiday_line_ids:
                line.unlink()
            # lines_ids = []    
            lines_ids = []
            for holiday_status_id in holiday_status_ids:
                data_days = {}
                remaining_leaves = 0
                employee_id = self.employee_id and self.employee_id or False
                # if employee_id:
                #     data_days = holiday_status_id.get_days(employee_id.id)
                for holiday_status in holiday_status_id:
                    # if holiday_status.code=='AV':
                    result = data_days.get(holiday_status.id, {})
                    remaining_leaves = result.get('remaining_leaves', 0)
                    print("remaining_leaves", remaining_leaves)
                    if holiday_status_id.request_unit == 'hour':
                        if employee_id.company_id:
                            remaining_leaves = remaining_leaves / (
                                employee_id.company_id.number_of_hours_per_day and employee_id.company_id.number_of_hours_per_day or 8)
                        elif employee_id.user_id.company_id:
                            remaining_leaves = remaining_leaves / (
                                employee_id.user_id.company_id.number_of_hours_per_day and employee_id.user_id.company_id.number_of_hours_per_day or 8)

                    elif holiday_status_id.request_unit == 'half_day':
                        remaining_leaves = remaining_leaves / 2
                lines_ids.append((0, 0, {'holiday_id': holiday_status_id.id,
                                         'remaining_leaves': remaining_leaves
                                         }))
            self.holiday_line_ids = lines_ids
            # lines_ids.append((0,0,{'remaining_leaves':self.employee_id.bfwd_previous_year}))
            # self.holiday_line_ids = lines_ids
            allowances = 0
            if self.employee_id and self.payment_type == 'wage_allowance':
                allowance_line_ids = []
                contract_obj = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id), ('state', '=', 'open')], limit=1)

                if contract_obj.struct_id.rule_ids:
                    # payslip_lines_to_remove = self.payslip_ids[0].line_ids.filtered(lambda p_line: p_line.category_id.code in ['BASIC']) 
                    basic = contract_obj.wage/30
                    basic1 = basic*self.days_number
                    vals = {}
                    for rule in contract_obj.struct_id.rule_ids:
                        if rule.category_id.code == 'ALW':
                            if rule.amount_select == 'percentage':
                                data_total = basic1*(rule.amount_percentage/100)
                                allowances += data_total
                                vals = {
                                        'allowance_id': rule.id,
                                        'percentage': rule.amount_percentage,
                                        'type': 'percentage',
                                        'fix_amount': data_total
                                }
                                allowance_line_ids.append((0, 0, vals))
                            elif rule.code in['mobile allowance', 'allowance mobile']:
                                allowances += contract_obj.mobile_allowance
                                vals = {
                                        'allowance_id': rule.id,
                                        'percentage': 0,
                                        'type': 'fix_amount',
                                        'fix_amount': contract_obj.mobile_allowance}
                                allowance_line_ids.append((0, 0, vals))
                            elif rule.code == 'other allowance':
                                allowances += contract_obj.housing_allowance
                                vals = {
                                        'allowance_id': rule.id,
                                        'percentage': 0,
                                        'type': 'fix_amount',
                                        'fix_amount': contract_obj.housing_allowance}
                                allowance_line_ids.append((0, 0, vals))
                            # elif rule.code=='BSTRP':
                            #     amt=self._get_business_trip_values()
                            #     print("amtaaa",amt)
                            #     allowances +=amt
                            #     vals={'allowance_id':rule.id,'percentage':0,'type':'fix_amount','fix_amount':amt}
                            #     allowance_line_ids.append((0, 0, vals))
                            # elif rule.code=='VOCC':
                            #     amt=self._get_vocation_salary()
                            #
                            #     allowances +=amt
                            #     # allowances+=150
                            #     vals={'allowance_id':rule.id,'percentage':0,'type':'fix_amount','fix_amount':amt}
                            #     allowance_line_ids.append((0, 0, vals))
                            # elif rule.code=='بدل اتصالات':
                            #     # amt=self._get_vocation_salary()
                            #     # print("amtaaa222",amt)
                            #     amt=rule.amount_fix
                            #     allowances +=amt
                            #     # allowances+=150
                            #     vals={'allowance_id':rule.id,'percentage':0,'type':'fix_amount','fix_amount':amt}
                            #     allowance_line_ids.append((0, 0, vals))
                            # else:
                            #     vals={'allowance_id':rule.id}
                            # allowance_line_ids.append((0, 0, vals))

                self.allowance_line_ids = allowance_line_ids
                self.total_allowance_new = allowances
            exit_obj = self.env['hr.exit'].search(
                [('employee_id', '=', self.employee_id.id), ('state', '=', 'done')])
            self.termination_id = exit_obj.id
            
            loan_search = self.env['hr.employee.loan.ps'].search([('employee_id', '=', self.employee_id.id),
                                                                  ('state', '=', 'approve')]).mapped('balance_amount')
            # for loan in loan_search:
            self.outstanding_loan_amount = sum(loan_search)
            
            advance_search = self.env['hr.employee.advance.ps'].search([('employee_id', '=', self.employee_id.id),
                                                                        ('state', '=', 'approve')]).mapped('balance_amount')
            self.outstanding_advance_amount = sum(advance_search)
                    # dd
                
                
                # """ For Updating Sanction table """
                # sanction_line_ids = []; total_sanction = 0
                # for sanction_obj in self.env['tw_sanction.sanction'].search([('employee_id', '=', self.employee_id.id),('state', '=', 'approve'),('is_paid', '=',False)]):
                #     if sanction_obj.payslip_id.state != 'paid':
                #         for line in sanction_obj.payslip_id.line_ids:
                #             if line.code in ['SANCT','sanct']:
                #                 sanction_line_ids.append((0, 0, {'sanction_name': line.name, 'sanction_code': line.code, 'total': line.total}))
                #                 total_sanction += line.total
                #
                # self.sanction_line_ids = sanction_line_ids
                # self.total_sanction = total_sanction
                # contract_obj = self.env['hr.contract'].search([('employee_id','=',self.employee_id.id),('state','=','open')],limit=1)
                # if contract_obj.structure_type_id.default_struct_id.rule_ids:
                #     for rule in contract_obj.structure_type_id.default_struct_id.rule_ids:
                #         if rule.code in ['SANCT','sanct']:
                #             sanction_line_ids.append((0, 0, {'sanction_id':rule.id}))
            #

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise ValidationError(_('You can only delete draft end service benefits'))
        res = super(HREndServiceBenifits, self).unlink()
        return res

  
       

    def action_submit(self):
        for record in self:
            group_manager = self.env.ref('hr.group_hr_manager')
            recipient_partners = []
            mail_server = self.env['ir.mail_server'].sudo().search([], order="sequence asc", limit=1)
            for recipient in group_manager[0].users:
                recipient_partners.append(
                    (4, recipient.partner_id.id)
                )
            template = False
            if recipient_partners and mail_server:
                template = self.env['ir.model.data']._xmlid_lookup('hr_end_service_benefits.email_es_request_submission')[1]

            if template:
                mail_template = self.env['mail.template'].browse(template)
                print("mail_template................", mail_template)
                mail_id = mail_template.send_mail(record.id)
                mail = self.env['mail.mail'].browse(mail_id)
                mail.recipient_ids = recipient_partners
             
            SequenceObj = self.env['ir.sequence']
            number = SequenceObj.next_by_code('hr.end.service.benefit')
            record.name = number
            record.write({'state': 'confirmed', 'name': number})
            if record.payslip_id:
                record.payslip_id.action_payslip_done()
            
                
                
            

    def action_validate(self):
        for record in self:
            group_manager = self.env.ref('account.group_account_manager')
            recipient_partners = []
            mail_server = self.env['ir.mail_server'].sudo().search([], order="sequence asc", limit=1)
            for recipient in group_manager[0].users:
                recipient_partners.append(
                    (4, recipient.partner_id.id)
                )
            template = False
            if recipient_partners and mail_server:
                template = self.env['ir.model.data']._xmlid_lookup('hr_end_service_benefits.email_es_request_payment_request')[1]
            if template:
                mail_template = self.env['mail.template'].browse(template)
                mail_id = mail_template.send_mail(record.id)
                mail = self.env['mail.mail'].browse(mail_id)
                mail.recipient_ids = recipient_partners

            record.write({'state': 'validated'})
            if record.type == 'ending_service':
                record.employee_id.toggle_active()
                contract_ids = self.env['hr.contract'].search(
                    [('employee_id', '=', record.employee_id.id), ('state', '=', 'open')],
                    order='id desc')
                for contract_id in contract_ids:
                    contract_id.state = 'cancel'
            
            
            settlement_record = self.env['hr.benefit.settlement'].search([('request_id', '=', record.id)], limit=1)

            if not settlement_record:
                # Optionally create a new settlement record if one doesn't exist
                settlement_record = self.env['hr.benefit.settlement'].create({
                    'request_id': record.id,
                    # Set other default values if necessary
                })
            settlement_record.sudo().settle_employee_reward()
           
    def action_draft(self):
        for record in self:
            record.write({'state': 'draft'})
            if record.payment_id:
                record.payment_id.action_draft()

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})
            if record.payment_id:
                record.payment_id.action_cancel()
            if record.account_move_id:
                # default_values=self._context()
                default_values = self._context.copy()
                default_values.update({
                        'campaign_id': record.account_move_id.campaign_id.id,
                        'medium_id': record.account_move_id.medium_id.id,
                        'source_id': record.account_move_id.source_id.id,
                        })
                reverted_payment_move = record.account_move_id._reverse_moves([{'date': time.strftime('%Y') + '-08-01'}], cancel=True)
                # record.account_move_id._reverse_moves(default_values_list=[default_values], cancel=False)
               # record.account_move_id._reverse_moves(record.account_move_id.date,
               # record.account_move_id.journal_id or False)


class HrEndBenefitAllowanceLine(models.Model):
    _name = 'hr.end.benefit.allowance.line'
    _description = 'allowance '

    benefit_type_id = fields.Many2one("hr.end.service.benefit",string='Benefit', ondelete="cascade")
    allowance_id = fields.Many2one('hr.salary.rule',string='Allowances')
    type = fields.Selection([('percentage','Percentage'), ('fix_amount',' Amount')], string='Type')
    percentage = fields.Float(string='Percentage')
    fix_amount = fields.Float(string='Amount')
    # total = fields.Float(string='Total')

    @api.onchange('type')
    def _onchange_type(self):
        if self.type == 'percentage':
            self.percentage = None
        if self.type == 'fix_amount':
            self.fix_amount = None
            
    @api.constrains('fix_amount')
    def _check_fix_amount(self): 
        for rec in self:
            if rec.type:
                if rec.fix_amount == 0.00:
                    raise ValidationError("Please Enter Some amount because Type is selected")       

class HrEndBenefitSanctionLine(models.Model):
    _name = 'hr.end.benefit.sanction.line'
    _description = 'sanction'

    benefit_type_id = fields.Many2one("hr.end.service.benefit", string='Benefit', ondelete="cascade")
    sanction_name = fields.Char(string='Sanction')
    sanction_code = fields.Char(string='Code')
    total = fields.Float(string='Total')
    # sanction_id = fields.Many2one('hr.salary.rule', string='Sanction')
    # type = fields.Selection([('percentage','Percentage'), ('fix_amount',' Amount')], string='Type')
    # percentage = fields.Float(string='Percentage')
    # fix_amount = fields.Float(string='Amount')

    # @api.onchange('type')
    # def _onchange_type(self):
    #     if self.type == 'percentage':
    #         self.percentage = None
    #     if self.type == 'fix_amount':
    #         self.fix_amount = None

class HolidaysReward(models.Model):
    _name = 'hr.end.benefit.holiday.line'
    _description = 'Holiday Reward'

   
   
    def _compute_leaves(self):
        for record in self:
            record.remaining_leaves = 0 
            if record.reward_id and record.reward_id.type == 'ending_service':
                data_days = {}
                employee_id = record.reward_id and record.reward_id.employee_id or False
                if employee_id:
                    data_days = record.holiday_id.get_days(employee_id.id)
                for holiday_status in record.holiday_id:
                    if data_days:
                        result = data_days.get(holiday_status.id, {})
                        record.remaining_leaves = result.get('remaining_leaves', 0)
                        if holiday_status.request_unit == 'hour':
                            record.remaining_leaves = record.remaining_leaves / (
                                employee_id.company_id.number_of_hours_per_day and employee_id.company_id.number_of_hours_per_day or 8)
                        elif holiday_status.request_unit == 'half_day':
                            record.remaining_leaves = record.remaining_leaves / 2
            else:
                record.remaining_leaves = 0
    

    holiday_id = fields.Many2one(comodel_name="hr.leave.type", string="Holiday", required=False, )
    reward_id = fields.Many2one(comodel_name="hr.end.service.benefit", )
    employee_id = fields.Many2one(comodel_name="hr.employee", related='reward_id.employee_id')
    remaining_leaves = fields.Float(string="Remaining Leaves", compute=_compute_leaves )
    pay = fields.Boolean(string="Pay As Reward",default = True)
    
    
    
    

class HrContract(models.Model):
    _inherit = 'hr.contract'

    date_reneview = fields.Date(string="Renew Date", default=datetime.now().strftime('%Y-%m-%d'), tracking=True, copy=False)
