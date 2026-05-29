from odoo import models, fields, api


class ResConfSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    hyperpay_url = fields.Char(string="URL")
    hyperpay_email = fields.Char(string="Email")
    hyperpay_password = fields.Char(string="Password")
    hyperpay_environment = fields.Selection([("production", "Production"), ("sandbox", "Sandbox")], string="Type")

    def set_values(self):
        super().set_values()
        config = self.env['ir.config_parameter'].sudo()
        config.set_param('hyperpay_settings.hyperpay_url', self.hyperpay_url or '')
        config.set_param('hyperpay_settings.hyperpay_email', self.hyperpay_email or '')
        config.set_param('hyperpay_settings.hyperpay_password', self.hyperpay_password or '')
        config.set_param('hyperpay_settings.hyperpay_environment', self.hyperpay_environment or '')

    @api.model
    def get_values(self):
        res = super(ResConfSettings, self).get_values()
        config = self.env['ir.config_parameter'].sudo()
        res.update(
            hyperpay_url=config.get_param('hyperpay_settings.hyperpay_url', default=''),
            hyperpay_email=config.get_param('hyperpay_settings.hyperpay_email', default=''),
            hyperpay_password=config.get_param('hyperpay_settings.hyperpay_password', default=''),
            hyperpay_environment=config.get_param('hyperpay_settings.hyperpay_environment', default=''),
        )
        return res