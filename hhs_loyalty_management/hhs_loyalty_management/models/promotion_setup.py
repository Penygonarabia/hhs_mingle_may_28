from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PromotionSetup(models.Model):
    _name = 'lp.setup.promotions'
    _description = 'Setup Promotion'
    _rec_name = 'promotion_name'
    _order = 'sort_order asc'

    promotion_reference = fields.Char(
        string='Reference',
        copy=False
    )

    promotion_name = fields.Char(
        string='Description',
        required=True
    )

    promotion_start_date = fields.Date(
        string='Start Date',
        required=True
    )

    promotion_end_date = fields.Date(
        string='End Date',
        required=True
    )

    sort_order = fields.Integer(
        string='Priority Order',
        default=lambda self: self._get_next_sort_order()
    )

    active = fields.Boolean(default=True)

    applicable_product_ids = fields.One2many(
        'lp.setup.promotions.products',
        'promotion_id',
        string='Products'
    )

    tier_line_ids = fields.One2many(
        'lp.setup.promotions.tiers',
        'promotion_id',
        string='Tiers'
    )

    customer_line_ids = fields.One2many(
        'lp.setup.promotions.customers',
        'promotion_id',
        string='Customers'
    )

    # _sql_constraints = [
    #     (
    #         'unique_promotion_name',
    #         'unique(promotion_name)',
    #         'Promotion Name must be unique.'
    #     )
    # ]
    select_all_customers = fields.Boolean(string="Select All Customers")

    @api.onchange('select_all_customers')
    def _onchange_select_all_customers(self):
        for rec in self:

            # Clear existing records
            rec.tier_line_ids = [(5, 0, 0)]
            rec.customer_line_ids = [(5, 0, 0)]

            if rec.select_all_customers:

                # Get only loyalty-enabled customers
                customers = self.env['res.partner'].search([
                    ('customer_rank', '>', 0),
                    ('activate_loyalty_feature', '=', True),
                ])

                customer_lines = []

                for customer in customers:
                    customer_lines.append((0, 0, {
                        'customer_id': customer.id,
                        'is_selected': True,
                    }))

                # Assign customer lines
                rec.customer_line_ids = customer_lines

    @api.model
    def _get_next_sort_order(self):
        last_record = self.search([], order='sort_order desc', limit=1)
        return (last_record.sort_order or 0) + 1

    @api.constrains('promotion_start_date', 'promotion_end_date')
    def _check_dates(self):
        for rec in self:
            if rec.promotion_end_date and rec.promotion_start_date:
                if rec.promotion_end_date < rec.promotion_start_date:
                    raise ValidationError(
                        'Promotion End Date cannot be earlier than Start Date.'
                    )

    @api.constrains('applicable_product_ids')
    def _check_applicable_product_ids(self):
        for rec in self:
            if not rec.applicable_product_ids:
                raise ValidationError(
                    "Please add at least one product."
                )

    def _validate_duplicate_products(self, vals):

        product_ids = []

        for line in vals.get('applicable_product_ids', []):

            if line[0] == 0:
                product_id = line[2].get('product_name_id')

                if product_id in product_ids:
                    raise ValidationError(
                        "Duplicate Product are not allowed in the same promotion."
                    )

                product_ids.append(product_id)

    def _validate_duplicate_tiers(self, vals):

        tier_ids = []

        for line in vals.get('tier_line_ids', []):

            if line[0] == 0:
                tier_id = line[2].get('tier_id')

                if tier_id in tier_ids:
                    raise ValidationError(
                        "Duplicate Customer Tier is not allowed in the same promotion."
                    )

                tier_ids.append(tier_id)

    def _validate_duplicate_customers(self, vals):

        customer_ids = []

        for line in vals.get('customer_line_ids', []):

            if line[0] == 0:
                customer_id = line[2].get('customer_id')

                if customer_id in customer_ids:
                    raise ValidationError(
                        "Duplicate customers are not allowed in the same promotion."
                    )

                customer_ids.append(customer_id)

    @api.model
    def create(self, vals):

        # Date validation
        if vals.get('promotion_start_date') and vals.get('promotion_end_date'):
            if vals['promotion_end_date'] < vals['promotion_start_date']:
                raise ValidationError(
                    'Promotion End Date cannot be earlier than Start Date.'
                )

        # Product required validation
        if not vals.get('applicable_product_ids'):
            raise ValidationError(
                "Please add at least one product."
            )

        # Duplicate validations BEFORE sequence
        self._validate_duplicate_products(vals)
        self._validate_duplicate_tiers(vals)
        self._validate_duplicate_customers(vals)

        # Generate sequence AFTER ALL validations
        if not vals.get('promotion_reference'):
            vals['promotion_reference'] = self.env['ir.sequence'].next_by_code(
                'lp.setup.promotions.sequence'
            ) or '/'

        return super().create(vals)


