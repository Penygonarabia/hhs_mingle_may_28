# from odoo import api, fields, models, _
# from odoo.exceptions import ValidationError, UserError
# import requests
# import logging
# from decimal import Decimal,ROUND_UP
# from lxml import etree
# import json
# import base64
# from odoo.tools import float_round
# _logger = logging.getLogger(__name__)
#
# class ServiceSaleOrder(models.Model):
#
#     _name = "service.sale.order"
#
#     _description = "Service Sale Order"
#
#     _inherit = ['mail.thread', 'mail.activity.mixin', 'format.address.mixin', 'portal.mixin']
#
#
#
#     name = fields.Char(string = "Quotation No.", default='New', store = True)
#
#     customer_name = fields.Char(string = "Customer Name")
#
#     customer_address = fields.Char("Delivery Address")
#
#     company_id = fields.Many2one('res.company',string = "Company", default = lambda self: self.env.user.company_id)
#
#     service_sale_order_line_ids = fields.One2many('service.sale.order.line','service_sale_id',string = "Service Sale Order Line")
#
#     service_order_line_duplicate = fields.One2many(
#         comodel_name='service.sale.order.line',
#         inverse_name='service_sale_id',
#         string="Order Lines",
#         copy=True, auto_join=True)
#
#     state = fields.Selection([
#         ('draft', 'Quotation'),
#         ('sent', 'Quotation Sent'),
#         ('sale', 'Confirmed'),
#         ('done', 'Locked'),
#         ('cancel', 'Cancelled'),
#         ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
#
#     job_task_id = fields.Many2one('project.task',string = "Job Task")
#
#     whatsapp_button_click_bool = fields.Boolean(string = "Whatsapp Click" , default = False)
#
#     rejection_reason = fields.Char(string="Rejection Reason", tracking=True)
#
#     service_sale_quotation_date = fields.Datetime(string = "Quotation Date" , default = fields.Datetime.now())
#
#     user_id = fields.Many2one('res.users',string  = "Salesperson")
#
#     untaxed_amount = fields.Float(string="Sub Total" ,compute = "_compute_total_amount" , store =True)
#
#     vat_amount = fields.Float(string="VAT Amount" , compute = "_compute_total_amount"  , store =True)
#
#     grand_total_amount = fields.Float(string = "Total", compute = "_compute_total_amount" , store =True)
#
#     inspection_charges_amount = fields.Float(string = "Inspection Charges amount",store = True,
#                                              compute = "_compute_inspection_charges_amount")
#
#
#     balance_paid = fields.Float(string = "Balance to be Paid",compute = "_compute_balance_paid",store = True)
#
#     contract_period = fields.Integer(string="Contract Period")
#     contract_interval = fields.Selection([
#         ('Days', 'Days'),
#         ('Weeks', 'Weeks'),
#         ('Months', 'Months'),
#         ('Years', 'Years'),
#     ], help='Recurring interval of subscription contract', string="Contract Interval", default='Years')
#     no_of_prevent_service = fields.Integer(string="No. of Prevent Service Per Year - XX")
#     add_paid_service_price = fields.Float(string="Additional Paid Service Price")
#     invoice_interval = fields.Integer(string="Invoice Interval (Days)")
#     approval_level_id = fields.Many2one('approval.approval', string="Approval Level")
#     no_of_correct_service = fields.Integer(string="No.of Corrective Service Per Year - XX")
#     # payment_term_id = fields.Many2one('account.payment.term', string="Payment Terms")
#     payment_term_id = fields.Many2one('account.payment.term', string="Payment Terms", required=True,
#                                       default=lambda self: self.env['account.payment.term'].search(
#                                           [('name', '=', 'Immediate Payment')], limit=1))
#     date_expiry = fields.Datetime(string = "Expiration Date")
#     amc_quotation = fields.Boolean(string="Is AMC Quotation", default=False)
#     crm_id = fields.Many2one('crm.lead', string="Crm Origin")
#     total_discount = fields.Float(string="Total Discount (-)")
#
#     whatsapp_sale_send_bool = fields.Boolean(string = "Whatsapp Send Y/N", default = False, help = "All Whatsapp Send feature Enable/Not in res.config_settings",
#                                         compute = "_compute_whatsapp_sale_send_bool")
#
#     warehouse_id = fields.Many2one('stock.warehouse', string = "Warehouse")
#
#     travel_hours = fields.Float(string="Travel Hours")
#     gross_profit = fields.Float(string="Gross Margin")
#     show_approval_button = fields.Boolean(string="Show Approval Button", compute='compute_approval_button')
#
#
#     # @api.depends('job_task_id')
#     # def _compute_warehouse_id(self):
#     #     for rec in self:
#     #         rec.warehouse_id = False
#     #         if rec.job_task_id:
#     #             rec.warehouse_id = rec.job_task_id.warehouse_id.id
#     #
#
#     @api.constrains('contract_period', 'invoice_interval')
#     def _check_contract_period(self):
#         for rec in self:
#             if rec.contract_period is not None and rec.contract_period <= 0:
#                 raise ValidationError(_("Contract period must be greater than 0."))
#             if rec.invoice_interval is not None and rec.invoice_interval <= 0:
#                 raise ValidationError(_("Invoice Interval must be greater than 0."))
#
#     @api.constrains('gross_profit')
#     def check_discount_limit_constrains(self):
#         conf_gross_profit = float(
#             self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.gross_profit', default=0.0))
#         total_gross_profit = conf_gross_profit - self.env.user.discount_limit
#         for record in self:
#             if self.env.user.discount_limit != 0.00 and record.gross_profit < total_gross_profit:
#                 message = "You can only assign maximum " + str(
#                     self.env.user.discount_limit) + "% Discount \nContact your administrator for more details"
#                 raise ValidationError(_(message))
#     ## End##
#
#
#     def _compute_whatsapp_sale_send_bool(self):
#         for rec in self:
#             rec.whatsapp_sale_send_bool = False
#             whatsapp_search = self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.whatsapp_send_bool')
#             if whatsapp_search == 'True':
#                 rec.whatsapp_sale_send_bool = True
#
#
#
#     @api.onchange('job_task_id','crm_id')
#     def _onchange_amc_quotation(self):
#         for rec in self:
#             if rec.job_task_id:
#                 rec.amc_quotation = False
#             if rec.crm_id:
#                 rec.amc_quotation = True
#
#
#     @api.depends('job_task_id','job_task_id.inspection_charges_bool','job_task_id.inspection_charges_amount')
#     def _compute_inspection_charges_amount(self):
#         for rec in self:
#             rec.inspection_charges_amount = False
#             if rec.job_task_id:
#                 if rec.job_task_id.inspection_charges_bool and (rec.job_task_id.inspection_charges_amount > 0):
#                     rec.inspection_charges_amount = rec.job_task_id.inspection_charges_amount
#
#     ''' This is currently working code commented on Nov 7 2025 due to only inspection charges given under warrantly they make negative in the balance paid field
#     @api.depends('grand_total_amount','inspection_charges_amount')
#     def _compute_balance_paid(self):
#         for rec in self:
#             rec.balance_paid = rec.grand_total_amount - rec.inspection_charges_amount
#     '''
#
#
#     @api.depends('job_task_id','job_task_id.balance_paid','grand_total_amount','inspection_charges_amount',
#                  'job_task_id.inspection_charges_bool','job_task_id.balance_amount_received_bool',
#                  'job_task_id.final_inspection_charges_amount', 'job_task_id.balance_amount_received_bool',)
#     def _compute_balance_paid(self):
#         for rec in self:
#             # rec.balance_paid = False
#             # if rec.job_task_id:
#             #     if rec.state in ('draft','sent'):
#             #         rec.balance_paid = rec.job_task_id.balance_paid
#             #
#             rec.balance_paid = abs(rec.grand_total_amount - rec.inspection_charges_amount)
#             if rec.job_task_id.inspection_charges_bool and not rec.job_task_id.balance_amount_received_bool:
#                 if rec.job_task_id.final_inspection_charges_amount > 0 and (rec.job_task_id.grand_total == 0 or rec.job_task_id.grand_total < rec.job_task_id.final_inspection_charges_amount):
#                     rec.balance_paid = 0.0
#
#             if rec.job_task_id.balance_amount_received_bool and rec.job_task_id.inspection_charges_bool:
#                 if rec.job_task_id.final_inspection_charges_amount > 0:
#                     rec.balance_paid = abs(rec.grand_total_amount - (rec.balance_paid + rec.job_task_id.final_inspection_charges_amount))
#                 else:
#                     rec.balance_paid = abs(rec.grand_total_amount - rec.balance_paid)
#
#
#
#     # @api.depends('service_sale_order_line_ids.product_qty','service_sale_order_line_ids.price_unit',
#     #              'service_sale_order_line_ids.vat','inspection_charges_amount')
#     # def _compute_total_amount(self):
#     #     for rec in self:
#     #         rec.untaxed_amount = sum((line.price_unit * line.product_qty) for line in rec.service_sale_order_line_ids )
#     #         rec.vat_amount = sum((line.product_qty * line.price_unit * (line.vat / 100)) for line in rec.service_sale_order_line_ids)
#     #         rec.grand_total_amount =  rec.untaxed_amount + rec.vat_amount
#     #
#
#
#     # @api.depends('service_sale_order_line_ids.product_qty','service_sale_order_line_ids.price_unit',
#     #              'service_sale_order_line_ids.vat')
#     # def _compute_total_amount(self):
#     #     for rec in self:
#             # rec.untaxed_amount = sum((line.price_unit * line.product_qty) for line in rec.service_sale_order_line_ids )
#             # rec.total_discount =  sum((line.price_unit * line.product_qty * line.discount/100) for line in rec.service_sale_order_line_ids)
#             # # for line in rec.service_sale_order_line_ids:
#             # #     rec.vat_amount = (rec.untaxed_amount  - rec.total_discount) * line.vat/100
#             # rec.vat_amount = sum((line.tax_amount)for line in rec.service_sale_order_line_ids)
#             # rec.grand_total_amount =  rec.untaxed_amount  - rec.total_discount + rec.vat_amount
#
#
#     @api.depends('service_sale_order_line_ids.product_qty','service_sale_order_line_ids.price_unit',
#                  'service_sale_order_line_ids.vat')
#     def _compute_total_amount(self):
#         for rec in self:
#             if rec.amc_quotation:
#                 rec.untaxed_amount = sum(line.total_price for line in rec.service_sale_order_line_ids )
#                 rec.untaxed_amount = float_round(rec.untaxed_amount, precision_digits=0)
#                 rec.total_discount =  sum((line.price_unit * line.product_qty * line.discount/100) for line in rec.service_sale_order_line_ids)
#                 rec.vat_amount =  sum(line.vat_percent for line in rec.service_sale_order_line_ids)
#                 rec.vat_amount = float_round(rec.vat_amount, precision_digits=0)
#                 rec.grand_total_amount =  rec.untaxed_amount  - rec.total_discount + rec.vat_amount
#                 rec.grand_total_amount = float_round(rec.grand_total_amount, precision_digits=0)
#                 """validation for gross profit by Maxwell on 18-11-2025"""
#                 conf_gross_profit = float(
#                     self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.gross_profit',
#                                                                      default=0.0))
#                 total_gross_profit = conf_gross_profit - self.env.user.discount_limit
#                 for record in self:
#                     if self.env.user.discount_limit != 0.00 and record.gross_profit < total_gross_profit:
#                         message = "You can only assign maximum " + str(
#                             self.env.user.discount_limit) + "% Discount \nContact your administrator for more details"
#                         raise ValidationError(_(message))
#             else:
#                 rec.untaxed_amount = sum((line.price_unit * line.product_qty) for line in rec.service_sale_order_line_ids )
#                 rec.total_discount =  sum((line.price_unit * line.product_qty * line.discount/100) for line in rec.service_sale_order_line_ids)
#                 # for line in rec.service_sale_order_line_ids:
#                 #     rec.vat_amount = (rec.untaxed_amount  - rec.total_discount) * line.vat/100
#                 rec.vat_amount = sum((line.tax_amount)for line in rec.service_sale_order_line_ids)
#                 rec.grand_total_amount =  rec.untaxed_amount  - rec.total_discount + rec.vat_amount
#
#
#
#
#     # @api.depends('job_task_id','job_task_id.inspection_charges_bool','job_task_id.inspection_charges_amount')
#     # def _compute_inspection_charges_amount(self):
#     #     for rec in self:
#     #         if rec.job_task_id:
#     #             rec.inspection_charges_amount = False
#     #             if rec.job_task_id:
#     #                 if rec.job_task_id.inspection_charges_bool and (rec.job_task_id.inspection_charges_amount > 0):
#     #                     rec.inspection_charges_amount = rec.job_task_id.inspection_charges_amount
#     #
#     #
#     # @api.depends('service_sale_order_line_ids.product_qty','service_sale_order_line_ids.price_unit',
#     #              'service_sale_order_line_ids.vat')
#     # def _compute_total_amount(self):
#     #     for rec in self:
#     #         # if rec.crm_id:
#     #         rec.untaxed_amount = sum((line.price_unit * line.product_qty) for line in rec.service_sale_order_line_ids )
#     #         rec.total_discount =  sum((line.price_unit * line.product_qty * line.discount/100) for line in rec.service_sale_order_line_ids)
#     #         for line in rec.service_sale_order_line_ids:
#     #             rec.vat_amount = (rec.untaxed_amount  - rec.total_discount) * line.vat/100
#     #         rec.grand_total_amount =  rec.untaxed_amount  - rec.total_discount + rec.vat_amount
#     #
#     #
#     # @api.depends('grand_total_amount','inspection_charges_amount')
#     # def _compute_balance_paid(self):
#     #     for rec in self:
#     #         if rec.job_task_id:
#     #             rec.balance_paid = rec.grand_total_amount - rec.inspection_charges_amount
#     #
#     #
#     # @api.depends('service_sale_order_line_ids.product_qty','service_sale_order_line_ids.price_unit',
#     #              'service_sale_order_line_ids.vat','inspection_charges_amount')
#     # def _compute_total_amount(self):
#     #     for rec in self:
#     #         if rec.job_task_id:
#     #             rec.untaxed_amount = sum((line.price_unit * line.product_qty) for line in rec.service_sale_order_line_ids )
#     #             rec.vat_amount = sum((line.product_qty * line.price_unit * (line.vat / 100)) for line in rec.service_sale_order_line_ids)
#     #             rec.grand_total_amount =  rec.untaxed_amount + rec.vat_amount
#
#
#     def action_view_project_task(self):
#         return {
#             'name':'Job Card',
#             'res_model':"project.task",
#             'type':"ir.actions.act_window",
#             'view_mode':"tree,form",
#             "res_id": self.job_task_id.id,
#             "domain":[('service_sale_id','=',self.id)],
#             'target':"current",
#             "views":[(False,'form')],
#
#             }
#
#
#     # def whatsapp_service_sale_sent(self):
#     #     for rec in self:
#     #         if rec.job_task_id:
#     #             if rec.state in ('draft','sent'):
#     #                 task_product = rec.job_task_id.product_line_ids.mapped('product_id')
#     #                 sale_product = rec.service_sale_order_line_ids.mapped('product_id')
#     #                 missed = task_product - sale_product
#     #                 sale_total = rec.grand_total_amount
#     #                 task_total = rec.job_task_id.grand_total
#     #                 if missed :
#     #                     raise ValidationError("During Confirm Products are matched with job card Products.Please check it or otherwise Please cancel once again create the quotation from the Job Card")
#     #                 if sale_total != task_total:
#     #                     raise ValidationError("Sale Total is different from Consume Parts service total ")
#     #
#     #     self._send_service_whatsapp_sale()
#     #     self.write({'state':'sent'})
#     #     self.whatsapp_button_click_bool = True
#
#
#     def whatsapp_service_sale_sent(self):
#         for rec in self:
#             if rec.job_task_id:
#                 if rec.state in ('draft','sent'):
#                     # task_product = rec.job_task_id.product_line_ids.mapped('product_id')
#                     # sale_product = rec.service_sale_order_line_ids.mapped('product_id')
#                     # missed = task_product - sale_product
#                     sale_total = rec.grand_total_amount
#                     task_total = round(rec.job_task_id.grand_total,2)
#                     # if missed :
#                     #     raise ValidationError("During Confirm Products are matched with job card Products.Please check it or otherwise Please cancel once again create the quotation from the Job Card")
#                     if sale_total != task_total:
#                         raise ValidationError("Sale Total is different from Consume Parts service total ")
#             elif rec.crm_id:
#                 if rec.state in ('draft', 'sent'):
#                     crm_product = rec.service_sale_order_line_ids.mapped('product_id')
#         self._send_service_whatsapp_sale()
#         self.write({'state':'sent'})
#         self.whatsapp_button_click_bool = True
#
#
#     def whatsapp_amc_service_sale_sent(self):
#         self._send_service_whatsapp_sale()
#         self.write({'state': 'sent'})
#         self.whatsapp_button_click_bool = True
#
#     def action_confirm(self):
#         for rec in self:
#             if rec.job_task_id:
#                 if rec.state in ('draft','sent'):
#                     # task_product = rec.job_task_id.product_line_ids.mapped('product_id')
#                     # sale_product = rec.service_sale_order_line_ids.mapped('product_id')
#                     # missed = task_product - sale_product
#                     sale_total = rec.grand_total_amount
#                     task_total = round(rec.job_task_id.grand_total,2)
#                     # if missed :
#                     #     raise ValidationError("During Confirm Products are matched with job card Products.Please check it or otherwise Please cancel once again create the quotation from the Job Card")
#                     if sale_total != task_total:
#                         raise ValidationError("Sale Total is different from Consume Parts service total ")
#
#                 # if rec.whatsapp_button_click_bool:
#                     # if rec.job_task_id:
#                     stage_model = self.env['project.task.type']
#                     stage_search = stage_model.search([('code', '=', '127')], limit=1)
#
#                     rec.job_task_id.job_card_state_code = stage_search.code
#                     rec.job_task_id.job_card_state = stage_search.name
#                     rec.job_task_id.job_state = stage_search
#                     rec.job_task_id.service_request_id.service_request_state = stage_search.name
#                     rec.job_task_id.service_request_id.service_request_state_code = stage_search.code
#                     rec.job_task_id.service_request_id.state  = stage_search
#
#                     # rec.job_task_id._onchange_job_card_state_status()
#
#
#                 self.write({'state':'sale'})
#                 self.write({'state':'done'})
#
#     def action_cancel(self):
#         for rec in self:
#             if rec.job_task_id:
#                 # if rec.whatsapp_button_click_bool:
#                 stage_model = self.env['project.task.type']
#                 stage_search = stage_model.search([('code', '=', '128')], limit=1)
#                 rec.job_task_id.job_card_state_code = stage_search.code
#                 rec.job_task_id.job_card_state_code = stage_search.code
#                 rec.job_task_id.job_card_state = stage_search.name
#                 rec.job_task_id.job_state = stage_search
#                 rec.job_task_id.service_request_id.service_request_state = stage_search.name
#                 rec.job_task_id.service_request_id.service_request_state_code = stage_search.code
#                 rec.job_task_id.service_request_id.state  = stage_search
#
#                 if rec.rejection_reason:
#                     rec.job_task_id.client_remarks = f"Rejected by customer:{rec.rejection_reason}"
#                 else:
#                     rec.job_task_id.client_remarks = f"Rejected by customer"
#
#                 # self.write({'state':'cancel'})
#         return self.write({'state': 'cancel'})
#
#
#     # @api.model
#     # def create(self,vals):
#     #     if vals.get('name','New') =='New':
#     #         name = self.env['ir.sequence'].next_by_code('service.sale.order')
#     #         vals['name'] = name
#     #         return super().create(vals)
#
#
#
#     def _send_service_whatsapp_sale(self):
#
#         # if not self.whatsapp_sale_send_bool:
#         #     _logger.info("❌ No WhatsApp set in res Config Settings")
#         #     return False
#
#         if not self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.whatsapp_send_bool') == 'True':
#             _logger.info("❌ No WhatsApp set in res Config Settings")
#             return False
#
#         if self.job_task_id:
#
#             phone_number = self.job_task_id.phone
#             country_code = self.job_task_id.country_id.phone_code
#
#             if not phone_number:
#                 _logger.info("❌ No Phone Number is linked")
#                 return False
#
#             phone_number = phone_number.replace('+', '').replace(' ', '')
#             phone_number = f"{country_code}{phone_number}"
#
#             if not self.job_task_id.whatsapp_opt_in:
#                 _logger.info("❌ No WhatsApp opt-in for Customer %s", self.customer_name)
#                 return False
#
#             whatsapp_phone_number_id = self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')
#             access_token = self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')
#
#             if not access_token or not whatsapp_phone_number_id:
#                 _logger.error("❌ WhatsApp configuration missing")
#                 return False
#
#             base_url = f'https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}'
#             headers = {
#                 'Authorization': f'Bearer {access_token}',
#                 'Content-Type': 'application/json'
#             }
#             # --- Step 1: Send WhatsApp Text Message ---
#             message = (
#             f"عزيزي {self.customer_name}،\n"
#             "نرفق لكم عرض السعر الخاص بالخدمات المطلوبة كما هو موضح أدناه.\n"
#             "يرجى التفضل بمراجعة العرض، وفي حال الموافقة نرجو تأكيد ذلك ليتم اتخاذ الإجراءات اللازمة.\n"
#             "نشكر لكم ثقتكم،\n"
#             "HH-Shaker – Service Team\n"
#             "-----------------------------\n"
#             f"Dear {self.customer_name},\n"
#             "Please find attached the Quotation for the requested services as detailed below.\n"
#             "Kindly review the quotation, and if acceptable, confirm your approval so we may proceed with the necessary arrangements.\n"
#             "Thank you for your trust,\n"
#             "HH-Shaker – Service Team"
#              )
#
#             template_payload = {
#                 'messaging_product': "whatsapp",
#                 'to': phone_number,
#                 'type': "text",
#                 'text': {'body': message},
#             }
#
#             try:
#                 response = requests.post(f"{base_url}/messages", headers=headers, json=template_payload)
#                 response.raise_for_status()
#                 _logger.info("✅ WhatsApp text message sent successfully to %s", phone_number)
#             except requests.exceptions.RequestException as e:
#                 _logger.error("❌ Failed to send WhatsApp message: %s", str(e))
#                 return False
#             # --- Step 2: Generate PDF ---
#             try:
#
#                 pdf_content, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
#                         'machine_repair_management.report_service_saleorder_document_hhs', [self.id]
#                     )
#                 _logger.info("📄 PDF generated successfully for job card %s", self.name)
#             except Exception as e:
#                 _logger.error("❌ Error rendering PDF for job card %s: %s", self.name, str(e))
#                 raise ValidationError(f"Failed to generate PDF: {str(e)}")
#
#             # --- Step 3: Upload and Send PDF ---
#             file_name = f"{self.name}.pdf"
#             media_id = self._upload_pdf_meta(pdf_content, file_name)
#
#             if not media_id:
#                 _logger.info("❌ Failed to upload PDF for %s", self.name)
#                 return False
#
#             try:
#                 self.send_pdf_to_whatsapp(phone_number, media_id, file_name, self.name)
#                 _logger.info("✅ PDF sent successfully to WhatsApp for %s", phone_number)
#             except Exception as e:
#                 _logger.error("❌ Failed to send PDF to WhatsApp: %s", str(e))
#                 return False
#
#             return {
#                 'effect': {
#                     'type': 'rainbow_man',
#                     'fadeout': 'slow',
#                     'message': 'Your Sale Quotation was sent successfully to the customer via WhatsApp.',
#                 }
#             }
#
#         elif self.crm_id:
#             phone_number = self.crm_id.partner_id.mobile
#             country_code = self.crm_id.partner_id.country_id.phone_code
#
#             if not phone_number:
#                 _logger.info("❌ No Phone Number is linked")
#                 return False
#
#             phone_number = phone_number.replace('+', '').replace(' ', '')
#             phone_number = f"{country_code}{phone_number}"
#
#             if not self.crm_id.partner_id.x_whatsapp_opt_in:
#                 _logger.info("❌ No WhatsApp opt-in for Customer %s", self.customer_name)
#                 return False
#
#             whatsapp_phone_number_id = self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')
#             access_token = self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')
#
#             if not access_token or not whatsapp_phone_number_id:
#                 _logger.error("❌ WhatsApp configuration missing")
#                 return False
#
#             base_url = f'https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}'
#             headers = {
#                 'Authorization': f'Bearer {access_token}',
#                 'Content-Type': 'application/json'
#             }
#
#             # --- Step 1: Send WhatsApp Text Message ---
#
#             message = (
#             f"عزيزي {self.customer_name}،\n"
#             "نرفق لكم عرض السعر الخاص بالخدمات المطلوبة كما هو موضح أدناه.\n"
#             "يرجى التفضل بمراجعة العرض، وفي حال الموافقة نرجو تأكيد ذلك ليتم اتخاذ الإجراءات اللازمة.\n"
#             "نشكر لكم ثقتكم،\n"
#             "HH-Shaker – Service Team\n"
#             "-----------------------------\n"
#             f"Dear {self.customer_name},\n"
#             "Please find attached the Quotation for the requested services as detailed below.\n"
#             "Kindly review the quotation, and if acceptable, confirm your approval so we may proceed with the necessary arrangements.\n"
#             "Thank you for your trust,\n"
#             "HH-Shaker – Service Team"
#              )
#
#             template_payload = {
#                 'messaging_product': "whatsapp",
#                 'to': phone_number,
#                 'type': "text",
#                 'text': {'body': message},
#             }
#
#             try:
#                 response = requests.post(f"{base_url}/messages", headers=headers, json=template_payload)
#                 response.raise_for_status()
#                 _logger.info("✅ WhatsApp text message sent successfully to %s", phone_number)
#             except requests.exceptions.RequestException as e:
#                 _logger.error("❌ Failed to send WhatsApp message: %s", str(e))
#                 return False
#
#             # --- Step 2: Generate PDF ---
#             try:
#
#                 pdf_content, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
#                         'machine_repair_management.report_service_saleorder_document_hhs', [self.id]
#                     )
#                 _logger.info("📄 PDF generated successfully for job card %s", self.name)
#             except Exception as e:
#                 _logger.error("❌ Error rendering PDF for job card %s: %s", self.name, str(e))
#                 raise ValidationError(f"Failed to generate PDF: {str(e)}")
#
#             # --- Step 3: Upload and Send PDF ---
#             file_name = f"{self.name}.pdf"
#             media_id = self._upload_pdf_meta(pdf_content, file_name)
#
#             if not media_id:
#                 _logger.info("❌ Failed to upload PDF for %s", self.name)
#                 return False
#
#             try:
#                 self.send_pdf_to_whatsapp(phone_number, media_id, file_name, self.name)
#                 _logger.info("✅ PDF sent successfully to WhatsApp for %s", phone_number)
#             except Exception as e:
#                 _logger.error("❌ Failed to send PDF to WhatsApp: %s", str(e))
#                 return False
#
#             return {
#                 'effect': {
#                     'type': 'rainbow_man',
#                     'fadeout': 'slow',
#                     'message': 'Your Quotation was sent successfully to the customer via WhatsApp.',
#                 }
#             }
#
#
#
#     def _upload_pdf_meta(self, pdf_content, file_name):
#         if not self.whatsapp_sale_send_bool:
#             _logger.info("❌ No WhatsApp set in res Config Settings")
#             return False
#
#         whatsapp_phone_number_id = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')}"
#         url = f'https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}/media'
#
#         access_token = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')}"
#
#         headers = {
#             'Authorization': f'Bearer {access_token}',
#         }
#
#         files = {
#             'file':(file_name, pdf_content, 'application/pdf'),
#             'type':(None, 'document'),
#             'messaging_product':(None, 'whatsapp')
#             }
#
#         try:
#             response = requests.post(url, headers=headers, files=files)
#             response.raise_for_status()
#             media_id = response.json().get('id')
#             _logger.info("✅ Uploaded PDF to WhatsApp. Media ID: %s", media_id)
#             return media_id
#
#         except requests.exceptions.RequestException as e:
#             _logger.error("❌ Media upload failed: %s", str(e))
#             return None
#
#     def send_pdf_to_whatsapp(self, phone_number, media_id, file_name, order_name):
#         # base_url = 'https://graph.facebook.com/v18.0/629139543620025'
#
#         if not self.whatsapp_sale_send_bool:
#             _logger.info("❌ No WhatsApp set in res Config Settings")
#             return False
#
#         access_token = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')}"
#
#         whatsapp_phone_number_id = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')}"
#
#         url = f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}/messages"
#
#         headers = {
#             'Authorization': f'Bearer {access_token}',
#             'Content-Type': 'application/json'
#         }
#
#
#         doc_payload = {
#             'messaging_product': 'whatsapp',
#             'recipient_type': 'individual',
#             'to': phone_number,
#             'type': 'document',
#             'document': {
#                 'id': media_id,
#                 'filename': file_name,
#                 'caption': f'Quotation {self.name}'
#             }
#         }
#
#         try:
#             response = requests.post(url, headers=headers, json=doc_payload)
#             response.raise_for_status()
#         except requests.exceptions.RequestException as e:
#             _logger.error("Document send error: %s", str(e))
#             return False
#
#         # 2. Send interactive buttons
#         button_payload = {
#             'messaging_product': 'whatsapp',
#             'recipient_type': 'individual',
#             'to': phone_number,
#             'type': 'interactive',
#             'interactive': {
#                 'type': 'button',
#                 'body': {
#                     'text': f'Please review Quotation {self.name} and choose an action below. Click Accept to approve or Reject if changes are needed'
#                 },
#                 'action': {
#                     'buttons': [
#                         {
#                             'type': 'reply',
#                             'reply': {
#                                 'id': f'accept_{self.id}',
#                                 'title': '✅ Accept'
#                             }
#                         },
#                         {
#                             'type': 'reply',
#                             'reply': {
#                                 'id': f'reject_{self.id}',
#                                 'title': '❌ Reject'
#                             }
#                         }
#                     ]
#                 }
#             }
#         }
#
#         try:
#             response = requests.post(url, headers=headers, json=button_payload)
#             response.raise_for_status()
#             self.message_post(body=_("WhatsApp message with quotation sent successfully"))
#             return True
#         except requests.exceptions.RequestException as e:
#             _logger.error("Buttons send error: %s", str(e))
#             return False
#
#
#
#     # def action_send_email(self):
#     #     self.ensure_one()
#     #     ir_model_data = self.env['ir.model.data']
#     #     try:
#     #         template_id = self.env.ref('service_sale_approval.mail_template_service_sale_order').id
#     #     except ValueError:
#     #         template_id = False
#     #     try:
#     #         compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[1]
#     #     except ValueError:
#     #         compose_form_id = False
#     #     ctx = {
#     #         'default_model': 'service.sale.order',
#     #         'default_res_ids': self.ids,
#     #         'default_use_template': bool(template_id),
#     #         'default_template_id': template_id,
#     #         'default_composition_mode': 'comment',
#     #     }
#     #     self.state = 'sent'
#     #     return {
#     #         'name': _('Compose Email'),
#     #         'type': 'ir.actions.act_window',
#     #         'view_mode': 'form',
#     #         'res_model': 'mail.compose.message',
#     #         'views': [(compose_form_id, 'form')],
#     #         'view_id': compose_form_id,
#     #         'target': 'new',
#     #         'context': ctx,
#     #     }
#
#     # def action_send_email(self):
#     #     self.ensure_one()
#     #     ir_model_data = self.env['ir.model.data']
#     #     template_id =False
#     #     compose_form_id =False
#     #     report = False
#     #     try:
#     #         template_id = self.env.ref('machine_repair_management.mail_template_service_sale_order').id
#     #     except ValueError:
#     #         template_id = False
#     #     try:
#     #         compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[1]
#     #     except ValueError:
#     #         compose_form_id = False
#     #     if self.amc_quotation == True:
#     #         report = self.env.ref('machine_repair_management.report_saleorder_amcquotation').id
#     #     else:
#     #         report = self.env.ref('machine_repair_management.custom_report_saleorder_hhs').id
#     #     ctx = {
#     #         'default_model': 'service.sale.order',
#     #         'default_res_ids': self.ids,
#     #         'default_use_template': template_id,
#     #         'default_template_id': template_id,
#     #         'default_composition_mode': 'comment',
#     #         'attachment_ids' : report,
#     #     }
#     #     self.state = 'sent'
#     #     return {
#     #         'name': _('Compose Email'),
#     #         'type': 'ir.actions.act_window',
#     #         'view_mode': 'form',
#     #         'res_model': 'mail.compose.message',
#     #         'views': [(compose_form_id, 'form')],
#     #         'view_id': compose_form_id,
#     #         'target': 'new',
#     #         'context': ctx,
#     #     }
#
#     def action_send_email(self):
#         self.ensure_one()
#
#         # 1. Load the mail template
#         template = self.env.ref('machine_repair_management.mail_template_service_sale_order', raise_if_not_found=False)
#         if not template:
#             raise UserError(_("Email template not found. Please contact your administrator."))
#
#         # 2. Choose correct report
#         if self.amc_quotation:
#             report = self.env.ref('machine_repair_management.sale_order_amc_quotation_report_details',
#                                   raise_if_not_found=False)
#         else:
#             report = self.env.ref('machine_repair_management.service_sale_order_quotation_report',
#                                   raise_if_not_found=False)
#
#         if not report:
#             raise UserError(_("Report template not found. Cannot send quotation."))
#
#         # 3. Temporarily assign the correct report to the template
#         template = template.sudo()
#         original_reports = template.report_template_ids.ids[:]
#
#         try:
#             template.write({'report_template_ids': [(6, 0, [report.id])]})
#
#             # 4. Send the email directly using the template (Odoo 17+ method)
#             template.send_mail(self.id, force_send=True)
#
#             # 5. Mark as sent
#             self.write({
#                 'state': 'sent',
#             })
#
#             # 6. Log in chatter
#             self.message_post(body=_("Quotation sent by email with attached PDF."))
#
#         finally:
#             # Always restore original report(s)
#             template.write({'report_template_ids': [(6, 0, original_reports)]})
#
#         return True
#
#     # def _send_service_whatsapp_sale(self):
#     #     if not self.whatsapp_sale_send_bool:
#     #         _logger.info("❌ No Whatsapp Settings set in the res.config_settings ")
#     #         return
#     #
#     #     if self.job_task_id:
#     #         phone_number = self.job_task_id.phone
#     #
#     #         whatsapp_opt_in = self.job_task_id.whatsapp_opt_in
#     #
#     #         if not whatsapp_opt_in:
#     #             _logger.info("❌ No Whatsapp Opt for customer %s check in", self.customer_name)
#     #             return
#     #         if not phone_number:
#     #             _logger.info("❌ No Mobile number found for customer %s",self.customer_name)
#     #             return
#     #         phone_number = phone_number.replace("+","").replace("","")
#     #
#     #         pdf_content = False
#     #         try:
#     #             pdf_content, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
#     #                 'machine_repair_management.report_service_saleorder_document_hhs',[self.id]
#     #                 )
#     #             _logger.info("✅ PDF generated for order %s",self.name)
#     #         except Exception as e:
#     #             _logger.error("❌ Error rendering PDF for order %s: %s", self.name, str(e))
#     #             return
#     #
#     #         file_name = f"{self.name}.pdf"
#     #         media_id = self._upload_pdf(pdf_content,file_name)
#     #         if not media_id:
#     #             _logger.error("❌ Error Media Id  order %s", self.name)
#     #             return
#     #         self._send_whatsapp_pdf(phone_number,media_id,file_name)
#     #
#     #     elif self.crm_id:
#     #         phone_number = False
#     #         for rec in self:
#     #             phone_number = rec.crm_id.partner_id.mobile
#     #
#     #         # whatsapp_opt_in = self.job_task_id.whatsapp_opt_in
#     #         #
#     #         # if not whatsapp_opt_in:
#     #         #     _logger.info("❌ No Whatsapp Opt for customer %s check in", self.customer_name)
#     #         #     return
#     #         if not phone_number:
#     #             _logger.info("❌ No Mobile number found for customer %s", self.customer_name)
#     #             return
#     #         phone_number = phone_number.replace("+", "").replace("", "")
#     #
#     #         pdf_content = False
#     #         try:
#     #             pdf_content, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
#     #                 'machine_repair_management.report_service_saleorder_document_hhs', [self.id]
#     #             )
#     #             _logger.info("✅ PDF generated for order %s", self.name)
#     #         except Exception as e:
#     #             _logger.error("❌ Error rendering PDF for order %s: %s", self.name, str(e))
#     #             return
#     #
#     #         file_name = f"{self.name}.pdf"
#     #         media_id = self._upload_pdf(pdf_content, file_name)
#     #         if not media_id:
#     #             _logger.error("❌ Error Media Id  order %s", self.name)
#     #             return
#     #         self._send_whatsapp_pdf(phone_number, media_id, file_name)
#
#
#
#     # def _send_service_whatsapp_sale(self):
#     #
#     #     phone_number = self.job_task_id.phone
#     #
#     #     whatsapp_opt_in = self.job_task_id.whatsapp_opt_in
#     #
#     #     if not whatsapp_opt_in:
#     #         _logger.info("❌ No Whatsapp Opt for customer %s check in", self.customer_name)
#     #         return
#     #     if not phone_number:
#     #         _logger.info("❌ No Mobile number found for customer %s",self.customer_name)
#     #         return
#     #     phone_number = phone_number.replace("+","").replace("","")
#     #
#     #     pdf_content = False
#     #     try:
#     #         pdf_content, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
#     #             'machine_repair_management.report_service_saleorder_document_hhs',[self.id]
#     #             )
#     #         _logger.info("✅ PDF generated for order %s",self.name)
#     #     except Exception as e:
#     #         _logger.error("❌ Error rendering PDF for order %s: %s", self.name, str(e))
#     #         return
#     #
#     #     file_name = f"{self.name}.pdf"
#     #     media_id = self._upload_pdf(pdf_content,file_name)
#     #     if not media_id:
#     #         _logger.error("❌ Error Media Id  order %s", self.name)
#     #         return
#     #     self._send_whatsapp_pdf(phone_number,media_id,file_name)
#     #
#     # def _upload_pdf(self,pdf_content, file_name):
#     #
#     #     access_token = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')}"
#     #
#     #     whatsapp_phone_number_id = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')}"
#     #
#     #     url = f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}/media"
#     #
#     #
#     #     headers = {
#     #         'Authorization': f'Bearer {access_token}',
#     #     }
#     #
#     #     files = {
#     #         'file': (file_name, pdf_content, 'application/pdf'),
#     #         'type': (None, 'document'),
#     #         'messaging_product': (None, 'whatsapp'),
#     #     }
#     #
#     #     try:
#     #         response = requests.post(url, headers=headers, files=files)
#     #         response.raise_for_status()
#     #         media_id = response.json().get('id')
#     #         _logger.info("✅ Uploaded PDF to WhatsApp. Media ID: %s", media_id)
#     #         return media_id
#     #     except requests.exceptions.RequestException as e:
#     #         _logger.error("❌ Media upload failed: %s", str(e))
#     #         return None
#     #
#     #
#     #
#     # def _send_whatsapp_pdf(self, phone_number, media_id, file_name):
#     #     """Send PDF document via WhatsApp with response buttons"""
#     #     # url = 'https://graph.facebook.com/v18.0/629139543620025/messages'
#     #
#     #     access_token = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')}"
#     #
#     #     whatsapp_phone_number_id = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')}"
#     #
#     #     url = f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}/messages"
#     #
#     #     headers = {
#     #         'Authorization': f'Bearer {access_token}',
#     #         'Content-Type': 'application/json'
#     #     }
#     #
#     #
#     #     doc_payload = {
#     #         'messaging_product': 'whatsapp',
#     #         'recipient_type': 'individual',
#     #         'to': phone_number,
#     #         'type': 'document',
#     #         'document': {
#     #             'id': media_id,
#     #             'filename': file_name,
#     #             'caption': f'Quotation {self.name}'
#     #         }
#     #     }
#     #
#     #     try:
#     #         response = requests.post(url, headers=headers, json=doc_payload)
#     #         response.raise_for_status()
#     #     except requests.exceptions.RequestException as e:
#     #         _logger.error("Document send error: %s", str(e))
#     #         return False
#     #
#     #     # 2. Send interactive buttons
#     #     button_payload = {
#     #         'messaging_product': 'whatsapp',
#     #         'recipient_type': 'individual',
#     #         'to': phone_number,
#     #         'type': 'interactive',
#     #         'interactive': {
#     #             'type': 'button',
#     #             'body': {
#     #                 'text': f'Please review Quotation {self.name} and choose an action below. Click Accept to approve or Reject if changes are needed'
#     #             },
#     #             'action': {
#     #                 'buttons': [
#     #                     {
#     #                         'type': 'reply',
#     #                         'reply': {
#     #                             'id': f'accept_{self.id}',
#     #                             'title': '✅ Accept'
#     #                         }
#     #                     },
#     #                     {
#     #                         'type': 'reply',
#     #                         'reply': {
#     #                             'id': f'reject_{self.id}',
#     #                             'title': '❌ Reject'
#     #                         }
#     #                     }
#     #                 ]
#     #             }
#     #         }
#     #     }
#     #
#     #     try:
#     #         response = requests.post(url, headers=headers, json=button_payload)
#     #         response.raise_for_status()
#     #         self.message_post(body=_("WhatsApp message with quotation sent successfully"))
#     #         return True
#     #     except requests.exceptions.RequestException as e:
#     #         _logger.error("Buttons send error: %s", str(e))
#     #         return False
#
#     contract_id = fields.Many2one(
#         'subscription.contracts',
#         string="Contract")
#     show_standard_hours = fields.Boolean(string="Show Standard Hours", compute="_compute_show_standrd_hr")
#
#     def _compute_show_standrd_hr(self):
#         if self.env.user.has_group('selling_cost_price_restrict.group_product_price_user'):
#             self.show_standard_hours = True
#         else:
#             self.show_standard_hours = False
#
#     # def action_contract_creation(self):
#     #     """Button: Create subscription contract linked to this service sale order."""
#     #     for order in self:
#     #         if order.contract_id:
#     #             raise ValidationError(_("A contract already exists for this order."))
#     #
#     #         contract = self.env['subscription.contracts'].create({
#     #             # 'name': order.name or _("Contract for %s") % order.partner_id.name,
#     #             'amc_quotation_id': order.id,
#     #         })
#     #
#     #         order.contract_id = contract
#     #         order.state = 'sale'
#     #         # Optional: auto-open the created contract
#     #         return {
#     #             'type': 'ir.actions.act_window',
#     #             'name': _('Subscription Contract'),
#     #             'res_model': 'subscription.contracts',
#     #             'view_mode': 'form',
#     #             'res_id': contract.id,
#     #             'target': 'current',
#     #         }
#     #
#     #     return True
#
#     ## Added on - 17-11-2025
#     def action_contract_creation(self):
#         """
#         Override: cancel revised orders automatically and then create contract.
#         Wizard is completely skipped.
#         """
#         for order in self:
#             # Step 1 — If revision confirmation not done, cancel all related orders
#             if not order.rev_confirm:
#                 related_orders = order.get_related_orders()
#                 # Remove the current order from the set
#                 related_orders = related_orders - order
#                 # Cancel revised orders if any
#                 if related_orders:
#                     for rec in related_orders:
#                         rec.action_cancel()  # or your custom cancel method
#                     # Mark revision as confirmed so it doesn't repeat
#                     order.rev_confirm = True
#             # Step 2 — Now call the original contract creation logic
#             if order.contract_id:
#                 raise ValidationError(_("A contract already exists for this order."))
#             contract = self.env['subscription.contracts'].create({
#                 'amc_quotation_id': order.id,
#             })
#             order.contract_id = contract
#             order.state = 'sale'
#             return {
#                 'type': 'ir.actions.act_window',
#                 'name': _('Subscription Contract'),
#                 'res_model': 'subscription.contracts',
#                 'view_mode': 'form',
#                 'res_id': contract.id,
#                 'target': 'current',
#             }
#         return True
#
#     def show_contract(self):
#         """Button: Open the related contract form view."""
#         self.ensure_one()
#         if not self.contract_id:
#             raise ValidationError(_("No contract is linked to this order."))
#
#         return {
#             'name': _('Contract'),
#             'type': 'ir.actions.act_window',
#             'res_model': 'subscription.contracts',
#             'view_mode': 'form',
#             'res_id': self.contract_id.id,
#             'target': 'current',
#         }
#
#     # '''AMC QUOTATION BY GOKUL'''
#
#     # def amc_quotation_report(self):
#     #     amc_qoutation_lst = []
#     #     total_qty = 0.00
#     #     total_vat_amt = 0.00
#     #     total_price = 0.00
#     #     vat_percent = 0.00
#     #     emergency_visit = 0.00
#     #     for amc in self.service_sale_order_line_ids:
#     #         vals = {
#     #             # 'quotation_no':amc.
#     #             # 'quotation_date': self.service_sale_quotation_date.strftime(
#     #             #     "%d-%m-%Y") if self.service_sale_quotation_date else None,
#     #             # 'quotation_expiry_date': self.date_expiry.strftime("%d-%m-%Y") if self.date_expiry else None,
#     #             # 'customer_name': self.customer_name if self.customer_name else None,
#     #             # 'address':amc.
#     #             # 'code':amc.description.code if amc.description else None,
#     #
#     #             'Qty': amc.product_qty if amc.product_qty else None,
#     #             # 'price':amc.
#     #             'total': amc.total_price if amc.total_price else 0.00,
#     #             'vat': amc.vat if amc.vat else None,
#     #             'grand_total': amc.total if amc.total else 0.00,
#     #             'no_of_emergency_visits': amc.no_of_emergency_visit if amc.no_of_emergency_visit else None,
#     #             'description': amc.product_id.name,
#     #             'code': amc.product_id.default_code,
#     #             'no_of_visits': amc.no_of_visits_per_year if amc.no_of_visits_per_year else None,
#     #         }
#     #         amc_qoutation_lst.append(vals)
#     #         total_qty += amc.product_qty
#     #         emergency_visit += amc.no_of_emergency_visit
#     #         # total_price +=amc.total
#     #         # vat_percent +=amc.vat_percent
#     #     datas = {
#     #         'quotation_no': self.name,
#     #         'quotations': amc_qoutation_lst,
#     #         'quotation_date': self.service_sale_quotation_date.strftime(
#     #             "%d-%m-%Y") if self.service_sale_quotation_date else None,
#     #         'quotation_expiry_date': self.date_expiry.strftime("%d-%m-%Y") if self.date_expiry else None,
#     #         # 'customer_name': self.customer_name if self.customer_name else None,
#     #         'customer_name': self.crm_id.name if self.crm_id.name else None,
#     #         'sub_total': self.untaxed_amount,
#     #         'total_vat': self.vat_amount,
#     #         'grand_total': self.grand_total_amount,
#     #         'vat_amt': total_vat_amt,
#     #         'total_price': total_price,
#     #         'vat_percent': vat_percent,
#     #         'total_qty': total_qty,
#     #         'company_symbol': self.company_id.currency_id.symbol,
#     #         'address': self.customer_address,
#     #         'emergency_visit': emergency_visit,
#     #         'att_to': self.crm_id.contact_name,
#     #         'contact_no': self.crm_id.mobile,
#     #     }
#     #     return self.env.ref('machine_repair_management.sale_order_amc_quotation_report_details').report_action(self,
#     #                                                                                                            data=datas)
#
#
#
#
#
# class ServiceSaleOrderLine(models.Model):
#
#     _name = "service.sale.order.line"
#
#     _description = "Service Sale Order Line"
#
#
#     service_sale_id = fields.Many2one('service.sale.order',string = "Service Sale ID")
#
#     product_id = fields.Many2one('product.product',string = "Product")
#
#     product_qty = fields.Float(string = "Quantity")
#
#     product_uom = fields.Many2one('uom.uom', string='UOM')
#
#     price_unit = fields.Float('Unit Price')
#
#     vat = fields.Float(string='VAT (%)', default=0.0)
#
#     tax_amount = fields.Float(string = "Tax Amount")
#
#     #commented on Nov 14
#     total = fields.Float(string='Total',compute='_compute_total', store=True)
#
#     total_amc = fields.Float(string='Net Price', store=True)
#
#
#     cost = fields.Float(string="Cost")
#     margin = fields.Float(string="Margin")
#     margin_percent = fields.Float(string="Margin %")
#     amc_quotation = fields.Boolean(string="Is AMC Quotation", default = False )
#     discount = fields.Float(string="Discount (%)", digits='Discount',
#                             store=True, readonly=False, help='Discount in %')
#
#
#
#     #added on Nov 14 Amc Quotation purpose
#
#     description = fields.Char(string="Description")
#
#     no_of_visits_per_year = fields.Integer(string="No.of Visits/Yr")
#
#     no_of_emergency_visit = fields.Integer(string="No.of Emergency Visits")
#
#     days_required_for_rpm = fields.Float(string="Days Required for RPM", compute="_compute_total_hour_cost")
#
#     standard_hours = fields.Float(string="Standard Hours")
#
#     total_hr = fields.Float(string="Total Hours", compute="_compute_total_hour_cost")
#
#     total_cost = fields.Float(string="Total Cost", compute="_compute_total_hour_cost")
#
#     total_price = fields.Float(string="Total Price", compute="_compute_total_hour_cost")
#
#     vat_percent = fields.Float(string="VAT", compute="_compute_total_hour_cost")
#
#     actual_prevent_count = fields.Integer(string="Actual Preventive Count")
#     actual_correct_count = fields.Integer(string="Actual Corrective Count")
#     total_correct_count = fields.Integer(string="Total Corrective Count", compute="_compute_total_hour_cost")
#     days_require_rpm_round_off = fields.Integer(string="Total Preventive Count", compute="_compute_total_hour_cost")
#     balance_prevent_count = fields.Integer(string="Balance Preventive Count", compute="_compute_total_hour_cost")
#     balance_correct_count = fields.Integer(string="Balance Corrective Count", compute="_compute_total_hour_cost")
#
#     @api.onchange('product_id')
#     def _onchange_standard_hours(self):
#         for rec in self:
#             if rec.product_id:
#                 rec.standard_hours = rec.product_id.standard_hours
#
#     @api.onchange('product_id')
#     def _onchange_description(self):
#         for rec in self:
#             if rec.product_id:
#                 rec.description = rec.product_id.name
#
#     @api.constrains('product_id')
#     def _check_duplicate_product(self):
#         for line in self:
#             if not line.service_sale_id:
#                 continue
#             # Collect all product_ids in the order lines except current one
#             products = line.service_sale_id.service_sale_order_line_ids.filtered(lambda l: l.id != line.id).mapped('product_id')
#             if line.product_id in products:
#                 raise ValidationError("This product is already added! Duplicate products are not allowed.")
#
#     """When no line items selected in service sale order"""
#     @api.constrains('service_sale_order_line_ids')
#     def _check_service_lines(self):
#         if not self.service_sale_order_line_ids:
#             raise ValidationError(_("Please give at least one Product in the product lines"))
#
#
#
#     @api.depends('product_qty', 'no_of_visits_per_year', 'no_of_emergency_visit', 'standard_hours', 'service_sale_id.travel_hours', 'service_sale_id.gross_profit', 'vat')
#     def _compute_total_hour_cost(self):
#         units_serviced_visit = float(self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.units_serviced_visit', default=0.0))
#
#         no_of_technician_each_visit = float(self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.no_of_technician_visit', default=0.0))
#
#         labor_cost_hr = float(self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.labor_cost_hr', default=0.0))
#
#         for rec in self:
#
#             product_qty = float(rec.product_qty or 0.0)
#
#             standard_hours = float(rec.standard_hours or 0.0)
#
#             no_of_visits = float(rec.no_of_visits_per_year or 0.0)
#
#             travel_hours = float(rec.service_sale_id.travel_hours or 0.0)
#
#             gross_profit = float((rec.service_sale_id and rec.service_sale_id.gross_profit) or 0.0)
#
#             vat_percent = float(rec.vat or 0.0)
#
#
#
#             # Avoid division by zero
#
#             days_required = product_qty / units_serviced_visit if units_serviced_visit else 0.0
#
#             rec.days_required_for_rpm = days_required
#
#             rec.days_require_rpm_round_off = float_round(rec.days_required_for_rpm, precision_digits=0)
#
#             rec.total_correct_count = rec.no_of_emergency_visit
#
#             rec.balance_prevent_count = rec.days_require_rpm_round_off - rec.actual_prevent_count
#
#             rec.balance_correct_count = rec.no_of_emergency_visit - rec.actual_correct_count
#
#             rec.total_hr = (
#
#                     (product_qty * no_of_technician_each_visit * standard_hours * no_of_visits) +
#
#                     (days_required * travel_hours * no_of_visits) +
#
#                     (no_of_visits * 2)
#
#             )
#
#             rec.total_cost = rec.total_hr * labor_cost_hr
#
#             rec.total_price = float_round(rec.total_cost / (1 - gross_profit / 100), precision_digits=0)
#
#             rec.vat_percent = float_round(rec.total_price * (vat_percent / 100), precision_digits=0)
#
#             if rec.service_sale_id.amc_quotation:
#                 rec.price_unit = float_round(rec.total_price / product_qty, precision_digits=0) if product_qty else 0.0
#
#             rec.total_amc = float_round(rec.total_price + rec.vat_percent, precision_digits=0)
#
#
#
#
#     # @api.depends('service_sale_id.amc_quotation')
#     # def _compute_amc_quotation(self):
#     #     for rec in self:
#     #
#     #         rec.amc_quotation = False
#     #
#     #         if rec.amc_quotation:
#     #             self.amc_quotation = True
#     #         else:
#     #             self.amc_quotation = False
#
#
#
#
#     @api.onchange('product_id')
#     def _product_line_onchange(self):
#         for rec in self:
#             if rec.product_id:
#                 rec.amc_quotation = rec.service_sale_id.amc_quotation
#                 rec.product_uom = rec.product_id.uom_id
#
#                 rec.price_unit = rec.product_id.lst_price
#
#                 if rec.product_id.taxes_id:
#                     rec.vat = rec.product_id.taxes_id[0].amount
#                 else:
#                     rec.vat = 0.0
#
#
#     # @api.depends('product_qty', 'price_unit', 'vat')
#     # def _compute_total(self):
#     #     for record in self:
#     #         if record.service_sale_id.job_task_id:
#     #             record.total = record.product_qty * record.price_unit * (1 + (record.vat / 100))
#     #             # record.vat = record.product_qty * record.price_unit * (record.vat / 100)
#     #             '''service amount is less than 0.01 price so this was added on July 22-2025'''
#     #
#     #             record.total = Decimal(str(record.total)).quantize(Decimal('0.01'),rounding=ROUND_UP)
#
#     @api.depends('product_qty', 'price_unit', 'vat', 'discount')
#     def _compute_total(self):
#         for record in self:
#             # if record.service_sale_id.crm_id:
#
#             total = record.product_qty * record.price_unit
#             # record.vat = record.product_qty * record.price_unit * (record.vat / 100)
#             discount = total * record.discount / 100
#             total_after_discount = total - discount
#             vat_with_total = total_after_discount * record.vat / 100
#             record.tax_amount = record.product_qty * record.price_unit * (record.vat / 100)
#
#             record.total = total_after_discount + vat_with_total
#             '''service amount is less than 0.01 price so this was added on July 22-2025'''
#             # record.total = Decimal(str(record.total)).quantize(Decimal('0.01'),rounding=ROUND_UP)
#
#
#
#
#
#     @api.constrains('service_sale_id','product_id', 'product_qty', 'price_unit')
#     def _check_task_product_match(self):
#         if self.env.context.get('from_task'):
#             return
#
#         for line in self:
#             order = line.service_sale_id
#             task = order.job_task_id
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
#             order_lines = order.service_sale_order_line_ids.filtered(lambda l: l.product_id)
#             order_product_map = {
#                 l.product_id.id: {
#                     'qty': l.product_qty,
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


