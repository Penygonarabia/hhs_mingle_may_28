from odoo import models, fields

class ResLangCustom(models.Model):
    _name = 't.cstgroupdesc'
    _description = 'Cstgroupdesc Model'

    cg_code = fields.Char(string='cg_code')
    cg_desc = fields.Char(string='cg_desc')
    cg_lang = fields.Char(string='cg_lang')
    lang_flag = fields.Char(string='lang_flag')
    user_lmd = fields.Char(string='user_lmd')