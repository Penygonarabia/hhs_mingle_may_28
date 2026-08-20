from odoo import fields, models, api, _

class Brand(models.Model):
    _name = 'brand'
    _description = 'Equipment Brand'

    name = fields.Char(string='Brand', required=True, unique=True)
    amc_product_category_id = fields.Many2one('product.category', domain ="[('parent_id','=',False),('allowed_is_contract','=',True)]", string = "Product Category")



class EquipmentModelCode(models.Model):
    _name = 'equipment.model.code'
    _description = 'Equipment Model'
    _rec_name = "model_code"

    brand_id = fields.Many2one('brand', string='Brand', required=True)
    model_code = fields.Char(string='Model', required=True)

    _sql_constraints = [
        ('brand_model_unique', 'unique(brand_id, model_code)', 'Model Code must be unique per Brand')
    ]
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
 
        # 🔥 This gets typed value from popup
        if self._context.get("default_name"):
            res["model_code"] = self._context.get("default_name")
 
        return res
