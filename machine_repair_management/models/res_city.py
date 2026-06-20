from odoo import api, fields, models, _


class UsersCity(models.Model):
    _inherit = "res.city"

    def_work_center_id = fields.Many2one('work.center.location', string="Default Work Center")

    country_district_id = fields.Many2one('res.state.district', string="District")

    # @api.model
    # def name_search(self, name='', args=None, operator='ilike', limit=100):
    #     args = args or []
    #     domain = args + ['|', ('name', operator, name), ('state_id.name', operator, name)]
    #     cities = self.search(domain, limit=limit)
    #     return cities.name_get()
    
    '''Code Added on June 20 2026 zip code was removed'''
    @api.depends('zipcode')
    def _compute_display_name(self):
        for city in self:
            name = city.name if not city.zipcode else city.name
            city.display_name = name