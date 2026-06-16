from odoo import models, fields,api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    fsm_loyalty_points = fields.Float(
        string="Salesman Loyalty Point",
        help="Loyalty points earned per unit sale"
    )

    show_in_dealer_app = fields.Boolean(
        string="Show in Dealer salesman app",
        default=False,
    )

    show_dealer_menu = fields.Boolean(
        compute='_compute_show_dealer_menu'
    )

    @api.depends()
    def _compute_show_dealer_menu(self):

        value = self.env['ir.config_parameter'].sudo().get_param(
            'dealer.show_dealer_menu'
        )

        for rec in self:
            rec.show_dealer_menu = value

class ProductProduct(models.Model):
    _inherit = 'product.product'

    fsm_loyalty_points = fields.Float(
        related='product_tmpl_id.fsm_loyalty_points',
        store=True,
        readonly=False
    )
    
    show_in_dealer_app = fields.Boolean(
        related='product_tmpl_id.show_in_dealer_app',
        store=True,
        readonly=False
    )
    show_dealer_menu = fields.Boolean(
        compute='_compute_show_dealer_menu'
    )

    @api.depends_context('show_only_default_code')
    def _compute_display_name(self):
        super()._compute_display_name()
        if self._context.get('show_only_default_code'):
            is_mobile_only = self.env.user.has_group('dealer.group_dealer_user') and not self.env.user.has_group('dealer.group_dealer_backoffice_user')
            if is_mobile_only:
                for record in self:
                    if record.default_code:
                        record.display_name = record.default_code

    @api.depends()
    def _compute_show_dealer_menu(self):

        value = self.env['ir.config_parameter'].sudo().get_param(
            'dealer.show_dealer_menu'
        )

        for rec in self:
            rec.show_dealer_menu = value