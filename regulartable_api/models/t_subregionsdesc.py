from odoo import models, fields, api

class ResLangCustom(models.Model):
    _name = 't.subregionsdesc'
    _description = 'Subregionsdesc Model'

    lang_flag = fields.Char(string='lang_flag')
    sr_code = fields.Char(string='sr_code')
    sr_desc = fields.Char(string='sr_desc')
    sr_lang = fields.Integer(string='sr_lang')
    user_lmd = fields.Char( string='user_lmd')
    