from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import requests
import logging
from decimal import Decimal, ROUND_UP
from lxml import etree
import json
import base64
from odoo.tools import float_round

from datetime import date
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

# Payment label mapping (ordinal names)
_ORDINAL_LABELS = [
    "First",
    "Second",
    "Third",
    "Fourth",
    "Fifth",
    "Sixth",
    "Seventh",
    "Eighth",
    "Ninth",
    "Tenth",
    "Eleventh",
    "Twelfth",
]
_ORDINAL_LABELS_AR = [
    "الأول",
    "الثاني",
    "الثالث",
    "الرابع",
    "الخامس",
    "السادس",
    "السابع",
    "الثامن",
    "التاسع",
    "العاشر",
    "الحادي عشر",
    "الثاني عشر",
    "الثالث عشر",
    "الرابع عشر",
    "الخامس عشر",
    "السادس عشر",
    "السابع عشر",
    "الثامن عشر",
    "التاسع عشر",
    "العشرون",
]


class ServiceSaleOrder(models.Model):
    _name = "service.sale.order"
    _description = "Service Sale Order"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "format.address.mixin",
        "portal.mixin",
    ]
    _order = "name desc"

    excel_file = fields.Binary("Excel File")
    excel_filename = fields.Char("Excel Filename")

    name = fields.Char(string="Quotation No.", default="New", store=True)

    customer_name = fields.Char(string="Customer Name")

    customer_address = fields.Char("Delivery Address")

    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.user.company_id
    )

    service_sale_order_line_ids = fields.One2many(
        "service.sale.order.line", "service_sale_id", string="Service Sale Order Line"
    )

    service_order_line_duplicate = fields.One2many(
        comodel_name="service.sale.order.line",
        inverse_name="service_sale_id",
        string="Order Lines",
        copy=True,
        auto_join=True,
    )

    state = fields.Selection(
        [
            ("draft", "Quotation"),
            ("sent", "Quotation Sent"),
            ("sale", "Confirmed"),
            ("done", "Locked"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        readonly=True,
        copy=False,
        index=True,
        tracking=3,
        default="draft",
    )

    job_task_id = fields.Many2one("project.task", string="Job Task")

    whatsapp_button_click_bool = fields.Boolean(string="Whatsapp Click", default=False)

    rejection_reason = fields.Char(string="Rejection Reason", tracking=True)

    service_sale_quotation_date = fields.Datetime(string="Quotation Date")

    user_id = fields.Many2one("res.users", string="Salesperson")

    untaxed_amount = fields.Float(
        string="Sub Total", compute="_compute_total_amount", store=True
    )

    vat_amount = fields.Float(
        string="VAT Amount", compute="_compute_total_amount", store=True
    )

    grand_total_amount = fields.Float(
        string="Total", compute="_compute_total_amount", store=True
    )

    inspection_charges_amount = fields.Float(
        string="Inspection Charges amount",
        store=True,
        compute="_compute_inspection_charges_amount",
    )

    balance_paid = fields.Float(
        string="Balance to be Paid", compute="_compute_balance_paid", store=True
    )

    contract_period = fields.Integer(string="Contract Period")
    contract_interval = fields.Selection(
        [
            ("Days", "Days"),
            ("Weeks", "Weeks"),
            ("Months", "Months"),
            ("Years", "Years"),
        ],
        help="Recurring interval of subscription contract",
        string="Contract Interval",
        default="Years",
    )

    contract_duration_days = fields.Integer(
        string="Contract Duration Days",
        compute="_compute_contract_duration_days",
        inverse="_inverse_contract_duration_days",
        store=True,
        readonly=False,
        help="Number of days between Quotation Date and Expiration Date. Editing this updates contract_period/contract_interval.",
    )

    no_of_prevent_service = fields.Integer(
        string="No. of Prevent Service Per Year - XX"
    )
    add_paid_service_price = fields.Float(string="Additional Paid Service Price")

    # Existing integer field — will be computed from invoice_interval_duration and stored.
    invoice_interval = fields.Integer(
        string="Invoice Interval (Days)",
        compute="_compute_invoice_interval",
        inverse="_inverse_invoice_interval",
        store=True,
    )

    # New selection: choose duration (drives invoice_interval)
    invoice_interval_duration = fields.Selection(
        [
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
            ("semi_annual", "Semi-Annual"),
            ("annual", "Annual"),
        ],
        string="Invoice Interval Duration",
        required=True,
        default="monthly",
        help="Select the interval duration for invoicing.",
    )

    # Add this field to track number of installments
    number_of_installments = fields.Integer(
        string="Number of Installments",
        compute="_compute_number_of_installments",
        store=True,
        help="Number of invoices to be generated during the contract period",
    )

    approval_level_id = fields.Many2one("approval.approval", string="Approval Level")
    no_of_correct_service = fields.Integer(
        string="No.of Corrective Service Per Year - XX"
    )
    # payment_term_id = fields.Many2one('account.payment.term', string="Payment Terms")
    payment_term_id = fields.Many2one(
        "account.payment.term",
        string="Payment Terms",
        required=True,
        default=lambda self: self.env["account.payment.term"].search(
            [("name", "=", "Immediate Payment")], limit=1
        ),
    )
    date_expiry = fields.Datetime(string="Expiration Date")
    amc_quotation = fields.Boolean(string="Is AMC Quotation", default=False)
    crm_id = fields.Many2one("crm.lead", string="Crm Origin")
    analytic_account_id = fields.Many2one(
        "account.analytic.account", string="Analytic Account", tracking=True
    )
    total_discount = fields.Float(string="Total Discount (-)")

    whatsapp_sale_send_bool = fields.Boolean(
        string="Whatsapp Send Y/N",
        default=False,
        help="All Whatsapp Send feature Enable/Not in res.config_settings",
        compute="_compute_whatsapp_sale_send_bool",
    )

    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")

    """Added on Nov 19 2025"""
    quote_created_user_id = fields.Many2one("res.users", string="Quote Created By")

    quote_created_by = fields.Char(
        string="Quote Created By", compute="_compute_quote_created_flag", store=True
    )

    """Added on Jan 05-2026"""

    service_vat_amount = fields.Float(
        string="Service VAT Amount", compute="_compute_total_amount", store=True
    )

    parts_vat_totamount = fields.Float(
        string="Parts VAT Amount", compute="_compute_total_amount", store=True
    )

    parts_total_amount = fields.Float(
        string="Parts Amount", compute="_compute_total_amount", store=True
    )

    service_charge_amount = fields.Float(
        string="Service Charge Amount", compute="_compute_total_amount", store=True
    )

    travel_hours = fields.Float(string="Travel Hours")
    # 20260313 Gokul
    gross_profit = fields.Float(string="Service Gross Margin")
    # sp_gross_margin = fields.Float(string="Spare Parts Gross Margin",  default = lambda self:float(self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.spare_parts_gross_profit')), store= True)
    sp_gross_margin = fields.Float(
        string="Spare Parts Discount", compute="_compute_sp_gross_margin", store=False
    )
    show_approval_button = fields.Boolean(
        string="Show Approval Button", compute="compute_approval_button"
    )

    # spare_parts_amount_discount = fields.Float("Spare Parts Discount", default = lambda self:float(self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.spare_parts_amount_discount', default=0.0)))
    def _default_spare_parts_discount(self):
        return float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "machine_repair_management.spare_parts_gross_profit", default=0.0
            )
        )

    spare_parts_amount_discount = fields.Float(
        "Spare Parts Gross Margin", default=_default_spare_parts_discount
    )

    contract_id = fields.Many2one("subscription.contracts", string="Contract")
    partner_name = fields.Char(string="Company Name")
    contact_name = fields.Char(string="Contact Name")
    function = fields.Char(string=" Position")

    mobile = fields.Char(string="Contact Mobile")
    # 20260408 GOkul
    job_position = fields.Char(string="Job Position")
    email_from = fields.Char(string="Email")

    show_standard_hours = fields.Boolean(
        string="Show Standard Hours", compute="_compute_show_standrd_hr"
    )

    # Internal mapping used for conversion between duration label and months to add
    _DURATION_TO_MONTHS = {
        "monthly": 1,
        "quarterly": 3,
        "semi_annual": 6,
        "annual": 12,
    }

    '''Code Added on May 22 2026 by Vijaya Bhaskar'''
    
    customer_code = fields.Char(string = "Customer Code")
    
    work_center_id = fields.Many2one('work.center.location', string = "Work center")
    
    work_center_group_id = fields.Many2one('work.center.group', string = "Work Center  Group")
    
    district = fields.Many2one('res.state.district',string = "District")
    
     
    '''Code Added on May 26 2026 by Vijaya Bhaskar '''
    
    sales_person_user_id = fields.Many2one('res.users', string  = "SalesPerson")
    
    
    '''Code Added on June 12 2026 by Vijaya Bhaskar client asked site address similar to address'''
    street = fields.Char(string = "Street")
    
    street2 = fields.Char(string = "Street2")
    
    customer_city_id = fields.Many2one('res.city', string = "Customer City")
    
    district_id  = fields.Many2one('res.state.district',string = "District")
    
    state_id = fields.Many2one('res.country.state', string = "State")
    
    country_id = fields.Many2one('res.country', string = "Country")
    
    zip = fields.Char(string = "Zip")
    
    
    '''Code Added on June 16 2026 by Vijaya Bhaskar client asked site address similar to address'''

    def write(self, vals):
        res = super(ServiceSaleOrder, self).write(vals)

        if 'street' in vals:
            self.crm_id.partner_id.street = vals.get('street')
        if 'street2' in vals:
            self.crm_id.partner_id.street2 = vals.get('street2')

        if 'customer_city_id' in vals:
            city_search = self.env['res.city'].search([('id', '=', vals.get('customer_city_id'))], limit=1)
            self.crm_id.partner_id.customer_city_id = city_search.id

        if 'state_id' in vals:
            state_search = self.env['res.country.state'].search([('id', '=', vals.get('state_id'))], limit=1)

            self.crm_id.partner_id.state_id = state_search.id

        if 'country_id' in vals:
            country_search = self.env['res.country'].search([('id', '=', vals.get('country_id'))], limit=1)

            self.crm_id.partner_id.country_id = country_search.id

        if 'zip' in vals:
            self.crm_id.partner_id.zip = vals.get('zip')

        if 'email_from' in vals:
            self.crm_id.partner_id.email = vals.get('email_from')

        if 'phone' in vals:
            self.crm_id.partner_id.mobile = vals.get('phone')
        return res
    
    
    # @api.depends('customer_name')
    def _compute_sp_gross_margin(self):
        for rec in self:
            rec.sp_gross_margin = float(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param(
                    "machine_repair_management.spare_parts_gross_profit", default=0.0
                )
            )
            # rec.spare_parts_amount_discount=float(self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.spare_parts_gross_profit', default=0.0))

    @api.constrains("contract_period", "invoice_interval")
    def _check_contract_period(self):
        for rec in self:
            if rec.amc_quotation:
                if rec.contract_period is not None and rec.contract_period <= 0:
                    raise ValidationError(_("Contract period must be greater than 0."))
                if rec.invoice_interval is not None and rec.invoice_interval <= 0:
                    raise ValidationError(_("Invoice Interval must be greater than 0."))

    # @api.constrains('sp_gross_margin')
    # def check_discount_limit_constrains_sp_gross_margin(self):
    #     conf_sp_gross_profit = float(
    #         self.env['ir.config_parameter'].sudo().get_param('machine_repair_management.gross_profit', default=0.0))
    #     total_gross_profit = conf_sp_gross_profit - self.env.user.discount_limit
    #     for record in self:
    #         if self.env.user.discount_limit != 0.00 and record.sp_gross_margin < total_gross_profit:
    #             message = "You can only assign maximum " + str(
    #                 self.env.user.discount_limit) + "% Discount \nContact your administrator for more details"
    #             raise ValidationError(_(message))

    @api.constrains("gross_profit")
    def check_discount_limit_constrains(self):
        conf_gross_profit = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("machine_repair_management.gross_profit", default=0.0)
        )
        total_gross_profit = conf_gross_profit - self.env.user.discount_limit
        for record in self:
            if (
                self.env.user.discount_limit != 0.00
                and record.gross_profit < total_gross_profit
            ):
                message = (
                    "You can only assign maximum "
                    + str(self.env.user.discount_limit)
                    + "% Discount \nContact your administrator for more details"
                )
                raise ValidationError(_(message))

    ## End##
    @api.constrains("spare_parts_amount_discount")
    def check_discount_limit_sp_constrains(self):
        conf_sp_gross_profit = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "machine_repair_management.spare_parts_gross_profit", default=0.0
            )
        )
        total_sp_gross_profit = (
            conf_sp_gross_profit - self.env.user.spare_parts_discount_limit
        )
        print(
            "___________________________",
            conf_sp_gross_profit,
            self.env.user.spare_parts_discount_limit,
        )
        # for record in self:
        if self.spare_parts_amount_discount < total_sp_gross_profit:
            message = (
                "You can only assign Spare Parts Maximum Discount "
                + str(self.env.user.spare_parts_discount_limit)
                + "% Discount. \nContact your administrator for more details"
            )
            raise ValidationError(_(message))

    def _compute_whatsapp_sale_send_bool(self):
        for rec in self:
            rec.whatsapp_sale_send_bool = False
            whatsapp_search = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("machine_repair_management.whatsapp_send_bool")
            )
            if whatsapp_search == "True":
                rec.whatsapp_sale_send_bool = True

    @api.onchange("job_task_id", "crm_id")
    def _onchange_amc_quotation(self):
        for rec in self:
            if rec.job_task_id:
                rec.amc_quotation = False
            if rec.crm_id:
                rec.amc_quotation = True

    @api.depends(
        "job_task_id",
        "job_task_id.inspection_charges_bool",
        "job_task_id.inspection_charges_amount",
    )
    def _compute_inspection_charges_amount(self):
        for rec in self:
            rec.inspection_charges_amount = False
            if rec.job_task_id:
                if rec.job_task_id.inspection_charges_bool and (
                    rec.job_task_id.inspection_charges_amount > 0
                ):
                    rec.inspection_charges_amount = (
                        rec.job_task_id.inspection_charges_amount
                    )

    """ This is currently working code commented on Nov 7 2025 due to only inspection charges given under warrantly they make negative in the balance paid field                
    @api.depends('grand_total_amount','inspection_charges_amount') 
    def _compute_balance_paid(self):
        for rec in self:
            rec.balance_paid = rec.grand_total_amount - rec.inspection_charges_amount
    """

    @api.depends(
        "job_task_id",
        "job_task_id.balance_paid",
        "grand_total_amount",
        "inspection_charges_amount",
        "job_task_id.inspection_charges_bool",
        "job_task_id.balance_amount_received_bool",
        "job_task_id.final_inspection_charges_amount",
        "job_task_id.balance_amount_received_bool",
    )
    def _compute_balance_paid(self):
        for rec in self:
            rec.balance_paid = abs(
                rec.grand_total_amount - rec.inspection_charges_amount
            )
            if (
                rec.job_task_id.inspection_charges_bool
                and not rec.job_task_id.balance_amount_received_bool
            ):
                if rec.job_task_id.final_inspection_charges_amount > 0 and (
                    rec.job_task_id.grand_total == 0
                    or rec.job_task_id.grand_total
                    < rec.job_task_id.final_inspection_charges_amount
                ):
                    rec.balance_paid = 0.0

            if (
                rec.job_task_id.balance_amount_received_bool
                and rec.job_task_id.inspection_charges_bool
            ):
                if rec.job_task_id.final_inspection_charges_amount > 0:
                    rec.balance_paid = abs(
                        rec.grand_total_amount
                        - (
                            rec.balance_paid
                            + rec.job_task_id.final_inspection_charges_amount
                        )
                    )
                else:
                    rec.balance_paid = abs(rec.grand_total_amount - rec.balance_paid)

    # @api.depends('service_sale_order_line_ids.product_qty', 'service_sale_order_line_ids.price_unit',
    #              'service_sale_order_line_ids.vat')
    '''Working Code Commented on May 21 2026 by Vijaya Bhaskar Because when we change the payment term ids it will calculate correctly so it was commented
    @api.depends(
        "service_sale_order_line_ids.product_qty",
        "service_sale_order_line_ids.price_unit",
        # "service_sale_order_line_ids.vat",
        "service_sale_order_line_ids.vat",
        "spare_parts_amount_discount",
        "inspection_charges_amount",
        'invoice_interval_duration'
       
    )
    def _compute_total_amount(self):
        for rec in self:
            if rec.amc_quotation:
                rec.untaxed_amount = sum(
                    line.total_selling_price for line in rec.service_sale_order_line_ids
                )
                rec.untaxed_amount = float_round(rec.untaxed_amount, precision_digits=2)
                rec.total_discount = sum(
                    (line.price_unit * line.product_qty * line.discount / 100)
                    for line in rec.service_sale_order_line_ids
                )
                rec.vat_amount = sum(
                    line.vat_percent for line in rec.service_sale_order_line_ids
                )
                rec.vat_amount = float_round(rec.vat_amount, precision_digits=2)
                rec.grand_total_amount = (
                    rec.untaxed_amount - rec.total_discount + rec.vat_amount
                )
                rec.grand_total_amount = float_round(
                    rec.grand_total_amount, precision_digits=2
                )
                """validation for gross profit by Maxwell on 18-11-2025"""
                conf_gross_profit = float(
                    self.env["ir.config_parameter"]
                    .sudo()
                    .get_param("machine_repair_management.gross_profit", default=0.0)
                )
                total_gross_profit = conf_gross_profit - self.env.user.discount_limit
                for record in self:
                    if (
                        self.env.user.discount_limit != 0.00
                        and record.gross_profit < total_gross_profit
                    ):
                        message = (
                            "You can only assign maximum "
                            + str(self.env.user.discount_limit)
                            + "% Discount \nContact your administrator for more details"
                        )
                        raise ValidationError(_(message))

            else:
                ## Added by Raj - 21-03-2026 - HHS live
                rec.parts_total_amount = sum(
                    line.price_unit * line.product_qty
                    for line in rec.service_sale_order_line_ids
                    if not line.under_warranty_bool
                    if not line.product_id.service_type_bool
                )
                rec.parts_vat_totamount = sum(
                    line.tax_amount
                    for line in rec.service_sale_order_line_ids
                    if not line.under_warranty_bool
                    if not line.product_id.service_type_bool
                )
                # rec.parts_total_amount = sum(line.price_unit for line in rec.product_line_ids if not line.under_warranty_bool if line.product_id.type != 'service' )
                # rec.parts_vat_totamount = sum(line.tax_amount for line in rec.product_line_ids if not line.under_warranty_bool if line.product_id.type != 'service' )
                rec.total_discount = sum(
                    (line.price_unit * line.product_qty * line.discount / 100)
                    for line in rec.service_sale_order_line_ids
                )

                # rec.parts_grand_total_amount = rec.parts_total_amount + rec.parts_vat_totamount

                rec.service_charge_amount = sum(
                    line.price_unit * line.product_qty
                    for line in rec.service_sale_order_line_ids
                    if not line.under_warranty_bool
                    if line.product_id.service_type_bool
                )
                rec.service_vat_amount = sum(
                    line.tax_amount
                    for line in rec.service_sale_order_line_ids
                    if not line.under_warranty_bool
                    if line.product_id.service_type_bool
                )
                # rec.service_grand_total_amount = sum([rec.service_charge_amount, rec.service_vat_amount])

                rec.untaxed_amount = rec.parts_total_amount + rec.service_charge_amount

                rec.vat_amount = round(rec.parts_vat_totamount, 2) + round(
                    rec.service_vat_amount, 2
                )

                rec.grand_total_amount = (
                    rec.untaxed_amount - rec.total_discount + rec.vat_amount
                )
                ## commented by Raj - 21-03-2026
                # rec.untaxed_amount = sum(
                #     (line.price_unit * line.product_qty) for line in rec.service_sale_order_line_ids)
                # rec.total_discount = sum((line.price_unit * line.product_qty * line.discount / 100) for line in
                #                          rec.service_sale_order_line_ids)
                # rec.vat_amount = sum((line.tax_amount) for line in rec.service_sale_order_line_ids)
                # rec.grand_total_amount = rec.untaxed_amount - rec.total_discount + rec.vat_amount
    
    '''
    
    '''Code Added on May 21 2026 By Vijaya Bhaskar'''
    @api.depends(
    "service_sale_order_line_ids.product_qty",
    "service_sale_order_line_ids.price_unit",
    "service_sale_order_line_ids.discount",
    "service_sale_order_line_ids.tax_amount",
    "service_sale_order_line_ids.total_selling_price",
    "service_sale_order_line_ids.vat_percent",
    "service_sale_order_line_ids.under_warranty_bool",
    "service_sale_order_line_ids.product_id",
    "service_sale_order_line_ids.product_id.service_type_bool",
    "spare_parts_amount_discount",
    "inspection_charges_amount",
    "invoice_interval_duration",
    "amc_quotation",
    )
    def _compute_total_amount(self):
        for rec in self:
    
            rec.parts_total_amount = 0.0
            rec.parts_vat_totamount = 0.0
            rec.service_charge_amount = 0.0
            rec.service_vat_amount = 0.0
            rec.total_discount = 0.0
            rec.untaxed_amount = 0.0
            rec.vat_amount = 0.0
            rec.grand_total_amount = 0.0
    
            if rec.amc_quotation:
    
                rec.untaxed_amount = sum(
                    line.total_selling_price
                    for line in rec.service_sale_order_line_ids
                )
    
                rec.total_discount = sum(
                    (line.price_unit * line.product_qty * line.discount / 100)
                    for line in rec.service_sale_order_line_ids
                )
    
                rec.vat_amount = sum(
                    line.vat_percent
                    for line in rec.service_sale_order_line_ids
                )
    
                rec.untaxed_amount = float_round(
                    rec.untaxed_amount, precision_digits=2
                )
    
                rec.vat_amount = float_round(
                    rec.vat_amount, precision_digits=2
                )
    
                rec.grand_total_amount = float_round(
                    rec.untaxed_amount
                    - rec.total_discount
                    + rec.vat_amount,
                    precision_digits=2
                )
    
                print("AMC UNTAXED :", rec.untaxed_amount)
                print("AMC VAT :", rec.vat_amount)
                print("AMC GRAND :", rec.grand_total_amount)
    
            else:
    
                rec.parts_total_amount = sum(
                    line.price_unit * line.product_qty
                    for line in rec.service_sale_order_line_ids
                    if not line.under_warranty_bool
                    and not line.product_id.service_type_bool
                )
    
                rec.parts_vat_totamount = sum(
                    line.tax_amount
                    for line in rec.service_sale_order_line_ids
                    if not line.under_warranty_bool
                    and not line.product_id.service_type_bool
                )
    
                rec.service_charge_amount = sum(
                    line.price_unit * line.product_qty
                    for line in rec.service_sale_order_line_ids
                    if not line.under_warranty_bool
                    and line.product_id.service_type_bool
                )
    
                rec.service_vat_amount = sum(
                    line.tax_amount
                    for line in rec.service_sale_order_line_ids
                    if not line.under_warranty_bool
                    and line.product_id.service_type_bool
                )
    
                rec.total_discount = sum(
                    (line.price_unit * line.product_qty * line.discount / 100)
                    for line in rec.service_sale_order_line_ids
                )
    
                rec.untaxed_amount = (
                    rec.parts_total_amount
                    + rec.service_charge_amount
                )
    
                rec.vat_amount = (
                    round(rec.parts_vat_totamount, 2)
                    + round(rec.service_vat_amount, 2)
                )
    
                rec.grand_total_amount = float_round(
                    rec.untaxed_amount
                    - rec.total_discount
                    + rec.vat_amount,
                    precision_digits=2
                )
    
                print("NORMAL UNTAXED :", rec.untaxed_amount)
                print("NORMAL VAT :", rec.vat_amount)
                print("NORMAL GRAND :", rec.grand_total_amount)
        # INVOICE CALCULATION METHODS - REPLACE THE EXISTING ONES

    @api.depends("quote_created_user_id")
    def _compute_quote_created_flag(self):
        for rec in self:
            rec.quote_created_by = False
            if rec.quote_created_user_id:
                if rec.quote_created_user_id.has_group(
                    "machine_repair_management.group_job_card_mobile_user"
                ):
                    rec.quote_created_by = "T"
                elif rec.quote_created_user_id.has_group(
                    "machine_repair_management.group_technical_allocation_user"
                ):
                    """For third case of unit pull out workflow"""
                    if (
                        rec.job_task_id.customer_need_quote_status_check
                        and rec.job_task_id.unit_pull_out_status_check
                    ):
                        rec.quote_created_by = "T"
                    else:
                        rec.quote_created_by = "S"

    @api.depends("invoice_interval_duration", "contract_duration_days")
    def _compute_invoice_interval(self):
        """
        Compute invoice_interval based on selected frequency within contract duration.
        This represents the days between each invoice installment.
        """
        for rec in self:
            if not rec.invoice_interval_duration or not rec.contract_duration_days:
                rec.invoice_interval = 30  # default monthly
            else:
                # Calculate invoice interval based on frequency
                if rec.invoice_interval_duration == "monthly":
                    rec.invoice_interval = 30  # approx 1 month
                elif rec.invoice_interval_duration == "quarterly":
                    rec.invoice_interval = 90  # approx 3 months
                elif rec.invoice_interval_duration == "semi_annual":
                    rec.invoice_interval = 180  # approx 6 months
                elif rec.invoice_interval_duration == "annual":
                    rec.invoice_interval = 365  # approx 1 year
                else:
                    rec.invoice_interval = 30  # fallback

    @api.depends("invoice_interval_duration", "contract_duration_days")
    def _compute_number_of_installments(self):
        """
        Compute number of installments based on contract duration and invoice frequency.
        Examples:
        - 1 Year + Monthly = 12 installments
        - 1 Year + Quarterly = 4 installments
        - 1 Year + Semi-Annual = 2 installments
        - 1 Year + Annual = 1 installment
        - 2 Years + Monthly = 24 installments
        - 6 Months + Monthly = 6 installments
        """
        for rec in self:
            if not rec.invoice_interval_duration or not rec.contract_duration_days:
                rec.number_of_installments = 1
                continue

            # Calculate based on contract duration in years (approximate)
            contract_years = rec.contract_duration_days / 365.0

            if rec.invoice_interval_duration == "monthly":
                rec.number_of_installments = max(1, int(contract_years * 12))
            elif rec.invoice_interval_duration == "quarterly":
                rec.number_of_installments = max(1, int(contract_years * 4))
            elif rec.invoice_interval_duration == "semi_annual":
                rec.number_of_installments = max(1, int(contract_years * 2))
            elif rec.invoice_interval_duration == "annual":
                rec.number_of_installments = max(1, int(contract_years))
            else:
                rec.number_of_installments = 1

    def _inverse_invoice_interval(self):
        """
        When invoice_interval is manually changed, compute the closest invoice_interval_duration.
        """
        for rec in self:
            if rec.invoice_interval is None:
                continue

            days = rec.invoice_interval

            # Map days to closest frequency
            if days <= 45:  # ~1.5 months
                closest_duration = "monthly"
            elif days <= 105:  # ~3.5 months
                closest_duration = "quarterly"
            elif days <= 210:  # ~7 months
                closest_duration = "semi_annual"
            else:
                closest_duration = "annual"

            rec.invoice_interval_duration = closest_duration

    @api.onchange("invoice_interval_duration")
    def _onchange_invoice_interval_duration(self):
        """When user selects invoice frequency, update invoice_interval and recalculate installments."""
        for rec in self:
            if not rec.invoice_interval_duration:
                rec.invoice_interval = 30  # default monthly
            else:
                # Set fixed intervals based on frequency
                if rec.invoice_interval_duration == "monthly":
                    rec.invoice_interval = 30
                elif rec.invoice_interval_duration == "quarterly":
                    rec.invoice_interval = 90
                elif rec.invoice_interval_duration == "semi_annual":
                    rec.invoice_interval = 180
                elif rec.invoice_interval_duration == "annual":
                    rec.invoice_interval = 365

            # Trigger computation of number of installments
            rec._compute_number_of_installments()

    # add compute method (place somewhere in the class methods)
    # Replace the existing _compute_contract_duration_days method with:
    @api.depends("contract_period", "contract_interval")
    def _compute_contract_duration_days(self):
        for rec in self:
            if rec.contract_period:
                if rec.contract_interval == "Weeks":
                    rec.contract_duration_days = rec.contract_period * 7
                elif rec.contract_interval == "Months":
                    rec.contract_duration_days = rec.contract_period * 30
                elif rec.contract_interval == "Years":
                    rec.contract_duration_days = rec.contract_period * 365
                else:
                    rec.contract_duration_days = 0
            else:
                rec.contract_duration_days = 0

    def _inverse_contract_duration_days(self):
        """
        When user edits contract_duration_days manually, convert it to contract_period + contract_interval.
        Uses same approximations as compute.
        """
        for rec in self:
            if rec.contract_duration_days is None:
                continue

            days = int(rec.contract_duration_days or 0)

            if days < 7:
                rec.contract_interval = "Days"
                rec.contract_period = days or 1
            elif 7 <= days < 30:
                rec.contract_interval = "Weeks"
                rec.contract_period = max(days // 7, 1)
            elif 30 <= days < 365:
                rec.contract_interval = "Months"
                rec.contract_period = max(days // 30, 1)
            else:
                rec.contract_interval = "Years"
                rec.contract_period = max(days // 365, 1)

    # ADD THIS NEW METHOD (it's not present in your original code):
    @api.onchange("contract_period", "contract_interval")
    def _onchange_contract_period_interval(self):
        """
        When contract_period or contract_interval are modified, update contract_duration_days.
        This ensures the days field updates immediately in the UI when period/interval change.
        """
        for rec in self:
            # Recompute the duration days based on the new period/interval
            if rec.contract_period:
                mul = 1
                if rec.contract_interval == "Weeks":
                    mul = 7
                elif rec.contract_interval == "Months":
                    mul = 30
                elif rec.contract_interval == "Years":
                    mul = 365
                rec.contract_duration_days = int(rec.contract_period or 0) * mul
            else:
                rec.contract_duration_days = 0

    def action_view_project_task(self):
        return {
            "name": "Job Card",
            "res_model": "project.task",
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_id": self.job_task_id.id,
            "domain": [("service_sale_id", "=", self.id)],
            "target": "current",
            "views": [(False, "form")],
        }

    def whatsapp_service_sale_sent(self):
        for rec in self:
            if rec.job_task_id:
                if rec.state in ("draft", "sent"):
                    # sale_total = rec.grand_total_amount
                    sale_total = round(rec.grand_total_amount, 2)
                    task_total = round(rec.job_task_id.grand_total, 2)
                    if sale_total != task_total:
                        raise ValidationError(
                            "Sale Total is different from Consume Parts service total "
                        )
            elif rec.crm_id:
                if rec.state in ("draft", "sent"):
                    crm_product = rec.service_sale_order_line_ids.mapped("product_id")
        self._send_service_whatsapp_sale()
        self.write({"state": "sent"})
        self.whatsapp_button_click_bool = True
        if self.job_task_id and self.whatsapp_button_click_bool:
            if self.state == "sent":
                stage = self.env["project.task.type"].search(
                    [("code", "=", "114")], limit=1
                )
                if stage:
                    self.job_task_id.write(
                        {
                            "job_state": stage.id,
                            "job_card_state_code": stage.code,
                            "job_card_state": stage.name,
                        }
                    )
                    self.job_task_id.service_request_id.service_request_state = (
                        stage.name
                    )
                    self.job_task_id.service_request_id.service_request_state_code = (
                        stage.code
                    )
                    self.job_task_id.service_request_id.state = stage.id

    def whatsapp_amc_service_sale_sent(self):
        self._send_service_whatsapp_sale()
        self.write({"state": "sent"})
        self.whatsapp_button_click_bool = True

    def action_confirm(self):
        for rec in self:
            if rec.job_task_id:
                if rec.state in ("draft", "sent"):
                    # sale_total = rec.grand_total_amount
                    sale_total = round(rec.grand_total_amount, 2)
                    task_total = round(rec.job_task_id.grand_total, 2)
                    if sale_total != task_total:
                        raise ValidationError(
                            "Sale Total is different from Consume Parts service total "
                        )

                    stage_model = self.env["project.task.type"]
                    stage_search = stage_model.search([("code", "=", "127")], limit=1)

                    rec.job_task_id.job_card_state_code = stage_search.code
                    rec.job_task_id.job_card_state = stage_search.name
                    rec.job_task_id.job_state = stage_search
                    rec.job_task_id.service_request_id.service_request_state = (
                        stage_search.name
                    )
                    rec.job_task_id.service_request_id.service_request_state_code = (
                        stage_search.code
                    )
                    rec.job_task_id.service_request_id.state = stage_search

                self.write({"state": "sale"})
                self.write({"state": "done"})

    def action_cancel(self):
        for rec in self:
            if rec.job_task_id:
                stage_model = self.env["project.task.type"]
                stage_search = stage_model.search([("code", "=", "128")], limit=1)
                rec.job_task_id.job_card_state_code = stage_search.code
                rec.job_task_id.job_card_state_code = stage_search.code
                rec.job_task_id.job_card_state = stage_search.name
                rec.job_task_id.job_state = stage_search
                rec.job_task_id.service_request_id.service_request_state = (
                    stage_search.name
                )
                rec.job_task_id.service_request_id.service_request_state_code = (
                    stage_search.code
                )
                rec.job_task_id.service_request_id.state = stage_search

                if rec.rejection_reason:
                    rec.job_task_id.client_remarks = (
                        f"Rejected by customer:{rec.rejection_reason}"
                    )
                else:
                    rec.job_task_id.client_remarks = f"Rejected by customer"
        return self.write({"state": "cancel"})

    def _send_service_whatsapp_sale(self):

        if (
            not self.env["ir.config_parameter"]
            .sudo()
            .get_param("machine_repair_management.whatsapp_send_bool")
            == "True"
        ):
            _logger.info("❌ No WhatsApp set in res Config Settings")
            return False

        if self.job_task_id:

            phone_number = self.job_task_id.phone
            country_code = self.job_task_id.country_id.phone_code

            if not phone_number:
                _logger.info("❌ No Phone Number is linked")
                return False

            phone_number = phone_number.replace("+", "").replace(" ", "")
            phone_number = f"{country_code}{phone_number}"

            if not self.job_task_id.whatsapp_opt_in:
                _logger.info(
                    "❌ No WhatsApp opt-in for Customer %s", self.customer_name
                )
                return False

            whatsapp_phone_number_id = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("whatsapp_sale_order_notify.whatsapp_phone_number_id")
            )
            access_token = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("whatsapp_sale_order_notify.whatsapp_access_token")
            )

            if not access_token or not whatsapp_phone_number_id:
                _logger.error("❌ WhatsApp configuration missing")
                return False

            base_url = f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            # --- Step 1: Send WhatsApp Text Message ---
            message = (
                f"عزيزي {self.customer_name}،\n"
                "نرفق لكم عرض السعر الخاص بالخدمات المطلوبة كما هو موضح أدناه.\n"
                "يرجى التفضل بمراجعة العرض، وفي حال الموافقة نرجو تأكيد ذلك ليتم اتخاذ الإجراءات اللازمة.\n"
                "نشكر لكم ثقتكم،\n"
                "HH-Shaker – Service Team\n"
                "-----------------------------\n"
                f"Dear {self.customer_name},\n"
                "Please find attached the Quotation for the requested services as detailed below.\n"
                "Kindly review the quotation, and if acceptable, confirm your approval so we may proceed with the necessary arrangements.\n"
                "Thank you for your trust,\n"
                "HH-Shaker – Service Team"
            )

            template_payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": message},
            }

            try:
                response = requests.post(
                    f"{base_url}/messages", headers=headers, json=template_payload
                )
                response.raise_for_status()
                _logger.info(
                    "✅ WhatsApp text message sent successfully to %s", phone_number
                )
            except requests.exceptions.RequestException as e:
                _logger.error("❌ Failed to send WhatsApp message: %s", str(e))
                return False
            # --- Step 2: Generate PDF ---
            try:

                pdf_content, _ = (
                    self.env["ir.actions.report"]
                    .sudo()
                    ._render_qweb_pdf(
                        "machine_repair_management.report_service_saleorder_document_hhs",
                        [self.id],
                    )
                )
                _logger.info("📄 PDF generated successfully for job card %s", self.name)
            except Exception as e:
                _logger.error(
                    "❌ Error rendering PDF for job card %s: %s", self.name, str(e)
                )
                raise ValidationError(f"Failed to generate PDF: {str(e)}")

            # --- Step 3: Upload and Send PDF ---
            file_name = f"{self.name}.pdf"
            media_id = self._upload_pdf_meta(pdf_content, file_name)

            if not media_id:
                _logger.info("❌ Failed to upload PDF for %s", self.name)
                return False

            try:
                self.send_pdf_to_whatsapp(phone_number, media_id, file_name, self.name)
                _logger.info(
                    "✅ PDF sent successfully to WhatsApp for %s", phone_number
                )
            except Exception as e:
                _logger.error("❌ Failed to send PDF to WhatsApp: %s", str(e))
                return False

            return {
                "effect": {
                    "type": "rainbow_man",
                    "fadeout": "slow",
                    "message": "Your Sale Quotation was sent successfully to the customer via WhatsApp.",
                }
            }

        elif self.crm_id:
            phone_number = self.crm_id.partner_id.mobile
            country_code = self.crm_id.partner_id.country_id.phone_code

            if not phone_number:
                _logger.info("❌ No Phone Number is linked")
                return False

            phone_number = phone_number.replace("+", "").replace(" ", "")
            phone_number = f"{country_code}{phone_number}"

            if not self.crm_id.partner_id.x_whatsapp_opt_in:
                _logger.info(
                    "❌ No WhatsApp opt-in for Customer %s", self.customer_name
                )
                return False

            whatsapp_phone_number_id = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("whatsapp_sale_order_notify.whatsapp_phone_number_id")
            )
            access_token = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("whatsapp_sale_order_notify.whatsapp_access_token")
            )

            if not access_token or not whatsapp_phone_number_id:
                _logger.error("❌ WhatsApp configuration missing")
                return False

            base_url = f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # --- Step 1: Send WhatsApp Text Message ---

            message = (
                f"عزيزي {self.customer_name}،\n"
                "نرفق لكم عرض السعر الخاص بالخدمات المطلوبة كما هو موضح أدناه.\n"
                "يرجى التفضل بمراجعة العرض، وفي حال الموافقة نرجو تأكيد ذلك ليتم اتخاذ الإجراءات اللازمة.\n"
                "نشكر لكم ثقتكم،\n"
                "HH-Shaker – Service Team\n"
                "-----------------------------\n"
                f"Dear {self.customer_name},\n"
                "Please find attached the Quotation for the requested services as detailed below.\n"
                "Kindly review the quotation, and if acceptable, confirm your approval so we may proceed with the necessary arrangements.\n"
                "Thank you for your trust,\n"
                "HH-Shaker – Service Team"
            )

            template_payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": message},
            }

            try:
                response = requests.post(
                    f"{base_url}/messages", headers=headers, json=template_payload
                )
                response.raise_for_status()
                _logger.info(
                    "✅ WhatsApp text message sent successfully to %s", phone_number
                )
            except requests.exceptions.RequestException as e:
                _logger.error("❌ Failed to send WhatsApp message: %s", str(e))
                return False

            # --- Step 2: Generate PDF ---
            try:

                pdf_content, _ = (
                    self.env["ir.actions.report"]
                    .sudo()
                    ._render_qweb_pdf(
                        "machine_repair_management.report_service_saleorder_document_hhs",
                        [self.id],
                    )
                )
                _logger.info("📄 PDF generated successfully for job card %s", self.name)
            except Exception as e:
                _logger.error(
                    "❌ Error rendering PDF for job card %s: %s", self.name, str(e)
                )
                raise ValidationError(f"Failed to generate PDF: {str(e)}")

            # --- Step 3: Upload and Send PDF ---
            file_name = f"{self.name}.pdf"
            media_id = self._upload_pdf_meta(pdf_content, file_name)

            if not media_id:
                _logger.info("❌ Failed to upload PDF for %s", self.name)
                return False

            try:
                self.send_pdf_to_whatsapp(phone_number, media_id, file_name, self.name)
                _logger.info(
                    "✅ PDF sent successfully to WhatsApp for %s", phone_number
                )
            except Exception as e:
                _logger.error("❌ Failed to send PDF to WhatsApp: %s", str(e))
                return False

            return {
                "effect": {
                    "type": "rainbow_man",
                    "fadeout": "slow",
                    "message": "Your Quotation was sent successfully to the customer via WhatsApp.",
                }
            }

    def _upload_pdf_meta(self, pdf_content, file_name):
        if not self.whatsapp_sale_send_bool:
            _logger.info("❌ No WhatsApp set in res Config Settings")
            return False

        whatsapp_phone_number_id = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')}"
        url = f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}/media"

        access_token = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')}"

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        files = {
            "file": (file_name, pdf_content, "application/pdf"),
            "type": (None, "document"),
            "messaging_product": (None, "whatsapp"),
        }

        try:
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            media_id = response.json().get("id")
            _logger.info("✅ Uploaded PDF to WhatsApp. Media ID: %s", media_id)
            return media_id

        except requests.exceptions.RequestException as e:
            _logger.error("❌ Media upload failed: %s", str(e))
            return None

    def send_pdf_to_whatsapp(self, phone_number, media_id, file_name, order_name):
        if not self.whatsapp_sale_send_bool:
            _logger.info("❌ No WhatsApp set in res Config Settings")
            return False

        access_token = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')}"

        whatsapp_phone_number_id = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')}"

        url = f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}/messages"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        doc_payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "document",
            "document": {
                "id": media_id,
                "filename": file_name,
                "caption": f"Quotation {self.name}",
            },
        }

        try:
            response = requests.post(url, headers=headers, json=doc_payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.error("Document send error: %s", str(e))
            return False

        # 2. Send interactive buttons
        button_payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": f"Please review Quotation {self.name} and choose an action below. Click Accept to approve or Reject if changes are needed"
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": f"accept_{self.id}", "title": "✅ Accept"},
                        },
                        {
                            "type": "reply",
                            "reply": {"id": f"reject_{self.id}", "title": "❌ Reject"},
                        },
                    ]
                },
            },
        }

        try:
            response = requests.post(url, headers=headers, json=button_payload)
            response.raise_for_status()
            self.message_post(
                body=_("WhatsApp message with quotation sent successfully")
            )
            return True
        except requests.exceptions.RequestException as e:
            _logger.error("Buttons send error: %s", str(e))
            return False

    def action_send_email(self):
        self.ensure_one()

        # 1. Load the mail template
        template = self.env.ref(
            "machine_repair_management.mail_template_service_sale_order",
            raise_if_not_found=False,
        )
        if not template:
            raise UserError(
                _("Email template not found. Please contact your administrator.")
            )

        # 2. Choose correct report
        if self.amc_quotation:
            report = self.env.ref(
                "machine_repair_management.sale_order_amc_quotation_report_details",
                raise_if_not_found=False,
            )
        else:
            report = self.env.ref(
                "machine_repair_management.service_sale_order_quotation_report",
                raise_if_not_found=False,
            )

        if not report:
            raise UserError(_("Report template not found. Cannot send quotation."))

        # 3. Temporarily assign the correct report to the template
        template = template.sudo()
        original_reports = template.report_template_ids.ids[:]

        try:
            template.write({"report_template_ids": [(6, 0, [report.id])]})

            # 4. Send the email directly using the template (Odoo 17+ method)
            template.send_mail(self.id, force_send=True)

            # 5. Mark as sent
            self.write(
                {
                    "state": "sent",
                }
            )

            # 6. Log in chatter
            self.message_post(body=_("Quotation sent by email with attached PDF."))

        finally:
            # Always restore original report(s)
            template.write({"report_template_ids": [(6, 0, original_reports)]})

        return True

        ## Added on - 17-11-2025

    def action_contract_creation(self):
        """
        Override: cancel revised orders automatically and then create contract.
        Wizard is completely skipped.
        """
        for order in self:
            # Step 1 — If revision confirmation not done, cancel all related orders
            if not order.rev_confirm:
                related_orders = order.get_related_orders()
                # Remove the current order from the set
                related_orders = related_orders - order
                # Cancel revised orders if any
                if related_orders:
                    for rec in related_orders:
                        rec.action_cancel()  # or your custom cancel method
                    # Mark revision as confirmed so it doesn't repeat
                    order.rev_confirm = True
            # Step 2 — Now call the original contract creation logic
            if order.contract_id:
                raise ValidationError(_("A contract already exists for this order."))
            
            '''Code Added on June 12 2026 by Vijaya Bhaskar client asked site address similar to address'''

            address = [
                order.crm_id.site_street or False,
                order.crm_id.site_street2 or False,
                order.crm_id.site_customer_city_id.name or False,
                order.crm_id.site_district_id.name or False,
                order.crm_id.site_state_id.name or False,
                order.crm_id.site_country_id.name or False,
                order.crm_id.site_zip or False
                
                ]
            site_address =", ".join(filter(None,address))
            
            contract = self.env["subscription.contracts"].create(
                {
                    "amc_quotation_id": order.id,
                    "site_address" : site_address,
                    # "site_address": order.customer_address,                    'partner_name': order.partner_name,
                    'warehouse_id' : order.warehouse_id.id or False,
                    'customer_code' : order.customer_code or False,
                    'work_center_id' :order.work_center_id.id or False,
                    'work_center_group_id' : order.work_center_group_id.id or False,
                    'district' :order.district.id or False,
                    # "mobile_no": f"+{order.crm_id.country_id.phone_code if order.crm_id and order.crm_id.country_id else ''}-{order.crm_id.phone if order.crm_id else ''}",
                    "sales_person_user_id" :   order.sales_person_user_id.id or False ,
                    
                    'street': order.street or '',
                    'street2':order.street2 or ' ',
                    'customer_city_id' :order.customer_city_id.id or '',
                    'district_id': order.district_id.id or '',
                    'state_id': order.state_id.id or '',
                    'country_id':order.country_id.id or '',
                    'zip': order.zip or '',           
                

                }
            )
            order.contract_id = contract
            order.state = "sale"
            contract.onchange_amc_quotation_id()
            contract.onchange_partner_id_set_identification()
            '''Code Added on June 05 2026 by Vijaya Bhaskar'''
            contract._onchange_invoice_interval()

            ContractLine = self.env["subscription.contracts.line"]

            # ✅ Step 4 — Insert lines ONLY if not already created
            existing_lines = ContractLine.search(
                [("subscription_contract_id", "=", contract.id)], limit=1
            )

            if not existing_lines:
                lines_vals = []
                for line in order.service_sale_order_line_ids:
                    lines_vals.append(
                        {
                            "subscription_contract_id": contract.id,
                            "product_id": line.product_id.id,
                            "main_category_id": line.main_category_id.id,
                            "brand_category_id": line.brand_category_id.id,
                            "contract_type_id": line.contract_type_id.id,
                            "amc_pricing_id": line.amc_pricing_id.id,
                            "unit_cost_price": line.unit_cost_price,
                            "unit_selling_price": line.unit_selling_price,
                            "spare_parts_cost_per_category": line.spare_parts_cost_per_category,
                            "spare_parts_cost": line.spare_parts_cost,
                            "spare_parts_selling_price": line.spare_parts_selling_price,
                            "total_selling_price": line.total_selling_price,
                            "per_unit_selling_price": line.per_unit_selling_price,
                          #  "analytic_account_id": order.analytic_account_id.id,
                        }
                    )

                ContractLine.create(lines_vals)

            # 🔥 STEP 5 — CREATE PAYMENT SCHEDULE (YOUR REQUIREMENT)
            if order.quotation_payment_term_ids:

                # Remove old schedule 'name_ara': line.name_ara,
                contract.payment_schedule_line_ids.unlink()

                schedule_vals = []
                for line in order.quotation_payment_term_ids:
                    schedule_vals.append(
                        {
                            "contract_id": contract.id,
                            "sequence": line.sequence,
                            "name": line.name,
                            "name_ara": line.name_arabic,
                            "payment_date": line.payment_date,
                            "amount": line.amount,
                            "state": line.state,
                        }
                    )

                self.env["contract.payment.schedule.line"].create(schedule_vals)

            return {
                "type": "ir.actions.act_window",
                "name": _("Subscription Contract"),
                "res_model": "subscription.contracts",
                "view_mode": "form",
                "res_id": contract.id,
                "target": "current",
            }
        return True

    def show_contract(self):
        """Button: Open the related contract form view."""
        self.ensure_one()
        if not self.contract_id:
            raise ValidationError(_("No contract is linked to this order."))

        return {
            "name": _("Contract"),
            "type": "ir.actions.act_window",
            "res_model": "subscription.contracts",
            "view_mode": "form",
            "res_id": self.contract_id.id,
            "target": "current",
        }

    def _compute_show_standrd_hr(self):
        if self.env.user.has_group(
            "selling_cost_price_restrict.group_product_price_user"
        ):
            self.show_standard_hours = True
        else:
            self.show_standard_hours = False

    def compute_approval_button(self):
        for rec in self:
            rec.show_approval_button = self.env.user.has_group("base.group_system")


