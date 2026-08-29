from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AmcPricing(models.Model):
    _name = 'amc.pricing'
    _description = 'AMC Price Calculation'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        copy=True,
    )
    # category_id = fields.Many2one(
    #     't.mainproducts',
    #     string='Product Category',
    #     required=False,
    # )
    
    category_id = fields.Many2one(
        'sub.category',
        string='Product Sub Category',
        required=True,
           ondelete='restrict',
    )
    brand_id = fields.Many2one(
        'brand',
        string='Brand',
    )
    brand_name = fields.Char(
        string='Brand Name',
        related='brand_id.name',
        store=True,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    is_default = fields.Boolean(
        string='Default',
        default=False,
    )
    semi_comprehensive_units = fields.Float(
        string='Semi-Comprehensive Units',
        digits=(12, 2),
    )
    full_comprehensive_units = fields.Float(
        string='Full Comprehensive Units',
        digits=(12, 2),
    )
    total_units = fields.Float(
        string='Total Units',
        digits=(12, 2),
        compute='_compute_total_units',
        store=True,
    )

    total_cost = fields.Float(
        string="Total Cost ",
        digits=(12, 2),
        compute="_compute_costs",
        store=True,
    )

    @api.depends('semi_comprehensive_units', 'full_comprehensive_units')
    def _compute_total_units(self):
        for rec in self:
            rec.total_units = rec.semi_comprehensive_units + rec.full_comprehensive_units

    # --- Calculated summary fields ---
    semi_total_cost = fields.Float(
        string='Semi-Comprehensive Total Cost',
        digits=(12, 2),
        compute='_compute_costs',
        store=True,
    )
    full_total_cost = fields.Float(
        string='Full Comprehensive Total Cost',
        digits=(12, 2),
        compute='_compute_costs',
        store=True,
    )
    semi_cost_per_unit = fields.Float(
        string='Semi-Comprehensive Cost per Unit',
        digits=(12, 2),
        compute='_compute_costs',
        store=True,
    )
    full_cost_per_unit = fields.Float(
        string='Full Comprehensive Cost per Unit',
        digits=(12, 2),
        compute='_compute_costs',
        store=True,
    )

    # --- Detail lines ---
    line_ids = fields.One2many(
        'amc.pricing.line',
        'pricing_id',
        string='Spare Parts Costing',
        copy=True,
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'The AMC Pricing template name must be unique!'),
    ]
    
    '''Code Added on August 25 2026 when we duplicate it will cause the error'''
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
    
        base_name = self.name
        copy_name = f"{base_name} (Copy)"
    
        count = 1
        while self.search_count([('name', '=', copy_name)]):
            count += 1
            copy_name = f"{base_name} (Copy {count})"
    
        default['name'] = copy_name
    
        return super().copy(default)

    # @api.depends(
    #     'line_ids.total_cost',
    #     'line_ids.is_full_comprehensive_only',
    #     'semi_comprehensive_units',
    #     'full_comprehensive_units',
    # )
    # def _compute_costs(self):
    #     for rec in self:
    #         semi_total = 0.0
    #         full_total = 0.0
    #         for line in rec.line_ids:
    #             full_total += line.total_cost
    #             if not line.is_full_comprehensive_only:
    #                 semi_total += line.total_cost
    #
    #         # Semi total only when semi units > 0
    #         rec.semi_total_cost = round(semi_total, 2) if rec.semi_comprehensive_units else 0.0
    #         rec.full_total_cost = round(full_total, 2)
    #         rec.semi_cost_per_unit = round(
    #             semi_total / rec.semi_comprehensive_units, 2
    #         ) if rec.semi_comprehensive_units else 0.0
    #         rec.full_cost_per_unit = round(
    #             full_total / rec.full_comprehensive_units, 2
    #         ) if rec.full_comprehensive_units else 0.0

    @api.depends(
        "line_ids.total_cost",
        "line_ids.is_full_comprehensive_only",
        "semi_comprehensive_units",
        "full_comprehensive_units",
    )

    @api.depends(
        "line_ids.total_cost",
        "line_ids.is_full_comprehensive_only",
        "semi_comprehensive_units",
        "full_comprehensive_units",
    )
    def _compute_costs(self):
        for rec in self:
            semi_total = 0.0
            full_total = 0.0

            for line in rec.line_ids:
                full_total += line.total_cost
                if not line.is_full_comprehensive_only:
                    semi_total += line.total_cost

            total_units = rec.total_units or 0

            # Safe ratios
            semi_ratio = (
                (rec.semi_comprehensive_units / total_units) if total_units else 0
            )
            full_ratio = (
                (rec.full_comprehensive_units / total_units) if total_units else 0
            )

            # Costs
            rec.semi_total_cost = round(semi_total * semi_ratio, 0)
            rec.full_total_cost = round(full_total * full_ratio, 0)

            # Per unit costs
            rec.semi_cost_per_unit = (
                round(rec.semi_total_cost / rec.semi_comprehensive_units, 0)
                if rec.semi_comprehensive_units
                else 0.0
            )

            rec.full_cost_per_unit = (
                round(rec.full_total_cost / rec.full_comprehensive_units, 0)
                if rec.full_comprehensive_units
                else 0.0
            )

            # Total
            rec.total_cost = round(rec.semi_total_cost + rec.full_total_cost, 0)

    #def _compute_costs(self):
        #for rec in self:
            #semi_total = 0.0
           # full_total = 0.0
            #for line in rec.line_ids:
               #full_total += line.total_cost
                #if not line.is_full_comprehensive_only:
                    #semi_total += line.total_cost

            # Semi total only when semi units > 0
            #rec.semi_total_cost = (
                #round(semi_total * (rec.semi_comprehensive_units / rec.total_units), 0)
                #if rec.semi_comprehensive_units
               # else 0.0
            # )
            # rec.full_total_cost = round(
            #     full_total * (rec.full_comprehensive_units / rec.total_units), 0
            # )
            # rec.semi_cost_per_unit = (
            #     round(rec.semi_total_cost / rec.semi_comprehensive_units, 0)
            #     if rec.semi_comprehensive_units
            #     else 0.0
            # )
            # rec.full_cost_per_unit = (
            #     round(rec.full_total_cost / rec.full_comprehensive_units, 0)
            #     if rec.full_comprehensive_units
            #     else 0.0
            # )
            # rec.total_cost = round(rec.semi_total_cost + rec.full_total_cost, 0)

    def action_calculate(self):
        """Recalculate costs — triggers the compute fields."""
        for rec in self:
            # Refresh cost price from product catalog
            for line in rec.line_ids:
                if line.product_id:
                    line.std_unit_cost = line.product_id.standard_price
            # Re-trigger computed fields
            rec._compute_costs()
        return True

    def action_create_copy(self):
        """Create a copy of this template."""
        self.ensure_one()
        new_rec = self.copy(default={
            'name': _('%s (Copy)') % self.name,
            'is_default': False,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'amc.pricing',
            'res_id': new_rec.id,
            'view_mode': 'form',
            'target': 'current',
        }


class AmcPricingLine(models.Model):
    _name = 'amc.pricing.line'
    _description = 'AMC Pricing Detail Line'
    _order = 'sequence, id'

    pricing_id = fields.Many2one(
        'amc.pricing',
        string='AMC Pricing',
        ondelete='cascade',
        required=True,
    )
    sequence = fields.Integer(
        string='SL No',
        default=10,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Item',
        required=True,
    )
    qty = fields.Float(
        string='Qty',
        digits=(12, 2),
        compute='_compute_qty',
        store=True,
        help='Calculated: Total Units × % to be Used',
    )
    std_unit_cost = fields.Float(
        string='Std Unit Cost',
        digits=(12, 2),
        help='Cost price from product catalog.',
    )
    total_cost = fields.Float(
        string='Total Cost',
        digits=(12, 2),
        compute='_compute_total_cost',
        store=True,
    )
    percent_to_use = fields.Float(
        string='% to be Used',
        digits=(12, 4),
        help='Percentage of usage (e.g., 0.10 = 10%).',
    )
    is_full_comprehensive_only = fields.Boolean(
        string='Full Comprehensive Only',
        default=False,
        help='If Yes, this item is excluded from Semi-Comprehensive calculation (e.g., Compressor).',
    )

    @api.depends('pricing_id.total_units', 'percent_to_use')
    def _compute_qty(self):
        for line in self:
            line.qty = round(line.pricing_id.total_units * line.percent_to_use, 2)

    @api.depends('qty', 'std_unit_cost')
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = line.qty * line.std_unit_cost

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-fill cost price when product is selected."""
        if self.product_id:
            self.std_unit_cost = self.product_id.standard_price
