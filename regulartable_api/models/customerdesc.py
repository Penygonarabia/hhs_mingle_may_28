from odoo import models, fields, api

class ResLangCustom(models.Model):
    _name = 'customerdesc'
    _description = 'customerdesc Model'

    cst_add = fields.Char(string='cst_add')
    cst_add2 = fields.Char(string='cst_add2')
    cst_cityname = fields.Char(string='cst_cityname')
    cst_cname = fields.Char(string='cst_cname')
    cst_countname = fields.Char(string='cst_countname')
    cst_ctitle = fields.Char(string='cst_ctitle')
    cst_lang = fields.Integer(string='cst_lang')
    cst_message = fields.Char(string='cst_message')
    cst_name = fields.Char(string='cst_name')
    cst_no = fields.Char(string='cst_no')
    lang_flag = fields.Integer(string='lang_flag')
    user_lmd = fields.Char(string='user_lmd')