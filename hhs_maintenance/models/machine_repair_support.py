from odoo import api, fields, models, _

class MachineRepairSupport(models.Model):
    
    _inherit = "machine.repair.support"
    
    brand_id = fields.Many2one('brand', string='Brand')
    model_id = fields.Many2one('equipment.model.code', string='Model')
    
    items_from_own_company_bool = fields.Boolean(string = "Items From Own Company",default = False, help = "When the brand have product category and service unit type have same product category")
    
    product_product_model_id = fields.Many2one('product.product',string = "Product model")
    
    product_search_ids = fields.Many2many('product.product',
                                          "machine_repair_support_rel", # different relation table
                                            "service_request_id",
                                            "product_id",
                                            string = "Product Search",
                                            compute = "_compute_product_search_ids",store = False)
                                            
    
    
    '''Code Added on June 08 2026 by Vijaya Bhaskar'''
    @api.depends('items_from_own_company_bool', 'service_products_code_id','project_related_amc_bool','brand_id')
    def _compute_product_search_ids(self):
        for rec in self:
            rec.product_search_ids = False
            if rec.project_related_amc_bool:
                if rec.items_from_own_company_bool and rec.service_products_code_id:
                    # products = self.env['product.product'].search([
                    #     ('categ_id', '=', rec.service_products_code_id.categ_id.id)
                    # ])
                   
                    products = self.env['product.product'].search([
                        ('product_category_id','=',rec.brand_id.amc_product_category_id.id),
                        ('product_group_id','=',rec.service_products_code_id.product_group_id.id)
                        ])
    
                    
                    rec.product_search_ids = [(6, 0, products.ids)]   
                    
    def _create_job_card(self):
        res = super()._create_job_card()
        for rec in self:
            if rec.task_id:
                rec.task_id.write({
                    'brand_id': rec.brand_id.id or False,
                    'items_from_own_company_bool': rec.items_from_own_company_bool or False,
                    'model_id': rec.model_id.id or False,
                    'product_product_model_id': rec.product_product_model_id.id or False,
                })

        return res 
    
    def write(self,vals):
        res = super().write(vals)
        for rec in self:
            if 'product_slno' in vals:
                rec.asset_id.serial_no = vals.get('product_slno')
        return res
  
