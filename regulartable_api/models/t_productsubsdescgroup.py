from odoo import models, fields, api

class ResLangCustom(models.Model):
    _name = 't.productsubsdescgroup'
    _description = 'Productsubsdescgroup Model'

    lang_flag = fields.Char(string='lang_flag')
    psg_desc = fields.Char(string='psg_desc')
    psg_grp = fields.Char(string='psg_grp')
    psg_lang = fields.Char(string='psg_lang')
    psg_pcode = fields.Char(string='psg_pcode')
    psg_psub = fields.Char(string='psg_psub')
    user_lmd = fields.Char(string='user_lmd')
