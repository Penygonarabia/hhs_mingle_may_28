from odoo import models, fields

class ResLangCustom(models.Model):
    _name = 't.cstclasstypedesc'
    _description = 'Cstclasstypedesc Model'

    cs_code = fields.Char(string='cs_code' ,required=True)
    cs_desc = fields.Char(string='cs_desc')
    cs_lang = fields.Char(string='cs_lang',required=True)
    lang_flag = fields.Char(string='lang_flag')
    user_lmd = fields.Char(string='user_lmd')

    _sql_constraints = [
    ('code_lang_unique', 'unique(cs_code, cs_lang)', 'Code and language must be unique together!')
    ]

