from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Questionnare(models.Model):
    _name = 'questionnaire'

    que_code = fields.Char(string='Code', required=True)
    que_desc = fields.Char(string="Question", required=True)

    @api.constrains('que_code')
    def _check_questionnare_valid_code(self):
        for rec in self:
            code_search = self.env['questionnaire'].search([('que_code', '=', rec.que_code)])
            if len(code_search) > 1:
                raise ValidationError("The Code must be unique!")
