from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    validate_geo_location = fields.Boolean(
        string="Validate for Geo Location",
        config_parameter="promoter.validate_geo_location",
        help="Enable this option to validate geo-location during operations."
    )

    show_promoter_menu = fields.Boolean(
        string="Show Promoter Menu",
        config_parameter="promoter.show_promoter_menu",
        help="Tick to show the Promoter menu in the backend."
    )

    promoter_wfo_radius = fields.Integer(
        string="Promoter WFO Radius (in meters)",
        config_parameter="promoter.promoter_wfo_radius",
        default=0,
        help="Set the allowed radius (in meters) for promoter's Work From Office location validation."
    )

    def set_values(self):
        super().set_values()
        params = self.env['ir.config_parameter'].sudo()

        # ✅ Use set_param, not get_param
        params.set_param('promoter.promoter_wfo_radius', int(self.promoter_wfo_radius or 0))
        params.set_param('promoter.show_promoter_menu', self.show_promoter_menu)
        params.set_param('promoter.validate_geo_location', self.validate_geo_location)

        group = self.env.ref('promoter.group_promoter_module_user', raise_if_not_found=False)
        user = self.env.user

        if group:
            if self.show_promoter_menu:
                user.write({'groups_id': [(4, group.id)]})  # Add group
            else:
                user.write({'groups_id': [(3, group.id)]})  # Remove group

        print('User groups after update:', user.groups_id)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()

        # Safely convert to int in case an old float or string remains
        radius_param = params.get_param('promoter.promoter_wfo_radius', '0')
        try:
            promoter_wfo_radius = int(float(radius_param))
        except ValueError:
            promoter_wfo_radius = 0

        res.update({
            'promoter_wfo_radius': promoter_wfo_radius,
            'show_promoter_menu': params.get_param('promoter.show_promoter_menu', False),
            'validate_geo_location': params.get_param('promoter.validate_geo_location', False),
        })
        return res
