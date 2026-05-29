from odoo import models, fields, api

class ResLangCustom(models.Model):
    _name = 't.warehousedesc'
    _description = 'Warehousedesc Model'

    lang_flag = fields.Integer(string='lang_flag')
    user_lmd = fields.Char(string='user_lmd')
    wh_code = fields.Char(string='wh_code')
    wh_desc = fields.Char(string='wh_desc')
    wh_lang = fields.Integer( string='wh_lang')
    wh_pmessage = fields.Char( string='wh_pmessage')