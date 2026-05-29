from odoo import models, fields, api

class ResLangCustom(models.Model):
    _name = 'sl.salesmandesc'
    _description = 'SL_salesmandesc Model'

    lang_flag = fields.Char(string='lang_flag')
    sm_code = fields.Char(string='sm_code')
    sm_lang = fields.Char(string='sm_lang')
    sm_name = fields.Char(string='sm_name')
    user_lmd = fields.Char(string='user_lmd')