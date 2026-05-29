from odoo import models, fields, api

class ResLangCustom(models.Model):
    _name = 't.subregions'
    _description = 'Subregions Model'

    sr_code = fields.Char(string='sr_code')
    sr_disable = fields.Char(string='sr_disable')
    sr_region = fields.Char(string='sr_region')
    sr_sort = fields.Integer(string='sr_sort')
    user_id = fields.Char( string='user_id')
    user_lmd = fields.Char( string='user_lmd')
    user_lmt = fields.Char( string='user_lmt')