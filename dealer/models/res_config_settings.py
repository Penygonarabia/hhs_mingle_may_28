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

    # General Promotion Settings
    gen_promo_required = fields.Boolean(
        string="General Promotion Multiplier Required",
        config_parameter="dealer.gen_promo_required"
    )
    gen_promo_from = fields.Char(
        string="Promotion From Date (YYYY-MM-DD)",
        config_parameter="dealer.gen_promo_from"
    )
    gen_promo_to = fields.Char(
        string="Promotion To Date (YYYY-MM-DD)",
        config_parameter="dealer.gen_promo_to"
    )
    gen_promo_multiplier = fields.Float(
        string="General Multiplier Value",
        config_parameter="dealer.gen_promo_multiplier",
        default=1.0
    )

    # Dealer Promotion Settings
    dealer_promo_required = fields.Boolean(
        string="Dealer Promotion Multiplier Required",
        config_parameter="dealer.dealer_promo_required"
    )
    dealer_promo_from = fields.Char(
        string="Dealer Promotion From Date (YYYY-MM-DD)",
        config_parameter="dealer.dealer_promo_from"
    )
    dealer_promo_to = fields.Char(
        string="Dealer Promotion To Date (YYYY-MM-DD)",
        config_parameter="dealer.dealer_promo_to"
    )
    dealer_promo_min_qty = fields.Integer(
        string="Minimum Quantity",
        config_parameter="dealer.dealer_promo_min_qty",
        default=1
    )
    dealer_promo_multiplier = fields.Float(
        string="Dealer Multiplier Value",
        config_parameter="dealer.dealer_promo_multiplier",
        default=1.0
    )

    filter_dealer_purchases = fields.Boolean(
        string="Filter Items Based on Dealer Purchases",
        config_parameter="dealer.filter_dealer_purchases"
    )

    retailer_sales_limit = fields.Integer(
        string="Retailer Sales Limit",
        config_parameter="dealer.retailer_sales_limit",
        default=25
    )

    dealer_sales_limit = fields.Integer(
        string="Dealer Sales Limit",
        config_parameter="dealer.dealer_sales_limit",
        default=100
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
