from odoo import models, fields,api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    fsm_loyalty_points = fields.Integer(
        string="Salesman Loyalty Point",
        help="Loyalty points earned per unit sale"
    )

    show_in_dealer_app = fields.Boolean(
        string="Show in Dealer App",
        default=True
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

    fsm_loyalty_points = fields.Integer(
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

    @api.depends()
    def _compute_show_dealer_menu(self):

        value = self.env['ir.config_parameter'].sudo().get_param(
            'dealer.show_dealer_menu'
        )

        for rec in self:
            rec.show_dealer_menu = value

    def name_get(self):
        if self.env.context.get('show_only_default_code'):
            return [(rec.id, rec.default_code or rec.name) for rec in self]
        return super().name_get()

    def _compute_display_name(self):
        super()._compute_display_name()
        if self.env.context.get('show_only_default_code'):
            for rec in self:
                rec.display_name = rec.default_code or rec.name