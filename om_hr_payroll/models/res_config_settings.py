# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_om_hr_payroll_account = fields.Boolean(string='Payroll Accounting')

    module_project_timesheet_holidays = fields.Boolean("Leave",
                                                       compute="_compute_timesheet_modules", store=True, readonly=False)

    module_project_timesheet_synchro = fields.Boolean("Awesome Timesheet",
                                                      compute="_compute_timesheet_modules", store=True, readonly=False)

    @api.depends('module_hr_timesheet')
    def _compute_timesheet_modules(self):
        self.filtered(lambda config: not config.module_hr_timesheet).update({
            'module_project_timesheet_synchro': False,
            'module_project_timesheet_holidays': False,
        })