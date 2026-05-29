from odoo import fields, api, models, _
from odoo.exceptions import UserError, warnings, ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    loyalty_points_hide_show = fields.Boolean(string="Loyalty & Rewards", default=False,
                                              config_parameter="hhs_loyalty_management.loyalty_points_hide_show")

    customer_loyalty_point_limit = fields.Integer(
        string="Maximum Point Allowed",
        config_parameter='hhs_loyalty_management.customer_loyalty_point_limit'
    )
    tier_downgrade_waiting_days = fields.Integer(
        string="Tier Downgrade Waiting Days",
        config_parameter='hhs_loyalty_management.tier_downgrade_waiting_days',
        default=90
    )

    # product_loyalty_point_limit = fields.Integer(
    #     string="Product Loyalty Point Limit",
    #     config_parameter='hhs_loyalty_management.product_loyalty_point_limit',
    # )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()

        res.update(
            loyalty_points_hide_show=params.get_param('hhs_loyalty_management.loyalty_points_hide_show'),
            customer_loyalty_point_limit=params.get_param('hhs_loyalty_management.customer_loyalty_point_limit'),
            tier_downgrade_waiting_days=params.get_param('hhs_loyalty_management.tier_downgrade_waiting_days'),
            # product_loyalty_point_limit=params.get_param('hhs_loyalty_management.product_loyalty_point_limit')
        )
        return res

    # def set_values(self):
    #     res = super(ResConfigSettings, self).set_values()
    #
    #     self.env['ir.config_parameter'].sudo().set_param('hhs_loyalty_management.loyalty_points_hide_show',
    #                                                      self.loyalty_points_hide_show)
    #     return res

    def set_values(self):
        super().set_values()

        group = self.env.ref(
            'hhs_loyalty_management.group_loyalty_program_user'
        )

        if self.loyalty_points_hide_show:
            group.users = [(4, self.env.user.id)]
        else:
            group.users = [(3, self.env.user.id)]
