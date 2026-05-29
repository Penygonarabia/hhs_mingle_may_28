from odoo import models, fields, api

class CrmContractType(models.Model):
    _name = 'crm.contract.type'
    _description = 'CRM Contract Type'
    _rec_name = 'name'
    _order = 'code'

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name", required=True)

    contract_category = fields.Selection([
        ('full', 'Full Comprehensive'),
        ('semi', 'Semi-Comprehensive'),
        ('non', 'Non-Comprehensive'),
    ], string="Type", required=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Contract Code must be unique!')
    ]

    @api.onchange('code')
    def _onchange_code(self):
        if self.code:
            self.code = self.code.upper()