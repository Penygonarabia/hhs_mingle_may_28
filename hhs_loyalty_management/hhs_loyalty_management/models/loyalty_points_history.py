from odoo import models, fields, api, _
from odoo.exceptions import UserError, warnings, ValidationError


class ProductLoyaltyPointsHistory(models.Model):
    _name = 'product.loyalty.points.history'
    _description = 'Product Loyalty Points History'
    _order = 'changed_date desc'

    product_tmpl_id = fields.Many2one('product.template', string='Product Template')
    product_id = fields.Many2one('product.product', string='Product Variant')
    old_points = fields.Char(string='Old Points')
    new_points = fields.Char(string='New Points')
    changed_by = fields.Many2one('res.users', string='Changed By', default=lambda self: self.env.user)
    changed_date = fields.Datetime(string='Changed Date', default=fields.Datetime.now)
    active = fields.Boolean(default=True)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # fsm_loyalty_points = fields.Char(
    #     string='Customer Loyalty Points',
    #     compute='_compute_fsm_loyalty_points',
    #     inverse='_inverse_fsm_loyalty_points',
    #     store=True,
    #     help="Defines loyalty points assigned to the product",
    # )

    cst_loyalty_points = fields.Integer(
        string='Customer Loyalty Points',
        compute='_compute_cst_loyalty_points',
        inverse='_inverse_cst_loyalty_points',
        store=True,
        help="Defines loyalty points assigned to the product"
    )

    loyalty_history_ids = fields.One2many(
        'product.loyalty.points.history',
        'product_tmpl_id',
        compute='_compute_loyalty_history_ids',
        inverse='_inverse_loyalty_history_ids',
        string='Loyalty Points Setup History'
    )

    @api.constrains('cst_loyalty_points')
    def _check_cst_loyalty_points_limit(self):

        limit = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'hhs_loyalty_management.customer_loyalty_point_limit',
                default=0
            )
        )
        for rec in self:
            if rec.cst_loyalty_points and limit:
                if rec.cst_loyalty_points > limit:
                    raise ValidationError(
                        _("Customer Loyalty Points cannot exceed %s.") % limit
                    )

    @api.depends('product_variant_ids.cst_loyalty_points')
    def _compute_cst_loyalty_points(self):
        for rec in self:
            variant = rec.product_variant_ids[:1]
            rec.cst_loyalty_points = variant.cst_loyalty_points if variant else False

    def _inverse_cst_loyalty_points(self):
        for rec in self:
            rec.product_variant_ids.write({
                'cst_loyalty_points': rec.cst_loyalty_points
            })

    @api.depends('product_variant_ids.loyalty_history_ids')
    def _compute_loyalty_history_ids(self):
        for rec in self:
            rec.loyalty_history_ids = rec.product_variant_ids.mapped('loyalty_history_ids')

    def _inverse_loyalty_history_ids(self):
        for rec in self:

            # remove old template-linked lines
            old_lines = self.env['product.loyalty.points.history'].search([
                ('product_tmpl_id', '=', rec.id)
            ])

            old_lines.unlink()

            # recreate from variant history
            vals_list = []

            for variant in rec.product_variant_ids:
                for line in variant.loyalty_history_ids:
                    vals_list.append({
                        'product_tmpl_id': rec.id,
                        'product_id': variant.id,
                        'old_points': line.old_points,
                        'new_points': line.new_points,
                        'changed_date': line.changed_date,
                        'changed_by': line.changed_by.id,
                    })

            if vals_list:
                self.env['product.loyalty.points.history'].create(vals_list)

    # def write(self, vals):
    #     if 'cst_loyalty_points' in vals:
    #         for record in self:
    #             if record.cst_loyalty_points != vals.get('cst_loyalty_points'):
    #                 self.env['product.loyalty.points.history'].create({
    #                     'product_tmpl_id': record.id,
    #                     'product_id': record.product_variant_ids[0].id if record.product_variant_ids else False,
    #                     'old_points': record.cst_loyalty_points or '',
    #                     'new_points': vals.get('cst_loyalty_points') or '',
    #                 })
    #     return super(ProductTemplate, self).write(vals)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # fsm_loyalty_points = fields.Char(string='Customer Loyalty Points',
    #                                  help="Defines loyalty points assigned to the product")
    cst_loyalty_points= fields.Integer(string='Customer Loyalty Points',
                                     help="Defines loyalty points assigned to the product")

    loyalty_history_ids = fields.One2many('product.loyalty.points.history', 'product_id',
                                          string='Loyalty Points Setup History Variant')

    @api.constrains('cst_loyalty_points')
    def _check_cst_loyalty_points_limit(self):

        limit = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'hhs_loyalty_management.customer_loyalty_point_limit',
                default=0
            )
        )
        for rec in self:
            if rec.cst_loyalty_points and limit:
                if rec.cst_loyalty_points > limit:
                    raise ValidationError(
                        _("Customer Loyalty Points cannot exceed %s.") % limit
                    )

    def write(self, vals):
        if 'cst_loyalty_points' in vals:
            for record in self:
                if record.cst_loyalty_points != vals.get('cst_loyalty_points'):
                    self.env['product.loyalty.points.history'].create({
                        'product_tmpl_id': record.product_tmpl_id.id,
                        'product_id': record.id,
                        'old_points': record.cst_loyalty_points or '',
                        'new_points': vals.get('cst_loyalty_points') or '',
                    })
        return super(ProductProduct, self).write(vals)
