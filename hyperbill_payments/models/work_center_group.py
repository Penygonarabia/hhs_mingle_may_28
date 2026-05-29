from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class WorkCenterGroup(models.Model):
    
    _inherit = "work.center.group"
    
    
    hyperpay_url = fields.Char(string="Hyperpay API URL")
    hyperpay_email = fields.Char(string="Hyperpay Account Email")
    hyperpay_password = fields.Char(string="Hyperpay Account Password")
    hyperpay_environment = fields.Selection([("production", "Production"), ("sandbox", "Sandbox")], string="Environment")
    hyperpay_token = fields.Char('Hyperpay Authenticate API Token')
    hyperpay_date_expires = fields.Datetime('Token Expiration Date')
    custom_region = fields.Char(string = "Region")
    
    
    
    def action_generate_token(self):
        try:
            email = self.hyperpay_email
            password = self.hyperpay_password
            environment = self.hyperpay_environment

            if not email or not password:
                raise UserError("Please provide both Email and Password")

            # base_url = self.env['ir.config_parameter'].sudo().get_param('hyperbill_payments.hyperpay_url')
            base_url = self.hyperpay_url
            api_url = f"{base_url}/api/login"

            # api_url = "https://hyperbill-sandbox.hyperpay.com/api/login" if environment == "sandbox" else "https://hyperbill.hyperpay.com/api/login"

            payload = {"email": email, "password": password}
            headers = {'Content-Type': 'application/json'}

            response = requests.post(api_url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                response_data = response.json()
                if isinstance(response_data, list):
                    response_data = response_data[0]
            
                data = response_data.get('data')
                if not data:
                    raise UserError(f"Invalid API response: {response_data}")

                
                # token = response_data.get('data', {}).get('accessToken')
                # expires_at_info = response_data.get('data', {}).get('expires_at', {})
                token = data.get('accessToken')
                expires_at_info = data.get('expires_at', {})

                if not token:
                    raise UserError("Token not found in API response.")

                # Parse the expiration datetime string from API response
                expires_at_str = expires_at_info.get('date')
                if not expires_at_str:
                    raise UserError("Token expiration date not found in API response.")

                # Try parsing with microseconds
                try:
                    expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S.%f')
                    _logger.info(f"[Hyperbill] Parsed with microseconds: {expires_at}")
                except ValueError:
                    try:
                        # Try parsing without microseconds
                        expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S')
                        _logger.info(f"[Hyperbill] Parsed without microseconds: {expires_at}")
                    except ValueError as e:
                        _logger.error(f"[Hyperbill] Date parsing failed: {e}")
                        raise UserError(f"Invalid date format in API response: {expires_at_str}")

                # Store as naive datetime (Odoo will handle timezone conversion)
                expires_at_naive = expires_at.replace(tzinfo=None)

                # Save the token and expiration date
                self.hyperpay_token = token
                self.hyperpay_date_expires = expires_at_naive

                # Save and verify
                # self.set_values()

                # Log the saved token and date for confirmation
                _logger.info(f"[Hyperbill] Token generated and saved. Expires at: {expires_at_naive}")

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': f'Token generated successfully. Expires at: {expires_at_str} UTC',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                error_data = response.json()
                error_msg = error_data.get('message', f"HTTP {response.status_code}: {response.text}")
                raise UserError(f"API Error: {error_msg}")

        except requests.exceptions.RequestException as e:
            _logger.error(f"[Hyperbill] Request error: {str(e)}")
            raise UserError(f"Connection error: {str(e)}")

        except Exception as e:
            _logger.exception("[Hyperbill] Unexpected error during token generation")
            raise UserError(f"Failed to generate token: {str(e)}")