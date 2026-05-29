from collections import defaultdict

from odoo import _, api, exceptions, fields, models, modules
from odoo.addons.base.models.res_users import is_selection_groups


class ResUsers(models.Model):
    
    _inherit = "res.users"
    
    notification_type = fields.Selection([
        ('email', 'Handle by Emails'),
        ('inbox', 'Handle in Cielo')],
        'Notification', required=True, default='email',
        help="Policy on how to handle Chatter notifications:\n"
             "- Handle by Emails: notifications are sent to your email address\n"
             "- Handle in Cielo: notifications appear in your Cielo Inbox")
    
    
    odoobot_state = fields.Selection(
        [
            ('not_initialized', 'Not initialized'),
            ('onboarding_emoji', 'Onboarding emoji'),
            ('onboarding_attachement', 'Onboarding attachement'),
            ('onboarding_command', 'Onboarding command'),
            ('onboarding_ping', 'Onboarding ping'),
            ('idle', 'Idle'),
            ('disabled', 'Disabled'),
        ], string="CieloBot Status", readonly=True, required=False)