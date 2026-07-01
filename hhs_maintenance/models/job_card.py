from odoo import api, fields,models, _

class JobCard(models.Model):
    
    _inherit = "project.task"
    
  
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
                                            
    
    
    
    @api.depends('items_from_own_company_bool', 'service_products_code_id','project_related_amc_bool','brand_id')
    def _compute_product_search_ids(self):
        for rec in self:
            rec.product_search_ids = False
            if rec.project_related_amc_bool:
                if rec.items_from_own_company_bool and rec.service_products_code_id:
                   
                    products = self.env['product.product'].search([
                        ('product_category_id','=',rec.brand_id.amc_product_category_id.id),
                        ('product_group_id','=',rec.service_products_code_id.product_group_id.id)
                        ])
    
                    
                    rec.product_search_ids = [(6, 0, products.ids)]  
                    
    def write(self,vals):
        
        res =super().write(vals)
        if 'brand_id' in vals:
           self.service_request_id.brand_id = vals.get('brand_id')
           self.asset_id.brand_id = vals.get('brand_id')

           
        if 'items_from_own_company_bool' in vals:
            self.service_request_id.items_from_own_company_bool = vals.get('items_from_own_company_bool')
            self.asset_id.items_from_own_company_bool = vals.get('items_from_own_company_bool')

        if 'model_id' in vals:
            self.service_request_id.model_id = vals.get('model_id')
            self.asset_id.model_id = vals.get('model_id')

        
        if 'product_product_model_id' in vals:
            self.service_request_id.product_product_model_id = vals.get('product_product_model_id')
            self.asset_id.product_product_model_id = vals.get('product_product_model_id')   
  
               
        return res
        
                        
