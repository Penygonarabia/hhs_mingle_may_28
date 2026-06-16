from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class DealerShowroomInvoice(models.Model):
    _name = 'dsales.showroom.invoice'
    _description = 'Showroom Sales Invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'invoice_number'
    _order = 'date_time desc'

    
    dealer_id = fields.Many2one('res.partner', string='Dealer', domain="[('dealersalesman_required', '=', True)]", required=True, tracking=True)
    dealer_showroom_id = fields.Many2one('dsales.showroom', string='Dealer Showroom', domain="[('dealer_id', '=', dealer_id)]", required=True, tracking=True)
    salesman_id = fields.Many2one('dsales.assignment', string='Salesman',domain="[('dealer_id', '=', dealer_id), ('dealer_showroom_id', '=', dealer_showroom_id)]",  required=True, tracking=True)
    invoice_number = fields.Many2one('dsales.showroom.sales', string='Invoice Number', required=True, tracking=True)
    date_time = fields.Datetime(string='Date & Time', default=fields.Datetime.now, required=True, tracking=True)
    invoice_attachment = fields.Binary(related='invoice_number.invoice_attachment', string='Invoice Scan Copy')

    # @api.constrains('invoice_number', 'dealer_id')
    # def _check_duplicate_invoice(self):
    #     for rec in self:
    #         if rec.invoice_number and rec.dealer_id:
    #             domain = [
    #                 ('invoice_number', '=', rec.invoice_number.id),
    #                 ('dealer_id', '=', rec.dealer_id.id),
    #                 ('dealer_showroom_id', '=', rec.dealer_showroom_id.id),
    #                 ('salesman_id', '=', rec.salesman_id.id),
    #                 ('id', '!=', rec.id)
    #             ]
    #             if self.search_count(domain) > 0:
    #                 raise ValidationError(_("Invoice Number must be unique per Dealer!"))


    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True)
    reject_reason = fields.Text(string='Reject Reason', tracking=True)

    sale_ids = fields.Many2many(
        'dsales.showroom.sales',
        string='Item Details'
    )

    sale_line_ids = fields.Many2many(
        'dsales.showroom.sales.line',
        string='Item Line Details',
        compute='_compute_sale_line_ids',
        store=False,
        readonly=True
    )

    @api.depends('invoice_number')
    def _compute_sale_line_ids(self):
        for rec in self:
            rec.sale_line_ids = rec.invoice_number.line_ids

    @api.onchange('invoice_number')
    def _onchange_invoice_number(self):
        if self.invoice_number:
            self.dealer_id = self.invoice_number.dealer_id
            self.dealer_showroom_id = self.invoice_number.dealer_showroom_id
            self.salesman_id = self.invoice_number.dealer_assignment_id


    @api.onchange('dealer_id', 'dealer_showroom_id', 'salesman_id', 'invoice_number')
    def _onchange_fetch_sales(self):
        for rec in self:
            rec.sale_ids = [(5, 0, 0)]

            if not rec.invoice_number:
                continue

            sale = rec.invoice_number

            # Dealer validation
            if rec.dealer_id and sale.dealer_id != rec.dealer_id:
                continue

            # Showroom validation
            if rec.dealer_showroom_id and sale.dealer_showroom_id != rec.dealer_showroom_id:
                continue

            rec.sale_ids = [(6, 0, [sale.id])]

    @api.onchange('invoice_number')
    def _onchange_fetch_sales(self):
        for rec in self:
            if rec.invoice_number:
                rec.sale_ids = rec.invoice_number
            else:
                rec.sale_ids = False

    def action_submit(self):
        for rec in self:
            params = self.env['ir.config_parameter'].sudo()
            retailer_limit = int(params.get_param('dealer.retailer_sales_limit', 25))
            dealer_limit = int(params.get_param('dealer.dealer_sales_limit', 100))

            sale_lines = rec.sale_line_ids

            total_qty = sum(
                abs(line.qty) for line in sale_lines
            )

            is_retailer = rec.dealer_id.is_retailer if hasattr(rec.dealer_id, 'is_retailer') else False
            limit = retailer_limit if is_retailer else dealer_limit

            if total_qty > limit:
                rec.state = 'pending'
                
                # Notify the authority in-charge
                auth_user = self.env['res.users'].sudo().search([('floor_sales_approval_auth', '=', True)], limit=1)
                if auth_user:
                    rec.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=auth_user.id,
                        summary=_("Approval Required: Exceeds limit"),
                        note=_("Quantity exceeds the permitted limit (%s units). Please review and approve.") % limit
                    )

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Pending Approval"),
                        'message': _("Quantity exceeds the permitted limit (%s). This sales claim will be sent for approval.") % limit,
                        'type': 'warning',
                        'sticky': False,
                        'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                    }
                }

            rec.state = 'submitted'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Submitted"),
                    'message': _("Sales claim submitted successfully."),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                }
            }

    def _check_approval_authority(self):
        """Return True if current user has approval authority."""
        user = self.env.user
        try:
            has_auth = bool(user.floor_sales_approval_auth)
        except Exception:
            has_auth = False
        try:
            # Check if current user has default_authority checked
            is_delegate = bool(user.default_authority)
        except Exception:
            is_delegate = False
        return has_auth or is_delegate

    def action_approve(self):
        for rec in self:
            if not self._check_approval_authority():
                raise ValidationError(_("You do not have authority to approve sales."))
            rec.state = 'approved'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Approved"),
                'message': _("Sales claim approved successfully."),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def action_reject(self):
        for rec in self:
            if not self._check_approval_authority():
                raise ValidationError(_("You do not have authority to reject sales."))
            if not rec.reject_reason or not rec.reject_reason.strip():
                raise ValidationError(_("Please enter Reject Reason."))
            rec.state = 'rejected'
            if rec.invoice_number and hasattr(rec.invoice_number, '_send_whatsapp_notification'):
                rec.invoice_number._send_whatsapp_notification(rec.invoice_number)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Rejected"),
                'message': _("Sales claim rejected successfully."),
                'type': 'warning',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.reject_reason = False
