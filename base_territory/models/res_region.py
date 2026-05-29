# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResRegion(models.Model):
    _name = "res.region"
    _description = "Region"

    name = fields.Char(string='Region Name', required=True,translate=True)
    description = fields.Char()
    partner_id = fields.Many2one("res.partner", string="Region Manager")
    code = fields.Char(string='Code', required=True)

    @api.constrains('code')
    def _check_unique_code(self):
        for record in self:
            if self.search_count([('code', '=', record.code)]) > 1:
                raise ValidationError('The code must be unique.')



class IqamaManagementCompany(models.Model):
    _name = "iqama.company"
    _description = "Iqama Company"


    name = fields.Char(string='Sponsor Name', required=True,translate=True)
    code = fields.Char(string='Sponsor Code', required=True)


    @api.constrains('code')
    def _check_unique_code(self):
        for record in self:
            if self.search_count([('code', '=', record.code)]) > 1:
                raise ValidationError('The code must be unique.')

class HRWorkLocation(models.Model):
    _inherit = 'hr.work.location'

    res_region_id = fields.Many2one('res.region', string='Region')
    code = fields.Char(string="Code")

    @api.constrains('code')
    def _check_location_code(self):
        """
        Constraint to ensure `code` is unique and follows a specific format.
        """
        for rec in self:
            if not rec.code:
                raise ValidationError("The Code cannot be empty.")
            if not rec.code.isalnum():
                raise ValidationError("The Code must contain only alphanumeric characters.")
            # Check Uniqueness
            existing_code = self.search([('code', '=', rec.code), ('id', '!=', rec.id)])
            if existing_code:
                raise ValidationError(f"The Code '{rec.code}' must be unique")


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    iqama_company_id = fields.Many2one('iqama.company', string='Sponsor')
