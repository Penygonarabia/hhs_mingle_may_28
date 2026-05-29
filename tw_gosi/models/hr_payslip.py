# -*- coding: utf-8 -*-
from odoo import models, fields

class HRContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Contract Inherited Model'

    gosi_amt = fields.Float('Gosi Amount', compute='compute_gosi_deduction_amount')
    gosi_comp_amt = fields.Float('Gosi Company Contribution Amount', compute='compute_gosi_deduction_amount')
    gosi_non_comp = fields.Float('Gosi Company Contribution non saudi employee', compute='compute_gosi_deduction_amount')
    gosi_percentage = fields.Float('Gosi Amount')
    calculate_based_on_allowance = fields.Selection(string="Calculate Based On",
                                                    selection=[('hra', 'HRA'), ('hra_trv', 'HRA + Travel'),('hr_tr_sch','HRA + Travel + School'),
                                                               ('hr_tr_fd','HRA + Travel + Food'),('hr_tr_fl','HRA + Travel + Fuel'),('hr_tr_tk','HRA + Travel + Ticket'),
                                                               ('hr_tr_fx','HRA + Travel + Fixed'),('hr_tr_mb','HRA + Travel + Mobile'),('hr_tr_oth','HRA + Travel + Other'),
                                                               ('hr_tr_wk','HRA + Travel + Work')], default='hra')

    def get_deduction_percentage(self):
        """
            Method to return Configuration parameter values of deduction
            percentages for Saudi and Non-saudi GOSI.
        """
        saudi_employee = float(self.env['ir.config_parameter'].sudo().get_param(
            'saudi_employee_deduction'))
        saudi_employer = float(self.env['ir.config_parameter'].sudo().get_param(
            'saudi_employer_deduction'))
        non_saudi_employee = float(self.env['ir.config_parameter'].sudo(
           ).get_param('non_saudi_employee_deduction'))
        non_saudi_employer = float(self.env['ir.config_parameter'].sudo(
            ).get_param('non_saudi_employer_deduction'))

        saudi_ded = saudi_employee
        comp_ded = saudi_employer
        non_saudi_ded = non_saudi_employee
        comp_non_ded = non_saudi_employer

        return saudi_ded, non_saudi_ded, comp_ded, comp_non_ded

    def compute_gosi_deduction_amount(self):
        """
            Method to compute the GOSI deduction amount.
        """
        
        for rec in self:
            rec.gosi_comp_amt = False
            rec.gosi_amt = False
            rec.gosi_non_comp = False
            saudi_deduction, non_saudi_deduction, comp_ded, comp_non_ded = self.get_deduction_percentage()
            if rec.employee_id.is_saudi:
                rec.gosi_amt = (rec.wage * saudi_deduction) / 100
                rec.gosi_comp_amt = (rec.wage * comp_ded) / 100
                if rec.calculate_based_on_allowance == 'hra':
                    rec.gosi_amt = ((rec.wage + rec.house_allowance) * saudi_deduction) / 100
                    rec.gosi_comp_amt = ((rec.wage + rec.house_allowance) * comp_ded) / 100
                if rec.calculate_based_on_allowance == 'hra_trv':
                    rec.gosi_amt = ((rec.wage + rec.house_allowance + rec.transport_allowance) * saudi_deduction) / 100
                    rec.gosi_comp_amt = ((rec.wage + rec.house_allowance + rec.transport_allowance) * comp_ded) / 100
                if rec.calculate_based_on_allowance == 'hr_tr_sch':
                    rec.gosi_amt = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.school_allowance ) * saudi_deduction) / 100
                    rec.gosi_comp_amt = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.school_allowance) * comp_ded) / 100
            else:
                rec.gosi_amt = (rec.wage * non_saudi_deduction) / 100
                rec.gosi_non_comp = (rec.wage * comp_non_ded) / 100
                if rec.calculate_based_on_allowance == 'hra':
                    rec.gosi_non_comp = ((rec.wage + rec.house_allowance) * comp_non_ded) / 100
                if rec.calculate_based_on_allowance == 'hra_trv':
                    rec.gosi_non_comp = ((rec.wage + rec.house_allowance + rec.transport_allowance) * comp_non_ded) / 100
                if rec.calculate_based_on_allowance == 'hr_tr_sch':
                    rec.gosi_non_comp = ((rec.wage + rec.house_allowance + rec.transport_allowance + rec.school_allowance) * comp_non_ded) / 100
    

        # self.gosi_comp_amt = False
        # self.gosi_amt = False
        # self.gosi_non_comp = False
        # saudi_deduction, non_saudi_deduction, comp_ded, comp_non_ded = self.get_deduction_percentage()
        # if self.employee_id.is_saudi:
        #     self.gosi_amt = (self.wage * saudi_deduction) / 100
        #     self.gosi_comp_amt = (self.wage * comp_ded) / 100
        #     if self.calculate_based_on_allowance == 'hra':
        #         self.gosi_amt = ((self.wage + self.house_allowance) * saudi_deduction) / 100
        #         self.gosi_comp_amt = ((self.wage + self.house_allowance) * comp_ded) / 100
        #     if self.calculate_based_on_allowance == 'hra_trv':
        #         self.gosi_amt = ((self.wage + self.house_allowance + self.transport_allowance) * saudi_deduction) / 100
        #         self.gosi_comp_amt = ((self.wage + self.house_allowance + self.transport_allowance) * comp_ded) / 100
        #     if self.calculate_based_on_allowance == 'hr_tr_sch':
        #         self.gosi_amt = ((self.wage + self.house_allowance + self.transport_allowance + self.school_allowance ) * saudi_deduction) / 100
        #         self.gosi_comp_amt = ((self.wage + self.house_allowance + self.transport_allowance + self.school_allowance) * comp_ded) / 100
        # else:
        #     self.gosi_amt = (self.wage * non_saudi_deduction) / 100
        #     self.gosi_non_comp = (self.wage * comp_non_ded) / 100
        #     if self.calculate_based_on_allowance == 'hra':
        #         self.gosi_non_comp = ((self.wage + self.house_allowance) * comp_non_ded) / 100
        #     if self.calculate_based_on_allowance == 'hra_trv':
        #         self.gosi_non_comp = ((self.wage + self.house_allowance + self.transport_allowance) * comp_non_ded) / 100
        #     if self.calculate_based_on_allowance == 'hr_tr_sch':
        #         self.gosi_non_comp = ((self.wage + self.house_allowance + self.transport_allowance + self.school_allowance) * comp_non_ded) / 100


