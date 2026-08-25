from odoo import models, fields, api, _
from odoo.tools.float_utils import float_round
from odoo.exceptions import ValidationError

class ServiceSaleOrderLine(models.Model):
    _inherit = 'service.sale.order.line'

    # --- New Fields from Specification ---
    main_category_id = fields.Many2one(
        't.mainproducts',
        string='Main Group',
        related='product_id.product_main_grp_id',
        store=True
    )
    # brand_category_id = fields.Many2one(
    #     'product.category',
    #     string='Brand (Category)',
    #     related='product_id.product_category_id',
    #     store=True,
    #     readonly=False
    # )
    
    brand_category_id = fields.Many2one(
        'product.category',
        string='Brand (Category)',
        store=True,
        readonly=False
    )
    brand_id = fields.Many2one(
        'brand',
        string='Brand',
        # compute='_compute_mapped_brand',
        store=True
    )
    contract_type_id = fields.Many2one(
        'crm.contract.type',
        string='Contract Type'
    )
    
    amc_pricing_id = fields.Many2one(
        'amc.pricing',
        string='Price Template',        
        # domain="[('active', '=', True), ('category_id', '=', main_category_id), ('brand_id', '=', brand_id)]"
    )

    # Unit Cost/Selling Prices (Labor)
    unit_cost_price = fields.Float(
        string='Unit Cost Price',
        compute='_compute_quotation_prices',
        store=True,
        digits=(16, 3),
        help="Total Labor Cost / Qty / No. of visits"
    )
    unit_selling_price = fields.Float(
        string='Unit Selling Price',
        compute='_compute_quotation_prices',
        store=True,
        digits=(16, 3),
        help="Labor Selling Price / Qty / No. of visits"
    )

    # Spare Parts Fields
    spare_parts_cost_per_category = fields.Float(
        string='Sp.Cost Category',
        compute='_compute_quotation_prices',
        store=True,
        digits=(16, 3),
        help="Pulled from AMC Pricing Template based on Contract Type"
    )
    spare_parts_cost = fields.Float(
        string='Sp.Cost',
        compute='_compute_quotation_prices',
        store=True,
        digits=(16, 3),
        help="Pulled from AMC Pricing Template Total Cost based on Contract Type"
    )
    spare_parts_selling_price = fields.Float(
        string='Sp. Selling Price',
        compute='_compute_quotation_prices',
        store=True,
        digits=(16, 3)
    )

    # Totals
    total_selling_price = fields.Float(
        string='Total Selling Price Labor+Spare parts',
        compute='_compute_quotation_prices',
        store=True,
        digits=(16, 3)
    )
    per_unit_selling_price = fields.Float(
        string='Per Unit Selling Price Rounded',
        compute='_compute_quotation_prices',
        store=True,
        digits=(16, 0),
        help="(Labor+Parts) / Qty / No. of visits"
    )
    
    
    per_unit_selling_price_not_round = fields.Float(
        string='Per Unit Selling Price',
        compute='_compute_quotation_prices',
        store=True,
        digits=(16, 3),
        help="(Labor+Parts) / Qty / No. of visits Not  Round"
    )
    
    
    '''Code Added on Augsut 18 2026 by Vijaya Bhaskar'''
    
    product_sub_category_id = fields.Many2one('sub_category',string = "Product Sub Category", related='product_id.product_sub_category_id',)
   
   
    
    '''Code Added on April 09 2026 by Vijaya Bhaskar'''
    @api.constrains('product_id','brand_category_id')
    def _check_product_id(self):
        for record in self:
            if record.service_sale_id.amc_quotation:
                if not record.product_id and not record.brand_category_id:
                    raise ValidationError(_("Please Add any product in the Order Lines"))
    # @api.depends('brand_category_id')
    # def _compute_mapped_brand(self):
    #     for rec in self:
    #         if rec.brand_category_id:
    #             brand = self.env['brand'].search([('name', '=', rec.brand_category_id.name)], limit=1)
    #             rec.brand_id = brand.id if brand else False
    #         else:
    #             rec.brand_id = False
                
                
    # @api.onchange('product_id', 'contract_type_id',)
    # def _onchange_amc_template(self):
    #     """Show the default template based on the brand, category & AMC unit type selection"""
    #     for rec in self:
    #         # if rec.product_sub_category_id:
    #         if rec.brand_id:
    #
    #             domain = [
    #                 ('active', '=', True),
    #                 ('brand_id', '=', rec.brand_id.id),
    #                 # ('category_id', '=', rec.main_category_id.id),
    #                 ('category_id', '=', rec.product_sub_category_id.id),
    #                 ('is_default', '=', True)
    #             ]
    #             template = self.env['amc.pricing'].search(domain, limit=1)
    #             if template:
    #                 rec.amc_pricing_id = template.id
            
    allowed_amc_pricing_ids = fields.Many2many(
    'amc.pricing',
        compute='_compute_allowed_amc_pricing_ids',
    )
    
    @api.depends('product_sub_category_id', 'brand_id')
    def _compute_allowed_amc_pricing_ids(self):
        Pricing = self.env['amc.pricing']
    
        for record in self:
            # Base / compulsory domain
            category_domain = [
                ('active', '=', True),
                ('category_id', '=', record.product_sub_category_id.id),
            ]
    
            # If brand is given, first search Category + Brand
            if record.brand_id:
                brand_domain = category_domain + [
                    ('brand_id', '=', record.brand_id.id),
                ]
    
                brand_pricings = Pricing.search(brand_domain)
    
                if brand_pricings:
                    # Brand-specific pricing exists
                    record.allowed_amc_pricing_ids = brand_pricings
                else:
                    # No Brand-specific pricing exists
                    # Fall back to Category-only pricing
                    '''Code Added on August 25 2026 by vijaya bhaskar if not category and brand is not matched then take * brand alone '''
                    """ record.allowed_amc_pricing_ids = Pricing.search(
                        category_domain
                    )"""
                    brand_domain = category_domain + [
                        ('brand_id.name', '=','*'),
                    ]
        
                    brand_pricings = Pricing.search(brand_domain)
                    
                    record.allowed_amc_pricing_ids = brand_pricings
    
            else:
                # No brand → Category is compulsory
                record.allowed_amc_pricing_ids = Pricing.search(
                    category_domain
                )
                
                
    @api.onchange('product_sub_category_id', 'brand_id')
    def _onchange_auto_select_amc_pricing(self):
        if not self.product_sub_category_id:
            self.amc_pricing_id = False
            return
    
        Pricing = self.env['amc.pricing']
    
        # Category is compulsory
        category_domain = [
            ('active', '=', True),
            ('category_id', '=', self.product_sub_category_id.id),
        ]
    
        pricings = Pricing.browse()
    
        # Brand given → Category + Brand
        if self.brand_id:
            brand_domain = category_domain + [
                ('brand_id', '=', self.brand_id.id),
            ]
    
            pricings = Pricing.search(brand_domain)
    
            # Fallback to Category only
            if not pricings:
                '''Code Added on August 25 2026 by vijaya bhaskar if not category and brand is not matched then take * brand alone
                pricings = Pricing.search(category_domain)
                '''
                brand_star_domain = category_domain + [
                ('brand_id.name', '=', '*'),
                ]
        
                pricings = Pricing.search(brand_star_domain)
    
        else:
            # Category only
            pricings = Pricing.search(category_domain)
    
        # Automatically select if exactly one exists
        if len(pricings) == 1:
            self.amc_pricing_id = pricings[0]
        else:
            self.amc_pricing_id = False  
            

    def action_open_amc_template(self):
        """Open the AMC Pricing Template Form View"""
        self.ensure_one()
        if self.amc_pricing_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'amc.pricing',
                'res_id': self.amc_pricing_id.id,
                'view_mode': 'form',
                'target': 'new',
            }

    '''Working Code Commented on May 12 2026'''
    # @api.depends('amc_pricing_id', 'contract_type_id', 'total_cost', 'total_price', 'product_qty', 'no_of_visits_per_year', 'vat','service_sale_id.spare_parts_amount_discount')
    # def _compute_quotation_prices(self):
    #     for rec in self:
    #         qty = rec.product_qty or 1.0
    #         visits = rec.no_of_visits_per_year or 1.0
    #
    #         #spare_parts_gp = float(self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.spare_parts_gross_profit', default=0.0))
    #         spare_parts_gp = rec.service_sale_id.spare_parts_amount_discount
    #
    #         # 1. & 2. Unit Cost and Selling Price (Labor) - Round to 0
    #         rec.unit_cost_price = float_round(rec.total_cost / (qty * visits), precision_digits=2)
    #         rec.unit_selling_price = float_round(rec.total_price / (qty * visits), precision_digits=2)
    #
    #         # 3. Spare Parts Costs from Template
    #         sp_cost_per_cat = 0.0
    #         sp_cost_total = 0.0
    #
    #         if rec.amc_pricing_id and rec.contract_type_id:
    #             if rec.contract_type_id.contract_category == 'full':
    #                 '''Code Added on April 08 2026 by Vijaya Bhaskar because of template dynamic amc pricing is update based on the qty given in the amc quotation'''
    #                 if qty :
    #                     rec.amc_pricing_id.full_comprehensive_units = qty 
    #                     rec.amc_pricing_id.semi_comprehensive_units = 0.0  
    #                 sp_cost_per_cat = rec.amc_pricing_id.full_cost_per_unit
    #                 sp_cost_total = rec.amc_pricing_id.full_total_cost
    #             elif rec.contract_type_id.contract_category == 'semi':
    #                 '''Code Added on April 08 2026 by Vijaya Bhaskar because of template dynamic amc pricing is update based on the qty given in the amc quotation'''
    #                 if qty :
    #                     rec.amc_pricing_id.semi_comprehensive_units = qty 
    #                     rec.amc_pricing_id.full_comprehensive_units = 0.0
    #
    #                 sp_cost_per_cat = rec.amc_pricing_id.semi_cost_per_unit
    #                 sp_cost_total = rec.amc_pricing_id.semi_total_cost
    #
    #         rec.spare_parts_cost_per_category = float_round(sp_cost_per_cat, precision_digits=2)
    #         # Spare parts cost - Round to 0
    #         rec.spare_parts_cost = float_round(sp_cost_total, precision_digits=2)
    #
    #         # 4. Spare Parts Selling Price - Round to 0
    #         if spare_parts_gp < 100 and spare_parts_gp > 0:
    #             rec.spare_parts_selling_price = float_round(sp_cost_total / (100.0 - spare_parts_gp) / 0.01, precision_digits=2)
    #         else:
    #             rec.spare_parts_selling_price = float_round(sp_cost_total, precision_digits=2)
    #
    #         # 5. Total Selling Price (Labor + Spare Parts) - Round to 0
    #         rec.total_selling_price = float_round(rec.total_price + rec.spare_parts_selling_price, precision_digits=2)
    #
    #         # 6. VAT Amount = Total Selling Price * VAT% (keep 2 decimals)
    #         vat_rate = rec.vat or 0.0
    #         rec.vat_percent = float_round(rec.total_selling_price * (vat_rate / 100.0), precision_digits=2)
    #         # Net Price = Total Selling Price + VAT Amount (round to 0)
    #         rec.total_amc = float_round(rec.total_selling_price + rec.vat_percent, precision_digits=2)
    #
    #         # 7. Per Unit Selling Price - Round to 0
    #         rec.per_unit_selling_price = float_round(rec.total_selling_price / (qty * visits), precision_digits=2)
    
    '''Code Added on May 12 2026'''
    @api.depends(
    'amc_pricing_id',
    'contract_type_id',
    'total_cost',
    'total_price',
    'product_qty',
    'no_of_visits_per_year',
    'vat',
    'service_sale_id.spare_parts_amount_discount',
   'service_sale_id.invoice_interval_duration'
)
    def _compute_quotation_prices(self):
        for rec in self:
            qty    = rec.product_qty or 1.0
            visits = rec.no_of_visits_per_year or 1.0
            spare_parts_gp = rec.service_sale_id.spare_parts_amount_discount
    
            # 1. Unit Cost Price (Labor) — 3dp
            rec.unit_cost_price   = round(rec.total_cost  / (qty * visits), 3)
            # rec.unit_cost_price = math.floor(rec.total_cost / (qty * visits) * 100) / 100
    
            # 2. Unit Selling Price (Labor only) — 3dp
            
            # rec.unit_selling_price_cost_not_round = round(rec.total_price / (qty * visits), 3)
            
            rec.unit_selling_price = round(rec.total_price / (qty * visits), 3)
    
            # 3. Spare Parts Costs from Template
            sp_cost_per_cat = 0.0
            sp_cost_total   = 0.0
    
            if rec.amc_pricing_id and rec.contract_type_id:
                pricing = rec.amc_pricing_id
    
                if rec.contract_type_id.contract_category == 'full':
                    rec.amc_pricing_id.full_comprehensive_units = qty 
                    rec.amc_pricing_id.semi_comprehensive_units = 0.0  
                    # ✅ FIXED: no mutation of shared template record
                    total_units = qty + (pricing.semi_comprehensive_units or 0.0)
                    full_ratio  = (qty / total_units) if total_units else 0.0
                    full_total  = sum(line.total_cost for line in pricing.line_ids)
                    sp_cost_total   = full_total * full_ratio
                    sp_cost_per_cat = (sp_cost_total / qty) if qty else 0.0
    
                elif rec.contract_type_id.contract_category == 'semi':
                    rec.amc_pricing_id.semi_comprehensive_units = qty 
                    rec.amc_pricing_id.full_comprehensive_units = 0.0
                    # ✅ FIXED: no mutation of shared template record
                    total_units = (pricing.full_comprehensive_units or 0.0) + qty
                    semi_ratio  = (qty / total_units) if total_units else 0.0
                    semi_total  = sum(
                        line.total_cost for line in pricing.line_ids
                        if not line.is_full_comprehensive_only
                    )
                    sp_cost_total   = semi_total * semi_ratio
                    sp_cost_per_cat = (sp_cost_total / qty) if qty else 0.0
    
            rec.spare_parts_cost_per_category = round(sp_cost_per_cat, 3)
            rec.spare_parts_cost              = round(sp_cost_total,   3)
    
            # 4. Spare Parts Selling Price — 3dp
            if 0 < spare_parts_gp < 100:
                sp_selling = sp_cost_total / ((100.0 - spare_parts_gp) * 0.01)
            else:
                sp_selling = sp_cost_total
            rec.spare_parts_selling_price = round(sp_selling, 3)
    
            # 5. Raw total (labor + spare parts) — NOT stored directly
            raw_total = rec.total_price + rec.spare_parts_selling_price
    
            # ✅ KEY FIX STEP A: per_unit rounded to 3dp first
            per_unit = round(raw_total / (qty * visits), 0)
            rec.per_unit_selling_price = per_unit
            
            per_unit_not_round = round(raw_total / (qty * visits), 3)
            rec.per_unit_selling_price_not_round = per_unit_not_round
    
            # ✅ KEY FIX STEP B: total = per_unit × qty × visits
            #    This ensures: per_unit × qty × visits == total (exactly, no mismatch)
            rec.total_selling_price = round(per_unit * qty * visits, 3)
    
            # 6. VAT
            vat_rate = rec.vat or 0.0
            rec.vat_percent = round(rec.total_selling_price * (vat_rate / 100.0), 2)
            rec.total_amc   = round(rec.total_selling_price + rec.vat_percent, 3)
        

   