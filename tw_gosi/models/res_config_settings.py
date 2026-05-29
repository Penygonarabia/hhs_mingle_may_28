# -*- coding: utf-8 -*-

from odoo import models, fields


class HRPayrollSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    saudi_employee_deduction = fields.Float(string="Employee's Deduction", default=10.0, config_parameter='saudi_employee_deduction')
    saudi_employer_deduction = fields.Float(string="Employer's Deduction", default=0.0, config_parameter='saudi_employer_deduction')
    non_saudi_employee_deduction = fields.Float(string="Employee's Deduction", default=0.0, config_parameter='non_saudi_employee_deduction')
    non_saudi_employer_deduction = fields.Float(string="Employer's Deduction", default=2.0, config_parameter='non_saudi_employer_deduction')

    def set_values(self):
        res = super(HRPayrollSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'saudi_employee_deduction', self.saudi_employee_deduction)
        self.env['ir.config_parameter'].sudo().set_param(
            'saudi_employer_deduction', self.saudi_employer_deduction)
        self.env['ir.config_parameter'].sudo().set_param(
            'non_saudi_employee_deduction', self.non_saudi_employee_deduction)
        self.env['ir.config_parameter'].sudo().set_param(
            'non_saudi_employer_deduction', self.non_saudi_employer_deduction)

        return res
