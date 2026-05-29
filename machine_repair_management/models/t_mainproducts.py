from odoo import models, fields

class MainProducts(models.Model):
    _name = 't.mainproducts'
    _description = 'Main Products'
    _rec_name = 'mp_code'   # what should display in dropdown

    mp_grp = fields.Char(string="Group", size=3, required=True)
    mp_code = fields.Char(string="Code", size=20)
    mp_sort = fields.Integer(string="Sort")
    user_id = fields.Char(string="User")
    user_lmd = fields.Date(string="Last Modified Date", default=fields.Date.today)
    user_lmt = fields.Char(string="Last Modified Time", size=5)