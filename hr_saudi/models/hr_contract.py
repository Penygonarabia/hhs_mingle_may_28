# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import UserError
from datetime import date, datetime


class HrContract(models.Model):
    _name = 'hr.contract'
    _inherit = ['hr.contract']
    _description = 'HR Contract'

    def _compute_auto_contract_no(self):
        # Object
        hr_configuration = self.env['hr.configuration']
        hr_configuration_id = hr_configuration.search([], limit=1)
        is_automatic = False
        if hr_configuration_id:
            is_automatic = hr_configuration_id.auto_contract_no
        return is_automatic

    # @api.depends('employee_id.ticket_depends','employee_id.insurance_ids')
    # def _compute_family_count(self):
    #     """
    #         Method to compute family length for ticket amount computation.
    #     """
    #     for contract in self:
    #         if contract.employee_id.ticket_depends:
    #             contract.ticket_count = contract.employee_id.ticket_depends
    #         else:
    #             if not contract.employee_id:
    #                 contract.ticket_count = 0
    #                 continue
    #             if contract.employee_id.insurance_ids:
    #                 ticket_count = len(contract.employee_id.insurance_ids) + 1
    #                 if ticket_count > 4:
    #                     contract.ticket_count = 4
    #                 else:
    #                     contract.ticket_count = ticket_count
    #             else:
    #                 contract.ticket_count = 1

    # @api.depends('ticket_count', 'per_ticket_amt')
    # def _compute_ticket_amt(self):
    #     """
    #         Method to compute ticket amount with ticket count.
    #     """
    #     for contract in self:
    #         if not contract.ticket_count or not contract.per_ticket_amt:
    #             contract.computed_ticket_amt = 0.0
    #             continue
    #
    #         contract.computed_ticket_amt = contract.ticket_count * contract.per_ticket_amt

    ramadan_working_hours = fields.Many2one('resource.calendar', 'Ramadan Working Hours')
    mobile_allowance = fields.Float(string='Mobile Allowance')
    housing_allowance = fields.Float(string='Other  Allowance')
    transport_allowance = fields.Float(string='Transport Allowance')
    work_allowance = fields.Float(string='Work Nature Allowance')
    house_allowance = fields.Float(string='Housing Allowance')
    food_allowance = fields.Float(string='Food Allowance')
    fuel_allowance = fields.Float(string='Fuel Allowance')
    ticket_allowance = fields.Float(string='Ticket Allowance')
    school_allowance = fields.Float(string='School Allowance')
    fixed_allowance = fields.Float(string='Fixed Allowance')
    total = fields.Float(string='Total', compute='_compute_total')
    duration = fields.Char(string='Contract Duration', compute='_compute_duration')
    auto_contract_no = fields.Boolean(string='Create contract no automatically', default=_compute_auto_contract_no)
    # overtime = fields.Boolean(string='Allow overtime', default=True)
    document = fields.Binary(string='Contract File')
    document_filename = fields.Char(string='File Name')
    # payment_type = fields.Selection([
    #     ('monthly', 'Monthly'),
    #     ('yearly', 'Yearly'),
    # ], string='Payment Type', default='monthly')
    # payment_method = fields.Selection([('cash', 'Cash'), ('Bank', 'Bank')], string='Payment Method')

    nature = fields.Selection([
        ('fixed', 'Fixed Term'),
        ('indef', 'Indefinite'),
    ], string='Contract Nature', default='fixed')
    salary_information_ids = fields.One2many('hr.contract.salary_information', 'contract_id')
    # ticket_count = fields.Integer(compute='_compute_family_count')
    # per_ticket_amt = fields.Float('Ticket Amount')
    # computed_ticket_amt = fields.Float(compute='_compute_ticket_amt')
    is_special_gosi = fields.Boolean(string='Special GOSI')
    #
    department_id = fields.Many2one('hr.department', compute='_compute_employee_contract', store=True, readonly=False, related='employee_id.department_id',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", string="Department")
    job_id = fields.Many2one('hr.job', compute='_compute_employee_contract', store=True, readonly=False, related='employee_id.job_id',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", string='Job Position')
    
    house_allowance_bool = fields.Boolean(default = False)
    transport_allowance_bool = fields.Boolean(default = False)
    school_allowance_bool = fields.Boolean(default = False)
    food_allowance_bool = fields.Boolean(default = False)
    fuel_allowance_bool = fields.Boolean(default = False)
    
    ticket_allowance_bool = fields.Boolean(default = False)
    fixed_allowance_bool = fields.Boolean(default = False)
    mobile_allowance_bool = fields.Boolean(default = False)
    work_allowance_bool = fields.Boolean(default = False)
    housing_allowance_bool = fields.Boolean(default = False)
    # employee_no = fields.Char('Employee No', store=True)
    employee_no = fields.Char('Employee No')


    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for rec in self:
            rec.employee_no = False
            if rec.employee_id:
                rec.employee_no = rec.employee_id.employee_no

    
    # @api.model
    # def create(self, vals):
    #     # Sequence
    #     if vals.get('auto_contract_no', False):
    #         name = self.env['ir.sequence'].get('hr.contract.seq')
    #         vals['name'] = name
    #         print("sequence name", name)
    #     return super(HrContract, self).create(vals)

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for ctr in self:
            if not ctr.date_start and not ctr.date_end:
                ctr.duration = False
                return False
            
            duration = ''
            start_date = fields.Date.from_string(ctr.date_start)
            end_date = fields.Date.from_string(ctr.date_end)
            months = relativedelta(end_date, start_date).months
            years = relativedelta(end_date, start_date).years
            days = relativedelta(end_date, start_date).days
            if 'ar' in self._context['lang']:
                if years > 0:
                    duration = str(years) + '  Year and ' + str(months) + ' Month and  ' + str(days) + ' Day'
                elif months > 0:
                    duration = str(months) + ' Month and  ' + str(days) + 'Day'
                elif days > 0:
                    duration = str(days) + ' Day'

            else:
                if years > 0:
                    duration = str(years) + ' year(s) and ' + str(months) + ' month(s) and ' + str(days) + ' day(s)'
                elif months > 0:
                    duration = str(months) + ' month(s)'

            ctr.update({'duration': duration})

    @api.depends('wage', 'mobile_allowance', 'housing_allowance', 'transport_allowance','house_allowance','work_allowance','food_allowance','school_allowance','ticket_allowance','fuel_allowance','fixed_allowance')
    def _compute_total(self):
        for ctr in self:
            total = ctr.wage + ctr.mobile_allowance + ctr.housing_allowance + ctr.transport_allowance + ctr.house_allowance + ctr.work_allowance + ctr.food_allowance + ctr.school_allowance + ctr.ticket_allowance + ctr.fuel_allowance + ctr.fixed_allowance
            ctr.update({'total': total})

    # @api.constrains('date_start', 'date_end')
    # def check_dates(self):
    #     # Objects
    #     for ctr in self:
    #         if self.nature == 'fixed':
    #             if ctr.date_start >= ctr.date_end:
    #                 raise ValidationError(_('End date must be greater than Start date!'))
    #             # Date overlap
    #             domain_search = [
    #                 ('employee_id', '=', ctr.employee_id.id),
    #                 ('id', '!=', ctr.id),
    #             ]
    #             for rec in self.search(domain_search):
    #                 if rec.date_start <= ctr.date_start <= rec.date_end or \
    #                         rec.date_start <= ctr.date_end <= rec.date_end or \
    #                         ctr.date_start <= rec.date_start <= ctr.date_end or \
    #                         ctr.date_start <= rec.date_end <= ctr.date_end:
    #                     raise ValidationError(_('There is another contact for this employee in this duration'))

    @api.onchange('employee_id')
    def onchange_employee(self):
        self.job_id = False
        if self.employee_id:
            self.job_id = self.employee_id.job_id

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
            Add employee number with employee name while searching for the contract.
        @override.

        :return: (str)
        """

        if not self._context.get('is_store_switch'):
            return super().name_search(name, args, operator, limit)

        domain = expression.AND([
            args or [],
            ['|', ('name', operator, name),
             ('employee_no', operator, name)]
        ])
        return self.sudo().search(domain, limit=limit).name_get()

    # @api.onchange('structure_type_id', 'wage')
    def compute_salary_structure_lines(self):
        """
            Method to compute salary structure lines.
        """
        if not self.struct_id and not self.wage:
            return

        if not self.struct_id:
            raise UserError(_(
                "No default payslip struct is updated with selected structure."))
        if self.wage <= 0.0:
            raise UserError(_(
                "There is an issue in computing salary information lines."
                "Wage cannot be 0.0 or less than that."))

        from_date = self.date_start
        to_date = (
                self.date_start + relativedelta(months=+1, day=1, days=-1))
        payslip_name = "Salary Slip %s %s %d" % (
            self.employee_id.name,
            from_date.strftime("%B"),
            from_date.year
        )

        values = {
            'date_from': from_date,
            'date_to': to_date,
            'employee_id': self.employee_id.id,
            'name': payslip_name,
            'struct_id': self.struct_id.id,
            'contract_id': self.id,
        }
        payslip = self.env['hr.payslip'].with_context(
            is_neglect_payslip_duplication=True).create(values)
        payslip.onchange_employee_id(from_date,to_date)
        payslip.compute_sheet()

        payslip_data = payslip.line_ids.read()
        salary_lines = []
        for line in payslip_data:
            # if line['total'] <= 0.0:
            #     continue

            salary_lines.append(
                (0, 0, {
                    'name': line['name'],
                    'code': line['code'],
                    'category_id': line['category_id'][0],
                    'amount': line['total']
                })
            )

        self.salary_information_ids = None
        self.salary_information_ids = salary_lines
        # Deleting after cancelling the payslip to avoid the collision
        # between current month's payslip.
        payslip.sudo().action_payslip_cancel()
        payslip.sudo().unlink()


class ContractSalaryInformation(models.Model):
    """
        Model to handle the salary information when new contract is created,
    or old one gets updated with new basic salary and salary structure.
    """
    _name = 'hr.contract.salary_information'
    _description = 'Salary Information'

    contract_id = fields.Many2one('hr.contract')
    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    category_id = fields.Many2one('hr.salary.rule.category')
    amount = fields.Float('Amount')
