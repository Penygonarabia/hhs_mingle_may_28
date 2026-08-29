from odoo import models, fields, _
from odoo.exceptions import UserError

class SalesTypesGroup(models.Model):
    _name = 'salestypes.group'
    _description = 'Sales Type Group'
    _rec_name = 'salgrp_name'

    salgrp_ref = fields.Char(string='Reference', required=True)
    salgrp_name = fields.Char(string='Name', required=True)
    salgrp_name2 = fields.Char(string='Name 2')

    _sql_constraints = [
        ('salgrp_ref_unique', 'unique(salgrp_ref)', 'Reference must be unique!')
    ]

    def unlink(self):
        for record in self:
            if self.env['sale.types'].search_count([('saltype_group', '=', record.id)]) > 0:
                
                raise UserError(f"You cannot delete the Sales Type Group '{record.salgrp_name}' because it is currently assigned to one or more Sale Types. Please reassign or delete the associated Sale Types first.")
        return super(SalesTypesGroup, self).unlink()
