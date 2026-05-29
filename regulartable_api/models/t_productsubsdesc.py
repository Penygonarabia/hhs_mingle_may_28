from odoo import models, fields, api

class ResLangCustom(models.Model):
    _name = 't.productsubsdesc'
    _description = 'Productsubsdesc Model'

    lang_flag = fields.Integer(string='lang_flag')
    ps_desc = fields.Char(string='ps_desc')
    ps_grp = fields.Char(string='ps_grp')
    ps_lang = fields.Char(string='ps_lang')
    ps_pcode = fields.Char( string='ps_pcode')
    ps_psub = fields.Char( string='ps_psub')
    user_lmd = fields.Integer( string='user_lmd')