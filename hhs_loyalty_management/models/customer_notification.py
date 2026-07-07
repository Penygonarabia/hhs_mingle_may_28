from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import requests
import json
import logging
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)

class LoyaltySalesman(models.Model):
    _name = 'loyalty.salesman'
    _description = 'Loyalty Salesman (Auto Populated from Partners)'

    name = fields.Char(string="Salesman Name", required=True)
    
    @api.model
    def sync_salesmen_from_partners(self):
        """ Fetch distinct salesman names from res.partner and create records if they don't exist. """
        self.env.cr.execute("SELECT DISTINCT salesman_name FROM res_partner WHERE salesman_name IS NOT NULL AND salesman_name != ''")
        salesmen_in_db = [row[0] for row in self.env.cr.fetchall()]
        
        existing_records = self.search([('name', 'in', salesmen_in_db)])
        existing_names = existing_records.mapped('name')
        
        to_create = [{'name': name} for name in salesmen_in_db if name not in existing_names]
        if to_create:
            self.create(to_create)

class CustomerNotification(models.Model):
    _name = 'customer.notification'
    _description = 'Customer Notification'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Title (English)', required=True, tracking=True)
    name_ar = fields.Char(string='Title (Arabic)', tracking=True)
    notes = fields.Html(string='Notes (English)', required=True)
    notes_ar = fields.Html(string='Notes (Arabic)')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    
    # Filters
    active_loyalty_only = fields.Boolean(string='Active Loyalty Customers', default=True)
    promotion_ids = fields.Many2many('lp.setup.promotions', string='Promotions')
    is_promotion_selected = fields.Boolean(compute='_compute_is_promotion_selected')
    promotion_start_date = fields.Date(string='Promotion Start Date', compute='_compute_promotion_dates')
    promotion_end_date = fields.Date(string='Promotion End Date', compute='_compute_promotion_dates')

    partner_ids = fields.Many2many('res.partner', string='Customer(s)')
    tier_ids = fields.Many2many('customer.tier', string='Tier(s)')
    activation_date_from = fields.Date(string='Activation Date From')
    activation_date_to = fields.Date(string='Activation Date To')
    salesman_ids = fields.Many2many('loyalty.salesman', string='Salesman')

    # Output Medium
    send_email = fields.Boolean(string='eMail', default=False)
    send_sms = fields.Boolean(string='SMS', default=False)
    send_whatsapp = fields.Boolean(string='WhatsApp', default=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent')
    ], string='Status', default='draft', tracking=True)

    @api.depends('promotion_ids')
    def _compute_is_promotion_selected(self):
        for rec in self:
            rec.is_promotion_selected = bool(rec.promotion_ids)

    @api.depends('promotion_ids')
    def _compute_promotion_dates(self):
        for rec in self:
            if rec.promotion_ids:
                start_dates = rec.promotion_ids.filtered(lambda p: p.promotion_start_date).mapped('promotion_start_date')
                end_dates = rec.promotion_ids.filtered(lambda p: p.promotion_end_date).mapped('promotion_end_date')
                rec.promotion_start_date = min(start_dates) if start_dates else False
                rec.promotion_end_date = max(end_dates) if end_dates else False
            else:
                rec.promotion_start_date = False
                rec.promotion_end_date = False

    @api.onchange('promotion_ids')
    def _onchange_promotion_ids(self):
        if self.promotion_ids:
            # Auto-populate tiers and customers configured on the selected promotions
            tiers = self.promotion_ids.mapped('tier_line_ids.tier_id')
            customers = self.promotion_ids.mapped('customer_line_ids.customer_id')
            
            self.tier_ids = [(6, 0, tiers.ids)]
            self.partner_ids = [(6, 0, customers.ids)]
            self.salesman_ids = [(5, 0, 0)]
            self.activation_date_from = False
            self.activation_date_to = False
        else:
            self.tier_ids = [(5, 0, 0)]
            self.partner_ids = [(5, 0, 0)]

    @api.model
    def default_get(self, fields_list):
        res = super(CustomerNotification, self).default_get(fields_list)
        try:
            self.env['loyalty.salesman'].sync_salesmen_from_partners()
        except Exception as e:
            _logger.warning("Failed to sync salesmen on load: %s", e)
        return res

    def action_sync_salesmen(self):
        self.env['loyalty.salesman'].sync_salesmen_from_partners()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Salesmen Synced',
                'message': 'Salesman list successfully refreshed from customer records.',
                'sticky': False,
                'type': 'success',
            }
        }

    def action_send_notification(self):
        self.ensure_one()
        
        # Validation 1: At least one filter must be selected
        if not (self.promotion_ids or self.partner_ids or self.tier_ids or self.salesman_ids or (self.activation_date_from and self.activation_date_to)):
            raise ValidationError(_("You must select at least one criteria (Promotions, Customer, Tier, Dates, or Salesman) to send a notification."))

        # Validation 2: At least one medium must be selected
        if not (self.send_email or self.send_sms or self.send_whatsapp):
            raise ValidationError(_("You must select at least one output medium (eMail, SMS, or WhatsApp)."))

        # Validation 3: Dates logic
        if self.activation_date_from and self.activation_date_to:
            if self.activation_date_from > self.activation_date_to:
                raise ValidationError(_("'From' date cannot be greater than 'To' date."))
        elif self.activation_date_from or self.activation_date_to:
            raise ValidationError(_("Both 'From' and 'To' dates must be provided if you want to filter by Activation Date."))

        # Sync salesmen first just in case
        self.env['loyalty.salesman'].sync_salesmen_from_partners()

        # Build Domain for Partners
        if self.promotion_ids:
            partners = self.env['res.partner']
            for promo in self.promotion_ids:
                if promo.select_all_customers:
                    partners |= self.env['res.partner'].search([('activate_loyalty_feature', '=', True)])
                else:
                    if promo.tier_line_ids:
                        partners |= self.env['res.partner'].search([
                            ('activate_loyalty_feature', '=', True),
                            ('customer_tier_id', 'in', promo.tier_line_ids.mapped('tier_id').ids)
                        ])
                    if promo.customer_line_ids:
                        partners |= promo.customer_line_ids.mapped('customer_id')
        else:
            domain = []
            if self.active_loyalty_only:
                domain.append(('activate_loyalty_feature', '=', True))
            
            if self.partner_ids:
                domain.append(('id', 'in', self.partner_ids.ids))
            if self.tier_ids:
                domain.append(('customer_tier_id', 'in', self.tier_ids.ids))
            if self.activation_date_from and self.activation_date_to:
                domain.append(('activation_date', '>=', self.activation_date_from))
                domain.append(('activation_date', '<=', self.activation_date_to))
            if self.salesman_ids:
                domain.append(('salesman_name', 'in', self.salesman_ids.mapped('name')))

            partners = self.env['res.partner'].search(domain)
        
        if not partners:
            raise ValidationError(_("No customers found matching the selected criteria."))

        success_count = 0
        for partner in partners:
            if self.send_email and partner.email:
                self._send_email(partner)
                success_count += 1
            if self.send_sms and partner.mobile:
                self._send_sms(partner)
                success_count += 1
            if self.send_whatsapp and partner.mobile:
                self._send_whatsapp(partner)
                success_count += 1

        self.write({'state': 'sent'})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Notification Sent',
                'message': f'Notification processed for {len(partners)} customers successfully.',
                'sticky': False,
                'type': 'success',
            }
        }

    def _send_email(self, partner):
        notes_en = self.notes or ''
        notes_ar = self.notes_ar or ''
        
        body = f"""
<div style="font-family: Arial, sans-serif; font-size: 14px; color: #333333; line-height: 1.6;">
    <p>Dear Customer,</p>
    <div style="direction: ltr; text-align: left; margin-bottom: 15px;">
        {notes_en}
    </div>
    <div style="direction: rtl; text-align: right; margin-bottom: 15px;">
        {notes_ar}
    </div>
    <p>Thank you.</p>
    <p>With Regards,<br/>HHS Sales Team</p>
</div>
        """
        
        is_arabic = partner.lang and partner.lang.startswith('ar')
        subject = self.name_ar if (is_arabic and self.name_ar) else self.name

        mail_values = {
            'subject': subject,
            'body_html': body,
            'email_to': partner.email,
            'attachment_ids': [(6, 0, self.attachment_ids.ids)],
        }
        self.env['mail.mail'].sudo().create(mail_values).send()

    def _send_sms(self, partner):
        try:
            is_arabic = partner.lang and partner.lang.startswith('ar')
            subject = self.name_ar if (is_arabic and self.name_ar) else self.name
            content = self.notes_ar if (is_arabic and self.notes_ar) else self.notes
            
            clean_text = html2plaintext(content)
            self.env['sms.sms'].sudo().create({
                'number': partner.mobile,
                'body': f"{subject}\n\n{clean_text}",
            }).send()
        except Exception as e:
            _logger.warning(f"SMS sending failed for {partner.name}: {e}")

    def _send_whatsapp(self, partner):
        phone_number = partner.mobile or partner.phone
        if not phone_number:
            return

        whatsapp_phone_number_id = self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_phone_number_id')
        access_token = self.env['ir.config_parameter'].sudo().get_param('whatsapp_sale_order_notify.whatsapp_access_token')

        if not whatsapp_phone_number_id or not access_token:
            _logger.warning("No WhatsApp configuration found.")
            return

        url = f"https://graph.facebook.com/v16.0/{whatsapp_phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        is_arabic = partner.lang and partner.lang.startswith('ar')
        subject = self.name_ar if (is_arabic and self.name_ar) else self.name
        content = self.notes_ar if (is_arabic and self.notes_ar) else self.notes

        clean_text = html2plaintext(content)
        full_msg = f"*{subject}*\n\n{clean_text}"

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number.replace("+", "").replace(" ", ""),
            "type": "text",
            "text": {"body": full_msg}
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            if response.status_code not in (200, 201):
                _logger.warning(f"WhatsApp sending failed for {partner.name}: {response.text}")
        except Exception as e:
            _logger.warning(f"WhatsApp sending exception for {partner.name}: {str(e)}")

