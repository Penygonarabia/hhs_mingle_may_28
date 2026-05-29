from odoo import models, fields

class ResLangCustom(models.Model):
    _name = 't.cstclassificationdesc'
    _description = 'Cstclassificationdesc Model'

    cc_code = fields.Char(string='cc_code',required=True)
    cc_desc = fields.Char(string='cc_desc')
    cc_lang = fields.Char(string='cc_lang',required=True)
    lang_flag = fields.Char(string='lang_flag')
    user_lmd = fields.Char(string='user_lmd')

