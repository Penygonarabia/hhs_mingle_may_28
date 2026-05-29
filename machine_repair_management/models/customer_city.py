# from odoo import api, fields, models, _
#
#
# class Customer_city(models.Model):
#     _inherit = 'res.partner'
#
#     customer_city_id = fields.Many2one('res.city', string="customer City")
#
#     @api.onchange('customer_city_id')
#     def _onchange_customer_city_id(self):
#         if self.customer_city_id:
#             self.city = self.customer_city_id.name
#             self.zip = self.customer_city_id.zipcode
#             self.state_id = self.customer_city_id.state_id
#             self.country_id = self.customer_city_id.country_id
#             # print(f"City selected: {self.customer_city_id.name}")
