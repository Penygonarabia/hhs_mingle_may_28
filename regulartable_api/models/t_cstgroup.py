from odoo import models, fields

class ResLangCustom(models.Model):
    _name = 't.cstgroup'
    _description = 'Cstgroup Model'

    cg_code = fields.Char(string='cg_code')
    user_id = fields.Char(string='user_id')
    user_lmd = fields.Char(string='user_lmd')
    user_lmt = fields.Char(string='user_lmt')
    cg_export = fields.Char(string='cg_export')