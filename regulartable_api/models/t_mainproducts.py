from odoo import models, fields

class TMainProducts(models.Model):
    _name = 't.mainproducts'
    _description = 'T Main Products'
   

    mp_grp = fields.Char(string="Main Product Group")
    mp_code = fields.Char(string="Main Product Code")
    mp_sort = fields.Integer(string="Sort")

    user_id = fields.Char(string="User ID")
    user_lmd = fields.Date(string="Last Modified Date")
    user_lmt = fields.Char(string="Last Modified Time")
