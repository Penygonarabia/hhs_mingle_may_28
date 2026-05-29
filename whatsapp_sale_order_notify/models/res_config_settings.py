from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    whatsapp_access_token = fields.Char(
        string="WhatsApp Access Token",
        help="Access token for WhatsApp Business API",
        config_parameter='whatsapp_sale_order_notify.whatsapp_access_token'
    )
    whatsapp_phone_number_id = fields.Char(
        string="WhatsApp Phone Number ID",
        help="Phone number ID for WhatsApp Business API",
        config_parameter='whatsapp_sale_order_notify.whatsapp_phone_number_id'
    )
    
    whatsapp_verify_token = fields.Char(
        string="WhatsApp Verify Token",
        help="Verify token for WhatsApp Business API",
        config_parameter='whatsapp_sale_order_notify.whatsapp_verify_token'
    )
    
    whatsapp_accept_message = fields.Char(
        string="WhatsApp Accept Message",
        help="Accept Message for WhatsApp Business API",
        config_parameter='whatsapp_sale_order_notify.whatsapp_accept_message'
    )
    
    whatsapp_reject_message = fields.Char(
        string="WhatsApp Reject Message",
        help="Reject Message for WhatsApp Business API",
        config_parameter='whatsapp_sale_order_notify.whatsapp_reject_message'
    )
    

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        res.update(
            whatsapp_access_token = IrConfigParameter.get_param('whatsapp_sale_order_notify.whatsapp_access_token'),
            whatsapp_phone_number_id = IrConfigParameter.get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id'),
            whatsapp_verify_token = IrConfigParameter.get_param('whatsapp_sale_order_notify.whatsapp_verify_token'),
            whatsapp_accept_message = IrConfigParameter.get_param('whatsapp_sale_order_notify.whatsapp_accept_message'),
            whatsapp_reject_message = IrConfigParameter.get_param('whatsapp_sale_order_notify.whatsapp_reject_message')

        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        IrConfigParameter.set_param('whatsapp_sale_order_notify.whatsapp_access_token', self.whatsapp_access_token )
        IrConfigParameter.set_param('whatsapp_sale_order_notify.whatsapp_phone_number_id', self.whatsapp_phone_number_id )
        IrConfigParameter.set_param('whatsapp_sale_order_notify.whatsapp_verify_token', self.whatsapp_verify_token )
        IrConfigParameter.set_param('whatsapp_sale_order_notify.whatsapp_accept_message', self.whatsapp_accept_message )
        IrConfigParameter.set_param('whatsapp_sale_order_notify.whatsapp_reject_message', self.whatsapp_reject_message )


        
        