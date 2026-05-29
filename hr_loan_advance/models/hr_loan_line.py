# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import  warnings, RedirectWarning
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

class hr_employee_loan_line_ps(models.Model):
    _name = 'hr.employee.loan.line.ps'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    hr_employee_loan_ps = fields.Many2one('hr.employee.loan.ps', string='HR Employee Loan', required=True,
                                          ondelete='cascade', index=True, )
    name = fields.Char(string='Installment Name', size=64, required=True, index=1, readonly=False)
    sequence = fields.Integer(string='Sequence', required=True, readonly=False)
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

    reschedule_done = fields.Boolean(string="Reschedule Done", default=False)
        

    
    def reschedule_loan(self):
        for rec in self:
            if rec.state == 'notdeducted' and not rec.confirm:
                # Calculate the last installment date and add a new line
                last_installment = self.env['hr.employee.loan.line.ps'].search([
                    ('hr_employee_loan_ps', '=', rec.hr_employee_loan_ps.id)  # Reference rec, not self
                ], order='installment_date desc',limit=1)
                
                if last_installment:
                    # Add a month to the last installment date for the new installment
                    new_installment_date = last_installment.installment_date + relativedelta(months=+1)
                else:
                    # If there are no existing installments, start with the loan's start date
                    new_installment_date = rec.hr_employee_loan_ps.loan_ins_start_date + relativedelta(months=+rec.hr_employee_loan_ps.loan_month_ins)
                # # Create a new installment line with the missed installment amount
                vals = {
                    'amount': rec.amount,  
                    'hr_employee_loan_ps': rec.hr_employee_loan_ps.id,  # Correct reference
                    'sequence': last_installment.sequence + 1 if last_installment else 1,
                    'name': str(rec.hr_employee_loan_ps.name) + ' - Rescheduled/' + str(last_installment.sequence + 1) if last_installment else 'Extra/1',
                    'remaining_value': 0.0,
                    'installment_value': 0.0,
                    'installment_date': new_installment_date.strftime('%Y-%m-%d'),
                    'confirm': True,
                }

                self.env['hr.employee.loan.line.ps'].create(vals)
                self.reschedule_done = True
    
               
        
        return True

    # def reschedule_loan(self):
    #     for rec in self:
    #         # Check if the installment was not deducted
    #         if rec.state == 'notdeducted':
    #             # Calculate the last installment date and add a new line
    #             last_installment = self.env['hr.employee.loan.line.ps'].search([
    #                 ('hr_employee_loan_ps', '=', self.id)
    #             ], order='installment_date desc', limit=1)
    #
    #             if last_installment:
    #                 # Add a month to the last installment date for the new installment
    #                 new_installment_date = last_installment.installment_date + relativedelta(months=+1)
    #             else:
    #                 # If there are no existing installments, start with the loan's start date
    #                 new_installment_date = self.hr_employee_loan_ps.loan_ins_start_date + relativedelta(months=+self.hr_employee_loan_ps.loan_month_ins)
    #
    #             # Create a new installment line with the missed installment amount
    #             vals = {
    #                 'amount': rec.amount,  # Missed installment amount
    #                 'hr_employee_loan_ps': self.id,
    #                 'sequence': last_installment.sequence + 1 if last_installment else 1,
    #                 'name': str(self.hr_employee_loan_ps.name) + ' - Extra/' + str(last_installment.sequence + 1) if last_installment else 'Extra/1',
    #                 'remaining_value': last_installment.remaining_value if last_installment else 0.00,
    #                 'installment_value': last_installment.installment_value + rec.amount if last_installment else rec.amount,
    #                 'installment_date': new_installment_date.strftime('%Y-%m-%d'),
    #                 'confirm': True,
    #             }
    #
    #             # Create the new installment line
    #             self.env['hr.employee.loan.line.ps'].create(vals)
    #
    #             # Optional: Update the missed installment's state (if needed)
    #             rec.state = 'notdeducted'
    #
    #     return True


    def unlink(self):
        if self.state not in ('notdeducted', False):
            raise Warning(_('You cannot delete record which is Deducted.'))
        return models.Model.unlink(self)
