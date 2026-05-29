from odoo import models, fields, api, _
from datetime import date, datetime, timedelta
from odoo.exceptions import AccessError, UserError, ValidationError



class HrLeave(models.Model):

    _inherit = 'hr.leave.type'

    transact_code_accrd_leave = fields.Many2one('hr.transaction.entry', string="Accrued Leave")
    transact_code_accrd_ticket = fields.Many2one('hr.transaction.entry', string="Accrued Ticket")
    transact_code_adv_payment = fields.Many2one('hr.transaction.entry', string="Advance Payment")
    prepare_payslip = fields.Boolean(string="Prepare payslip")
    monthly_carry_accrued_leave = fields.Boolean(string="Monthly Carry for Accrued Leave")
    full_accrued_leave = fields.Boolean(string="Full Accrued Leave")
    thirty_days_flag = fields.Boolean(string="Default to 30 Days",default=False)
    calendar_days_flag = fields.Boolean(string="Use Calendar Days",default=False)

    @api.constrains('monthly_carry_accrued_leave', 'full_accrued_leave', 'default_thirty_flag', 'calendar_days_flag')
    # @api.constrains('monthly_carry_accrued_leave', 'full_accrued_leave')
    def _check_accrued_leave_exclusivity(self):
        for rec in self:
            if rec.monthly_carry_accrued_leave and rec.full_accrued_leave:
                raise ValidationError(
                    "Only one of 'Monthly Carry for Accrued Leave' or 'Full Accrued Leave' can be true at a time.")

            if rec.thirty_days_flag and rec.calendar_days_flag:
                raise ValidationError(
                    "Only one of 'Default to 30 Days' or 'Use Calendar Days' can be true at a time.")