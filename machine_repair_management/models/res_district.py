from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResStateDistrict(models.Model):
    _name = "res.state.district"
    _description = "State District"

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")
    country_id = fields.Many2one('res.country', string="Country")
    country_state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict',
                                       domain="[('country_id', '=?', country_id)]")
    city_id = fields.Many2one('res.city', string="City")

    @api.constrains('code')
    def _valid_check_district_code(self):
        for rec in self:
            code_search = self.env['res.state.district'].search([('code', '=', rec.code), ('id', '!=', rec.id)])
            if len(code_search) > 1:
                raise ValidationError(
                    "Already code %s is associated with some other district name.Please Change it" % rec.code)