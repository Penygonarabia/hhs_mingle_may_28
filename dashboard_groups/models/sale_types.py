from odoo import models, fields

class SaleTypes(models.Model):
    _name = 'sale_types'
    _description = 'Sale Types'

    sal_ref = fields.Char(string='Reference', required=True)
    saltype_name = fields.Char(string='Name', required=True)
    saltype_name2 = fields.Char(string='Name 2')
    saltype_group = fields.Many2one('salestypes_group', string='Sales Type Group', ondelete='restrict', required=True)

    _sql_constraints = [
        ('sal_ref_unique', 'unique(sal_ref)', 'Reference must be unique!')
    ]
