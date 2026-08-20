# -*- coding: utf-8 -*

from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

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
    # Contract based Added on - 29-07-2028
    contract_number = fields.Char(string='Contract Number')
    contract_field_visible = fields.Boolean(
        compute='_compute_contract_field_visible',
        store=False
    )
    asset_number = fields.Char(string='Asset Number')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
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
    category_group_type = fields.Char(string="Product Group Type")
    product_arabic_name = fields.Char(string="Arabic Name")
    use_for_promoter = fields.Boolean(string="Use For Promoter", default=False)
    standard_hours = fields.Float(string="Standard Hours")
    return_damage_item_to_warehouse = fields.Boolean(
        string="Return Damage Item To Warehouse",
    )
    service_product_price_edit_bool = fields.Boolean(string="Service Product Price Edit", default=False,
                                                     help="Whenever Technician allow to change the service product unit price"
                                                     )
    
    '''Code Added on August 18 2026 By Vijaya Bhaskar'''
    product_sub_category_id = fields.Many2one(
        "sub_category",
        string="Product Sub Category",
        compute="_compute_product_sub_category",
        inverse="_inverse_product_sub_category",
        store=True,
    )

    @api.depends("product_tmpl_id.product_sub_category_id")
    def _compute_product_sub_category(self):
        for product in self:
            product.product_sub_category_id = (
                product.product_tmpl_id.product_sub_category_id
            )

    def _inverse_product_sub_category(self):
        for product in self:
            product.product_tmpl_id.product_sub_category_id = (
                product.product_sub_category_id
            )
    
    # promoter_user_bool = fields.Boolean(string = "Promoter User",default = False, compute = "_compute_promoter_user_bool")

    # def _compute_promoter_user_bool(self):
    #     for rec in self:
    #         rec.promoter_user_bool = False
    #         if self.env.user.has_group('promoter.group_promoter_module_user'):
    #             rec.promoter_user_bool = True

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

    @api.depends('is_machine')
    def _compute_contract_field_visible(self):
        Param = self.env['ir.config_parameter'].sudo()
        contract_installed = self.env['ir.module.module'].sudo().search_count([
            ('name', '=', 'sales_contract_and_recurring_invoices'),
            ('state', '=', 'installed')
        ]) > 0
        contract_required = Param.get_param('machine_repair_management.maintenance_service_show')
        for rec in self:
            # rec.contract_field_visible = rec.is_machine and contract_installed and contract_required
            rec.contract_field_visible = contract_installed and contract_required

    ###contract code end

    # @api.depends('warehouse_id')
    # def _compute_on_hand_qty(self):
    #     print("............11111111111111111111111")
    #     for product in self:
    #         warehouse_id = self.env.context.get('warehouse')
    #         if warehouse_id:
    #             # Assuming stock.quant model is used for stock calculation
    #             quant = self.env['stock.quant'].search([
    #                 ('product_id', '=', product.id),
    #                 ('location_id', '=', warehouse_id.lot_stock_id.id)
    #             ])
    #             product.on_hand_qty = sum(quant.mapped('quantity'))
    #             print(".............;product",)
    #         else:
    #             product.on_hand_qty = 0.0

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

    '''This only Worked'''
   

    def action_machine_repair_request(self):
        self.ensure_one()
        res = self.env.ref('machine_repair_management.action_machine_repair_support')
        res = res.sudo().read()[0]
        res['domain'] = str([('product_id', '=', self.id)])
        return res
    
    '''Code Added on April 07 2026 by Vijaya Bhaskar'''
    '''During Product sync the product category is not updated correctly because of '*' in the product category'''
    @api.model
    def _update_product_service_category(self):
        
        service_product_search = self.env['product.product'].search([
                                    
                                    ('service_product_price_edit_bool','=', True),
                                    ('service_type_bool' ,'=', False),
                                    ('active','=', True)
                                    ])
        
        for service in service_product_search:
            service.categ_id = service.product_category_id.id or False
        
