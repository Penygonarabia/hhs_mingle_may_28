from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

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

    # --- General Promotion Multiplier ---
    general_promotion_multiplier_required = fields.Boolean(
        string="General Promotion Multiplier Required",
        config_parameter='dealer.general_promotion_multiplier_required',
        help="Enable this to apply a general promotion multiplier on loyalty points for a selected date range."
    )
    general_promotion_from_date = fields.Date(
        string="From Date"
    )
    general_promotion_to_date = fields.Date(
        string="To Date"
    )
    general_promotion_multiplier_value = fields.Float(
        string="Multiplier Value",
        config_parameter='dealer.general_promotion_multiplier_value',
        default=1.0
    )

    # --- Dealer Promotion Multiplier ---
    dealer_promotion_multiplier_required = fields.Boolean(
        string="Dealer Promotion Multiplier Required",
        config_parameter='dealer.dealer_promotion_multiplier_required',
        help="Enable this to apply additional multiplier when sales qty in a single invoice crosses the minimum quantity."
    )
    dealer_promotion_from_date = fields.Date(
        string="From Date"
    )
    dealer_promotion_to_date = fields.Date(
        string="To Date"
    )
    dealer_promotion_min_qty = fields.Integer(
        string="Min Qty",
        config_parameter='dealer.dealer_promotion_min_qty',
        default=0,
        help="Minimum quantity threshold in a single invoice to trigger the dealer multiplier."
    )
    dealer_promotion_multiplier_value = fields.Float(
        string="Multiplier Value",
        config_parameter='dealer.dealer_promotion_multiplier_value',
        default=1.0
    )

    # --- Filter Items / Sales Limits ---
    filter_items_by_dealer_purchases = fields.Boolean(
        string="Filter items based on the dealer's purchases",
        config_parameter='dealer.filter_items_by_dealer_purchases',
        help="Enable to filter product items based on what the dealer has previously purchased."
    )
    retailer_sales_limit = fields.Integer(
        string="Retailer Sales Limit",
        config_parameter='dealer.retailer_sales_limit',
        default=25,
        help="Maximum sales limit for retailer customers (e.g. 25)."
    )
    dealer_sales_limit = fields.Integer(
        string="Dealer Sales Limit",
        config_parameter='dealer.dealer_sales_limit',
        default=100,
        help="Maximum sales limit for dealer customers (e.g. 100)."
    )

    @api.constrains('general_promotion_from_date', 'general_promotion_to_date')
    def _check_general_promotion_dates(self):
        for rec in self:
            if rec.general_promotion_from_date and rec.general_promotion_to_date:
                if rec.general_promotion_from_date > rec.general_promotion_to_date:
                    raise ValidationError(_("General Promotion: 'From Date' must be less than or equal to 'To Date'."))

    @api.constrains('dealer_promotion_from_date', 'dealer_promotion_to_date')
    def _check_dealer_promotion_dates(self):
        for rec in self:
            if rec.dealer_promotion_from_date and rec.dealer_promotion_to_date:
                if rec.dealer_promotion_from_date > rec.dealer_promotion_to_date:
                    raise ValidationError(_("Dealer Promotion: 'From Date' must be less than or equal to 'To Date'."))


    def set_values(self):
        super().set_values()
        params = self.env['ir.config_parameter'].sudo()

        # ✅ Use set_param, not get_param
        params.set_param('dealer.dealer_wfo_radius', int(self.dealer_wfo_radius or 0))
        params.set_param('dealer.show_dealer_menu', self.show_dealer_menu)
        params.set_param('dealer.validate_geo_location', self.validate_geo_location)

        # Save date fields as strings
        params.set_param('dealer.general_promotion_from_date', str(self.general_promotion_from_date or ''))
        params.set_param('dealer.general_promotion_to_date', str(self.general_promotion_to_date or ''))
        params.set_param('dealer.dealer_promotion_from_date', str(self.dealer_promotion_from_date or ''))
        params.set_param('dealer.dealer_promotion_to_date', str(self.dealer_promotion_to_date or ''))

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

        # Load date fields from string params
        from odoo.fields import Date as FieldDate
        def _parse_date(val):
            if val and val != 'False':
                try:
                    return FieldDate.to_date(val)
                except Exception:
                    return False
            return False

        res.update({
            'dealer_wfo_radius': dealer_wfo_radius,
            'show_dealer_menu': params.get_param('dealer.show_dealer_menu', False),
            'validate_geo_location': params.get_param('dealer.validate_geo_location', False),
            'general_promotion_from_date': _parse_date(params.get_param('dealer.general_promotion_from_date', '')),
            'general_promotion_to_date': _parse_date(params.get_param('dealer.general_promotion_to_date', '')),
            'dealer_promotion_from_date': _parse_date(params.get_param('dealer.dealer_promotion_from_date', '')),
            'dealer_promotion_to_date': _parse_date(params.get_param('dealer.dealer_promotion_to_date', '')),
        })
        return res
