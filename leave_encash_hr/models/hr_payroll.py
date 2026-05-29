
from odoo import api, fields, models, _


class hr_payslip(models.Model):
    _inherit = 'hr.payslip'

    encash_leave = fields.Float(string="Encash Leave", compute='compute_salary_encash_leave')
    encash_amt = fields.Float(string="Encash Amount",compute='compute_salary_encash_leave')

    @api.depends('employee_id', 'date_from', 'date_to')
    def compute_salary_encash_leave(self):
        for rec in self:
            rec.encash_leave = False
            rec.encash_amt = False
            leave_to_encash = self.env['leave.encash'].search([
                            ('employee_id', '=', rec.employee_id.id),
                            ('state', '=', 'approved'),
                            ('date', '>=', rec.date_from),
                            ('date', '<=', rec.date_to)
                            ])
            for encash in leave_to_encash:
                if rec.employee_id:
                    rec.encash_leave += encash.days_want
                    rec.encash_amt += encash.amount
            # for encash in leave_to_encash:
            #         encash.state = 'paid'
            #         encash.payslip_id = self.id
