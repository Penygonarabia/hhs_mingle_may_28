# from odoo import models, api
#
#
# class ProductTemplate(models.Model):
#     _inherit = 'product.template'
#
#     def search_qty_available(self, qty_filter):
#         return self.search([('qty_available', '=', qty_filter)])
#
#     @api.model
#     def search(self, args, offset=0, limit=None, order=None, count=False):
#         # Look for a specific filter in the search criteria
#         qty_filter = next((arg[2] for arg in args if arg[0] == 'qty_available' and arg[1] == '='), None)
#
#         if qty_filter is not None:
#             return self.search_qty_available(qty_filter)
#
#         return super(ProductTemplate, self).search(args, offset=offset, limit=limit, order=order, count=count)