# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.exceptions import ValidationError


class HrBranch(models.Model):
    _name = 'hr.branch'
    _description = 'Company Branch'

    name = fields.Char('Office Name', size=64, translate=True)
    # arabic_name = fields.Char('Arabic Name', size=64)
    code = fields.Char('Code', size=64)
    street = fields.Char('Street', size=128)
    street2 = fields.Char('Street2', size=128)
    zip = fields.Char('Zip', size=24)
    po_box_no = fields.Char('P.O.Box', size=128)
    city = fields.Char('City', size=128)
    country_id = fields.Many2one('res.country', string='Country')
    phone = fields.Char('Tel', size=18)
    mobile = fields.Char('Mobile', size=18)
    fax = fields.Char('Fax', size=18)

    @api.constrains('name')
    def duplicate_name(self):
        branch_obj = self.env['hr.branch'].search([('id', '!=', self.id), ('name', '=', self.name)])
        print("branch_obj", branch_obj)
        if branch_obj:
            raise ValidationError(('Already %s is created no need to create again' % self.name))
