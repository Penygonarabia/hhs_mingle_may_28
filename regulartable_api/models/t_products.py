from odoo import models, fields

class TProducts(models.Model):
    _name = 't.products'
    _description = 'T Products'
    

    p_grp = fields.Char(string="Group")
    p_code = fields.Char(string="Code")
    p_markup = fields.Float(string="Markup")
    p_pcat = fields.Char(string="Product Category")
    p_duty = fields.Char(string="Duty")
    user_id = fields.Char(string="User ID")
    user_lmd = fields.Date(string="Last Modified Date")
    user_lmt = fields.Char(string="Last Modified Time")
    p_desc = fields.Char(string="Description")
    p_desc2 = fields.Char(string="Description 2")
    lang_flag = fields.Char(string="Lang Flag")
    lang_flag2 = fields.Char(string="Lang Flag 2")
    p_sort = fields.Integer(string="Sort")
    p_loyaltyreq = fields.Char(string="Loyalty Req")
    p_mpcode = fields.Char(string="MP Code")
    p_maincat = fields.Char(string="Main Category")
