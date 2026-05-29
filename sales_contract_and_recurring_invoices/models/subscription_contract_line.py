from odoo import api, fields, models

class SubscriptionContractLines(models.Model):
    """ Add subscription contract line """
    _name = 'subscription.contracts.line'
    _description = 'Subscription Contracts Line'

    subscription_contract_id = fields.Many2one(
        'subscription.contracts',
        string='Subscription Contracts',
        help='Subscription Contract Reference')
    product_id = fields.Many2one('product.product',
                                 string='Products',
                                 help='Products to be added in contract')

    analytic_account_id = fields.Many2one('account.analytic.account',
                                          string='Analytic Account',
                                          help="Analytic account of the warehouse",
                                          store=True)
    currency_id = fields.Many2one(string='Currency',
                                  related='subscription_contract_id.currency_id',
                                  depends=[
                                      'subscription_contract_id.currency_id'])
    description = fields.Text(
        string="Description", compute='_compute_description', store=True,
        readonly=False, precompute=True, help='Product description')
    qty_ordered = fields.Integer(string="Quantity",
                               digits='Product Unit of Measure', default=1.0,
                               help='Ordered Quantity')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure',
                                     compute='_compute_product_uom', store=True,
                                     help='Unit of measure of product')
    price_unit = fields.Float(string="Unit Price",
                              compute='_compute_price_unit',
                              digits='Product Price',
                              store=True, readonly=False, precompute=True,
                              help='Unit price of product')
    tax_ids = fields.Many2many(comodel_name='account.tax', string="Taxes",
                               context={'active_test': False},
                               help='Taxes to be added')
    # discount = fields.Float(string="Discount (%)", digits='Discount',
    #                         store=True, readonly=False, help='Discount in %')
    vat_amt = fields.Float(sttring="VAT")
    vat = fields.Float(string='VAT (%)', default=0.0)
    discount = fields.Float(string="Discount (%)", digits='Discount',
                            store=True, readonly=False, help='Discount in %')
    # sub_total = fields.Monetary(
    #     string="Net Price", store=True,
    #     help='Sub Total Amount')
    
    sub_total = fields.Monetary(
        string="Net Price", store=True,
        currency_field='currency_id',
        help='Sub Total Amount')
    
    asset_number = fields.Char(string='Asset Tag No', compute="_compute_contract_number")
    available_asset_product_ids = fields.Many2many(
        'product.product',
        string='Assets in Products',
        compute="_compute_available_asset_products"
    )
    no_of_visits_per_year = fields.Integer(string="No.of Visits/Yr")
    no_of_emergency_visit = fields.Integer(string="No.of Emergency Visits")
    days_required_for_rpm = fields.Float(string="Days Required for PPM")
    standard_hours = fields.Float(string="Standard Hours")
    total_hr = fields.Float(string="Total Hours")
    total_cost = fields.Float(string="Total Labor Cost")
    total_price = fields.Float(string="Labor Selling Price")
    days_require_rpm_round_off = fields.Integer(string="Total Preventive Count")
    actual_prevent_count = fields.Integer(string="Actual Preventive Count")
    actual_correct_count = fields.Integer(string="Actual Corrective Count")
    total_correct_count = fields.Integer(string="Total Corrective Count")
    # balance_prevent_count = fields.Integer(string="Balance Preventive Count")
    # balance_correct_count = fields.Integer(string="Balance Corrective Count")
    '''Added on Nov 21 2025'''
    balance_prevent_count = fields.Integer(string="Balance Preventive Count", compute = "_compute_balance_prevent_count", store = True)
    balance_correct_count = fields.Integer(string="Balance Corrective Count", compute = "_compute_balance_prevent_count", store = True)
    paid_visit_count = fields.Integer(string="Paid Visit Count")
    
    currency_id = fields.Many2one(
    'res.currency',
    default=lambda self: self.env.company.currency_id,
    readonly=True
)

    @api.depends('total_correct_count','actual_correct_count' , 'days_require_rpm_round_off','actual_prevent_count')
    def _compute_balance_prevent_count(self):
        for rec in self:
            # rec.balance_prevent_count = False
            # rec.balance_correct_count = False
            # if rec.total_correct_count and rec.actual_correct_count:
            rec.balance_correct_count = rec.total_correct_count - rec.actual_correct_count or 0.0
            # if rec.days_require_rpm_round_off and  rec.actual_prevent_count:
            rec.balance_prevent_count =  rec.days_require_rpm_round_off - rec.actual_prevent_count   or 0.0
            

    @api.depends('product_id')
    def _compute_available_asset_products(self):
        for rec in self:
            products = self.env['product.product'].search([
                ('detailed_type', '=', 'service'),
                ('asset_number', '!=', False),
                ('contract_number', '!=', False)
            ])
            rec.available_asset_product_ids = products
    
    @api.depends('product_id')
    def _compute_contract_number(self):
        """ Compute unit price"""
        for rec in self:
            rec.asset_number = rec.product_id.asset_number or None

    @api.depends('product_id')
    def _compute_description(self):
        """ Compute product description """
        for option in self:
            if not option.product_id:
                continue
            product_lang = option.product_id.with_context(
                lang=self.subscription_contract_id.partner_id.lang)
            option.description = product_lang.get_product_multiline_description_sale()

    @api.depends('product_id')
    def _compute_product_uom(self):
        """ Compute product uom """
        for rec in self:
            rec.product_uom_id = rec.product_id.uom_id

    @api.depends('product_id')
    def _compute_price_unit(self):
        """ Compute unit price"""
        for rec in self:
            rec.price_unit = rec.product_id.lst_price

    # @api.depends('product_id', 'qty_ordered', 'discount', 'price_unit')
    # def _compute_amount(self):
    #     """ Compute total amount """
    #     for rec in self:
    #         total = rec.price_unit * rec.qty_ordered
    #         discount = total * rec.discount / 100
    #         total_after_discount = total - discount
    #         vat_with_total = total_after_discount * rec.product_id.taxes_id.amount / 100
    #         rec.vat_amt = vat_with_total
    #         rec.sub_total = total_after_discount + vat_with_total


 


    @api.onchange('product_id')
    def _onchange_product_id(self):
        """ Onchange to set taxes from product master """
        for rec in self:
            if rec.product_id:
                # Fetch customer taxes directly from the product master
                rec.tax_ids = rec.product_id.taxes_id.filtered(lambda t: t.type_tax_use == 'sale')
            else:
                rec.tax_ids = False

    main_category_id = fields.Many2one(
        't.mainproducts',
        string='Main Group'
    )

    brand_category_id = fields.Many2one(
        'product.category',
        string='Brand Category'
    )

    contract_type_id = fields.Many2one(
        'crm.contract.type',
        string='Contract Type'
    )

    amc_pricing_id = fields.Many2one(
        'amc.pricing',
        string='AMC Pricing'
    )

    unit_cost_price = fields.Float(string='Unit Cost Price')
    unit_selling_price = fields.Float(string='Unit Selling Price')

    spare_parts_cost_per_category = fields.Float(string='Sp.Cost Category')
    spare_parts_cost = fields.Float(string='Sp.Cost')
    spare_parts_selling_price = fields.Float(string='Sp. Selling Price')

    total_selling_price = fields.Float(string='Total Selling Price')

    per_unit_selling_price = fields.Float(string='Per Unit Selling Price')
    

    @api.depends('amc_pricing_id', 'contract_type_id', 'total_cost', 'total_price', 'qty_ordered', 'no_of_visits_per_year', 'vat')
    def _compute_quotation_prices(self):
        for rec in self:
            qty = rec.qty_ordered or 1.0
            visits = rec.no_of_visits_per_year or 1.0

            spare_parts_gp = float(self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.spare_parts_gross_profit', default=0.0))

            # 1. & 2. Unit Cost and Selling Price (Labor) - Round to 0
            rec.unit_cost_price = float_round(rec.total_cost / (qty * visits), precision_digits=2)
            rec.unit_selling_price = float_round(rec.total_price / (qty * visits), precision_digits=2)

            # 3. Spare Parts Costs from Template
            sp_cost_per_cat = 0.0
            sp_cost_total = 0.0
            
            if rec.amc_pricing_id and rec.contract_type_id:
                if rec.contract_type_id.contract_category == 'full':
                    sp_cost_per_cat = rec.amc_pricing_id.full_cost_per_unit
                    sp_cost_total = rec.amc_pricing_id.full_total_cost
                elif rec.contract_type_id.contract_category == 'semi':
                    sp_cost_per_cat = rec.amc_pricing_id.semi_cost_per_unit
                    sp_cost_total = rec.amc_pricing_id.semi_total_cost

            rec.spare_parts_cost_per_category = float_round(sp_cost_per_cat, precision_digits=2)
            # Spare parts cost - Round to 0
            rec.spare_parts_cost = float_round(sp_cost_total, precision_digits=2)

            # 4. Spare Parts Selling Price - Round to 0
            if spare_parts_gp < 100 and spare_parts_gp > 0:
                rec.spare_parts_selling_price = float_round(sp_cost_total / (100.0 - spare_parts_gp) / 0.01, precision_digits=2)
            else:
                rec.spare_parts_selling_price = float_round(sp_cost_total, precision_digits=2)

            # 5. Total Selling Price (Labor + Spare Parts) - Round to 0
            rec.total_selling_price = float_round(rec.total_price + rec.spare_parts_selling_price, precision_digits=2)

            # 6. VAT Amount = Total Selling Price * VAT% (keep 2 decimals)
            vat_rate = rec.vat or 0.0
            rec.vat_amt = float_round(rec.total_selling_price * (vat_rate / 100.0), precision_digits=2)
            # Net Price = Total Selling Price + VAT Amount (round to 0)
            rec.sub_total = float_round(rec.total_selling_price + rec.vat_percent, precision_digits=2)

            # 7. Per Unit Selling Price - Round to 0
            rec.per_unit_selling_price = float_round(rec.total_selling_price / (qty * visits), precision_digits=2)
