# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
from odoo import models, fields, api, exceptions
import math
import logging

_logger = logging.getLogger(__name__)


class Company(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    settlement_journal_id = fields.Many2one(comodel_name="account.journal", string="Default Payment Journal", )
    expense_journal_id = fields.Many2one(comodel_name="account.journal", string="Default Expense Journal", )
    expense_account_id = fields.Many2one(comodel_name="account.account", string="Expense Account", )
    category_id = fields.Many2one(comodel_name="hr.salary.rule.category", string="Salary Net Category",
                                  required=False, )
    number_of_hours_per_day = fields.Float(default=8)
    

class ResConfigSettings(models.TransientModel):
    _name = 'res.config.settings'
    _inherit = 'res.config.settings'

    settlement_journal_id = fields.Many2one(comodel_name="account.journal", related="company_id.settlement_journal_id",
                                            readonly=False)
    expense_journal_id = fields.Many2one(comodel_name="account.journal", related="company_id.expense_journal_id",
                                         readonly=False)
    expense_account_id = fields.Many2one(comodel_name="account.account", related="company_id.expense_account_id",
                                         readonly=False)
    category_id = fields.Many2one(comodel_name="hr.salary.rule.category", related="company_id.category_id",
                                  readonly=False)
    number_of_hours_per_day = fields.Float(related='company_id.number_of_hours_per_day', readonly=False)

    gosi_for_exit_bool = fields.Boolean(string="Gosi Calculation (Y/N)",default = False,readonly=False,config_parameter="hr_end_service_benefits.gosi_for_exit_bool" )
    
    gosi_amount = fields.Float(string="Gosi Amount", default = 0.0975, digits=(16, 4),config_parameter = "hr_end_service_benefits.gosi_amount")
    
    
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        # self.ensure_one()
        self.env['ir.config_parameter'].sudo().set_param('hr_end_service_benefits.gosi_for_exit_bool', self.gosi_for_exit_bool)
        self.env['ir.config_parameter'].sudo().set_param('hr_end_service_benefits.gosi_amount',self.gosi_amount)
        return res
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            gosi_for_exit_bool=params.get_param('hr_end_service_benefits.gosi_for_exit_bool'),
            gosi_amount=params.get_param('hr_end_service_benefits.gosi_amount')
        )
        return res
    
    
    
# class contract(models.Model):
#     _inherit = 'hr.contract'
#
#     net_payment = fields.Float(string="Net Payment")


