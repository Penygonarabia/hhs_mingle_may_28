from odoo import models, fields


class SLSalesman(models.Model):
    _name = 'sl.salesman'
    _description = 'SL Salesman Model'

    sm_code = fields.Char(string='SM Code')
    sm_payroll = fields.Char(string='SM Payroll')
    user_id = fields.Char(string='User ID')
    user_lmd = fields.Char(string='User LMD')
    sm_userid = fields.Char(string='SM UserID')

    sm_name = fields.Char(string='SM Name')
    sm_name2 = fields.Char(string='SM Name 2')

    lang_flag = fields.Integer(string='Lang Flag')
    lang_flag2 = fields.Integer(string='Lang Flag 2')

    sm_mobile = fields.Char(string='SM Mobile')

    sm_type = fields.Char(string='SM Type')
    sm_region = fields.Char(string='SM Region')
    sm_city = fields.Char(string='SM City')

    sm_stype = fields.Char(string='SM SType')
    sm_sup = fields.Char(string='SM Supervisor')

    sm_expdays = fields.Integer(string='SM Exp Days')
    sm_alrtdays = fields.Integer(string='SM Alert Days')