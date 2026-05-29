# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import warnings, RedirectWarning
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT



def _get_employee(obj):
    ids = obj.env['hr.employee'].search([('user_id', '=', obj.env.uid)])
    if ids:
        return ids[0]
    else:
        raise warnings.warn(_('The user is not an employee.'))
    return False

class hr_employee_advance_line_ps(models.Model):
    _name = 'hr.employee.advance.line.ps'

    hr_employee_advance_ps = fields.Many2one('hr.employee.advance.ps', string='HR Employee Advance', required=True,
                                             ondelete='cascade', index=True, )
    name = fields.Char(string='Installment Name', size=64, required=True, index=1, readonly=True)
    sequence = fields.Integer(string='Sequence', required=True, readonly=True)
    amount = fields.Monetary(string='Current Installment', digits='Account', required=True,
                          readonly=False)
    remaining_value = fields.Monetary(string='Next Period Installment', digits='Account',
                                   required=True, readonly=False)
    installment_value = fields.Monetary(string='Amount Already Paid', digits='Account',
                                     required=True, readonly=False)
    installment_date = fields.Date(string='Installment Date', index=1, readonly=False)
    confirm = fields.Boolean(string='Confirm', readonly=False,
                             default=False)
    state = fields.Selection([('deducted', 'Deducted'), ('notdeducted', 'Not Deducted')], string='Status',
                             readonly=True, tracking=True, default='notdeducted')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)


    def unlink(self):
        if self.state not in ('notdeducted', False):
            raise Warning(_('You cannot delete record which is Deducted.'))
        return models.Model.unlink(self)
