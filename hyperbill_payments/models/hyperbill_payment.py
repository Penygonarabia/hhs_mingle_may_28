from odoo import models, fields, api
from odoo.exceptions import UserError
import requests
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    _inherit = 'project.task'

    inspection_inv_no = fields.Char(
        string="Inspection Invoice No",
        readonly=True,
        help="Stores Hyperbill invoice number for inspection charges"
    )

    balance_inv_no = fields.Char(
        string="Balance Invoice No",
        readonly=True,
        help="Stores Hyperbill invoice number for balance payment"
    )
    payment_insp_link_sent_bool = fields.Boolean(string="Payment INSP Link Sent", default=False)
    payment_bal_link_sent_bool = fields.Boolean(string="Payment BAL Link Sent", default=False)
    payment_button_hide = fields.Boolean(string="Payment Buttons Hide", default=False)

    payment_final_button_hide = fields.Boolean(string="Payment Final Buttons Hide", default=False)



    def action_create_hyperbill_inspection_payment(self):
        """Create Hyperbill payment link for inspection charges and send via WhatsApp"""
        self.ensure_one()

        try:
            # Validate prerequisites
            if not self.inspection_charges_amount or self.inspection_charges_amount <= 0:
                raise UserError("Inspection charges amount must be greater than 0.")

            if not self.customer_name:
                raise UserError("Customer name is required.")

            if not self.phone:
                raise UserError("Customer phone number is required.")

            # if not self.email:
            #     raise UserError("Customer email is required.")

            
            # Get API configuration from existing settings
            ''' commented on Jan 09-2026 by Vijaya Bhaskar due to hyper pay bill is added on work center group
            config = self.env['ir.config_parameter'].sudo()
            token = config.get_param('hyperbill_payments.hyperpay_token')
            '''
            token = self.work_center_group_id.hyperpay_token
            
            

            # Use the correct base URL

            # base_url = "https://hyperbill-sandbox.hyperpay.com"
            ''' commented on Jan 09-2026 by Vijaya Bhaskar due to hyper pay bill is added on work center group
            base_url = self.env['ir.config_parameter'].sudo().get_param('hyperbill_payments.hyperpay_url')
            '''
            base_url = self.work_center_group_id.hyperpay_url

            if not token:
                raise UserError("Hyperbill API token is not configured in the Work Center Group. Please generate a token in Settings.")

            # Calculate total amount including VAT
            # vat_amount = self.inspection_charges_amount * 0.15
            # total_amount = self.inspection_charges_amount + vat_amount
            total_amount = self.inspection_charges_amount

            # Prepare payload
            payload = {
                "name": self.customer_name,
                # "email": self.email,
                "phone": self.phone,
                "lang": "en",
                "amount": total_amount,
                # "vat": 15,
                "currency": "SAR",
                "payment_type": "DB",
                "merchant_invoice_number": f"JC-{self.name}-I-{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}",
                
            }
            
            custom_region = self.work_center_group_id.custom_region
            if not custom_region:
                raise UserError("Custom region is not configured in Work Center Group.")
            
            if self.work_center_group_id.hyperpay_environment == 'production':
                payload[f"custom_{custom_region}"] = self.name

            

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }

            # Make API call to create simple invoice with correct URL
            api_url = f"{base_url}/api/simpleInvoice"
            _logger.info(f"Making Hyperbill API request to: {api_url}")
            _logger.info(f"Request payload: {payload}")

            response = requests.post(api_url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                response_data = response.json()
                _logger.info(f"Hyperbill API response: {response_data}")

                if response_data.get('status'):
                    data = response_data['data']
                    payment_url = data.get('short_url')
                    invoice_no = data.get('invoice_no')
                    merchant_invoice_number = data.get('merchant_invoice_number', '')
                    self.inspection_inv_no = invoice_no
                    self.payment_insp_link_sent_bool = True

                    # Create HyperpayAudit record with CURRENT data
                    
                    eastern_region_vals = False
                    
                    central_region_vals = False
                    
                    # if self.work_center_group_id:
                    #     if self.work_center_group_id.name:
                    #         if self.work_center_group_id.name.lower().startswith('eastern region'):
                    #             eastern_region_vals ={
                    #                 'region' : f'custom_319 = {self.name}'
                    #                 # 'custom_319' : self.name,
                    #                 }
                    #
                    # if (self.work_center_group_id and self.work_center_group_id.name and
                    #     self.work_center_group_id.name.lower().startswith('central region')
                    # ):
                    #     central_region_vals = {
                    #         'region' : f'custom_317 = {self.name}'
                    #         # 'custom_317': self.name,
                    #     }        
                        
                        
                    audit_vals = {
                        'jobcard_id': self.id,  # Current task ID
                        'name': self.name,  # Current jobcard number
                        'payment_for': 'inspection',
                        'payment_receipt_number': invoice_no,
                        'payment_reference': merchant_invoice_number or f"SIINV{invoice_no}",
                        # 'invoice_no': invoice_no,  # Current Hyperbill invoice number
                        'payment_received': 'no',
                        'status': 'pending',
                        
                    }
                    audit_record = self.env['hyperpay.audit'].create(audit_vals)
                    # if eastern_region_vals:
                    #     audit_record.write(eastern_region_vals)
                    #
                    # if central_region_vals:
                    #     audit_record.write(central_region_vals)
                    #
               

                    _logger.info(f"✅ HyperpayAudit record created: ID {audit_record.id}, Invoice: {invoice_no}")

                    # Log successful payment link creation with details
                    _logger.info(f"""
                            Hyperbill Payment Link Created Successfully:
                            - Task: {self.name}
                            - Invoice Number: {invoice_no}
                            - Payment URL: {payment_url}
                            - Amount: {total_amount} SAR
                            - Customer: {self.customer_name} ({self.email})
                            """)

                    # Send payment link via WhatsApp
                    whatsapp_sent = self._send_payment_link_via_whatsapp(payment_url, total_amount, invoice_no)

                    if whatsapp_sent:
                        message = f"""
                                Hyperbill payment link created and sent via WhatsApp successfully!

                                Invoice Number: {invoice_no}
                                Amount: {total_amount} SAR (Including 15% VAT)
                                Customer: {self.customer_name}
                                Phone: {self.phone}

                                The payment link has been sent to the customer's WhatsApp.
                                """
                        message_type = 'success'
                    else:
                        message = f"""
                                Hyperbill payment link created but failed to send via WhatsApp!

                                Payment URL: {payment_url}
                                Invoice Number: {invoice_no}
                                Amount: {total_amount} SAR (Including 15% VAT)

                                Please share this link manually with the customer.
                                """
                        message_type = 'warning'

                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Payment Link Created',
                            'message': message,
                            'type': message_type,
                            'sticky': True,
                        }
                    }
                else:
                    error_msg = response_data.get('message', 'Unknown error occurred')
                    _logger.error(f"Hyperbill API Error: {error_msg} | Payload: {payload}")
                    raise UserError(f"Hyperbill API Error: {error_msg}")
            else:
                error_data = response.json()
                error_msg = error_data.get('message', f"HTTP {response.status_code}: {response.text}")
                _logger.error(f"Hyperbill API Request Failed: {error_msg} | URL: {api_url} | Payload: {payload}")
                raise UserError(f"API Request Failed: {error_msg}")

        except requests.exceptions.RequestException as e:
            _logger.error(f"Hyperbill API connection error: {str(e)}")
            raise UserError(f"Connection error: {str(e)}")
        except Exception as e:
            _logger.error(
                f"Error creating Hyperbill payment: {str(e)} | Task: {self.name} | Customer: {self.customer_name}")
            raise UserError(f"Failed to create payment link: {str(e)}")

    def action_create_hyperbill_balance_payment(self):
        """Create Hyperbill payment link for the remaining balance and send via WhatsApp"""
        self.ensure_one()

        try:
            # Check pending balance
            # if self.balance_amount <= 0:
            if self.balance_paid <= 0:
                raise UserError("No pending balance to be paid. Balance amount must be greater than 0.")

            # if not self.customer_name or not self.phone or not self.email:
            #     raise UserError("Customer details missing. Name, Phone and Email are required.")
            if not self.customer_name:
                raise UserError("Customer name is required.")

            if not self.phone:
                raise UserError("Customer phone number is required.")

            # if not self.email:
            #     raise UserError("Customer email is required.")

           
            
            ''' commented on Jan 09-2026 by Vijaya Bhaskar due to hyper pay bill is added on work center group
            # Fetch token from Hyperbill settings
            config = self.env['ir.config_parameter'].sudo()
            token = config.get_param('hyperbill_payments.hyperpay_token')
            '''
            token = self.work_center_group_id.hyperpay_token
            
            
            ''' commented on Jan 09-2026 by Vijaya Bhaskar due to hyper pay bill is added on work center group
              # base_url = "https://hyperbill-sandbox.hyperpay.com"
            base_url = self.env['ir.config_parameter'].sudo().get_param('hyperbill_payments.hyperpay_url')
            '''
            
            base_url = self.work_center_group_id.hyperpay_url


            if not token:
                raise UserError("Hyperbill token not configured in Work Center Group.")

            # VAT Calculation
            # vat_amount = self.balance_paid * 0.15
            # total_amount = self.balance_paid + vat_amount
            total_amount = False
            total_amount = self.balance_paid
            # if self.balance_received != 0.0:
            if total_amount > self.balance_received:
                balance_amount = 0
                balance_amount = self.balance_paid
                total_amount  = balance_amount - self.balance_received
                
            payload = {
                "name": self.customer_name,
                # "email": self.email,
                "phone": self.phone,
                "lang": "en",
                "amount": total_amount,
                # "vat": 15,
                "currency": "SAR",
                "payment_type": "DB",
                "merchant_invoice_number": f"JC-{self.name}-F-{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
            custom_region = self.work_center_group_id.custom_region
            if not custom_region:
                raise UserError("Custom region is not configured in Work Center Group.")
            
            if self.work_center_group_id.hyperpay_environment == 'production':
                payload[f"custom_{custom_region}"] = self.name

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }

            api_url = f"{base_url}/api/simpleInvoice"
            _logger.info("Hyperbill Balance Payment Payload: %s", payload)

            response = requests.post(api_url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                res = response.json()
                if res.get("status"):
                    data = res["data"]
                    payment_url = data.get("short_url")
                    invoice_no = data.get("invoice_no")
                    self.balance_inv_no = invoice_no
                    merchant_invoice_number = data.get('merchant_invoice_number', '')
                    self.payment_bal_link_sent_bool = True


                    # Create HyperpayAudit record with CURRENT data
                    audit_vals = {
                        'jobcard_id': self.id,  # Current task ID
                        'name': self.name,  # Current jobcard number
                        'payment_for': 'final',
                        'payment_receipt_number': invoice_no,
                        'payment_reference': merchant_invoice_number or f"SIINV{invoice_no}",
                        # 'invoice_no': invoice_no,  # Current Hyperbill invoice number
                        'payment_received': 'no',
                        'status': 'pending'
                    }
                    audit_record = self.env['hyperpay.audit'].create(audit_vals)

                    _logger.info(f"✅ HyperpayAudit record created: ID {audit_record.id}, Invoice: {invoice_no}")

                    whatsapp_sent = self._send_balance_payment_link_via_whatsapp(
                        payment_url, total_amount, invoice_no)

                    if whatsapp_sent:
                        msg = f"""Balance Hyperbill link created and sent via WhatsApp.
                        Invoice No: {invoice_no}
                        Amount: {total_amount} SAR (Incl. 15% VAT)
                        Customer: {self.customer_name}
                        Phone: {self.phone}
                        """
                        msg_type = "success"
                    else:
                        msg = f"""Payment link created but WhatsApp failed.
                        Payment URL: {payment_url}
                        Invoice No: {invoice_no}
                        """
                        msg_type = "warning"

                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Final Payment Link',
                            'message': msg,
                            'type': msg_type,
                            'sticky': True,
                        }
                    }
                else:
                    raise UserError(res.get("message", "Unknown Hyperbill error"))

            else:
                raise UserError(f"Hyperbill HTTP Error: {response.text}")

        except Exception as e:
            _logger.error(f"Balance Payment error: {str(e)} | Task: {self.name}")
            raise UserError(f"Failed: {str(e)}")

    def _send_payment_link_via_whatsapp(self, payment_url, total_amount, invoice_no):
        """Send payment link to customer via WhatsApp"""
        try:
            # Get WhatsApp configuration
            config = self.env['ir.config_parameter'].sudo()
            access_token = config.get_param('whatsapp_sale_order_notify.whatsapp_access_token')
            phone_number_id = config.get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')

            if not access_token:
                _logger.error("WhatsApp Access Token is not configured")
                return False

            if not phone_number_id:
                _logger.error("WhatsApp Phone Number ID is not configured")
                return False

            # Format phone number EXACTLY like the working code
            phone_number = self.phone.replace('+', ' ').replace(' ', '')

            # Get country code and format phone number like working code
            country_code = self.country_id.phone_code if self.country_id else '966'  # Default to Saudi Arabia
            phone_number = f"{country_code}{phone_number}"

            if not phone_number:
                _logger.error("Customer phone number is not available")
                return False

            # Prepare WhatsApp message URL like working code
            whatsapp_phone_number_id = f"{phone_number_id}"
            base_url = f'https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}'
            template_url = f"{base_url}/messages"

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            # Use SIMPLE TEXT message instead of interactive (like working code)
            message_text = f"""💰 *Payment Request - Inspection Charges*

                    Dear {self.customer_name},
                
                    Your inspection charges payment is ready.
                
                    *Invoice Number:* {invoice_no}
                    *Amount:* {total_amount} SAR (Including 15% VAT)
                
                    Please click the link below to complete your payment:
                    {payment_url}
                
                    Thank you for choosing our services!"""

            payload = {
                'messaging_product': "whatsapp",
                'to': phone_number,
                "type": "text",
                "text": {
                    'body': message_text,
                }
            }

            # Send WhatsApp message
            response = requests.post(template_url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                _logger.info(f"✅ Payment link sent via WhatsApp to {phone_number}")
                _logger.info(f"WhatsApp API response: {response.json()}")

                # Add message to chatter like working code
                self.message_post(
                    body=f"Hyperbill payment link sent via WhatsApp to customer. "
                         f"Invoice: {invoice_no}, Amount: {total_amount} SAR"
                )
                return True
            else:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown WhatsApp API error')
                _logger.error(f"❌ WhatsApp API error {response.status_code}: {error_msg}")
                return False

        except requests.exceptions.RequestException as e:
            _logger.error(f"❌ WhatsApp API connection error: {str(e)}")
            return False
        except Exception as e:
            _logger.error(f"❌ Unexpected error sending WhatsApp message: {str(e)}")
            return False

    def _send_balance_payment_link_via_whatsapp(self, payment_url, total_amount, invoice_no):
        """Send balance payment link to customer via WhatsApp"""
        try:
            # Fetch WhatsApp API credentials
            config = self.env['ir.config_parameter'].sudo()
            access_token = config.get_param('whatsapp_sale_order_notify.whatsapp_access_token')
            phone_number_id = config.get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')

            if not access_token or not phone_number_id:
                _logger.error("WhatsApp Access Token or Phone Number ID missing in configuration")
                return False

            # Clean and format phone number
            phone_number = self.phone.replace('+', '').replace(' ', '')
            country_code = self.country_id.phone_code if self.country_id else '966'
            phone_number = f"{country_code}{phone_number}"

            if not phone_number:
                _logger.error("Missing customer phone number")
                return False

            # WhatsApp URL
            api_url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            # Balance payment WhatsApp message
            message_text = f"""💰 *Balance Payment Request*
                Dear {self.customer_name},

                A balance payment is due.

                *Invoice Number:* {invoice_no}
                *Balance Amount:* {total_amount} SAR

                Please click below to complete your payment:
                {payment_url}

                Thank you for choosing our services!"""

            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": message_text}
            }

            # Send WhatsApp message
            response = requests.post(api_url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                _logger.info(f"✅ Balance Payment WhatsApp sent to: {phone_number}")
                _logger.info(f"Response: {response.json()}")

                self.message_post(
                    body=f"Balance payment link sent via WhatsApp. Invoice: {invoice_no}, Amount: {total_amount} SAR"
                )
                return True
            else:
                error_msg = response.json().get("error", {}).get("message", "Unknown WhatsApp API error")
                _logger.error(f"❌ WhatsApp Sending Failed: {error_msg}")
                return False

        except Exception as e:
            _logger.error(f"❌ Unexpected WhatsApp Error: {str(e)}")
            return False

    # def check_hyperbill_payment_status(self, specific_invoice_no=None):
    #     """Check payment status for Hyperbill invoices"""
    #     try:
    #         config = self.env['ir.config_parameter'].sudo()
    #         token = config.get_param('hyperbill_payments.hyperpay_token')
    #         # base_url = "https://hyperbill-sandbox.hyperpay.com"
    #         base_url = self.env['ir.config_parameter'].sudo().get_param('hyperbill_payments.hyperpay_url')
    #
    #
    #
    #         if not token:
    #             _logger.error("Hyperbill API token is not configured.")
    #             return False
    #
    #         # Build domain for search
    #         domain = [('payment_received', '=', 'no')]
    #         domain += [('status', '!=', 'failure')]
    #
    #         if specific_invoice_no:
    #             # Check specific invoice only
    #             # domain.append(('invoice_no', '=', specific_invoice_no))
    #             domain.append(('payment_reference', '=', specific_invoice_no))
    #             _logger.info(f"Checking specific invoice: {specific_invoice_no}")
    #         else:
    #             # Check all pending invoices
    #             # domain.append(('invoice_no', '!=', False))
    #             domain.append(('payment_reference', '!=', False))
    #             _logger.info("Checking all pending invoices")
    #
    #         pending_audits = self.env['hyperpay.audit'].search(domain)
    #
    #         headers = {
    #             'Content-Type': 'application/json',
    #             'Authorization': f'Bearer {token}'
    #         }
    #
    #         updated_count = 0
    #
    #         for audit in pending_audits:
    #             try:
    #                 # Use the CURRENT invoice_no from audit record
    #                 # current_invoice_no = audit.invoice_no
    #                 current_invoice_no = audit.payment_reference
    #                 if not current_invoice_no:
    #                     continue
    #
    #                 # Make API call to check CURRENT invoice status
    #                 api_url = f"{base_url}/api/simpleInvoice/retrieve/min/{current_invoice_no}"
    #                 _logger.info(f"🔍 Checking payment status for current invoice: {current_invoice_no}")
    #
    #                 response = requests.get(api_url, headers=headers, timeout=30)
    #
    #                 if response.status_code == 200:
    #                     response_data = response.json()
    #
    #                     if response_data.get('status'):
    #                         data = response_data['data']
    #                         invoice_status = data.get('status', '').lower()
    #                         current_merchant_invoice = data.get('merchant_invoice_number', '')
    #
    #                         _logger.info(f"📊 Invoice {current_invoice_no} status: {invoice_status}")
    #
    #                         if invoice_status == 'paid':
    #                             # Update with CURRENT payment data
    #                             paid_at_str = data.get('paid_at')
    #                             paid_datetime = False
    #
    #                             if paid_at_str:
    #                                 try:
    #                                     paid_datetime = datetime.strptime(paid_at_str, '%Y-%m-%d %H:%M:%S')
    #                                 except ValueError:
    #                                     _logger.warning(f"Could not parse paid_at date: {paid_at_str}")
    #                                     paid_datetime = fields.Datetime.now()
    #
    #                             # Update audit record with current payment info
    #                             audit.write({
    #                                 'payment_received': 'yes',
    #                                 'received_datetime': paid_datetime or fields.Datetime.now(),
    #                                 'status': 'success',
    #                                 'payment_reference': current_merchant_invoice or audit.payment_reference
    #                             })
    #                             audit.jobcard_id.payment_button_hide = True
    #
    #                             # Log the successful update
    #                             _logger.info(f"""
    #                             ✅ PAYMENT CONFIRMED:
    #                             - Audit ID: {audit.id}
    #                             - Job Card: {audit.name}
    #                             - Invoice: {current_invoice_no}
    #                             - Amount: {data.get('amount', 'N/A')} {data.get('currency', 'SAR')}
    #                             - Paid at: {paid_at_str}
    #                             - Payment For: {audit.payment_for}
    #                             """)
    #
    #                             updated_count += 1
    #
    #                         elif invoice_status == 'declined':
    #                             paid_at_str = data.get('paid_at')
    #                             paid_datetime = False
    #
    #                             if paid_at_str:
    #                                 try:
    #                                     paid_datetime = datetime.strptime(paid_at_str, '%Y-%m-%d %H:%M:%S')
    #                                 except ValueError:
    #                                     _logger.warning(f"Could not parse paid_at date: {paid_at_str}")
    #                                     paid_datetime = fields.Datetime.now()
    #                             # ❌ Payment declined
    #                             audit.write({
    #                                 'payment_received': 'no',
    #                                 'received_datetime': paid_datetime or fields.Datetime.now(),
    #                                 'status': 'failure',
    #                                 'payment_reference': current_merchant_invoice or audit.payment_reference
    #                             })
    #
    #                             _logger.warning(f"""
    #                                     ❌ PAYMENT DECLINED:
    #                                     - Audit ID: {audit.id}
    #                                     - Job Card: {audit.name}
    #                                     - Invoice: {current_invoice_no}
    #                                     - Paid at: {paid_at_str or 'N/A'}
    #                                     - Payment For: {audit.payment_for}
    #                                     """)
    #
    #                             updated_count += 1
    #
    #                 elif response.status_code == 404:
    #                     _logger.warning(f"Invoice not found: {current_invoice_no}")
    #                 else:
    #                     _logger.error(f"API error for invoice {current_invoice_no}: HTTP {response.status_code}")
    #
    #             except requests.exceptions.RequestException as e:
    #                 _logger.error(f"Connection error checking invoice {current_invoice_no}: {str(e)}")
    #             except Exception as e:
    #                 _logger.error(f"Error checking invoice {current_invoice_no}: {str(e)}")
    #
    #         _logger.info(f"Payment status check completed. Updated {updated_count} records.")
    #         return updated_count
    #
    #     except Exception as e:
    #         _logger.error(f"Error in payment status check: {str(e)}")
    #         return False
    #
    # def schedule_payment_status_check(self):
    #     """Method to be called by scheduled action for automatic payment status checking"""
    #     try:
    #         Task = self.env['project.task']
    #         updated_count = Task.check_hyperbill_payment_status()
    #         _logger.info(f"Scheduled payment check completed. Updated {updated_count} records.")
    #         return True
    #     except Exception as e:
    #         _logger.error(f"Scheduled payment check failed: {str(e)}")
    #         return False

    def check_hyperbill_payment_status(self, specific_invoice_no=None):
        """Check payment status for Hyperbill invoices"""
        try:
            
            ''' commented on Jan 09-2026 by Vijaya Bhaskar due to hyper pay bill is added on work center group
            config = self.env['ir.config_parameter'].sudo()
            token = config.get_param('hyperbill_payments.hyperpay_token')
            # base_url = "https://hyperbill-sandbox.hyperpay.com"
            base_url = self.env['ir.config_parameter'].sudo().get_param('hyperbill_payments.hyperpay_url')
            '''

          
            # Build domain for search
            domain = [('payment_received', '=', 'no')]
            domain += [('status', '!=', 'failure')]
            domain += [('payment_for', '=', 'inspection')]

            if specific_invoice_no:
                # Check specific invoice only
                # domain.append(('invoice_no', '=', specific_invoice_no))
                domain.append(('payment_reference', '=', specific_invoice_no))
                _logger.info(f"Checking specific invoice: {specific_invoice_no}")
            else:
                # Check all pending invoices
                # domain.append(('invoice_no', '!=', False))
                domain.append(('payment_reference', '!=', False))
                _logger.info("Checking all pending invoices")

            pending_audits = self.env['hyperpay.audit'].search(domain)

            # headers = {
            #     'Content-Type': 'application/json',
            #     # 'Authorization': f'Bearer {token}'
            # }

            updated_count = 0

            for audit in pending_audits:
                try:
                    
                    # Use the CURRENT invoice_no from audit record
                    # current_invoice_no = audit.invoice_no
                    current_invoice_no = audit.payment_reference
                    if not current_invoice_no:
                        continue
                    work_center = audit.jobcard_id.work_center_group_id
                    token = work_center.hyperpay_token
                    base_url = work_center.hyperpay_url
    
                    # Safety check
                    if not token or not base_url:
                        _logger.warning(
                            f"⚠️ Skipping Audit ID {audit.id}: Missing Hyperpay token or URL"
                        )
                        continue
    
                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {token}',
                    }


                    # Make API call to check CURRENT invoice status
                    api_url = f"{base_url}/api/simpleInvoice/retrieve/min/{current_invoice_no}"
                    _logger.info(f"🔍 Checking payment status for current invoice: {current_invoice_no}")

                    response = requests.get(api_url, headers=headers, timeout=30)

                    if response.status_code == 200:
                        response_data = response.json()

                        if response_data.get('status'):
                            data = response_data['data']
                            invoice_status = data.get('status', '').lower()
                            current_merchant_invoice = data.get('merchant_invoice_number', '')

                            _logger.info(f"📊 Invoice {current_invoice_no} status: {invoice_status}")

                            if invoice_status == 'paid':
                                # Update with CURRENT payment data
                                paid_at_str = data.get('paid_at')
                                paid_datetime = False

                                if paid_at_str:
                                    try:
                                        paid_datetime = datetime.strptime(paid_at_str, '%Y-%m-%d %H:%M:%S')
                                    except ValueError:
                                        _logger.warning(f"Could not parse paid_at date: {paid_at_str}")
                                        paid_datetime = fields.Datetime.now()

                                # Update audit record with current payment info
                                audit.write({
                                    'payment_received': 'yes',
                                    'received_datetime': paid_datetime or fields.Datetime.now(),
                                    'status': 'success',
                                    'payment_reference': current_merchant_invoice or audit.payment_reference
                                })
                                audit.jobcard_id.payment_button_hide = True

                                # Log the successful update
                                _logger.info(f"""
                                ✅ PAYMENT CONFIRMED:
                                - Audit ID: {audit.id}
                                - Job Card: {audit.name}
                                - Invoice: {current_invoice_no}
                                - Amount: {data.get('amount', 'N/A')} {data.get('currency', 'SAR')}
                                - Paid at: {paid_at_str}
                                - Payment For: {audit.payment_for}
                                """)

                                updated_count += 1

                            elif invoice_status == 'declined':
                                paid_at_str = data.get('paid_at')
                                paid_datetime = False

                                if paid_at_str:
                                    try:
                                        paid_datetime = datetime.strptime(paid_at_str, '%Y-%m-%d %H:%M:%S')
                                    except ValueError:
                                        _logger.warning(f"Could not parse paid_at date: {paid_at_str}")
                                        paid_datetime = fields.Datetime.now()
                                # ❌ Payment declined
                                audit.write({
                                    'payment_received': 'no',
                                    'received_datetime': paid_datetime or fields.Datetime.now(),
                                    'status': 'failure',
                                    'payment_reference': current_merchant_invoice or audit.payment_reference
                                })

                                _logger.warning(f"""
                                        ❌ PAYMENT DECLINED:
                                        - Audit ID: {audit.id}
                                        - Job Card: {audit.name}
                                        - Invoice: {current_invoice_no}
                                        - Paid at: {paid_at_str or 'N/A'}
                                        - Payment For: {audit.payment_for}
                                        """)

                                updated_count += 1

                    elif response.status_code == 404:
                        _logger.warning(f"Invoice not found: {current_invoice_no}")
                    else:
                        _logger.error(f"API error for invoice {current_invoice_no}: HTTP {response.status_code}")

                except requests.exceptions.RequestException as e:
                    _logger.error(f"Connection error checking invoice {current_invoice_no}: {str(e)}")
                except Exception as e:
                    _logger.error(f"Error checking invoice {current_invoice_no}: {str(e)}")

            _logger.info(f"Payment status check completed. Updated {updated_count} records.")
            return updated_count

        except Exception as e:
            _logger.error(f"Error in payment status check: {str(e)}")
            return False

    def check_hyperbill_final_payment_status(self, specific_invoice_no=None):
        """Check payment status for Hyperbill invoices"""
        try:
            
            ''' commented on Jan 09-2026 by Vijaya Bhaskar due to hyper pay bill is added on work center group
            config = self.env['ir.config_parameter'].sudo()
            token = config.get_param('hyperbill_payments.hyperpay_token')
            # base_url = "https://hyperbill-sandbox.hyperpay.com"
            base_url = self.env['ir.config_parameter'].sudo().get_param('hyperbill_payments.hyperpay_url')
            '''
            
            # token = self.work_center_group_id.hyperpay_token
            #
            # base_url = self.work_center_group_id.hyperpay_url
            #
            #
            # if not token:
            #     _logger.error("Hyperbill API token is not configured in Work Center group.")
            #     return False

            # Build domain for search
            domain = [('payment_received', '=', 'no')]
            domain += [('status', '!=', 'failure')]
            domain += [('payment_for', '=', 'final')]

            if specific_invoice_no:
                # Check specific invoice only
                # domain.append(('invoice_no', '=', specific_invoice_no))
                domain.append(('payment_reference', '=', specific_invoice_no))
                _logger.info(f"Checking specific invoice: {specific_invoice_no}")
            else:
                # Check all pending invoices
                # domain.append(('invoice_no', '!=', False))
                domain.append(('payment_reference', '!=', False))
                _logger.info("Checking all pending invoices")

            pending_audits = self.env['hyperpay.audit'].search(domain)

            # headers = {
            #     'Content-Type': 'application/json',
            #     'Authorization': f'Bearer {token}'
            # }

            updated_count = 0

            for audit in pending_audits:
                try:
                    # Use the CURRENT invoice_no from audit record
                    # current_invoice_no = audit.invoice_no
                    current_invoice_no = audit.payment_reference
                    if not current_invoice_no:
                        continue
                    
                    work_center = audit.jobcard_id.work_center_group_id
                    token = work_center.hyperpay_token
                    base_url = work_center.hyperpay_url
    
                    # Safety check
                    if not token or not base_url:
                        _logger.warning(
                            f"⚠️ Skipping Audit ID {audit.id}: Missing Hyperpay token or URL"
                        )
                        continue
    
                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {token}',
                    }


                    # Make API call to check CURRENT invoice status
                    api_url = f"{base_url}/api/simpleInvoice/retrieve/min/{current_invoice_no}"
                    _logger.info(f"🔍 Checking payment status for current invoice: {current_invoice_no}")

                    response = requests.get(api_url, headers=headers, timeout=30)

                    if response.status_code == 200:
                        response_data = response.json()

                        if response_data.get('status'):
                            data = response_data['data']
                            invoice_status = data.get('status', '').lower()
                            current_merchant_invoice = data.get('merchant_invoice_number', '')

                            _logger.info(f"📊 Invoice {current_invoice_no} status: {invoice_status}")

                            if invoice_status == 'paid':
                                # Update with CURRENT payment data
                                paid_at_str = data.get('paid_at')
                                paid_datetime = False

                                if paid_at_str:
                                    try:
                                        paid_datetime = datetime.strptime(paid_at_str, '%Y-%m-%d %H:%M:%S')
                                    except ValueError:
                                        _logger.warning(f"Could not parse paid_at date: {paid_at_str}")
                                        paid_datetime = fields.Datetime.now()

                                # Update audit record with current payment info
                                audit.write({
                                    'payment_received': 'yes',
                                    'received_datetime': paid_datetime or fields.Datetime.now(),
                                    'status': 'success',
                                    'payment_reference': current_merchant_invoice or audit.payment_reference
                                })
                                
                                audit.jobcard_id.write({
                                    'payment_final_button_hide': True,
                                    'balance_received': abs(audit.jobcard_id.grand_total - audit.jobcard_id.final_inspection_charges_amount)
                                    # 'balance_received': float(data.get('amount', 0.0)),
                                })
                                
                                # audit.jobcard_id.payment_final_button_hide = True
                                # audit.jobcard_id.balance_received = float(data.get('amount', 0.0))
                                # audit.jobcard_id.balance_received =  audit.jobcard_id.balance_paid

                                # Log the successful update
                                _logger.info(f"""
                                ✅ PAYMENT CONFIRMED:
                                - Audit ID: {audit.id}
                                - Job Card: {audit.name}
                                - Invoice: {current_invoice_no}
                                - Amount: {data.get('amount', 'N/A')} {data.get('currency', 'SAR')}
                                - Paid at: {paid_at_str}
                                - Payment For: {audit.payment_for}
                                """)

                                updated_count += 1

                            elif invoice_status == 'declined':
                                paid_at_str = data.get('paid_at')
                                paid_datetime = False

                                if paid_at_str:
                                    try:
                                        paid_datetime = datetime.strptime(paid_at_str, '%Y-%m-%d %H:%M:%S')
                                    except ValueError:
                                        _logger.warning(f"Could not parse paid_at date: {paid_at_str}")
                                        paid_datetime = fields.Datetime.now()
                                # ❌ Payment declined
                                audit.write({
                                    'payment_received': 'no',
                                    'received_datetime': paid_datetime or fields.Datetime.now(),
                                    'status': 'failure',
                                    'payment_reference': current_merchant_invoice or audit.payment_reference
                                })

                                _logger.warning(f"""
                                        ❌ PAYMENT DECLINED:
                                        - Audit ID: {audit.id}
                                        - Job Card: {audit.name}
                                        - Invoice: {current_invoice_no}
                                        - Paid at: {paid_at_str or 'N/A'}
                                        - Payment For: {audit.payment_for}
                                        """)

                                updated_count += 1

                    elif response.status_code == 404:
                        _logger.warning(f"Invoice not found: {current_invoice_no}")
                    else:
                        _logger.error(f"API error for invoice {current_invoice_no}: HTTP {response.status_code}")

                except requests.exceptions.RequestException as e:
                    _logger.error(f"Connection error checking invoice {current_invoice_no}: {str(e)}")
                except Exception as e:
                    _logger.error(f"Error checking invoice {current_invoice_no}: {str(e)}")

            _logger.info(f"Payment status check completed. Updated {updated_count} records.")
            return updated_count

        except Exception as e:
            _logger.error(f"Error in payment status check: {str(e)}")
            return False


    def schedule_payment_status_check(self):
        """Method to be called by scheduled action for automatic payment status checking"""
        try:
            Task = self.env['project.task']
            count1 = Task.check_hyperbill_payment_status()
            count2 = Task.check_hyperbill_final_payment_status()
            _logger.info(f"Scheduled payment check completed. Updated {count1 + count2} records.")
            return True
        except Exception as e:
            _logger.error(f"Scheduled payment check failed: {str(e)}")
            return False

    def action_check_payment_status(self):
        """Manual payment status check for current task"""
        self.ensure_one()

        try:
            # Find audit records for CURRENT task
            audit_records = self.env['hyperpay.audit'].search([
                ('jobcard_id', '=', self.id),  # Current task ID
                ('payment_received', '=', 'no')
            ])

            if not audit_records:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'No Pending Payments',
                        'message': 'No pending payments found for this job card.',
                        'type': 'info',
                        'sticky': False,
                    }
                }

            # Check status for all invoices of current task
            # invoice_list = [audit.invoice_no for audit in audit_records if audit.invoice_no]
            invoice_list = [audit.payment_reference for audit in audit_records if audit.payment_reference]
            _logger.info(f"Checking payment status for invoices: {invoice_list}")

            updated_count = self.check_hyperbill_payment_status()

            if updated_count > 0:
                message = f"Payment status checked. {updated_count} payments confirmed for current task."
                message_type = 'success'
            else:
                pending_count = len(audit_records)
                message = f"Payment status checked. {pending_count} payments still pending for current task."
                message_type = 'info'

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Payment Status Check',
                    'message': message,
                    'type': message_type,
                    'sticky': False,
                }
            }

        except Exception as e:
            _logger.error(f"Error checking payment status for current task {self.name}: {str(e)}")
            raise UserError(f"Failed to check payment status: {str(e)}")
        
        
        
        
        