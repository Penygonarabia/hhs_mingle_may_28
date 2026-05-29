from odoo import models, fields, api

class ResLangCustom(models.Model):
    _name = 'catalogdesc'
    _description = 'Catalogdesc Model'

    cat_comments = fields.Char(string='Comments')
    cat_desc = fields.Char(string='Description')
    cat_grp = fields.Char(string='Group')
    cat_lang = fields.Integer(string='Language Name')
    cat_part = fields.Char(string='Part')
    cat_sdesc = fields.Char(string='Sub Description')
    cat_shortdesc = fields.Char(string='short Description')
    cat_specs = fields.Char(string='specs')
    cat_splname = fields.Char(string='splname')
    cat_stock = fields.Char(string='stock')
    lang_flag = fields.Integer(string='language flag')
    user_lmd = fields.Char(string='Language Code')