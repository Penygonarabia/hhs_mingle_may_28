from odoo import models, fields

class ResLangCustom(models.Model):
    _name = 't.cstclassification'
    _description = 'Cstclassification Model'

    cc_code = fields.Char(string='Code', required=True)
    cc_cstclasstype = fields.Char(string='cc_cstclasstype')
    user_id = fields.Char(string='user_id')
    user_lmd = fields.Char(string='user_lmd')
    user_lmt = fields.Char(string='user_lmt')

    _sql_constraints = [
        ('cc_code_unique', 'unique(cc_code)', 'Code must be unique!')
    ]
