# # -*- coding: utf-8 -*
#
# from odoo import models, fields, api, _
# from odoo.exceptions import ValidationError
#
# class SaleOrder(models.Model):
#     _inherit = 'sale.order'
#
#     task_id = fields.Many2one(
#         'project.task',
#         string="Task",
#     ) # This field is present in odoo Enterprice named industry_fsm 
#
#
#     partner_id = fields.Many2one(
#         comodel_name='res.partner',
#         string="Customer",
#         required=False,
#         change_default=True, index=True,
#         tracking=1,
#         check_company=True)
#
#
#     partner_invoice_id = fields.Many2one(
#         comodel_name='res.partner',
#         string="Invoice Address",
#         compute='_compute_partner_invoice_id',
#         store=True, readonly=False, required=False, precompute=True,
#         check_company=True,
#         index='btree_not_null')
#     partner_shipping_id = fields.Many2one(
#         comodel_name='res.partner',
#         string="Delivery Address",
#         compute='_compute_partner_shipping_id',
#         store=True, readonly=False, required=False, precompute=True,
#         check_company=True,
#         index='btree_not_null')
#
#     state = fields.Selection([
#         ('draft', 'Quotation'),
#         ('sent', 'Quotation Sent'),
#         ('sale', 'Confirmed'),
#         ('done', 'Locked'),
#         ('cancel', 'Cancelled'),
#         ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
#
#     # Order Lines Duplicate One2many fields
#     order_line_duplicate = fields.One2many(
#         comodel_name='sale.order.line',
#         inverse_name='order_id',
#         string="Order Lines",
#         copy=True, auto_join=True)
#
#     customer_name = fields.Char(string = "Customer")
#
#     address = fields.Char(string = "Address",store = True,compute = "_compute_address")
#
#     @api.depends('task_id')
#     def _compute_address(self):
#         for rec in self:
#             rec.address = False
#             if rec.task_id:
#                 rec.address = rec.task_id.address
#
#
#
#
#     def send_whatsapp_message(self):
#         for rec in self:
#             if rec.task_id:
#                 if rec.state in ('draft','sent'):
#                     task_product = rec.task_id.product_line_ids.mapped('product_id')
#                     sale_product = rec.order_line.mapped('product_id')
#                     missed = task_product - sale_product
#                     sale_total = rec.amount_total
#                     task_total = rec.task_id.grand_total
#                     if missed :
#                         raise ValidationError("During Confirm Products are matched with job card Products.Please check it or otherwise Please cancel once again create the quotation from the Job Card")
#                     if sale_total != task_total:
#                         raise ValidationError("Sale Total is different from Consume Parts service total ") 
#
#
#         return super().send_whatsapp_message()
#
#
#     def action_quotation_send(self):
#         for rec in self:
#             if rec.task_id:
#                 if rec.state == 'draft':
#                     task_product = rec.task_id.product_line_ids.mapped('product_id')
#                     sale_product = rec.order_line.mapped('product_id')
#                     missed = task_product - sale_product
#                     sale_total = rec.amount_total
#                     task_total = rec.task_id.grand_total
#                     if missed:
#                         raise ValidationError("Products are not matched in the sale order and job card quotation")
#                     if sale_total != task_total:
#                         raise ValidationError("Sale Total is different from Consume Parts service total ") 
#
#         return super().action_quotation_send()
#
#     def action_confirm(self):
#         for rec in self:
#             if rec.task_id:
#                 if rec.state in ('draft','sent'):
#                     task_product = rec.task_id.product_line_ids.mapped('product_id')
#                     sale_product = rec.order_line.mapped('product_id')
#                     missed = task_product - sale_product
#                     sale_total = rec.amount_total
#                     task_total = rec.task_id.grand_total
#                     if missed :
#                         raise ValidationError("During Confirm Products are matched with job card Products.Please check it or otherwise Please cancel once again create the quotation from the Job Card")
#                     if sale_total != task_total:
#                         raise ValidationError("Sale Total is different from Consume Parts service total ") 
#
#                 if rec.whatsapp_button_click_bool:
#                     if rec.task_id:
#                         stage_model = self.env['project.task.type']
#                         stage_search = stage_model.search([('code', '=', '127')], limit=1)
#                         if stage_search:
#                             rec.task_id.update({
#                                 'job_state': stage_search,
#                                 'job_card_state_code': stage_search.code,
#                                 'job_card_state': stage_search.name
#                             })
#                             # rec.task_id._onchange_job_card_state_status()
#
#         return super().action_confirm()    
#
#
#     def action_cancel(self):
#         for rec in self:
#             if rec.task_id:
#                 if rec.whatsapp_button_click_bool:
#                     stage_model = self.env['project.task.type']
#                     stage_search = stage_model.search([('code', '=', '128')], limit=1)
#                     if stage_search:
#                         rec.task_id.update({
#                                 'job_state': stage_search,
#                                 'job_card_state_code': stage_search.code,
#                                 'job_card_state': stage_search.name
#                             })
#                         # rec.task_id._onchange_job_card_state_status()
#                         rec.task_id.client_remarks = f"Rejected by customer:{rec.rejection_reason}"
#         return super().action_cancel()   
#
#     def action_view_job_card(self):
#
#         return{
#
#             'name':'Job Card',
#             'res_model':'project.task',
#             'type':'ir.actions.act_window',
#             'view_mode':'tree,form',
#             'domain':[('sale_id','=',self.id)],
#             'views': [(False, 'form')],
#             'target': 'current', 
#             'res_id': self.task_id.id,
#
#             }
#     # @api.constrains('amount_total','task_id')
#     # def _check_total(self):
#     #     for rec in self:
#     #         if rec.state in ('draft','sent'):
#     #             if rec.task_id:
#     #                 sale_total = rec.amount_total
#     #                 task_total = rec.task_id.grand_total
#     #                 if sale_total != task_total:
#     #                     raise ValidationError("Sale Total is different from Consume Parts service total.So Please Cancel it and then Create a new one from the job card screen")    
#
#     #
#     # @api.model
#     # def create(self,vals):
#     #     if self.env.user.has_group('machine_repair_management.group_machine_repair_user'):
#     #         if self.env.context.get('from_task'):
#     #             raise ValidationError("You are not allowed to create the sales order ")
#     #     return super(SaleOrder, self).create(vals)         
#
#
# class SaleOrder(models.Model):
#
#     _inherit = 'sale.order.line'   
#
#
#     @api.constrains('order_id','product_id', 'product_uom_qty', 'price_unit', 'name')
#     def _check_task_product_match(self):
#         if self.env.context.get('from_task'):
#             return
#
#         for line in self:
#             order = line.order_id
#             task = order.task_id
#
#             if not task or not task.product_line_ids:
#                 continue
#
#             if order.state not in ('draft', 'sent'):
#                 continue
#
#             task_lines = task.product_line_ids.filtered(lambda l: l.product_id)
#
#             task_product_map = {
#                 l.product_id.id: {
#                     'qty': l.qty,
#                     'price_unit': l.price_unit,
#                     'name': l.product_id.name,
#                 }
#                 for l in task_lines
#             }
#
#             order_lines = order.order_line.filtered(lambda l: l.product_id)
#             order_product_map = {
#                 l.product_id.id: {
#                     'qty': l.product_uom_qty,
#                     'price_unit': l.price_unit,
#                     'name': l.product_id.name,
#                 }
#                 for l in order_lines
#             }
#
#             errors = []
#
#             # Check if all products in task exist in quotation with exact qty, price and name
#             for product_id, task_vals in task_product_map.items():
#                 order_vals = order_product_map.get(product_id)
#                 if not order_vals:
#                     product = self.env['product.product'].browse(product_id)
#                     errors.append(f"Product '{product.display_name}' is missing in the quotation.")
#                     continue
#
#                 if task_vals['name'] != order_vals['name']:
#                     errors.append(
#                         f"Product name mismatch for '{task_vals['name']}'."
#                     )
#
#                 if float(task_vals['qty']) != float(order_vals['qty']):
#                     errors.append(
#                         f"Quantity mismatch for '{task_vals['name']}': Task = {task_vals['qty']}, Quotation = {order_vals['qty']}."
#                     )
#
#                 if float(task_vals['price_unit']) != float(order_vals['price_unit']):
#                     errors.append(
#                         f"Price mismatch for '{task_vals['name']}': Task = {task_vals['price_unit']}, Quotation = {order_vals['price_unit']}."
#                     )
#
#             if errors:
#                 raise ValidationError(
#                     "Quotation amount does not exactly match Job card Amount" )
#
#
#
#         # for order in self:
#         #     if not order.order_id.task_id or not order.order_id.task_id.product_line_ids:
#         #         continue
#         #     if order.order_id.task_id:
#         #         if order.order_id.state in ('draft','sent'):
#         #             task_products = order.order_id.task_id.product_line_ids.mapped('product_id')
#         #             order_products = order.mapped('product_id')
#         #             missing = task_products - order_products
#         #             sale_total = order.order_id.amount_total
#         #             task_total = order.order_id.task_id.grand_total
#         #             if missing:
#         #                 raise ValidationError(
#         #                 "All products from the linked task must be included in the quotation.If You Include the Product in the quotation.Please Cancel this and Create the new one from the Job Card screen")
#         #
#
#
