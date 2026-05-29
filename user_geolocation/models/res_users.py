from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    _inherit = "res.users"

    current_latitude = fields.Float("Latitude", digits=(9, 6))
    current_longitude = fields.Float("Longitude", digits=(9, 6))
    map_url = fields.Char("Map URL", compute="_compute_map_url")

    @api.depends('current_latitude', 'current_longitude')
    def _compute_map_url(self):
        for rec in self:
            if rec.current_latitude and rec.current_longitude:
                rec.map_url = f"https://maps.google.com/maps?q={rec.current_latitude},{rec.current_longitude}&z=15&output=embed"
            else:
                rec.map_url = False

    # @api.model
    # def update_current_location(self, latitude, longitude):
    #     if not self.env.uid:
    #         raise ValidationError("No authenticated user found.")
    #     if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
    #         raise ValidationError("Invalid latitude or longitude values.")
    #     self.browse(self.env.uid).write({
    #         'current_latitude': latitude,
    #         'current_longitude': longitude,
    #     })
    #     return True

    @api.model
    def update_current_location(self, latitude, longitude):
        user = self.browse(self.env.uid)
        user.sudo().write({
            "current_latitude": latitude,
            "current_longitude": longitude,
        })
        return True

