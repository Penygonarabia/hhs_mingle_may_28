from odoo import models, fields, api

class ResLangCustom(models.Model):
    _name = 't.regionsdesc'
    _description = 'Custom Language Model'

    r_lang = fields.Integer(string='Language Name')
    lang_flag = fields.Integer(string='Flag')
    r_code = fields.Char(string='Language Code')
    r_desc = fields.Char(string='Description')
    user_lmd = fields.Integer( string='Last Modified By')