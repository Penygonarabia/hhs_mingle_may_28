from odoo import api, fields, models, _


class hr_payslip(models.Model):
    _inherit = 'hr.payslip'

    terminal_amount = fields.Float(string="EOS Reward Amount", compute='compute_terminal_amount')
    
    eos_accured_leave = fields.Float(string="EOS Accured Leave", compute="compute_terminal_amount")
    
    eos_outstanding_loan = fields.Float(string="EOS Outstanding Loan", compute="compute_terminal_amount")
    
    eos_outstanding_advance = fields.Float(string="EOS Outstanding Advance", compute="compute_terminal_amount")


    @api.depends('employee_id', 'date_from', 'date_to')
    def compute_terminal_amount(self):
        for rec in self:
            rec.terminal_amount = False
            rec.eos_accured_leave = False
            rec.eos_outstanding_loan = False
            rec.eos_outstanding_advance = False
            terminal_amount = self.env['hr.end.service.benefit'].search([
                            ('employee_id', '=', rec.employee_id.id),
                            ('state', 'in', ['confirmed', 'validated', 'paid']),
                            ('termination_date', '>=', rec.date_from),
                            ('termination_date', '<=', rec.date_to)
                            ])
            for amount in terminal_amount:
                if rec.employee_id:
                    rec.terminal_amount += amount.total_deserved_amount
                    rec.eos_accured_leave += amount.total_holiday_deserved_amount
                    rec.eos_outstanding_loan += amount.outstanding_loan_amount
                    rec.eos_outstanding_advance += amount.outstanding_advance_amount
