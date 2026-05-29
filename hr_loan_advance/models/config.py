# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from ast import literal_eval
#from odoo.exceptions import except_orm, Warning, RedirectWarning

class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    # Relational Fields
    loan_journal_id = fields.Many2one('account.journal',help="The journal used when the loan is done.")
    advance_journal_id = fields.Many2one('account.journal',help="The journal used when the loan is done.")

# class hr_accounting_config(models.TransientModel):
#     _inherit = 'hr.accounting.config'
#
#     def _get_loan_journal(self):
#         config = self._get_hr_accounting_config()
#         if (config) and config.loan_journal_id: return config.loan_journal_id.id
#         return False
#
#     def _get_advance_journal(self):
#         config = self._get_hr_accounting_config()
#         if (config) and config.advance_journal_id: return config.advance_journal_id.id
#         return False
#
#     loan_journal_id = fields.Many2one('account.journal', string='Loan Journal',
#                                       help="The journal used when the loan is done.", default=_get_loan_journal)
#     advance_journal_id = fields.Many2one('account.journal', string='Advance Journal',
#                                          help="The journal used when the loan is done.", default=_get_advance_journal)
#
#
#
#     # @api.model
#     # def get_values(self):
#     #     res = super(hr_accounting_config, self).get_values()
#     #     get_param = self.env['ir.config_parameter'].get_param
#     #     advance_journal_id = literal_eval(get_param('hr_loan_advance.advance_journal_id', default='False'))
#     #     loan_journal_id = literal_eval(get_param('hr_loan_advance.loan_journal_id', default="False"))
#     #
#     #     res.update(
#     #         advance_journal_id=advance_journal_id,
#     #         loan_journal_id=loan_journal_id,
#     #     )
#     #     return res
#     #
#     #
#     # def set_values(self):
#     #     super(hr_accounting_config, self).set_values()
#     #     set_param = self.env['ir.config_parameter'].set_param
#     #     # we store the repr of the values, since the value of the parameter is a required string
#     #     set_param('hr_loan_advance.advance_journal_id', repr(self.advance_journal_id.id))
#     #     set_param('hr_loan_advance.loan_journal_id', repr(self.loan_journal_id.id))

