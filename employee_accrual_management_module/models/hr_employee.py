# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    custom_gratuity_generate = fields.Boolean(
        string='Grauity Generate?',
        default=True
    )
    # date_of_join = fields.Date(string="Date of Join", size=14, required=True)
    eos_amount = fields.Float(string='EOS Amount', store=True)
    eos_accrued_date = fields.Date(string='EOS Accrued Date')
    previous_eos_amount = fields.Float(string="Previous EOS Amount", invisible=True)