from odoo import models, fields

class SalesTypesGroup(models.Model):
    _name = 'salestypes_group'
    _description = 'Sales Type Group'
    _rec_name = 'salgrp_name'

    salgrp_ref = fields.Char(string='Reference', required=True)
    salgrp_name = fields.Char(string='Name', required=True)
    salgrp_name2 = fields.Char(string='Name 2')

    _sql_constraints = [
        ('salgrp_ref_unique', 'unique(salgrp_ref)', 'Reference must be unique!')
    ]
