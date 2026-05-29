from odoo import models, fields

class ResLangCustom(models.Model):
    _name = 't.groupsdesc'
    _description = 'Groupsdesc Model'

    detail1 = fields.Char(string='detail1')
    detail2 = fields.Char(string='detail2')
    detail3 = fields.Char(string='detail3')
    grpd_code = fields.Char(string='grpd_code')
    grpd_comments = fields.Char(string='grpd_comments')
    grpd_desc = fields.Char(string='grpd_desc')
    grpd_lang = fields.Char(string='grpd_lang')
    grpd_splname = fields.Char(string='grpd_splname')
    lang_flag = fields.Char(string='lang_flag')
    user_lmd = fields.Char(string='user_lmd')