from odoo import models, fields


class Brand(models.Model):
    _name = 'brand'
    _description = 'Brand'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Name', required=True)

