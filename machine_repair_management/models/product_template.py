from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    brand = fields.Char(
        string="Brand"
    )
    color_custom = fields.Char(
        string="Color"
    )
    model = fields.Char(
        string="Model"
    )
    year = fields.Char(
        string="Year"
    )
    is_machine = fields.Boolean(
        string="Is Machine", default=False
    )
    machine_repair_ids = fields.One2many(
        'machine.repair.support',
        'product_id',
        string='Machine Repair Request',
        copy=False,
        readonly=True,
    )
    on_hand_qty = fields.Float(
        string='O/H Qty',
        compute='_compute_qty_available_in_warehouse',
        store=True
    )
    service_type_bool = fields.Boolean(string="Service Type", default=False)
    product_main_grp_id = fields.Many2one('t.mainproducts', string="Main Group")
    product_category_id = fields.Many2one('product.category', string="Product Category",
                                          domain="[('parent_id','=',False)]")
    product_group_id = fields.Many2one('product.category', string="Product Group",
                                       domain="[('parent_id','=',product_category_id)]")
    product_sub_group_id = fields.Many2one('product.category', string="Product Sub Group",
                                           domain="[('parent_id','=',product_group_id)]")
    product_sub_grouping_id = fields.Many2one('product.category', string="Product Sub Grouping",
                                              domain="[('parent_id','=',product_group_id),('allowed_group_is_promoter','=',True)]")
    category_code = fields.Char(string="Category Code", compute="_compute_category_code", store=True)
    group_code = fields.Char(string="Group Code", compute="_compute_group_code", store=True)
    sub_group_code = fields.Char(string="Sub Group Code", compute="_compute_sub_group_code", store=True)
    sub_grouping_code = fields.Char(string="Sub Group Code", compute="_compute_sub_grouping_code", store=True)
    category_template_group_type = fields.Char(string="Product Group Type")
    product_arabic_name = fields.Char(string="Arabic Name")
    use_for_promoter = fields.Boolean(string="Use For Promoter", default=False)
    standard_hours = fields.Float(string="Standard Hours", compute="_compute_standard_hours",
                                  inverse="_inverse_standard_hours", store=True)
    return_damage_item_to_warehouse = fields.Boolean(
        string="Return Damage Item To Warehouse",
        compute="_compute_return_damage_item_to_warehouse",
        inverse="_inverse_return_damage_item_to_warehouse",
        store=True
    )
    service_product_price_edit_bool = fields.Boolean(string="Service Product Price Edit", default=False, store=True,
                                                     compute="_compute_service_product_price_edit_bool",
                                                     inverse="_inverse_service_product_price_edit_bool",
                                                     help="Whenever Technician allow to change the service product unit price"
                                                     )

    product_sub_category_id = fields.Many2one('sub_category', string = "Product Sub Category")
    
    @api.depends('product_variant_ids.use_for_promoter')
    def _compute_use_for_promoter(self):
        for use_promoter in self:
            variant = use_promoter.product_variant_ids[:1]
            use_promoter.use_for_promoter = bool(variant and variant.use_for_promoter)

    def _inverse_use_for_promoter(self):
        for promoter in self:
            promoter.product_variant_ids.write({'use_for_promoter': promoter.use_for_promoter})

    @api.depends('product_variant_ids.product_arabic_name')
    def _compute_product_arabic_name(self):
        for arabic_name in self:
            variant = arabic_name.product_variant_ids[:1]
            arabic_name.product_arabic_name = variant and variant.product_arabic_name

    def _inverse_product_arabic_name(self):
        for arabic_name in self:
            arabic_name.product_variant_ids.write({'product_arabic_name': arabic_name.product_arabic_name})

    @api.depends('product_variant_ids.service_product_price_edit_bool')
    def _compute_service_product_price_edit_bool(self):
        for product in self:
            variant = product.product_variant_ids[:1]
            product.service_product_price_edit_bool = bool(variant and variant.service_product_price_edit_bool)

    def _inverse_service_product_price_edit_bool(self):
        for product in self:
            product.product_variant_ids.write(
                {'service_product_price_edit_bool': product.service_product_price_edit_bool})

    @api.depends('product_variant_ids.service_type_bool')
    def _compute_service_type_bool(self):
        for service_type in self:
            service_bool = service_type.product_variant_ids[:1]
            service_type.service_type_bool = bool(service_bool and service_bool.service_type_bool)

    def _inverse_service_type_bool(self):
        for service_type in self:
            service_type.product_variant_ids.write({'service_type_bool': service_type.service_type_bool})

    @api.depends("product_variant_ids.return_damage_item_to_warehouse")
    def _compute_return_damage_item_to_warehouse(self):
        """Compute template cost from the first variant"""
        for template in self:
            if template.product_variant_count == 1:
                template.return_damage_item_to_warehouse = (
                    template.product_variant_ids.return_damage_item_to_warehouse
                )
            else:
                # If multiple variants, Odoo does not compute a mean; uses the first one
                template.return_damage_item_to_warehouse = template.product_variant_ids[
                                                           :1
                                                           ].return_damage_item_to_warehouse

    def _inverse_return_damage_item_to_warehouse(self):
        """Write template cost to ALL product variants"""
        for template in self:
            template.product_variant_ids.write(
                {
                    "return_damage_item_to_warehouse": template.return_damage_item_to_warehouse
                }
            )

    @api.depends('product_variant_ids.standard_hours')
    def _compute_standard_hours(self):
        """Compute template cost from the first variant"""
        for template in self:
            if template.product_variant_count == 1:
                template.standard_hours = template.product_variant_ids.standard_hours
            else:
                # If multiple variants, Odoo does not compute a mean; uses the first one
                template.standard_hours = template.product_variant_ids[:1].standard_hours

    def _inverse_standard_hours(self):
        """Write template cost to ALL product variants"""
        for template in self:
            template.product_variant_ids.write({
                'standard_hours': template.standard_hours
            })

    @api.onchange('product_category_id', 'product_group_id', 'product_sub_group_id', 'product_sub_grouping_id')
    def _onchange_product_groups(self):
        for rec in self:
            if rec.product_sub_grouping_id:
                rec.categ_id = rec.product_sub_grouping_id.id
                # rec.sub_grouping_code = rec.product_sub_grouping_id.code   

            elif rec.product_sub_group_id:
                rec.categ_id = rec.product_sub_group_id.id
                # rec.sub_group_code = rec.product_sub_group_id.code
            elif rec.product_group_id:
                rec.categ_id = rec.product_group_id.id
                # rec.group_code = rec.product_group_id.code

            elif rec.product_category_id:
                rec.categ_id = rec.product_category_id.id
                # rec.category_code = rec.product_category_id.code
            else:
                rec.categ_id = False

    @api.depends('product_category_id')
    def _compute_category_code(self):
        for rec in self:
            rec.category_code = False
            if rec.product_category_id:
                rec.category_code = rec.product_category_id.code

    @api.depends('product_group_id')
    def _compute_group_code(self):
        for rec in self:
            rec.group_code = False
            if rec.product_group_id:
                rec.group_code = rec.product_group_id.code

    @api.depends('product_sub_group_id')
    def _compute_sub_group_code(self):
        for rec in self:
            rec.sub_group_code = False
            if rec.product_sub_group_id:
                rec.sub_group_code = rec.product_sub_group_id.code

    @api.depends('product_sub_grouping_id')
    def _compute_sub_grouping_code(self):
        for rec in self:
            rec.sub_grouping_code = False
            if rec.product_sub_grouping_id:
                rec.sub_grouping_code = rec.product_sub_grouping_id.code

    @api.depends('warehouse_id')
    def _compute_qty_available_in_warehouse(self):
        warehouse_id = self.warehouse_id
        location = self.env['stock.location']
        if warehouse_id:
            # warehouse = self.env['stock.warehouse'].browse(warehouse_id)
            location = warehouse_id.lot_stock_id
        for product in self:
            product.on_hand_qty = 0.0
            if location:
                quants = self.env['stock.quant'].sudo().search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', location.id)
                ])
                product.on_hand_qty = sum(quants.mapped('quantity'))

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        self._compute_quantities()
