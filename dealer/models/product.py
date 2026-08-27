from odoo import models, fields,api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Patches to force these fields to be Text so Odoo does not crash on '*'
    category_template_group_type = fields.Char(string="Category Template Group Type")
    category_group_type = fields.Char(string="Category Group Type")
    sub_group_code = fields.Char(string="Sub Group Code")
    group_code = fields.Char(string="Group Code")
    product_arabic_name = fields.Char(string="Product Arabic Name")

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

    # Patches to force these fields to be Text so Odoo does not crash on '*'
    category_template_group_type = fields.Char(string="Category Template Group Type")
    category_group_type = fields.Char(string="Category Group Type")
    sub_group_code = fields.Char(string="Sub Group Code")
    group_code = fields.Char(string="Group Code")
    product_arabic_name = fields.Char(string="Product Arabic Name")

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



    @api.depends()
    def _compute_show_dealer_menu(self):

        value = self.env['ir.config_parameter'].sudo().get_param(
            'dealer.show_dealer_menu'
        )

        for rec in self:
            rec.show_dealer_menu = value

    '''Code Commented on August 27 2026 by Vijaya Bhaskar due to unnamed show in the product in mobile view so that i commented three unnamed  and made it in a single one '''
            
    @api.depends('default_code', 'name')
    @api.depends_context(
        'show_only_default_code', 'uid', 'hide_code', 'display_default_code'
    )
    def _compute_display_name(self):
        ctx = self.env.context
        is_dealer_user = self.env.user.has_group('dealer.group_dealer_user') \
            or self.env.user.has_group('dealer.group_dealer_backoffice_user')

        for rec in self:
            if ctx.get('hide_code'):
                rec.display_name = rec.name
            elif ctx.get('show_only_default_code') or is_dealer_user:
                rec.display_name = rec.default_code or rec.name
            elif rec.default_code and not ctx.get('display_default_code') is False:
                rec.display_name = f"[{rec.default_code}] {rec.name}"
            else:
                rec.display_name = rec.name

    def name_get(self):
        # Keep name_get calling the same logic so old-API callers
        # (name_search results, some widgets) stay consistent.
        self._compute_display_name()
        return [(rec.id, rec.display_name) for rec in self]
    
    
            
    '''Code Commented on August 27 2026 by Vijaya Bhaskar due to unnamed show in the product in mobile view so that i commented three unnamed  and made it in a single one
    @api.depends_context('show_only_default_code', 'uid')
    def _compute_display_name(self):
        super()._compute_display_name()
        is_dealer_user = self.env.user.has_group('dealer.group_dealer_user') or self.env.user.has_group('dealer.group_dealer_backoffice_user')
        if self.env.context.get('show_only_default_code') or is_dealer_user:
            for record in self:
                if record.default_code:
                    record.display_name = record.default_code

    def name_get(self):
        is_dealer_user = self.env.user.has_group('dealer.group_dealer_user') or self.env.user.has_group('dealer.group_dealer_backoffice_user')
        if self.env.context.get('show_only_default_code') or is_dealer_user:
            res = []
            for record in self:
                name = record.default_code if record.default_code else record.name
                res.append((record.id, name))
            return res
        return super().name_get()
        
    '''    