class ServiceSaleOrderLine(models.Model):
    _name = "service.sale.order.line"
    _description = "Service Sale Order Line"

    service_sale_id = fields.Many2one("service.sale.order", string="Service Sale ID")
    product_id = fields.Many2one("product.product", string="Product")
    product_qty = fields.Float(string="Quantity")
    product_uom = fields.Many2one("uom.uom", string="UOM")
    price_unit = fields.Float("Unit Price")
    vat = fields.Float(string="VAT (%)", default=0.0)
    tax_amount = fields.Float(string="Tax Amount")
    # commented on Nov 14
    total = fields.Float(string="Total", compute="_compute_total", store=True)
    total_amc = fields.Float(string="Net Price", store=True)
    cost = fields.Float(string="Cost")
    margin = fields.Float(string="Margin")
    margin_percent = fields.Float(string="Margin %")
    amc_quotation = fields.Boolean(string="Is AMC Quotation", default=False)
    discount = fields.Float(
        string="Discount (%)",
        digits="Discount",
        store=True,
        readonly=False,
        help="Discount in %",
    )
    under_warranty_bool = fields.Boolean(
        string="UW",
        default=False,
    )

    # added on Nov 14 Amc Quotation purpose
    description = fields.Char(string="Description")
    no_of_visits_per_year = fields.Integer(string="No.of Visits/Yr")
    no_of_emergency_visit = fields.Integer(string="No.of Emergency Visits")
    days_required_for_rpm = fields.Float(
        string="Days Required for PPM", compute="_compute_total_hour_cost"
    )
    standard_hours = fields.Float(string="Standard Hours")
    total_hr = fields.Float(string="Total Hours", compute="_compute_total_hour_cost")
    total_cost = fields.Float(
        string="Total Labor Cost", compute="_compute_total_hour_cost"
    )
    total_price = fields.Float(
        string="Labor Selling Price", compute="_compute_total_hour_cost"
    )
    vat_percent = fields.Float(string="VAT", compute="_compute_total_hour_cost")
    actual_prevent_count = fields.Integer(string="Actual Preventive Count")
    actual_correct_count = fields.Integer(string="Actual Corrective Count")
    total_correct_count = fields.Integer(
        string="Total Corrective Count", compute="_compute_total_hour_cost"
    )
    days_require_rpm_round_off = fields.Integer(
        string="Total Preventive Count", compute="_compute_total_hour_cost"
    )
    balance_prevent_count = fields.Integer(
        string="Balance Preventive Count", compute="_compute_total_hour_cost"
    )
    balance_correct_count = fields.Integer(
        string="Balance Corrective Count", compute="_compute_total_hour_cost"
    )
    total_selling_price = fields.Float(
        string="Total Selling Price", compute="_compute_total_hour_cost", store=True
    )
    amc_quotation_id = fields.Many2one("pm.service", string="Quotation")

    @api.onchange("product_id")
    def _onchange_standard_hours(self):
        for rec in self:
            if rec.product_id:
                rec.standard_hours = rec.product_id.standard_hours
                
    '''Code Added on June 17 2026 by Vijaya Bhaskar client asked when standard hours is  changed then immediately validation error shows'''            
    @api.onchange('standard_hours')
    def _change_standard_hours_self(self):
        for rec in self:
            if rec.product_id:
                product_standard_hours = rec.product_id.standard_hours or 0.0

                if rec.standard_hours < product_standard_hours:
                    raise ValidationError(_(
                        "Standard Hours must be greater than or equal to the Product Standard Hours.\n\n"
                        "Product: %s\n"
                        "Product Standard Hours: %.2f\n"
                        "Entered Standard Hours: %.2f"
                    ) % (
                                              rec.product_id.display_name,
                                              product_standard_hours,
                                              rec.standard_hours
                                          ))
            
                           

    @api.constrains('product_id', 'standard_hours')
    def _check_standard_hours(self):
        for rec in self:
            if rec.product_id:
                product_standard_hours = rec.product_id.standard_hours or 0.0

                if rec.standard_hours < product_standard_hours:
                    raise ValidationError(_(
                        "Standard Hours must be greater than or equal to the Product Standard Hours.\n\n"
                        "Product: %s\n"
                        "Product Standard Hours: %.2f\n"
                        "Entered Standard Hours: %.2f"
                    ) % (
                                              rec.product_id.display_name,
                                              product_standard_hours,
                                              rec.standard_hours
                                          ))

    @api.onchange("product_id")
    def _onchange_description(self):
        for rec in self:
            if rec.product_id:
                rec.description = rec.product_id.name

    # @api.constrains("product_id")
    # def _check_duplicate_product(self):
    #     for line in self:
    #         if not line.service_sale_id:
    #             continue
    #         # Collect all product_ids in the order lines except current one
    #         products = line.service_sale_id.service_sale_order_line_ids.filtered(
    #             lambda l: l.id != line.id
    #         ).mapped("product_id")
    #         if line.product_id in products:
    #             raise ValidationError(
    #                 "This product is already added! Duplicate products are not allowed."
    #             )

    """When no line items selected in service sale order"""

    @api.constrains("service_sale_order_line_ids")
    def _check_service_lines(self):
        if not self.service_sale_order_line_ids:
            raise ValidationError(
                _("Please give at least one Product in the product lines")
            )

    @api.depends(
        "product_qty",
        "no_of_visits_per_year",
        "no_of_emergency_visit",
        "standard_hours",
        "service_sale_id.travel_hours",
        "service_sale_id.gross_profit",
        "vat",
    )
    def _compute_total_hour_cost(self):
        units_serviced_visit = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("machine_repair_management.units_serviced_visit", default=0.0)
        )

        no_of_technician_each_visit = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("machine_repair_management.no_of_technician_visit", default=0.0)
        )

        labor_cost_hr = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("machine_repair_management.labor_cost_hr", default=0.0)
        )

        for rec in self:

            product_qty = float(rec.product_qty or 0.0)

            standard_hours = float(rec.standard_hours or 0.0)

            no_of_visits = float(rec.no_of_visits_per_year or 0.0)

            travel_hours = float(rec.service_sale_id.travel_hours or 0.0)

            gross_profit = float(
                (rec.service_sale_id and rec.service_sale_id.gross_profit) or 0.0
            )

            vat_percent = float(rec.vat or 0.0)

            # Avoid division by zero
            days_required = (
                product_qty / units_serviced_visit if units_serviced_visit else 0.0
            )

            rec.days_required_for_rpm = days_required

            rec.days_require_rpm_round_off = (
                rec.days_required_for_rpm
            )

            rec.total_correct_count = rec.no_of_emergency_visit

            rec.balance_prevent_count = (
                rec.days_require_rpm_round_off - rec.actual_prevent_count
            )

            rec.balance_correct_count = (
                rec.no_of_emergency_visit - rec.actual_correct_count
            )

            rec.total_hr = (
                (
                    product_qty
                    * no_of_technician_each_visit
                    * standard_hours
                    * no_of_visits
                )
                + (days_required * travel_hours * no_of_visits)
                + (rec.no_of_emergency_visit * 2)
            )
            
            '''Code Added on April 11 2026 by vijaya bhaskar'''
            rec.total_hr = rec.total_hr

            rec.total_cost = rec.total_hr * labor_cost_hr
           
            
            '''Code Added on April 11 2026 by vijaya bhaskar'''
            rec.total_cost = rec.total_cost
           
            
            
            rec.total_price = (rec.total_cost / (1 - gross_profit / 100))
            

            # rec.vat_percent = float_round(rec.total_price * (vat_percent / 100), precision_digits=2)

            rec.vat_percent = (
                rec.total_selling_price * (vat_percent / 100)
            )

            if rec.service_sale_id.amc_quotation:
                rec.price_unit = (
                    (rec.total_price / product_qty)
                    if product_qty
                    else 0.0
                )

            rec.total_amc = (
                rec.total_selling_price + rec.vat_percent
            )

    #working code commented on May 12 2026
    # @api.depends(
    #     "product_qty",
    #     "no_of_visits_per_year",
    #     "no_of_emergency_visit",
    #     "standard_hours",
    #     "service_sale_id.travel_hours",
    #     "service_sale_id.gross_profit",
    #     "vat",
    # )
    # def _compute_total_hour_cost(self):
    #     units_serviced_visit = float(
    #         self.env["ir.config_parameter"]
    #         .sudo()
    #         .get_param("machine_repair_management.units_serviced_visit", default=0.0)
    #     )
    #
    #     no_of_technician_each_visit = float(
    #         self.env["ir.config_parameter"]
    #         .sudo()
    #         .get_param("machine_repair_management.no_of_technician_visit", default=0.0)
    #     )
    #
    #     labor_cost_hr = float(
    #         self.env["ir.config_parameter"]
    #         .sudo()
    #         .get_param("machine_repair_management.labor_cost_hr", default=0.0)
    #     )
    #
    #     for rec in self:
    #
    #         product_qty = float(rec.product_qty or 0.0)
    #
    #         standard_hours = float(rec.standard_hours or 0.0)
    #
    #         no_of_visits = float(rec.no_of_visits_per_year or 0.0)
    #
    #         travel_hours = float(rec.service_sale_id.travel_hours or 0.0)
    #
    #         gross_profit = float(
    #             (rec.service_sale_id and rec.service_sale_id.gross_profit) or 0.0
    #         )
    #
    #         vat_percent = float(rec.vat or 0.0)
    #
    #         # Avoid division by zero
    #         days_required = (
    #             product_qty / units_serviced_visit if units_serviced_visit else 0.0
    #         )
    #
    #         rec.days_required_for_rpm = days_required
    #
    #         rec.days_require_rpm_round_off = float_round(
    #             rec.days_required_for_rpm, precision_digits=2
    #         )
    #
    #         rec.total_correct_count = rec.no_of_emergency_visit
    #
    #         rec.balance_prevent_count = (
    #             rec.days_require_rpm_round_off - rec.actual_prevent_count
    #         )
    #
    #         rec.balance_correct_count = (
    #             rec.no_of_emergency_visit - rec.actual_correct_count
    #         )
    #
    #         rec.total_hr = (
    #             (
    #                 product_qty
    #                 * no_of_technician_each_visit
    #                 * standard_hours
    #                 * no_of_visits
    #             )
    #             + (days_required * travel_hours * no_of_visits)
    #             + (rec.no_of_emergency_visit * 2)
    #         )
    #
    #         '''Code Added on April 11 2026 by vijaya bhaskar'''
    #         rec.total_hr = float_round(rec.total_hr,precision_digits=2)
    #
    #         rec.total_cost = rec.total_hr * labor_cost_hr
    #
    #         '''Code Added on April 11 2026 by vijaya bhaskar'''
    #         rec.total_cost = float_round(rec.total_cost, precision_digits=2)
    #
    #
    #
    #         rec.total_price = float_round(
    #             rec.total_cost / (1 - gross_profit / 100), precision_digits=2
    #         )
    #
    #         # rec.vat_percent = float_round(rec.total_price * (vat_percent / 100), precision_digits=2)
    #
    #         rec.vat_percent = float_round(
    #             rec.total_selling_price * (vat_percent / 100), precision_digits=2
    #         )
    #
    #         if rec.service_sale_id.amc_quotation:
    #             rec.price_unit = (
    #                 float_round(rec.total_price / product_qty, precision_digits=2)
    #                 if product_qty
    #                 else 0.0
    #             )
    #
    #         rec.total_amc = float_round(
    #             rec.total_selling_price + rec.vat_percent, precision_digits=2
    #         )

    @api.onchange("product_id")
    def _product_line_onchange(self):
        for rec in self:
            if rec.product_id:
                rec.amc_quotation = rec.service_sale_id.amc_quotation
                rec.product_uom = rec.product_id.uom_id

                rec.price_unit = rec.product_id.lst_price

                if rec.product_id.taxes_id:
                    rec.vat = rec.product_id.taxes_id[0].amount
                else:
                    rec.vat = 0.0

    @api.depends("product_qty", "price_unit", "vat", "discount")
    def _compute_total(self):
        for record in self:
            total = record.product_qty * record.price_unit
            discount = total * record.discount / 100
            total_after_discount = total - discount
            vat_with_total = total_after_discount * record.vat / 100
            record.tax_amount = (
                record.product_qty * record.price_unit * (record.vat / 100)
            )
            record.total = total_after_discount + vat_with_total

    @api.constrains("service_sale_id", "product_id", "product_qty", "price_unit")
    def _check_task_product_match(self):
        if self.env.context.get("from_task"):
            return

        for line in self:
            order = line.service_sale_id
            task = order.job_task_id

            if not task or not task.product_line_ids:
                continue

            if order.state not in ("draft", "sent"):
                continue

            task_lines = task.product_line_ids.filtered(lambda l: l.product_id)

            task_product_map = {
                l.product_id.id: {
                    "qty": l.qty,
                    "price_unit": l.price_unit,
                    "name": l.product_id.name,
                }
                for l in task_lines
            }

            order_lines = order.service_sale_order_line_ids.filtered(
                lambda l: l.product_id
            )
            order_product_map = {
                l.product_id.id: {
                    "qty": l.product_qty,
                    "price_unit": l.price_unit,
                    "name": l.product_id.name,
                }
                for l in order_lines
            }

            errors = []

            # Check if all products in task exist in quotation with exact qty, price and name
            for product_id, task_vals in task_product_map.items():
                order_vals = order_product_map.get(product_id)
                if not order_vals:
                    product = self.env["product.product"].browse(product_id)
                    errors.append(
                        f"Product '{product.display_name}' is missing in the quotation."
                    )
                    continue

                if task_vals["name"] != order_vals["name"]:
                    errors.append(f"Product name mismatch for '{task_vals['name']}'.")

                if float(task_vals["qty"]) != float(order_vals["qty"]):
                    errors.append(
                        f"Quantity mismatch for '{task_vals['name']}': Task = {task_vals['qty']}, Quotation = {order_vals['qty']}."
                    )

                if float(task_vals["price_unit"]) != float(order_vals["price_unit"]):
                    errors.append(
                        f"Price mismatch for '{task_vals['name']}': Task = {task_vals['price_unit']}, Quotation = {order_vals['price_unit']}."
                    )

            if errors:
                raise ValidationError(
                    "Quotation amount does not exactly match Job card Amount"
                )
