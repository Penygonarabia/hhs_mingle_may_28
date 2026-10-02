# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class ExpiryExtensionWizard(models.Model):
    _name = 'crm.commercial.expiry.extension.wizard'
    _description = 'Order Expiry Extension Wizard'

    order_id = fields.Many2one('crm.commercial.sale.order', string='Order', required=True)
    current_expiry_date = fields.Date(string='Current Expiry Date', related='order_id.expiry_date', readonly=True)
    new_expiry_date = fields.Date(string='New Expiry Date', required=True)
    reason = fields.Text(string='Reason for Extension', required=True)

    def action_apply_extension(self):
        self.ensure_one()
        if self.new_expiry_date <= self.current_expiry_date:
            raise ValidationError(_("New expiry date must be strictly after current expiry date."))
        self.order_id.action_extend_expiry(self.new_expiry_date, self.reason)
        return {'type': 'ir.actions.act_window_close'}
