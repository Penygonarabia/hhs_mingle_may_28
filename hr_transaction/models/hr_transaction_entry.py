# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HrTransactionEntry(models.Model):

    _name = 'hr.transaction.entry'
    _rec_name = 'complete_name'
    _description = 'HR Transaction Entry'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin', 'rating.mixin']

    complete_name = fields.Char(string="Name", compute="_compute_complete_name")
    name = fields.Char('Seq No')
    transaction_type_id = fields.Many2one('hr.transaction.rule', string='Transaction Type', required=True)
    code = fields.Char('Code', required=True, related='transaction_type_id.code')
    rule_type = fields.Selection([('transaction_allowance', 'Allowance'), ('transaction_detection', 'Deduction'), ('charge out', 'Charge Out'), ('accrual', 'Accrual(Reserve)'), ('not_applicable', 'Not Applicable')],
                                 string='Rule Type', related='transaction_type_id.rule_type')

    unit_type = fields.Selection([('hour', 'Hours'), ('day', 'Days'), ('amount', 'Amount')], string='Unit Type', related='transaction_type_id.unit_type')
    fixed_amount = fields.Float('Fixed Amount')
    description = fields.Char('Description', required=True, translate=True)
    calculate_based_on_allowance = fields.Selection(string="Calculate Based On",
                                                    selection=[('wage', 'Basic'),
                                                                ('hra', 'HRA'),
                                                               ('wage_trv', 'Basic + Transport'),
                                                               ('wage_tr_fd','Basic + Transport + Food'),
                                                               ('hra_trv', 'HRA + Transport'),
                                                               ('hr_tr_sch', 'HRA + Transport + School'),
                                                               ('hr_tr_fd', 'HRA + Transport + Food'),
                                                               ('hr_tr_fl', 'HRA + Transport + Fuel'),
                                                               ('hr_tr_tk', 'HRA + Transport + Ticket'),
                                                               ('hr_tr_fx', 'HRA + Transport + Fixed'),
                                                               ('hr_tr_mb', 'HRA + Transport + Mobile'),
                                                               ('hr_tr_oth', 'HRA + Transport + Other'),
                                                               ('hr_tr_wk', 'HRA + Transport + Work'), ('all', 'All')],
                                                    default='wage', required=True)
    transact_visibility = fields.Boolean('Transaction Visibility', default=False)
    rate = fields.Float('Rate')

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('hr.transaction.entry') or ' '
        res = super(HrTransactionEntry, self).create(values)
        return res


    @api.onchange('transaction_type_id')
    def required_fixed_amount_rate(self):
        if self.transaction_type_id:
            self.transact_visibility = True
        else:
            self.transact_visibility = False

    # @api.constrains('transaction_type_id')
    # def dupl_transaction(self):
    #     if self.transaction_type_id:
    #         existing_transaction = self.env['hr.transaction.entry'].search(
    #             [('id', '!=', self.id), ('transaction_type_id', '=', self.transaction_type_id.id)])
    #         if existing_transaction:
    #             raise ValidationError(('Already Transaction Type %s is existing' % self.transaction_type_id.name))
    '''For time being constarint is removed'''
    # @api.constrains('fixed_amount', 'rate')
    # def check_fixed_amount(self):
    #     for rec in self:
    #         if rec.unit_type == 'amount':
    #             if rec.fixed_amount < 1:
    #                 raise ValidationError("'Fixed amount' must be greater than 0.")
    #         if rec.unit_type in ['days', 'hours']:
    #             if rec.rate < 1:
    #                 raise ValidationError("'Rate' must be greater than 0.")


    # def name_get(self):
    #     result = []
    #     for record in self:
    #         name = f'{record.description} {record.name}'
    #         result.append((record.id, name))
    #         print("result", result, name)
    #     return result

    @api.depends('description', 'name')
    def _compute_complete_name(self):
        for record in self:
            if record.description and record.name:
                record.complete_name = f'{record.description} {record.name}'
            else:
                record.complete_name = None
            # print("record.complete_name", record.complete_name)


    # def write(self, vals):
    #
    #     vals['transaction_type_id'] = vals['transaction_type_id']
    #     # vals['name']=
    #     return super(HrTransactionEntry, self).write(vals)

    @api.onchange('transaction_type_id')
    def _onchange_trasaction(self):
        for rec in self:
            rec.fixed_amount = 0
            rec.rate = 0

