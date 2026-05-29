# -*- coding: utf-8 -*

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ServiceNature(models.Model):
    _name = 'service.nature'
    _description = "Service Nature"

    name = fields.Char(
        string="Name",
        required=True,
        translate=True
    )
    code = fields.Char(string="Code", required=True)

    @api.constrains('code')
    def _check_unique_code(self):
        for rec in self:
            code_search = self.env['service.nature'].search([('code', '=', rec.code)])
            if len(code_search) > 1:
                raise ValidationError('Code is unique one.Please give an another one')
