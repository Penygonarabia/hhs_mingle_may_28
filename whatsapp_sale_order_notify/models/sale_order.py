from odoo import models, api,fields,_
import requests
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    whatsapp_button_click_bool = fields.Boolean(string = "Whatsapp Click" , default = False)
    
    rejection_reason = fields.Char(string="Rejection Reason", tracking=True)
    
    def send_whatsapp_message(self):
        
        self._send_whatsapp_pdf()
        self.write({'state':'sent'})
        self.whatsapp_button_click_bool = True
        # self.action_confirm()
        # self.action_quotation_sent()
    
    def _send_whatsapp_pdf(self):
        
        _logger.info("✅ WhatsApp PDF send triggered for order %s", self.name)

        phone_number = self.task_id.phone
        
        whatsapp_opt_in = self.task_id.whatsapp_opt_in
        
        if not whatsapp_opt_in:
            
            _logger.info("❌ No Whatsapp Opt for partner %s check in", self.partner_id.name)
            return

            
        if not phone_number:
            _logger.info("❌ No mobile number found for partner %s", self.partner_id.name)
            return

        phone_number = phone_number.replace('+', '').replace(' ', '')

        try:
            
            pdf_content, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
                'machine_repair_management.custom_report_saleorder_hhs', [self.id]
            )
            # pdf_content, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
            #     'sale.action_report_saleorder', [self.id]
            # )
            _logger.info("✅ PDF generated for order %s", self.name)
        except Exception as e:
            _logger.error("❌ Error rendering PDF for order %s: %s", self.name, str(e))
            return

        file_name = f'{self.name}.pdf'

        # Upload to WhatsApp (Meta)
        media_id = self._upload_pdf_to_meta(pdf_content, file_name)
        if not media_id:
            _logger.error("❌ Failed to upload PDF for order %s", self.name)
            return

        # Send via WhatsApp
        self._send_pdf_via_whatsapp(phone_number, media_id, file_name)

    def _upload_pdf_to_meta(self, pdf_content, file_name):
        
        access_token = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')}"
        
        whatsapp_phone_number_id = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')}"
        
        url = f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}/media"
        
        # url = 'https://graph.facebook.com/v18.0/629139543620025/media'
       
        headers = {
            'Authorization': f'Bearer {access_token}',
        }

        files = {
            'file': (file_name, pdf_content, 'application/pdf'),
            'type': (None, 'document'),
            'messaging_product': (None, 'whatsapp'),
        }

        try:
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            media_id = response.json().get('id')
            _logger.info("✅ Uploaded PDF to WhatsApp. Media ID: %s", media_id)
            return media_id
        except requests.exceptions.RequestException as e:
            _logger.error("❌ Media upload failed: %s", str(e))
            return None


        
    def _send_pdf_via_whatsapp(self, phone_number, media_id, file_name):
        """Send PDF document via WhatsApp with response buttons"""
        # url = 'https://graph.facebook.com/v18.0/629139543620025/messages'
       
        access_token = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')}"
        
        whatsapp_phone_number_id = f"{self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')}"
        
        url = f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
      
        # New one to add Jun 17 2025 for Welcome Message before whatsapp
       

        # 1. Send the PDF document
        doc_payload = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': phone_number,
            'type': 'document',
            'document': {
                'id': media_id,
                'filename': file_name,
                'caption': f'Quotation {self.name}'
            }
        }

        try:
            response = requests.post(url, headers=headers, json=doc_payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.error("Document send error: %s", str(e))
            return False

        # 2. Send interactive buttons
        button_payload = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': phone_number,
            'type': 'interactive',
            'interactive': {
                'type': 'button',
                'body': {
                    'text': f'Please review Quotation {self.name} and choose an action below. Click Accept to approve or Reject if changes are needed'
                },
                'action': {
                    'buttons': [
                        {
                            'type': 'reply',
                            'reply': {
                                'id': f'accept_{self.id}',
                                'title': '✅ Accept'
                            }
                        },
                        {
                            'type': 'reply',
                            'reply': {
                                'id': f'reject_{self.id}',
                                'title': '❌ Reject'
                            }
                        }
                    ]
                }
            }
        }

        try:
            response = requests.post(url, headers=headers, json=button_payload)
            response.raise_for_status()
            self.message_post(body=_("WhatsApp message with quotation sent successfully"))
            return True
        except requests.exceptions.RequestException as e:
            _logger.error("Buttons send error: %s", str(e))
            return False    
    
  
        
    def process_whatsapp_response(self, response):
        """ Process incoming WhatsApp response """
        self.ensure_one()
        
        if response == 'accepted':
            self.message_post(body=_("Customer accepted via WhatsApp"))
            self.action_confirm()
        elif response == 'rejected':
            self.message_post(body=_("Customer rejected via WhatsApp"))
            self.action_cancel()


