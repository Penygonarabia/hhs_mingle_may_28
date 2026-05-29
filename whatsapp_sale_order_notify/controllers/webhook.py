from odoo import http
from odoo.http import request
import json
import logging
import requests

_logger = logging.getLogger(__name__)

class WhatsAppWebhookController(http.Controller):

    @http.route('/whatsapp/webhook', auth='public', type='json', csrf=False, methods=['POST'])
    def whatsapp_webhook(self):
        data = json.loads(request.httprequest.data)
        _logger.info("Webhook received: %s", data)

        try:
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    for message in messages:
                        msg_type = message.get("type")
                        phone_number = message.get("from")

                        if msg_type == "text":
                            user_text = message["text"]["body"].strip().lower()
                            if user_text in ["hi", "hello"]:
                                self.send_service_buttons(phone_number)

                        # elif msg_type == "button":
                        elif msg_type == "interactive":
                            interactive = message.get("interactive", {})
                            if interactive.get("type") == "button_reply":
                                button_id = interactive.get("button_reply", {}).get("id")
                                _logger.info("📲 WhatsApp button clicked: %s", button_id)
                         
                                if button_id == "service_request":
                                    self._send_text(
                                        phone_number,
                                        "🔧 Click below to submit a service request:\n👉 https://hhsv2.cieloapps.com"
                                    )
                                elif button_id == "service_status":
                                    self._send_text(
                                        phone_number,
                                        "📦 Check your service status here:\n👉 https://hhsv2.cieloapps.com"
                                    )
                                else:
                                    '''this is for accept the reject the quotation via whatsapp'''
                                    self._handle_interactive_response(message)
        # @api.onchange('product_arabic_name')
    # def _onchange_product_arabic_name(self):
    #     for rec in self:
    #         if rec.product_arabic_name:
    #             rec.product_variant_id.product_arabic_name = rec.product_arabic_name
                                    
                            # button_id = message["button"]["payload"]
                            # # Handle button clicks
                            # if button_id == "service_request":                            self._handle_interactive_response(message)

                            #
                            #
                            #     self._send_text(
                            #         phone_number,
                            #         "You can access the service request page here: https://hhsv2.cieloapps.com"
                            #     )
                            # elif button_id == "service_status":
                            #     self._send_text(
                            #         phone_number,
                            #         "You can check your service status here: https://hhsv2.cieloapps.com"
                            #     )
                            elif button_id.startswith("reject_order_"):
                                order_name = button_id.replace("reject_order_", "")
                                self.cancel_order_by_name(order_name, phone_number)
 
                            elif button_id.startswith("confirm_order_"):
                                order_name = button_id.replace("confirm_order_", "")
                                self.confirm_order_by_name(order_name, phone_number)    
                                
                            elif button_id == "accept_quotation":
                                self._handle_quotation_response(phone_number, accept=True)
                            elif button_id == "reject_quotation":
                                self._handle_quotation_response(phone_number, accept=False) 
                                
                                
                        # # elif msg_type == 'interactive':
                        #     self._handle_interactive_response(message)
                        #

                
            
            return {'status': 'success'}, 200
                                       
        except Exception as e:
            _logger.error("Error in WhatsApp Webhook: %s", str(e))

        return "EVENT_RECEIVED"

    @http.route('/whatsapp/webhook', auth='public', methods=['GET'], csrf=False, type='http')
    def whatsapp_webhook_verify(self, **kwargs):
        mode = kwargs.get("hub.mode")
        token = kwargs.get("hub.verify_token")
        challenge = kwargs.get("hub.challenge")

        whatsapp_verify_token = request.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_verify_token')
        VERIFY_TOKEN = f"{whatsapp_verify_token}"
        # VERIFY_TOKEN = "odoo_whatsapp_123"

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return request.make_response(challenge, [('Content-Type', 'text/plain')])
        else:
            return request.make_response("Verification failed", status=403)

    def send_service_buttons(self, to_number):
        # Hardcoded URL and Access Token
        # access_token = "EAAPm1DIjp9ABO55WDpnbwBBrOgDNcjxZBRdmWUoMDEams0ZABkkQI6MpZASjZB6hyTS4JqPtQxqK5HU5iCYSV6RRLNUleCwLf36eexhtxlPZCe0tEWA1eXfV4zJpwJ0teAyq3n3dgI285ZAgQsYXpdPsRa5GrdE9ASvU33QqUC7SOUULodJ5PhbxBMwZCxjWt6Q"
        access_token = f"{request.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')}"
        # whatsapp_phone_number_id = request.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')
        whatsapp_phone_number_id = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')}"

        url = f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}/messages"        
        # url = "https://graph.facebook.com/v18.0/629139543620025/messages"


        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": "Welcome! What would you like to do?"
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": "service_request",
                                "title": "Service Request"
                            }
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": "service_status",
                                "title": "Service Status"
                            }
                        }
                    ]
                }
            }
        }

        response = requests.post(url, headers=headers, json=payload)
        _logger.info("Service buttons sent. Response: %s", response.text)

    def send_order_status(self, to_number):
        partner = request.env["res.partner"].sudo().search([("mobile", "like", to_number)], limit=1)
        if not partner:
            self._send_text(to_number, "Sorry, we couldn't find your record.")
            return

        order = request.env["sale.order"].sudo().search([("partner_id", "=", partner.id)], order="id desc", limit=1)
        if order:
            status_msg = f"Your latest order ({order.name}) is currently: {order.state.capitalize()}"
        else:
            status_msg = "You don't have any orders yet."

        self._send_text(to_number, status_msg)
        
    def cancel_order_by_name(self, order_name, to_number):
        order = request.env["sale.order"].sudo().search([("name", "=", order_name)], limit=1)
        if not order:
            self._send_text(to_number, f"Order {order_name} not found.")
            return
 
        if order.state != "cancel":
            order.action_cancel()
            self._send_text(to_number, f"Order {order_name} has been cancelled.")
        else:
            self._send_text(to_number, f"Order {order_name} is already cancelled.")
 
    def confirm_order_by_name(self, order_name, to_number):
        order = request.env["sale.order"].sudo().search([("name", "=", order_name)], limit=1)
        if not order:
            self._send_text(to_number, f"Order {order_name} not found.")
            return
 
        if order.state == "draft":
            order.action_confirm()
            self._send_text(to_number, f"Order {order_name} has been confirmed.")
        else:
            self._send_text(to_number, f"Order {order_name} cannot be confirmed from its current state.")    

    def _send_text(self, to_number, message):
        # Hardcoded URL and Access Token
        # access_token = "EAAPm1DIjp9ABO55WDpnbwBBrOgDNcjxZBRdmWUoMDEams0ZABkkQI6MpZASjZB6hyTS4JqPtQxqK5HU5iCYSV6RRLNUleCwLf36eexhtxlPZCe0tEWA1eXfV4zJpwJ0teAyq3n3dgI285ZAgQsYXpdPsRa5GrdE9ASvU33QqUC7SOUULodJ5PhbxBMwZCxjWt6Q"
        # access_token = self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')
        #
        # url = "https://graph.facebook.com/v18.0/629139543620025/messages"
        
        access_token = f"{request.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')}"
        
        whatsapp_phone_number_id = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')}"
        
        url = f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}/messages"

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {
                "body": message
            }
        }

        response = requests.post(url, headers=headers, json=payload)
        _logger.info("Text message sent. Response: %s", response.text)
        
        
        
    def _send_quotation_buttons(self, to_number, order_name):
        # access_token = "EAAPm1DIjp9ABO6Ne7ZA4gKjOUrdGHLrap7qxsJh2gv1Cq9AOCQ0voop41Bj0aZBaWjJWXOyWRVEjdkZCDCFYlOnuHkCMwmliEknJg70ZCBev2qX1eUstyXUXU6sWzZCTEMjxEDMOBMFKOSYjUXCjoKlufM9hWs9TraiHZBvbRZC4Eo3P7gjrH2WdCsipdGfeothBdSI2gIEC4HOL7DaQPk29A3iQSD8wlMZD"
        # access_token = "EAAPm1DIjp9ABO55WDpnbwBBrOgDNcjxZBRdmWUoMDEams0ZABkkQI6MpZASjZB6hyTS4JqPtQxqK5HU5iCYSV6RRLNUleCwLf36eexhtxlPZCe0tEWA1eXfV4zJpwJ0teAyq3n3dgI285ZAgQsYXpdPsRa5GrdE9ASvU33QqUC7SOUULodJ5PhbxBMwZCxjWt6Q"
        #
        # url = "https://graph.facebook.com/v18.0/629139543620025/messages"
        
        access_token = f"{request.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')}"
        
        whatsapp_phone_number_id = f"{request.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')}"
        
        url = f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}/messages"

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": f"Please review your quotation {order_name}. Would you like to accept or reject it?"
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": "accept_quotation",
                                "title": "Accept"
                            }
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": "reject_quotation",
                                "title": "Reject"
                            }
                        }
                    ]
                }
            }
        }

        response = requests.post(url, headers=headers, json=payload)
        _logger.info("Quotation buttons sent for order %s. Response: %s", order_name, response.text)

    def _handle_quotation_response(self, phone_number, accept=True):
        partner = request.env["res.partner"].sudo().search([("mobile", "like", phone_number)], limit=1)
        if not partner:
            self._send_text(phone_number, "Sorry, we couldn't find your record.")
            return
        # First, try to find a draft quotation
        order = request.env["sale.order"].sudo().search(
            [("partner_id", "=", partner.id), ("state", "=", "draft")],
            order="id desc",
            limit=1
        )

        # If no draft quotation found and rejecting, check for a sale order in "sale" state
        if not order and not accept:
            order = request.env["sale.order"].sudo().search(
                [("partner_id", "=", partner.id), ("state", "=", "sale")],
                order="id desc",
                limit=1
            )

        if not order:
            self._send_text(phone_number, "No pending or confirmed quotations found.")
            return

        # Check if the order is already canceled
        if order.state == "cancel":
            self._send_text(phone_number, f"Quotation {order.name} has already been canceled.")
            return

        if accept:
            if order.state == "draft":
                order.action_confirm()
                self._send_text(phone_number, f"Quotation {order.name} has been accepted and confirmed as a sale order.")
            else:
                self._send_text(phone_number, f"Quotation {order.name} is already confirmed (current state: {order.state.capitalize()}).")
        else:
            if order.state in ["draft", "sale"]:
                order.action_cancel()
                self._send_text(phone_number, f"Quotation {order.name} has been rejected and canceled.")
            else:
                self._send_text(phone_number, f"Quotation {order.name} cannot be canceled (current state: {order.state.capitalize()}).")
  
  
    
    def _handle_interactive_response(self, message):
        """Process button replies with interactive rejection reasons"""
        interactive = message.get('interactive', {})
        if interactive.get('type') != 'button_reply':
            return
        button_reply = interactive.get('button_reply', {})
        button_id = button_reply.get('id', '')

        from_number = message.get('from')
        if not button_id.startswith(('accept_', 'reject_')):
            return
    
        ### currently working on sale.order commented by Vijaya bhaskr on July 14 2025 because they want without partner_id.so we create the service.sale.order
        # try:
        #     if button_id.startswith('reject_'):
        #         parts = button_id.split('_')
        #         if len(parts) == 2:  # Initial reject (reject_96)
        #             _, order_id = parts
        #             order = request.env['sale.order'].sudo().browse(int(order_id))
        #             if not order.exists():
        #                 _logger.error("Order %s not found", order_id)
        #                 return
        #
        #
        #
        #             # First cancel the order
        #             order_lines = order.order_line.sudo()
        #             invoices = order.invoice_ids.sudo()
        #             pickings = order.picking_ids.sudo()
        #
        #              # Cancel draft invoices
        #             for invoice in invoices:
        #                 if invoice.state == 'draft':
        #                     invoice.button_cancel()
        #
        #              # Cancel deliveries
        #             for picking in pickings:
        #                 if picking.state not in ('cancel', 'done'):
        #                     picking.action_cancel()
        #
        #              # Temporarily assign order.order_line = sudoed lines
        #             order.order_line = order_lines
        #
        #              # Cancel the order
        #             order.action_cancel()
        #
        #             request.env.cr.commit()
        #             # self._send_rejection_reasons(from_number, order_id)
        #             whatsapp_reject_message = request.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_reject_message')
        #
        #             if whatsapp_reject_message:
        #                 self._send_whatsapp_reply(message.get('from'),f"❌ {whatsapp_reject_message}")
        #             else:
        #                 self._send_whatsapp_reply(message.get('from'),f"❌ We are sorry.Kindly provide your reason for rejecting the quotation {order.name}.")
        #             self._send_rejection_buttons(from_number, order_id)
        #
        #             return
        #
        #         elif len(parts) == 4:  # Reason selected (reject_96_reason_price)
        #             _, order_id, _, reason_key = parts
        #             order = request.env['sale.order'].sudo().browse(int(order_id))
        #             if not order.exists():
        #                 _logger.error("Order %s not found", order_id)
        #                 return
        #
        #             # Update reject reason in sale order
        #             reason_map = {
        #                 'price': 'Price too high',
        #                 'delivery': 'Delivery time too long',
        #                 'other': 'Other reason'
        #             }
        #             reason = reason_map.get(reason_key, 'Unknown')
        #
        #             # Update the reject_reason field if it exists
        #             if 'rejection_reason' in order._fields:
        #                 order.write({'rejection_reason': reason})
        #
        #             # Also store in chatter
        #             order.message_post(body=f"Rejection reason: {reason}")
        #
        #             self._send_whatsapp_reply(
        #                 from_number,
        #                 f"❌ Order {order.name} cancelled\nReason: {reason}"
        #             )
        #             return
        #
        #     # Handle accept case
        #     action, order_id = button_id.split('_', 1)
        #     order = request.env['sale.order'].sudo().browse(int(order_id))
        #     whatsapp_accept_message = request.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_accept_message')
        #     if action == 'accept':
        #         order.action_confirm()
        #         if whatsapp_accept_message:
        #             self._send_whatsapp_reply(message.get('from'),f"✅ {whatsapp_accept_message}")
        #         else:    
        #             self._send_whatsapp_reply(message.get('from'),f"✅Thank you for the confirmation of the quotation {order.name}. We will arrange to start the job as soon as possible.")
        #

        try:
            if button_id.startswith('reject_'):
                parts = button_id.split('_')
                if len(parts) == 2:  # Initial reject (reject_96)
                    _, order_id = parts
                    order = request.env['service.sale.order'].sudo().browse(int(order_id))
                    if not order.exists():
                        _logger.error("Order %s not found", order_id)
                        return
                    
                    
                    
                    # First cancel the order
                    order_lines = order.service_sale_order_line_ids.sudo()
                    # invoices = order.invoice_ids.sudo()
                    # pickings = order.picking_ids.sudo()
                    #
                    
                     # Cancel draft invoices
                    # for invoice in invoices:
                    #     if invoice.state == 'draft':
                    #         invoice.button_cancel()
                    #
                    #  # Cancel deliveries
                    # for picking in pickings:
                    #     if picking.state not in ('cancel', 'done'):
                    #         picking.action_cancel()
                    
                     # Temporarily assign order.order_line = sudoed lines
                    order.service_sale_order_line_ids = order_lines
        
                     # Cancel the order
                    order.action_cancel()
        
                    request.env.cr.commit()
                    # self._send_rejection_reasons(from_number, order_id)
                    whatsapp_reject_message = request.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_reject_message')
        
                    if whatsapp_reject_message:
                        self._send_whatsapp_reply(message.get('from'),f"❌ {whatsapp_reject_message}")
                    else:
                        self._send_whatsapp_reply(message.get('from'),f"❌ We are sorry.Kindly provide your reason for rejecting the quotation {order.name}.")
                    self._send_rejection_buttons(from_number, order_id)

                    return
                
                elif len(parts) == 4:  # Reason selected (reject_96_reason_price)
                    _, order_id, _, reason_key = parts
                    order = request.env['service.sale.order'].sudo().browse(int(order_id))
                    if not order.exists():
                        _logger.error("Order %s not found", order_id)
                        return
                    
                    # Update reject reason in sale order
                    reason_map = {
                        'price': 'Price too high',
                        'delivery': 'Delivery time too long',
                        'other': 'Other reason',
                        'slow' :'Slow delivery'
                    }
                    reason = reason_map.get(reason_key, 'Unknown')
                    
                    # Update the reject_reason field if it exists
                    if 'rejection_reason' in order._fields:
                        order.write({'rejection_reason': reason})
                    
                    # Also store in chatter
                    order.message_post(body=f"Rejection reason: {reason}")
                    
                    self._send_whatsapp_reply(
                        from_number,
                        f"❌ Order {order.name} cancelled\nReason: {reason}"
                    )
                    return
    
            # Handle accept case
            action, order_id = button_id.split('_', 1)
            order = request.env['service.sale.order'].sudo().browse(int(order_id))
            whatsapp_accept_message = request.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_accept_message')
            if action == 'accept':
                order.action_confirm()
                if whatsapp_accept_message:
                    self._send_whatsapp_reply(message.get('from'),f"✅ {whatsapp_accept_message}")
                else:    
                    self._send_whatsapp_reply(message.get('from'),f"✅Thank you for the confirmation of the quotation {order.name}. We will arrange to start the job as soon as possible.")
                    
    
        except Exception as e:
            _logger.error("Button processing failed: %s", str(e))
            self._send_whatsapp_reply(
                from_number,
                "⚠️ Error processing your request"
            )
    
    def _send_rejection_buttons(self, phone_number, order_id):
        """Send interactive buttons for rejection reasons"""
        try:
            whatsapp_config = request.env['ir.config_parameter'].sudo()
            phone_id = f"{whatsapp_config.get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')}"
            token = whatsapp_config.get_param('whatsapp_sale_order_notify.whatsapp_access_token')
            # url = "https://graph.facebook.com/v18.0/629139543620025/messages"

            url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
    
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": "Please help us improve by selecting a reason below:"
                    },
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {
                                    "id": f"reject_{order_id}_reason_price",
                                    "title": "Price too high"
                                }
                            },
                            {
                                "type": "reply",
                                "reply": {
                                    "id": f"reject_{order_id}_reason_delivery",
                                    "title": "Long delivery"
                                }
                            },
                            {
                                "type": "reply",
                                "reply": {
                                    "id": f"reject_{order_id}_reason_other",
                                    "title": "Other reason"
                                }
                            },
                            {
                                "type": "reply",
                                "reply": {
                                    "id": f"reject_{order_id}_reason_slow",
                                    "title": "Slow delivery"
                                }
                            },
                            
                        ]
                    }
                }
            }
    
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
        except Exception as e:
            _logger.error("Failed to send rejection buttons: %s", str(e))
            # Fallback to text message
            self._send_whatsapp_reply(
                phone_number,
                "Reply with:\n1. Price too high\n2. Slow delivery\n3. Other reason"
            )
    
        
        
    
    
  
    ''' this is correctly working commented by Vijaya bhaskar on June-09-2025 because when we reject button is clicked then three resaon button is shown after that we select the reason then only sale order is cancelled. 
    def _handle_interactive_response(self, message):
        """Process button replies"""
        interactive = message.get('interactive', {})
        if interactive.get('type') != 'button_reply':
            return

        button_reply = interactive.get('button_reply', {})
        button_id = button_reply.get('id', '')
        
        from_number = message.get('from')
        
        if not button_id.startswith(('accept_', 'reject_')):
            return

        try:
            
            if button_id.startswith('reject_'):
                parts = button_id.split('_')
                if len(parts) == 2:  # Initial reject (reject_96)
                    order_id = parts[1]
                    self._send_rejection_buttons(from_number, order_id)
                    return
                elif len(parts) == 4:  # Reason selected (reject_96_reason_price)
                    order_id = parts[1]  # Get the order ID part
                    order = request.env['sale.order'].sudo().browse(int(order_id))
                    if not order.exists():
                        _logger.error("Order %s not found", order_id)
                        return
                    self._process_rejection(from_number, order, button_id)
                    return
            
            action, order_id = button_id.split('_', 1)
            order = request.env['sale.order'].sudo().browse(int(order_id))
            
            if not order.exists():
                _logger.error("❌ Order %s not found", order_id)
                return
         
            _logger.info("Processing %s for order %s (state: %s)",
                         action, order.name, order.state)
         
            whatsapp_accept_message = request.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_accept_message')
            if action == 'accept':
                order.action_confirm()
                if whatsapp_accept_message:
                    self._send_whatsapp_reply(
                    message.get('from'),
                    f"✅ {whatsapp_accept_message}"
                    )
                else:    
                    self._send_whatsapp_reply(
                        message.get('from'),
                        f"✅Thank you for the confirmation of the quotation {order.name}. We will arrange to start the job as soon as possible."
                    )
                    
           
                            
            # elif action == 'reject':
            #     order = request.env['sale.order'].sudo().browse(int(order_id))
            #
            #     if order.state in ('draft', 'sent', 'sale'):
            #         try:
            #             # Force sudo on all related records
            #             order_lines = order.order_line.sudo()
            #             invoices = order.invoice_ids.sudo()
            #             pickings = order.picking_ids.sudo()
            #
            #             # Cancel draft invoices
            #             for invoice in invoices:
            #                 if invoice.state == 'draft':
            #                     invoice.button_cancel()
            #
            #             # Cancel deliveries
            #             for picking in pickings:
            #                 if picking.state not in ('cancel', 'done'):
            #                     picking.action_cancel()
            #
            #             # Temporarily assign order.order_line = sudoed lines
            #             order.order_line = order_lines
            #
            #             # Cancel the order
            #             order.action_cancel()
            #
            #             request.env.cr.commit()
            #             self._send_rejection_reasons(from_number, order_id)
            #             whatsapp_reject_message = request.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_reject_message')
            #
            #             if whatsapp_reject_message:
            #                 self._send_whatsapp_reply(
            #                     message.get('from'),
            #                     f"❌ {whatsapp_reject_message}"
            #                 )
            #             else:
            #                 self._send_whatsapp_reply(
            #                     message.get('from'),
            #                     f"❌ We are sorry.Kindly provide your reason for rejecting the quotation {order.name}."
            #                 )
            #
            #         except Exception as e:
            #             _logger.error("Cancel failed: %s", str(e))
            #             self._send_whatsapp_reply(
            #                 message.get('from'),
            #                 f"⚠️ Unable to cancel Order {order.name}: {str(e)}"
            #             )
            #     else:
            #         self._send_whatsapp_reply(
            #             message.get('from'),
            #             f"⚠️ Cannot cancel Order {order.name} in current state ({order.state})."
            #         )
        except Exception as e:
            _logger.error("❌ Button processing failed: %s", str(e))
            
    # def _send_rejection_reasons(self, phone_number, order_id):
    #     """Send simple text message with rejection reason options"""
    #     try:
    #         message = (
    #             "Please reply with the reason for rejecting:\n"
    #             "1. Price is too high\n"
    #             "2. Delivery time is too long\n"
    #             "3. Other reason"
    #         )
    #         self._send_whatsapp_reply(phone_number, message)
    #
    #     except Exception as e:
    #         _logger.error("Failed to send rejection reasons: %s", str(e))
    
    def _send_rejection_buttons(self, phone_number, order_id):
        """Send interactive message with rejection reason options"""
        try:
            whatsapp_phone_number_id = int(request.env['ir.config_parameter'].sudo().get_param(
                'whatsapp_sale_order_notify.whatsapp_phone_number_id'))
            access_token = f"{request.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')}"
    
            url = f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}/messages"
            # url = "https://graph.facebook.com/v18.0/629139543620025/messages"
    
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
    
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": "Please select reason for rejecting this order:"
                    },
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {
                                    "id": f"reject_{order_id}_reason_price",
                                    "title": "Price too high"
                                }
                            },
                            {
                                "type": "reply",
                                "reply": {
                                    "id": f"reject_{order_id}_reason_delivery",
                                    "title": "Slow delivery"
                                }
                            },
                            {
                                "type": "reply",
                                "reply": {
                                    "id": f"reject_{order_id}_reason_other",
                                    "title": "Other reason"
                                }
                            }
                        ]
                    }
                }
            }
    
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            _logger.info("Sent rejection buttons to %s", phone_number)
    
        except Exception as e:
            _logger.error("Failed to send rejection reasons: %s", str(e))
            self._send_whatsapp_reply(phone_number, "Reply with:\n1. Price too high\n2. Slow delivery\n3. Other reason")
    

    def _process_rejection(self, phone_number, order, button_id):
        """Cancel order and notify customer"""
        try:
            # Get rejection reason
            reason = {
                'price': 'Price is too high',
                'delivery': 'Delivery time is too long',
                'other': 'Other reasons'
            }.get(button_id.split('_')[-1], 'Unknown reason')
             
            order_name = request.env['sale.order'].sudo().browse(int(order))
            
            if order_name.state in ('draft', 'sent', 'sale'):
                try:
                    # Force sudo on all related records
                    order_lines = order_name.order_line.sudo()
                    invoices = order_name.invoice_ids.sudo()
                    pickings = order_name.picking_ids.sudo()
        
                    # Cancel draft invoices
                    for invoice in invoices:
                        if invoice.state == 'draft':
                            invoice.button_cancel()
        
                    # Cancel deliveries
                    for picking in pickings:
                        if picking.state not in ('cancel', 'done'):
                            picking.action_cancel()
        
                    # Temporarily assign order.order_line = sudoed lines
                    order_name.order_line = order_lines
        
                    # Cancel the order
                    order_name.action_cancel()
                    request.env.cr.commit()
                    # self._send_rejection_reasons(from_number, order_id)
                    order_name.message_post(body=f"WhatsApp Rejection Reason: {reason}")
                    
                    # order_name.write({
                    #     'rejection_reason': reason,  # Saves to the new field
                    #     # Optional: Mark as rejected in a status field
                    #     'state': 'cancel'  # If not already cancelled
                    # })
                    whatsapp_reject_message = request.env['ir.config_parameter'].sudo().get_param(
                        'whatsapp_sale_order_notify.whatsapp_reject_message')
        
                    if whatsapp_reject_message:
                        confirmation = f"❌ {whatsapp_reject_message}\nReason: {reason}"
                    else:
                        confirmation = (
                            f"❌ Quotation {order.name} has been cancelled.\n"
                            f"Reason: {reason}\n"
                            "Thank you for your feedback."
                        )
        
                    self._send_whatsapp_reply(phone_number, confirmation)
                    _logger.info("Cancelled order %s with reason: %s", order.name, reason)
                except Exception as e:
                    _logger.error("Cancel failed: %s", str(e))
                    self._send_whatsapp_reply(
                        phone_number,
                        f"⚠️ Unable to cancel Order {order.name}: {str(e)}"
                    )    
                        
        except Exception as e:
            _logger.error("Rejection failed: %s", str(e))
            self._send_whatsapp_reply(
                phone_number,
                f"⚠️ Failed to cancel order: {str(e)}"
            )'''
    # def _process_rejection_with_reason(self, phone_number, order, button_id):
    #     """Process order cancellation with selected rejection reason"""
    #     try:
    #         if not order.exists():
    #             _logger.error("Order %s no longer exists", order.id)
    #             self._send_whatsapp_reply(phone_number, "⚠️ Order no longer exists")
    #             return
    #
    #         # Extract reason from button_id (format: reject_123_reason_price)
    #         reason_key = button_id.split('_')[-1]
    #
    #         reason_mapping = {
    #             'price': 'Price is too high',
    #             'delivery': 'Delivery time is too long',
    #             'other': 'Other reasons'
    #         }
    #         reason = reason_mapping.get(reason_key, 'Unknown reason')
    #
    #         if order.state in ('draft', 'sent', 'sale'):
    #             # Cancel related records
    #             order_lines = order.order_line.sudo()
    #             invoices = order.invoice_ids.sudo()
    #             pickings = order.picking_ids.sudo()
    #
    #             for invoice in invoices:
    #                 if invoice.state == 'draft':
    #                     invoice.button_cancel()
    #
    #             for picking in pickings:
    #                 if picking.state not in ('cancel', 'done'):
    #                     picking.action_cancel()
    #
    #             order.order_line = order_lines
    #             order.action_cancel()
    #
    #             # Store rejection reason
    #             order.message_post(body=f"WhatsApp Rejection Reason: {reason}")
    #
    #             whatsapp_reject_message = request.env['ir.config_parameter'].sudo().get_param(
    #                 'whatsapp_sale_order_notify.whatsapp_reject_message')
    #
    #             if whatsapp_reject_message:
    #                 confirmation = f"❌ {whatsapp_reject_message}\nReason: {reason}"
    #             else:
    #                 confirmation = (
    #                     f"❌ Quotation {order.name} has been cancelled.\n"
    #                     f"Reason: {reason}\n"
    #                     "Thank you for your feedback."
    #                 )
    #
    #             self._send_whatsapp_reply(phone_number, confirmation)
    #             _logger.info("Cancelled order %s with reason: %s", order.name, reason)
    #         else:
    #             self._send_whatsapp_reply(
    #                 phone_number,
    #                 f"⚠️ Cannot cancel order {order.name} in current state ({order.state})"
    #             )
    #
    #     except Exception as e:
    #         _logger.error("❌ Rejection processing failed: %s", str(e))
    #         self._send_whatsapp_reply(
    #             phone_number,
    #             f"⚠️ Failed to process cancellation: {str(e)}"
    #         )
                
    def _send_whatsapp_reply(self, phone_number, message):
        """Send confirmation message"""
        url = 'https://graph.facebook.com/v18.0/629139543620025/messages'
        # access_token = "EAAPm1DIjp9ABO55WDpnbwBBrOgDNcjxZBRdmWUoMDEams0ZABkkQI6MpZASjZB6hyTS4JqPtQxqK5HU5iCYSV6RRLNUleCwLf36eexhtxlPZCe0tEWA1eXfV4zJpwJ0teAyq3n3dgI285ZAgQsYXpdPsRa5GrdE9ASvU33QqUC7SOUULodJ5PhbxBMwZCxjWt6Q"
        #
        access_token = f"{request.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')}"
        
        whatsapp_phone_number_id = request.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')
        
        # url = f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {"body": message}
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
        except Exception as e:
            _logger.error("❌ Confirmation message failed: %s", str(e))        

   