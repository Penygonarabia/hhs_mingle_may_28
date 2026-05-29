from odoo import models, fields


class TMainProducts(models.Model):
    _name = 't.mainproducts'
    _description = 'Main Products Category'
    _rec_name = 'mp_code'
    _order = 'mp_sort'

    mp_grp = fields.Char(string='Group', required=True)
    mp_code = fields.Char(string='Product Code', required=True)
    mp_sort = fields.Integer(string='Sort Order', default=0)
