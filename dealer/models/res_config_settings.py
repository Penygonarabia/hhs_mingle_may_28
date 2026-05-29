from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    validate_geo_location = fields.Boolean(
        string="Validate for Geo Location",
        config_parameter="dealer.validate_geo_location",
        help="Enable this option to validate geo-location during operations."
    )

    show_dealer_menu = fields.Boolean(
        string="Show Dealer Menu",
        config_parameter="dealer.show_dealer_menu",
        help="Tick to show the dealer menu in the backend."
    )

    dealer_wfo_radius = fields.Integer(
        string="Dealer WFO Radius (in meters)",
        config_parameter="dealer.dealer_wfo_radius",
        default=0,
        help="Set the allowed radius (in meters) for dealer's Work From Office location validation."
    )

    fsm_loyalty_point_value = fields.Float(
        string="FSM Loyalty Point Value (SR)",
        config_parameter="fsm.loyalty_point_value"
    )

    make_interface_code_mandatory = fields.Boolean(
        string="Make the interface code mandatory",
        config_parameter='dealer.make_interface_code_mandatory'
    )


    def set_values(self):
        super().set_values()
        params = self.env['ir.config_parameter'].sudo()

        # ✅ Use set_param, not get_param
        params.set_param('dealer.dealer_wfo_radius', int(self.dealer_wfo_radius or 0))
        params.set_param('dealer.show_dealer_menu', self.show_dealer_menu)
        params.set_param('dealer.validate_geo_location', self.validate_geo_location)

        group = self.env.ref('dealer.group_dealer_module_user', raise_if_not_found=False)
        user = self.env.user

        if group:
            if self.show_dealer_menu:
                user.write({'groups_id': [(4, group.id)]})  # Add group
            else:
                user.write({'groups_id': [(3, group.id)]})  # Remove group

        print('User groups after update:', user.groups_id)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()

        # Safely convert to int in case an old float or string remains
        radius_param = params.get_param('dealer.dealer_wfo_radius', '0')
        try:
            dealer_wfo_radius = int(float(radius_param))
        except ValueError:
            dealer_wfo_radius = 0

        res.update({
            'dealer_wfo_radius': dealer_wfo_radius,
            'show_dealer_menu': params.get_param('dealer.show_dealer_menu', False),
            'validate_geo_location': params.get_param('dealer.validate_geo_location', False),
        })
        return res
