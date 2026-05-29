from odoo import models, fields

class ResLangCustom(models.Model):
    _name = 'customergroups'
    _description = 'Customer Groups Model'

    cst_no = fields.Char(string='Customer No')
    cst_group = fields.Char(string='Customer Group')
    user_id = fields.Char(string='User ID')
    user_lmd = fields.Char(string='Last Modified Date')
    user_lmt = fields.Char(string='Last Modified Time')
