from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class DealerShowroomInvoice(models.Model):
    _name = 'dsales.showroom.invoice'
    _description = 'Showroom Sales Invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'invoice_number'
    _order = 'date_time desc'

    invoice_number = fields.Char(string='Invoice Number', required=True, tracking=True)
    dealer_id = fields.Many2one('res.partner', string='Dealer', required=True, tracking=True)
    dealer_showroom_id = fields.Many2one('dsales.showroom', string='Dealer Showroom', required=True, tracking=True)
    salesman_id = fields.Many2one('res.users', string='Salesman', required=True, tracking=True)
    date_time = fields.Datetime(string='Date & Time', default=fields.Datetime.now, required=True, tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Invoice Scan Copy')
    @api.constrains('invoice_number', 'dealer_id')
    def _check_duplicate_invoice(self):
        for rec in self:
            if rec.invoice_number and rec.dealer_id:
                domain = [
                    ('invoice_number', '=', rec.invoice_number),
                    ('dealer_id', '=', rec.dealer_id.id),
                    ('id', '!=', rec.id)
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError(_("Invoice Number must be unique per Dealer!"))

    @api.constrains('attachment_ids')
    def _check_attachments(self):
        for rec in self:
            if not rec.attachment_ids:
                raise ValidationError(_("Invoice attachment is required."))
            if len(rec.attachment_ids) > 1:
                raise ValidationError(_("Only one invoice attachment is allowed."))
            
            for att in rec.attachment_ids:
                if att.mimetype not in ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf']:
                    raise ValidationError(_("Supported formats are JPG, JPEG, PNG, PDF."))

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True)
    reject_reason = fields.Text(string='Reject Reason', tracking=True)
    sale_line_ids = fields.One2many('dsales.showroom.sales', 'invoice_id', string='Product Details')

    def action_submit(self):
        for rec in self:
            if not rec.sale_line_ids:
                raise ValidationError(_("Please add at least one product."))
            
            params = self.env['ir.config_parameter'].sudo()
            retailer_limit = int(params.get_param('dealer.retailer_sales_limit', 25))
            dealer_limit = int(params.get_param('dealer.dealer_sales_limit', 100))
            
            is_exceeding = False
            total_qty = sum(line.qty for line in rec.sale_line_ids if not line.is_sales_return)
            
            is_retailer = getattr(rec.dealer_id, 'is_retailer', False) if hasattr(rec.dealer_id, 'is_retailer') else False
            if is_retailer:
                if total_qty > retailer_limit:
                    is_exceeding = True
            else:
                if total_qty > dealer_limit:
                    is_exceeding = True
                    
            if is_exceeding:
                rec.state = 'pending'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Pending Approval"),
                        'message': _("Quantity exceeds the permitted limit. This sales claim will be sent for approval."),
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            else:
                rec.state = 'approved'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Success"),
                        'message': _("Sales claim submitted and approved automatically."),
                        'type': 'success',
                        'sticky': False,
                    }
                }

    def action_approve(self):
        for rec in self:
            if not self.env.user.floor_sales_approval_auth and not self.env.user.default_authority:
                raise ValidationError(_("You do not have authority to approve sales."))
            rec.state = 'approved'

    def action_reject(self):
        for rec in self:
            if not self.env.user.floor_sales_approval_auth and not self.env.user.default_authority:
                raise ValidationError(_("You do not have authority to reject sales."))
            if not rec.reject_reason:
                raise ValidationError(_("Please provide a reject reason."))
            rec.state = 'rejected'
            
            # WhatsApp Notification simulation
            # Note: Integrate with actual WhatsApp module methods if available
            if rec.salesman_id.partner_id.mobile:
                msg = f"Your invoice {rec.invoice_number} submitted on {rec.date_time} has been rejected.\nReason: {rec.reject_reason}"
                _logger = self.env['ir.logging']
                # Try to call whatsapp action if partner_whatsapp module provides it
                if hasattr(rec.salesman_id.partner_id, 'send_whatsapp_message'):
                    try:
                        rec.salesman_id.partner_id.send_whatsapp_message(msg)
                    except Exception as e:
                        pass
