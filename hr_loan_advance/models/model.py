# # -*- coding: utf-8 -*-
# from odoo import models, fields, api, _
# from odoo.exceptions import except_orm, Warning, RedirectWarning
# import odoo.addons.decimal_precision as dp
# from dateutil.relativedelta import relativedelta
# from datetime import datetime
# from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
#
#
#
# def _get_employee(obj):
#     ids = obj.env['hr.employee'].search([('user_id', '=', obj.env.uid)])
#     if ids:
#         return ids[0]
#     else:
#         raise Warning(_('The user is not an employee.'))
#     return False
#
#
# class hr_employee_loan_line_ps(models.Model):
#     _name = 'hr.employee.loan.line.ps'
#
#     hr_employee_loan_ps = fields.Many2one('hr.employee.loan.ps', string='HR Employee Loan', required=True,
#                                           ondelete='cascade', index=True, )
#     name = fields.Char(string='Installment Name', size=64, required=True, index=1, readonly=False,
#                        states={'deducted': [('readonly', True)], })
#     sequence = fields.Integer(string='Sequence', required=True, readonly=False,
#                               states={'deducted': [('readonly', True)], })
#     amount = fields.Monetary(string='Current Installment', digits='Account', required=True,
#                           readonly=False, states={'deducted': [('readonly', True)], })
#     remaining_value = fields.Monetary(string='Next Period Installment', digits='Account',
#                                    required=True, readonly=False, states={'deducted': [('readonly', True)], })
#     installment_value = fields.Monetary(string='Amount Already Paid', digits='Account',
#                                      required=True, readonly=False, states={'deducted': [('readonly', True)], })
#     installment_date = fields.Date(string='Installment Date', index=1, readonly=False,
#                                    states={'deducted': [('readonly', True)], })
#     confirm = fields.Boolean(string='Confirm', readonly=False, states={'deducted': [('readonly', True)], },
#                              default=False)
#     state = fields.Selection([('deducted', 'Deducted'), ('notdeducted', 'Not Deducted')], string='Status',
#                              readonly=True, track_visibility='onchange', default='notdeducted')
#     currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
#
#
#     def unlink(self):
#         if self.state not in ('notdeducted', False):
#             raise Warning(_('You cannot delete record which is Deducted.'))
#         return models.Model.unlink(self)
#
#
# class hr_employee_loan_type_ps(models.Model):
#     _name = 'hr.employee.loan.type.ps'
#
#     name = fields.Char(string='Name', required=True)
#     is_annual = fields.Boolean("Annual Vacation")
#
#
# class hr_employee_loan_ps(models.Model):
#     _name = 'hr.employee.loan.ps'
#     _inherit = ['mail.thread', 'resource.mixin']
#
#     def _get_currency(self):
#         user = self.env['res.users'].browse([self.env.uid])[0]
#         return user.company_id.currency_id.id
#
#
#     def _old_loan_remaining(self):
#         loan_obj = self.env['hr.employee.loan.ps']
#         loan_line_obj = self.env['hr.employee.loan.line.ps']
#         amount = 0
#         if self.employee_id:
#             loan_ids = loan_obj.search(
#                 [('employee_id', '=', self.employee_id.id), ('state', '=', 'approve'), ('id', '!=', self.id)])
#             for loan in loan_ids:
#                 loan_line_ids = loan_line_obj.search(
#                     [('hr_employee_loan_ps', '=', loan.id), ('state', '=', 'notdeducted')])
#                 for loan_line in loan_line_ids: amount += loan_line.amount
#         self.old_loan_remaining = amount
#
#
#     def _warning(self):
#         self.warning = ''
#         amount_to_ins, ins_per_month, remaining_value, loan_month_ins, y, installment_value = self.compute_installment_value(
#             False)
#         contract_ids = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)], limit=1,
#                                                       order='id desc')
#         if self.contract_id:
#             if ins_per_month >= self.contract_id.wage: self.warning = 'Warning! Current Installment is greater or equal to employee contract wage.'
#
#         else:
#             self.warning = 'Warning! Please choose contract.'
#         if not contract_ids: self.warning = 'Warning! There is no contract for this employee.'
#
#
#     def _get_ins_amount(self):
#         total_amount = paid_amount = total_installment = paid_installment = 0
#         for line in self.hr_employee_loan_line_ps:
#             if line.state == 'deducted':
#                 paid_amount += line.amount
#                 paid_installment += 1
#             total_amount += line.amount
#             total_installment += 1
#         self.total_amount = total_amount
#         self.paid_amount = paid_amount
#         self.balance_amount = total_amount - paid_amount
#         self.paid_installment = paid_installment
#         self.unpaid_installment = total_installment - paid_installment
#
#
#     def _get_current_user(self):
#         self.current_user = False
#         if ((self.guarantor_id) and (self.guarantor_id.user_id)) and self.guarantor_id.user_id.id == self.env.uid:
#             self.current_user = True
#
#     name = fields.Char(string='Loan Reference', default=lambda self: _('New'))
#     employee_id = fields.Many2one('hr.employee', string='Employee', required=True, default=_get_employee)
#     contract_id = fields.Many2one('hr.contract', string='Contract')
#     type_id = fields.Many2one('hr.employee.loan.type.ps', string='Loan Type', required=True)
#     request_date = fields.Date(string='Request Date')
#     move_id = fields.Many2one('account.move', string='Journal Entry')
#     company_id = fields.Many2one('res.company', string='Company', required=True,
#                                  default=lambda self: self.env['res.company']._company_default_get(
#                                      'hr.employee.loan.ps'))
#     loan_amount_required = fields.Monetary(string='Loan Amount Required', required=True, digits='Account', copy=False)
#     loan_amount = fields.Float(string='Loan Amount Approved')
#     loan_month_ins = fields.Integer(string='Number of Installments')
#     loan_ins_start_date = fields.Date(string='Installment Start Date')
#     loan_open = fields.Boolean(string='Loan Open')
#     hr_employee_loan_line_ps = fields.One2many('hr.employee.loan.line.ps', 'hr_employee_loan_ps', string='Loan Line')
#     currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=_get_currency)
#     employee_comment = fields.Text(string='Comments')
#     hr_comment = fields.Text(string='Comments')
#     account_comment = fields.Text(string='Comments')
#     warning = fields.Text(string='Warning', compute='_warning')
#     old_loan_remaining = fields.Float(string='Old Loan Remaining Amount', compute='_old_loan_remaining')
#     total_amount = fields.Float(string='Total Amount', compute='_get_ins_amount')
#     paid_amount = fields.Float(string='Paid Amount', compute='_get_ins_amount')
#     balance_amount = fields.Float(string='Balance Amount', compute='_get_ins_amount')
#     paid_installment = fields.Integer(string='Paid Installment', compute='_get_ins_amount')
#     unpaid_installment = fields.Integer(string='Unpaid Installment', compute='_get_ins_amount')
#     current_user = fields.Boolean(string='Current User', readonly=True, compute='_get_current_user')
#     allow_another_loan = fields.Boolean(string='Allow Another Loan')
#     guarantor_id = fields.Many2one('hr.employee', string='Guarantor')
#     guarantor_user_id = fields.Many2one('res.users', string='Guarantor User', readonly=True)
#     guarantor_date = fields.Datetime(string='Confirmed Date', readonly=True)
#     hr_manager_id = fields.Many2one('res.users', string='HR Manager', readonly=True)
#     hr_manager_date = fields.Datetime(string='Confirmed Date', readonly=True)
#     account_manager_id = fields.Many2one('res.users', string='Account Manager', readonly=True)
#     account_manager_date = fields.Datetime(string='Confirmed Date', readonly=True)
#
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('request', 'Request Sent'),
#         ('guarantor_approve', 'Guarantor Confirmed'),
#         ('progress', 'Waiting for DM Approval'),
#         ('progress2', 'Waiting for HR Manager Approval'),
#         ('progress3', 'Waiting for FM Approval'),
#         ('approve', 'Approved'),
#         ('refuse', 'Refused'),
#
#     ], string='Status', readonly=True, track_visibility='onchange', default='draft')
#
#     @api.constrains('guarantor_id')
#     def _guarantor_constrains(self):
#         if (self.guarantor_id):
#             guarantor_ids = self.env['hr.employee.loan.ps'].search(
#                 [('employee_id', '=', self.guarantor_id.id), ('balance_amount', '>', 0)])
#             if guarantor_ids: raise Warning(_('The Guarantor has already unpaid loan, So he cannot be a Gaurantor'))
#
#     @api.onchange('employee_id')
#     def _onchange_employee(self):
#         self.contract_id = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)], limit=1,
#                                                           order='id desc').id
#
#     @api.model
#     def create(self, values):
#         if values.get('name', 'New') == 'New':
#             values['name'] = self.env['ir.sequence'].next_by_code('hr.employee.loan.ps') or 'New'
#         result = super(hr_employee_loan_ps, self).create(values)
#         return result
#
#
#     def unlink(self):
#         if self.state not in ('draft', False):
#             raise Warning(_('You cannot delete record which is not in Draft.'))
#         return models.Model.unlink(self)
#
#
#     def action_request(self):
#         if self.loan_amount_required <= 0: raise Warning(_('Loan Amount Required must be greater than Zero!'))
#         config = self.env['hr.config.settings']._get_limit_of_loan_advance()
#         if self.type_id.is_annual:
#             year_bef = datetime.now() - relativedelta(years=1)
#             if self.employee_id.aj_date and datetime.strptime(self.employee_id.aj_date,DEFAULT_SERVER_DATETIME_FORMAT) > year_bef:
#                 raise Warning(_('You are not eligible to apply for Annual Loan!'))
#             if not self.employee_id.aj_date:
#                 raise Warning(_('You are not eligible to apply for Annual Loan!'))
#
#         if config:
#             if config.limit_of_loan == 'amount':
#                 if self.loan_amount_required > config.loan_amount: raise Warning(_('Over limit loan amount required!'))
#             elif config.limit_of_loan == 'basic':
#                 if not self.contract_id: raise Warning(_('There is no contract.Please contact administrator!'))
#                 amount = self.contract_id.wage * config.loan_months
#                 if self.loan_amount_required > amount: raise Warning(_('Over limit loan amount required!'))
#         return self.write(
#             {'state': 'request', 'loan_amount': self.loan_amount_required, 'request_date': fields.date.today()})
#
#
#     def action_guarantor_approve(self):
#         return self.write(
#             {'state': 'guarantor_approve', 'guarantor_user_id': self.env.uid, 'guarantor_date': fields.date.today()})
#
#
#     def action_progress(self):
#         return self.write({'state': 'progress', 'hr_manager_id': self.env.uid, 'hr_manager_date': fields.date.today()})
#
#
#     def action_approve(self):
#         if not self.allow_another_loan and self.old_loan_remaining > 0: raise Warning(
#             _('The Employee has already loan with balance.Please allow another loan or refuse!'))
#         self.compute_installment_board()
#         move_id = self.generate_entry()
#         return self.write({'state': 'approve', 'move_id': move_id, 'account_manager_id': self.env.uid,
#                            'account_manager_date': fields.date.today()})
#
#
#     def action_refuse(self):
#         return self.write({'state': 'refuse'})
#
#
#     def check_detucted(self):
#         result = False
#         for record in self.hr_employee_loan_line_ps:
#             if record.state == 'deducted': result = True
#         return result
#
#
#     def update_detucted(self, update):
#         installment_value = tot_current_value = rem_value = t = 0
#         for installment_lin_deducted in self.hr_employee_loan_line_ps:
#             if installment_lin_deducted.state == 'deducted':
#                 tot_current_value = tot_current_value + installment_lin_deducted.amount
#                 rem_value = self.loan_amount - tot_current_value
#                 t += 1
#                 name_temp = str(self.name) + ' - ' + str(t) + '/' + str(self.loan_month_ins)
#                 if update: self.env.cr.execute(
#                     "update hr_employee_loan_line_ps set installment_value = %s,remaining_value = %s,name = '%s' where id = %s" % (
#                     installment_value, rem_value, name_temp, installment_lin_deducted.id))
#                 installment_value = installment_value + installment_lin_deducted.amount
#         return tot_current_value, t, installment_value
#
#
#     def compute_installment_value(self, update):
#         amount_to_ins = ins_per_month = installment_value = remaining_value = loan_month_ins = t = 0
#         if self.check_detucted():
#             tot_current_value, t, installment_value = self.update_detucted(update)
#             amount_to_ins = self.loan_amount - tot_current_value
#             if (self.loan_month_ins - t) > 0: ins_per_month = amount_to_ins / (self.loan_month_ins - t)
#             remaining_value = amount_to_ins - ins_per_month
#             loan_month_ins = (self.loan_month_ins - t)
#         else:
#             amount_to_ins = self.loan_amount
#             if self.loan_month_ins > 0: ins_per_month = amount_to_ins / self.loan_month_ins
#             remaining_value = amount_to_ins - ins_per_month
#             loan_month_ins = self.loan_month_ins
#         return amount_to_ins, ins_per_month, remaining_value, loan_month_ins, t, installment_value
#
#
#     def compute_installment_board(self):
#         if self.loan_amount_required <= 0: raise Warning(_('Loan Amount must be greater than Zero!'))
#         if self.loan_month_ins <= 0: raise Warning(_('Number of Installments must be greater than Zero!'))
#         if not self.loan_ins_start_date: raise Warning(_('Choose Installment Start Date'))
#         loan_ins_start_date = fields.datetime.strptime(self.loan_ins_start_date, '%Y-%m-%d')
#         for record in self.hr_employee_loan_line_ps:
#             if record.state == 'notdeducted':
#                 record.unlink()
#             else:
#                 loan_ins_start_date = (
#                 fields.datetime.strptime(record.installment_date, '%Y-%m-%d') + relativedelta(months=+1))
#         amount_to_ins, ins_per_month, remaining_value, loan_month_ins, t, installment_value = self.compute_installment_value(
#             True)
#         for x in range(0, loan_month_ins):
#             installment_date = (loan_ins_start_date + relativedelta(months=+x))
#             i = x + 1 + t
#             vals = {
#                 'amount': ins_per_month,
#                 'hr_employee_loan_ps': self.id,
#                 'sequence': i,
#                 'name': str(self.name) + ' - ' + str(i) + '/' + str(self.loan_month_ins),
#                 'remaining_value': remaining_value,
#                 'installment_value': installment_value,
#                 'installment_date': installment_date.strftime('%Y-%m-%d'),
#                 'confirm': True,
#             }
#             self.env['hr.employee.loan.line.ps'].create(vals)
#             installment_value = installment_value + ins_per_month
#             remaining_value = remaining_value - ins_per_month
#         return True
#
#
#     def generate_entry(self):
#         move_obj = self.env['account.move']
#         move_line_obj = self.env['account.move.line']
#         nazar_obj = self.env['account.nazar']
#         company_currency = self.company_id.currency_id.id
#         diff_currency_p = self.currency_id.id != company_currency
#         if not self.employee_id.address_home_id: raise Warning(_('Please set the home address for employee'))
#         ref = self.employee_id.name + '/' + self.name
#         config = self.env['hr.accounting.config']._get_hr_accounting_config()
#         if not config or not config.loan_journal_id: raise Warning(_('Journal is not configure.'))
#         journal_id = config.loan_journal_id
#         if not journal_id.default_debit_account_id or not journal_id.default_credit_account_id:
#             raise Warning(
#                 _('Missing credit or debit account for journal.Please set credit and debit account for journal.'))
#         # move_id = move_obj.create(nazar_obj.account_move_get(self, journal_id, date=fields.datetime.today(), ref=ref,
#         #                                                      company_id=self.company_id.id))
#
#         vals = {
#             'journal_id': journal_id.id,
#             'date': fields.datetime.today(),
#             # 'period_id': period_obj.find(date)[0],
#             'ref': '',
#             'company_id': self.company_id.id,
#         }
#
#         line1 = [(0, 0, {
#             #'move_id': move_id.id,
#             'journal_id': journal_id.id,
#             'partner_id': self.employee_id.address_home_id.id,
#             'credit': 0,
#             'debit': self.loan_amount,
#             # 'centralisation': 'normal',
#             'company_id': self.company_id.id,
#             'state': 'valid',
#             'blocked': False,
#             'account_id': journal_id.default_debit_account_id.id,
#             #'period_id': move_id.period_id.id,
#             'name': 'Loan',
#             'amount_currency': diff_currency_p and self.currency_id.id or False,
#             'quantity': 1,
#
#             })]
#         line1.append((0, 0, {
#             #'move_id': move_id.id,
#             'journal_id': journal_id.id,
#             'partner_id': self.employee_id.address_home_id.id,
#             'credit': self.loan_amount,
#             'debit': 0,
#             # 'centralisation': 'normal',
#             'company_id': self.company_id.id,
#             'state': 'valid',
#             'blocked': False,
#             'account_id': self.employee_id.address_home_id.property_account_payable_id.id,
#             #'period_id': move_id.period_id.id,
#             'name': '/',
#             'amount_currency': diff_currency_p and self.currency_id.id or False,
#             'quantity': 1,
#
#         }))
#
#         vals.update({'line_ids': line1})
#
#         move_id = move_obj.create(vals)
#         return move_id.id
#
#
#     def action_draft(self):
#         return self.write({'state': 'draft'})
#
#
# class hr_employee_advance_line_ps(models.Model):
#     _name = 'hr.employee.advance.line.ps'
#
#     hr_employee_advance_ps = fields.Many2one('hr.employee.advance.ps', string='HR Employee Advance', required=True,
#                                              ondelete='cascade', index=True, )
#     name = fields.Char(string='Installment Name', size=64, required=True, index=1, readonly=False,
#                        states={'deducted': [('readonly', True)], })
#     sequence = fields.Integer(string='Sequence', required=True, readonly=False,
#                               states={'deducted': [('readonly', True)], })
#     amount = fields.Monetary(string='Current Installment', digits='Account', required=True,
#                           readonly=False, states={'deducted': [('readonly', True)], })
#     remaining_value = fields.Monetary(string='Next Period Installment', digits='Account',
#                                    required=True, readonly=False, states={'deducted': [('readonly', True)], })
#     installment_value = fields.Monetary(string='Amount Already Paid', digits='Account',
#                                      required=True, readonly=False, states={'deducted': [('readonly', True)], })
#     installment_date = fields.Date(string='Installment Date', index=1, readonly=False,
#                                    states={'deducted': [('readonly', True)], })
#     confirm = fields.Boolean(string='Confirm', readonly=False, states={'deducted': [('readonly', True)], },
#                              default=False)
#     state = fields.Selection([('deducted', 'Deducted'), ('notdeducted', 'Not Deducted')], string='Status',
#                              readonly=True, track_visibility='onchange', default='notdeducted')
#     currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
#
#
#     def unlink(self):
#         if self.state not in ('notdeducted', False):
#             raise Warning(_('You cannot delete record which is Deducted.'))
#         return models.Model.unlink(self)
#
#
# class hr_employee_advance_type_ps(models.Model):
#     _name = 'hr.employee.advance.type.ps'
#
#     name = fields.Char(string='Name', required=True)
#
#
# class hr_employee_advance_ps(models.Model):
#     _name = 'hr.employee.advance.ps'
#     _inherit = ['mail.thread', 'resource.mixin']
#
#     def _get_currency(self):
#         user = self.env['res.users'].browse([self.env.uid])[0]
#         return user.company_id.currency_id.id
#
#
#     def _old_advance_remaining(self):
#         advance_obj = self.env['hr.employee.advance.ps']
#         advance_line_obj = self.env['hr.employee.advance.line.ps']
#         amount = 0
#         if self.employee_id:
#             advance_ids = advance_obj.search(
#                 [('employee_id', '=', self.employee_id.id), ('state', '=', 'approve'), ('id', '!=', self.id)])
#             for advance in advance_ids:
#                 advance_line_ids = advance_line_obj.search(
#                     [('hr_employee_advance_ps', '=', advance.id), ('state', '=', 'notdeducted')])
#                 for advance_line in advance_line_ids: amount += advance_line.amount
#         self.old_advance_remaining = amount
#
#
#     def _warning(self):
#         self.warning = ''
#         amount_to_ins, ins_per_month, remaining_value, advance_month_ins, y, installment_value = self.compute_installment_value(
#             False)
#         contract_ids = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)], limit=1,
#                                                       order='id desc')
#         if self.contract_id:
#             if ins_per_month >= self.contract_id.wage: self.warning = 'Warning! Current Installment is greater or equal to employee contract wage.'
#
#         else:
#             self.warning = 'Warning! Please choose contract.'
#         if not contract_ids: self.warning = 'Warning! There is no contract for this employee.'
#
#
#     def _get_ins_amount(self):
#         total_amount = paid_amount = total_installment = paid_installment = 0
#         for line in self.hr_employee_advance_line_ps:
#             if line.state == 'deducted':
#                 paid_amount += line.amount
#                 paid_installment += 1
#             total_amount += line.amount
#             total_installment += 1
#         self.total_amount = total_amount
#         self.paid_amount = paid_amount
#         self.balance_amount = total_amount - paid_amount
#         self.paid_installment = paid_installment
#         self.unpaid_installment = total_installment - paid_installment
#
#     name = fields.Char(string='Advance Reference', default=lambda self: _('New'))
#     employee_id = fields.Many2one('hr.employee', string='Employee', required=True, default=_get_employee)
#     contract_id = fields.Many2one('hr.contract', string='Contract')
#     type_id = fields.Many2one('hr.employee.advance.type.ps', string='Advance Type', required=True)
#     request_date = fields.Date(string='Request Date')
#     move_id = fields.Many2one('account.move', string='Journal Entry')
#     company_id = fields.Many2one('res.company', string='Company', required=True,
#                                  default=lambda self: self.env['res.company']._company_default_get(
#                                      'hr.employee.advance.ps'))
#     advance_amount_required = fields.Float(string='Advance Amount Required', required=True)
#     advance_amount = fields.Float(string='Advance Amount Approved')
#     advance_month_ins = fields.Integer(string='Number of Installments')
#     advance_ins_start_date = fields.Date(string='Installment Start Date')
#     advance_open = fields.Boolean(string='Advance Open')
#     hr_employee_advance_line_ps = fields.One2many('hr.employee.advance.line.ps', 'hr_employee_advance_ps',
#                                                   string='Advance Line')
#     currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=_get_currency)
#     employee_comment = fields.Text(string='Comments')
#     hr_comment = fields.Text(string='Comments')
#     account_comment = fields.Text(string='Comments')
#     warning = fields.Text(string='Warning', compute='_warning')
#     old_advance_remaining = fields.Float(string='Old Advance Remianing Amount', compute='_old_advance_remaining')
#     total_amount = fields.Float(string='Total Amount', compute='_get_ins_amount')
#     paid_amount = fields.Float(string='Paid Amount', compute='_get_ins_amount')
#     balance_amount = fields.Float(string='Balance Amount', compute='_get_ins_amount')
#     paid_installment = fields.Integer(string='Paid Installment', compute='_get_ins_amount')
#     unpaid_installment = fields.Integer(string='Unpaid Installment', compute='_get_ins_amount')
#     allow_another_advance = fields.Boolean(string='Allow Another Advance')
#     hr_manager_id = fields.Many2one('res.users', string='HR Manager', readonly=True)
#     hr_manager_date = fields.Datetime(string='Confirmed Date', readonly=True)
#     account_manager_id = fields.Many2one('res.users', string='Account Manager', readonly=True)
#     account_manager_date = fields.Datetime(string='Confirmed Date', readonly=True)
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('request', 'Request Sent'),
#         ('progress', 'Waiting for Approval'),
#         ('approve', 'Approved'),
#         ('refuse', 'Refused'),
#
#     ], string='Status', readonly=True, track_visibility='onchange', default='draft')
#
#     @api.model
#     def create(self, values):
#         if values.get('name', 'New') == 'New':
#             values['name'] = self.env['ir.sequence'].next_by_code('hr.employee.advance.ps') or 'New'
#         result = super(hr_employee_advance_ps, self).create(values)
#         return result
#
#
#     def unlink(self):
#         if self.state not in ('draft', False):
#             raise Warning(_('You cannot delete record which is not in Draft.'))
#         return models.Model.unlink(self)
#
#     @api.onchange('employee_id')
#     def _onchange_employee(self):
#         self.contract_id = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)], limit=1,
#                                                           order='id desc').id
#
#
#     def action_request(self):
#         if self.advance_amount_required <= 0: raise Warning(_('Advance Amount Required must be greater than Zero!'))
#         config = self.env['hr.config.settings']._get_limit_of_loan_advance()
#         if config:
#             if config.limit_of_advance == 'amount':
#                 if self.advance_amount_required > config.advance_amount: raise Warning(
#                     _('Over limit advance amount required!'))
#             elif config.limit_of_advance == 'basic':
#                 if not self.contract_id:
#                     contract = self.env['hr.contract'].search(['employee_id', '=', self.employee_id.id])
#                     if not contract:
#                         raise Warning(_('There is no contract for this employee.Please contact administrator!'))
#                     else:
#                         raise Warning(_('Please choose contract!'))
#                 amount = self.contract_id.wage * config.advance_months
#                 if self.advance_amount_required > amount: raise Warning(_('Over limit advance amount required!'))
#         return self.write(
#             {'state': 'request', 'advance_amount': self.advance_amount_required, 'request_date': fields.date.today()})
#
#
#     def action_progress(self):
#         return self.write({'state': 'progress', 'hr_manager_id': self.env.uid, 'hr_manager_date': fields.date.today()})
#
#
#     def action_draft(self):
#         return self.write({'state': 'draft'})
#
#
#     def action_approve(self):
#         if not self.allow_another_advance and self.old_advance_remaining > 0: raise Warning(
#             _('The Employee has already advance with balance.Please allow another advance or refuse!'))
#         self.compute_installment_board()
#         move_id = self.generate_entry()
#         return self.write({'state': 'approve', 'move_id': move_id, 'account_manager_id': self.env.uid,
#                            'account_manager_date': fields.date.today()})
#
#
#     def action_refuse(self):
#         return self.write({'state': 'refuse'})
#
#
#     def check_detucted(self):
#         result = False
#         for record in self.hr_employee_advance_line_ps:
#             if record.state == 'deducted': result = True
#         return result
#
#
#     def update_detucted(self, update):
#         installment_value = tot_current_value = rem_value = t = 0
#         for installment_lin_deducted in self.hr_employee_advance_line_ps:
#             if installment_lin_deducted.state == 'deducted':
#                 tot_current_value = tot_current_value + installment_lin_deducted.amount
#                 rem_value = self.advance_amount - tot_current_value
#                 t += 1
#                 name_temp = str(self.name) + ' - ' + str(t) + '/' + str(self.advance_month_ins)
#                 if update: self.env.cr.execute(
#                     "update hr_employee_advance_line_ps set installment_value = %s,remaining_value = %s,name = '%s' where id = %s" % (
#                     installment_value, rem_value, name_temp, installment_lin_deducted.id))
#                 installment_value = installment_value + installment_lin_deducted.amount
#         return tot_current_value, t, installment_value
#
#
#     def compute_installment_value(self, update):
#         amount_to_ins = ins_per_month = installment_value = remaining_value = advance_month_ins = t = 0
#         if self.check_detucted():
#             tot_current_value, t, installment_value = self.update_detucted(update)
#             amount_to_ins = self.advance_amount - tot_current_value
#             if (self.advance_month_ins - t) > 0: ins_per_month = amount_to_ins / (self.advance_month_ins - t)
#             remaining_value = amount_to_ins - ins_per_month
#             advance_month_ins = (self.advance_month_ins - t)
#         else:
#             amount_to_ins = self.advance_amount
#             if self.advance_month_ins > 0: ins_per_month = amount_to_ins / self.advance_month_ins
#             remaining_value = amount_to_ins - ins_per_month
#             advance_month_ins = self.advance_month_ins
#         return amount_to_ins, ins_per_month, remaining_value, advance_month_ins, t, installment_value
#
#
#     def compute_installment_board(self):
#         if self.advance_amount <= 0: raise Warning(_('Advance Amount must be greater than Zero!'))
#         if self.advance_month_ins <= 0: raise Warning(_('Number of Installments must be greater than Zero!'))
#         if not self.advance_ins_start_date: raise Warning(_('Choose Installment Start Date'))
#         advance_ins_start_date = fields.datetime.strptime(self.advance_ins_start_date, '%Y-%m-%d')
#         for record in self.hr_employee_advance_line_ps:
#             if record.state == 'notdeducted': record.unlink()
#         amount_to_ins, ins_per_month, remaining_value, advance_month_ins, t, installment_value = self.compute_installment_value(
#             True)
#         for x in range(0, advance_month_ins):
#             installment_date = (advance_ins_start_date + relativedelta(months=+x))
#             i = x + 1 + t
#             vals = {
#                 'amount': ins_per_month,
#                 'hr_employee_advance_ps': self.id,
#                 'sequence': i,
#                 'name': str(self.name) + ' - ' + str(i) + '/' + str(self.advance_month_ins),
#                 'remaining_value': remaining_value,
#                 'installment_value': installment_value,
#                 'installment_date': installment_date.strftime('%Y-%m-%d'),
#                 'confirm': True,
#             }
#             self.env['hr.employee.advance.line.ps'].create(vals)
#             installment_value = installment_value + ins_per_month
#             remaining_value = remaining_value - ins_per_month
#         return True
#
#
#     def generate_entry(self):
#         move_obj = self.env['account.move']
#         move_line_obj = self.env['account.move.line']
#         nazar_obj = self.env['account.nazar']
#         company_currency = self.company_id.currency_id.id
#         diff_currency_p = self.currency_id.id != company_currency
#         if not self.employee_id.address_home_id: raise Warning(_('Please set the home address for employee'))
#         ref = self.employee_id.name + '/' + self.name
#         config = self.env['hr.accounting.config']._get_hr_accounting_config()
#         if not config or not config.advance_journal_id: raise Warning(_('Journal is not configure.'))
#         journal_id = config.advance_journal_id
#         if not journal_id.default_debit_account_id or not journal_id.default_credit_account_id:
#             raise Warning(
#                 _('Missing credit or debit account for journal.Please set credit and debit account for journal.'))
#         # move_id = move_obj.create(nazar_obj.account_move_get(self, journal_id, date=fields.datetime.today(), ref=ref,
#         #                                                      company_id=self.company_id.id))
#
#         vals = {
#             'journal_id': journal_id.id,
#             'date': fields.datetime.today(),
#             # 'period_id': period_obj.find(date)[0],
#             'ref': '',
#             'company_id': self.company_id.id,
#         }
#
#         line1 = [(0, 0, {
#             #'move_id': move_id.id,
#             'journal_id': journal_id.id,
#             'partner_id': self.employee_id.address_home_id.id,
#             'credit': 0,
#             'debit': self.advance_amount,
#             # 'centralisation': 'normal',
#             'company_id': self.company_id.id,
#             'state': 'valid',
#             'blocked': False,
#             'account_id': journal_id.default_debit_account_id.id,
#             #'period_id': move_id.period_id.id,
#             'name': 'Advance',
#             'amount_currency': diff_currency_p and self.currency_id.id or False,
#             'quantity': 1,
#
#         })]
#         line1.append((0, 0, {
#             #'move_id': move_id.id,
#             'journal_id': journal_id.id,
#             'partner_id': self.employee_id.address_home_id.id,
#             'credit': self.advance_amount,
#             'debit': 0,
#             # 'centralisation': 'normal',
#             'company_id': self.company_id.id,
#             'state': 'valid',
#             'blocked': False,
#             'account_id': self.employee_id.address_home_id.property_account_payable_id.id,
#             #'period_id': move_id.period_id.id,
#             'name': '/',
#             'amount_currency': diff_currency_p and self.currency_id.id or False,
#             'quantity': 1,
#
#         }))
#
#         vals.update({'line_ids': line1})
#
#         move_id = move_obj.create(vals)
#
#         return move_id.id
#
#
#