class LPSetupPromotionsProducts(models.Model):
    _name = 'lp.setup.promotions.products'
    _description = 'Applicable Products'

    promotion_id = fields.Many2one(
        'lp.setup.promotions',
        string='Promotion'
    )

    product_category_id = fields.Many2one(
        'product.category',
        string='Product Category'
    )

    product_name_id = fields.Many2one(
        'product.product',
        string='Product'
    )

    promotion_type = fields.Selection([('bonus', 'Bonus'), ('multiplier', 'Multiplier')],
                                      string='Promotion Type')

    promotional_value_per_qty = fields.Float(
        string='Promotional Value Per Qty'
    )

    # @api.constrains('product_name_id', 'promotion_id')
    # def _check_product_name_id(self):
    #     for rec in self:
    #         product_search = self.env['lp.setup.promotions.products'].search([
    #             ('promotion_id', '=', rec.promotion_id.id),
    #             ('product_name_id', '=', rec.product_name_id.id),
    #             ('id', '!=', rec.id),
    #         ], limit=1)
    #
    #         if product_search:
    #             raise ValidationError(
    #                 "Duplicate Product are not allowed in the same promotion."
    #             )


class LPSetupPromotionsTiers(models.Model):
    _name = 'lp.setup.promotions.tiers'
    _description = 'Promotion Tiers'

    promotion_id = fields.Many2one(
        'lp.setup.promotions',
        string='Promotion'
    )

    tier_id = fields.Many2one(
        'customer.tier',
        string='Tier',
        required=True
    )

    # @api.constrains('tier_id', 'promotion_id')
    # def _check_tier_id(self):
    #     for rec in self:
    #
    #         tier_search = self.env['lp.setup.promotions.tiers'].search([
    #             ('promotion_id', '=', rec.promotion_id.id),
    #             ('tier_id', '=', rec.tier_id.id),
    #             ('id', '!=', rec.id),
    #         ], limit=1)
    #
    #         if tier_search:
    #             raise ValidationError(
    #                 "Duplicate Customer Tier is not allowed in the same promotion."
    #             )


class LPSetupPromotionsCustomers(models.Model):
    _name = 'lp.setup.promotions.customers'
    _description = 'Promotion Customers'

    promotion_id = fields.Many2one(
        'lp.setup.promotions',
        string='Promotion'
    )
    is_selected = fields.Boolean('is_selected')

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        domain="[('activate_loyalty_feature', '=', True)]"
    )

    # @api.constrains('customer_id', 'promotion_id')
    # def _check_customer_id(self):
    #     for rec in self:
    #         customer_search = self.env['lp.setup.promotions.customers'].search([
    #             ('promotion_id', '=', rec.promotion_id.id),
    #             ('customer_id', '=', rec.customer_id.id),
    #             ('id', '!=', rec.id),
    #         ], limit=1)
    #
    #         if customer_search:
    #             raise ValidationError(
    #                 "Duplicate customers are not allowed in the same promotion."
    #             )
