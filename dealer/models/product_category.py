# from odoo import models, fields, api

# class ProductCategory(models.Model):
#     _inherit = "product.category"
#     _rec_name = "alternative_description"

#     def name_get(self):
#         result = []
#         for rec in self:
#             if self.env.context.get("use_alt_desc"):
#                 # Show ONLY alternative_description (even if empty)
#                 name = rec.alternative_description or ""
#             else:
#                 # Default everywhere else
#                 name = rec.name
#             result.append((rec.id, name))
#         return result
