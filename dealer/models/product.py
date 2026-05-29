from odoo import models, fields,api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    fsm_loyalty_points = fields.Float(
        string="Salesman Loyalty Point",
        help="Loyalty points earned per unit sale"
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