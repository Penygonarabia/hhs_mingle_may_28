from odoo import models, fields, api
from odoo.exceptions import UserError
import requests
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class ResConfSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hyperpay_url = fields.Char(string="URL")
    hyperpay_email = fields.Char(string="Email")
    hyperpay_password = fields.Char(string="Password")
    hyperpay_environment = fields.Selection([("production", "Production"), ("sandbox", "Sandbox")], string="Type")
    hyperpay_token = fields.Char('API Token')
    hyperpay_date_expires = fields.Datetime('Token Expires')

    @api.onchange('hyperpay_environment')
    def _onchange_hyperpay_environment(self):
        """Automatically update URL based on selected environment"""
        if self.hyperpay_environment == "sandbox":
            self.hyperpay_url = "https://hyperbill-sandbox.hyperpay.com"
        elif self.hyperpay_environment == "production":
            self.hyperpay_url = "https://hyperbill.hyperpay.com"
        else:
            self.hyperpay_url = False

    def set_values(self):
        super().set_values()
        config = self.env['ir.config_parameter'].sudo()

        # Handle datetime properly - convert to string format without microseconds
        date_expires_str = ''
        if self.hyperpay_date_expires:
            # Remove microseconds and convert to string
            date_expires_str = self.hyperpay_date_expires.strftime('%Y-%m-%d %H:%M:%S')

        config.set_param('hyperbill_payments.hyperpay_url', self.hyperpay_url or '')
        config.set_param('hyperbill_payments.hyperpay_email', self.hyperpay_email or '')
        config.set_param('hyperbill_payments.hyperpay_password', self.hyperpay_password or '')
        config.set_param('hyperbill_payments.hyperpay_environment', self.hyperpay_environment or '')
        config.set_param('hyperbill_payments.hyperpay_token', self.hyperpay_token or '')
        config.set_param('hyperbill_payments.hyperpay_date_expires', date_expires_str)

    @api.model
    def get_values(self):
        res = super(ResConfSettings, self).get_values()
        config = self.env['ir.config_parameter'].sudo()

        # Get the date string and handle microseconds if present
        date_expires_str = config.get_param('hyperbill_payments.hyperpay_date_expires', default='')
        date_expires = False

        if date_expires_str:
            try:
                # Remove microseconds if present
                if '.' in date_expires_str:
                    date_expires_str = date_expires_str.split('.')[0]
                # Convert to datetime
                date_expires = fields.Datetime.from_string(date_expires_str)
            except Exception as e:
                _logger.error(f"Error parsing date: {e}")
                date_expires = False

        res.update({
            'hyperpay_url': config.get_param('hyperbill_payments.hyperpay_url', default=''),
            'hyperpay_email': config.get_param('hyperbill_payments.hyperpay_email', default=''),
            'hyperpay_password': config.get_param('hyperbill_payments.hyperpay_password', default=''),
            'hyperpay_environment': config.get_param('hyperbill_payments.hyperpay_environment', default='sandbox'),
            'hyperpay_token': config.get_param('hyperbill_payments.hyperpay_token', default=''),
            'hyperpay_date_expires': date_expires,
        })
        return res

    def action_generate_token(self):
        try:
            email = self.hyperpay_email
            password = self.hyperpay_password
            environment = self.hyperpay_environment

            if not email or not password:
                raise UserError("Please provide both Email and Password")

            base_url = self.env['ir.config_parameter'].sudo().get_param('hyperbill_payments.hyperpay_url')
            api_url = f"{base_url}/api/login"

            # api_url = "https://hyperbill-sandbox.hyperpay.com/api/login" if environment == "sandbox" else "https://hyperbill.hyperpay.com/api/login"

            payload = {"email": email, "password": password}
            headers = {'Content-Type': 'application/json'}

            response = requests.post(api_url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                response_data = response.json()
                token = response_data.get('data', {}).get('accessToken')
                expires_at_info = response_data.get('data', {}).get('expires_at', {})

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
                self.set_values()

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