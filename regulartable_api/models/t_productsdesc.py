from odoo import models, fields, api

class ResLangCustom(models.Model):
    _name = 't.productsdesc'
    _description = 'Productsdesc Model'

    p_code = fields.Char(string='product code')
    p_desc = fields.Char(string='product description')
    lang_flag = fields.Integer(string='lang_flag')
    p_grp = fields.Char(string='p_grp')
    p_lang = fields.Char(string='p_lang')
    user_lmd = fields.Char( string='user_lmd')    