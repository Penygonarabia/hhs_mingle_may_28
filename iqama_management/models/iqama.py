from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Iqama(models.Model):
    _name = 'iqama.management'
    _description = 'Iqama Management'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Iqama Profession', required=True, translate=True)

    @api.constrains('code')
    def _check_unique_code(self):
        for record in self:
            if self.search_count([('code', '=', record.code)]) > 1:
                raise ValidationError('The code must be unique.')
