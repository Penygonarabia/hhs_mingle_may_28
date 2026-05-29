from odoo import api, fields, models, _
from odoo.tools import date_utils
from odoo.tools.safe_eval import datetime
from odoo.exceptions import ValidationError, AccessError
from datetime import datetime, timedelta, time, date
from dateutil.relativedelta import relativedelta
from odoo.osv import expression
import logging
from num2words import num2words

_logger = logging.getLogger(__name__)


class SubscriptionContracts(models.Model):
    """ Model for subscription contracts """
    _name = 'subscription.contracts'
    _description = 'Subscription Contracts'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True,
                       help='Name of Contract')
    reference = fields.Char(string='Project Name', help='Contract reference')
    partner_id = fields.Many2one('res.partner', string="Customer",
                                 help='Customer for this contract')
    recurring_period = fields.Integer(string='Contract Period', default=12,
                                      help='Recurring period of subscription contract in months')
    
    contract_reminder = fields.Integer(
        string='Contract Expiration Reminder (Days)', default=30,
        help='Expiry reminder of subscription contract in days.')
    
    # Modified field - changed from Integer to Selection
    recurring_invoice = fields.Selection([
        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly'),
        ('Semi-Annual', 'Semi-Annual'),
        ('Annual', 'Annual'),
    ], string='Invoice Frequency', default='Monthly',
        help='Frequency of invoice generation')
    
    next_invoice_date = fields.Date(string='Next Invoice Date', store=True,
                                    compute='_compute_next_invoice_date',
                                    help='Date of next invoice')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        required=True, default=lambda self: self.env.company.currency_id)
    date_start = fields.Date(string='Start Date', default=fields.Date.today(),
                             help='Subscription contract start date')
    invoice_count = fields.Integer(store=True,
                                   compute='_compute_invoice_count',
                                   string='Invoice count',
                                   help='Number of invoices generated')
    date_end = fields.Date(string='End Date', help='Subscription End Date')
    current_reference = fields.Integer(compute='_compute_sale_order_lines',
                                       string='Current Subscription Id',
                                       help='Current Subscription id')
    lock = fields.Boolean(string='Lock', default=False,
                          help='Lock subscription contract so that further modifications are not possible.')
    state = fields.Selection([
        ('New', 'New'),
        ('Ongoing', 'Ongoing'),
        ('Expire Soon', 'Expire Soon'),
        ('Expired', 'Expired'),
        ('Cancelled', 'Cancelled'),
    ], string='Stage', default='New', copy=False, tracking=True,
        readonly=True, help='Status of subscription contract')
    contract_line_ids = fields.One2many(
        'subscription.contracts.line',
        'subscription_contract_id',
        string='Contract lines', help='Products to be added in the contract')
    
    untaxed_amount = fields.Float(string="Sub Total", compute='_compute_amount_total', store=True)
    vat_amount = fields.Float(string="VAT Amount", compute='_compute_amount_total', store=True)
    
    amount_total = fields.Monetary(string="Total", store=True,
                                   compute='_compute_amount_total', tracking=4,
                                   help='Total amount')
    
    total_discount = fields.Float(string="Total Discount (-) ")
    sale_order_line_ids = fields.One2many(
        'sale.order.line', 'contract_id',
        string='Sale Order Lines',
        help='Order lines of Sale Orders which belongs to this contract')
    note = fields.Html(string="Terms and conditions",
                       help='Add any notes', translate=True)
    invoices_active = fields.Boolean(
        'Invoice active', default=False,
        compute='_compute_invoice_active',
        help='Compute invoices are active or not')
    
    contract_type = fields.Selection([('maintenance','Maintenance'),('construction','Construction')],string="Contract Type")
    travel_hours = fields.Float(string="Travel Hours")
    gross_profit = fields.Float(string="Gross Profit")
    entitlement_prevent = fields.Integer(string="Entitlement - as per contract")
    entitlement_correct = fields.Integer(string="Entitlement - as per contract")
    actuals_up_to_date_prevent = fields.Date(string="Actuals Upto Date")
    actuals_up_to_date_correct = fields.Date(string="Actuals Upto Date")
    balance_prevent = fields.Float(string="Balance")
    balance_correct = fields.Float(string="Balance")
    paid_visit = fields.Char(string="Paid Visit")
    quotation_ref = fields.Char(string="Quotation Reference")
    payment_term_id = fields.Many2one('account.payment.term', string="Payment Terms")
    show_product_fields = fields.Boolean(string="Show Product Fields", compute="_compute_show_product_fields")
    customer_name = fields.Char(string="Name")
    signature = fields.Binary(string="Signature")
    date = fields.Date(string="Date")
    stamp = fields.Binary(string="Stamp")
    contact_person = fields.Char(string="Contact Person")
    mobile_no = fields.Char(string="Mobile No.")
    additional_info = fields.Char(string="Additional Information")
    actual_prevent_count = fields.Integer(string="Actual Preventive Count", compute="_compute_actual_prevent_count", store=True)
    actual_correct_count = fields.Integer(string="Actual Corrective Count", compute="_compute_actual_prevent_count", store=True)
    paid_visit_count = fields.Integer(string="Paid Visit", compute="_compute_actual_prevent_count", store=True)
    
    add_paid_service_price = fields.Float(string="Additional Paid Service Price")
    id_party = fields.Char(string="ID")
    job_position = fields.Char(string="Job Position")
    email = fields.Char(string="Email Id")
    site_address = fields.Char(string="Site Address")
    equipment = fields.Char(string="Equipment")
    
    manual_next_invoice_date = fields.Boolean(
        string='Manual Next Invoice Date',
        default=False,
        help='If set, the next invoice date will not be recomputed automatically'
    )

    # ========== COMPUTE METHODS ==========

    @api.depends('contract_line_ids.actual_prevent_count', 'contract_line_ids.actual_correct_count',
                 'contract_line_ids.paid_visit_count')
    def _compute_actual_prevent_count(self):
        """Compute actual preventive, corrective and paid visit counts from contract lines"""
        for rec in self:
            prevent_count = correct_count = paid_visit_count = 0
            for line in rec.contract_line_ids:
                prevent_count += line.actual_prevent_count or 0
                correct_count += line.actual_correct_count or 0
                paid_visit_count += line.paid_visit_count or 0
            rec.actual_prevent_count = prevent_count
            rec.actual_correct_count = correct_count
            rec.paid_visit_count = paid_visit_count

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        """Override search to apply security rules based on user permissions"""
        user = self.env.user

        if not user.user_has_groups('hr_saudi.group_sys_manager'):
            leader_teams = self.env['crm.team'].search([('user_id', '=', user.id)])

            if leader_teams:
                domain = expression.AND([
                    domain,
                    ['|',
                     ('create_uid', '=', user.id),
                     ('create_uid', 'in', leader_teams.member_ids.ids)
                     ]
                ])
            else:
                domain = expression.AND([
                    domain,
                    [('create_uid', '=', user.id)]
                ])

        return super(SubscriptionContracts, self).search_fetch(domain, field_names, offset, limit, order)

    def _compute_show_product_fields(self):
        """Compute whether to show product fields based on user group"""
        for rec in self:
            rec.show_product_fields = self.env.user.has_group('selling_cost_price_restrict.group_product_price_user')

    @api.depends('contract_line_ids.total_price', 'contract_line_ids.discount', 
                 'contract_line_ids.vat_amt', 'contract_line_ids.price_unit', 
                 'contract_line_ids.qty_ordered')
    def _compute_amount_total(self):
        """Compute total amounts including discounts and VAT"""
        for rec in self:
            lines = rec.contract_line_ids
            rec.untaxed_amount = sum(lines.mapped('total_price'))
            rec.total_discount = sum((line.price_unit * line.qty_ordered * line.discount / 100) for line in lines)
            rec.vat_amount = sum(lines.mapped('vat_amt'))
            rec.amount_total = rec.untaxed_amount - rec.total_discount + rec.vat_amount

    @api.depends('date_start', 'recurring_invoice', 'recurring_period')
    def _compute_next_invoice_date(self):
        """Compute next invoice date and end date based on frequency and period"""
        for rec in self:
            if not rec.date_start:
                rec.next_invoice_date = False
                rec.date_end = False
                continue

            # Compute next_invoice_date only if not manually overridden
            if not rec.manual_next_invoice_date:
                rec.next_invoice_date = rec._get_next_invoice_date(rec.date_start, rec.recurring_invoice)

            # Calculate end date based on recurring_period (in months)
            if rec.recurring_period:
                # Add the contract period in months to start date
                rec.date_end = rec.date_start + relativedelta(months=rec.recurring_period)
            else:
                rec.date_end = False

    def _get_next_invoice_date(self, start_date, frequency):
        """Helper method to calculate next invoice date based on frequency"""
        frequency_map = {
            'Monthly': relativedelta(months=1),
            'Quarterly': relativedelta(months=3),
            'Semi-Annual': relativedelta(months=6),
            'Annual': relativedelta(years=1),
        }
        return start_date + frequency_map.get(frequency, relativedelta(months=1))

    @api.depends('partner_id')
    def _compute_invoice_count(self):
        """Compute the count of invoices generated"""
        for rec in self:
            rec.invoice_count = self.env['account.move'].search_count([
                ('contract_origin', '=', rec.id)
            ])

    @api.depends('invoice_count')
    def _compute_invoice_active(self):
        """Check invoice count to display the invoice smart button"""
        for rec in self:
            rec.invoices_active = rec.invoice_count > 0

    @api.depends('current_reference')
    def _compute_sale_order_lines(self):
        """Get sale order line of contract lines"""
        for rec in self:
            rec.current_reference = rec.id
            product_ids = rec.contract_line_ids.mapped('product_id')
            sale_order_lines = self.env['sale.order.line'].search([
                ('order_partner_id', '=', rec.partner_id.id)
            ])
            
            for sol in sale_order_lines:
                sol_date = sol.create_date.date()
                if rec.date_start <= sol_date <= rec.date_end and sol.product_id in product_ids:
                    sol.contract_id = rec.id

    # ========== CONSTRAINT METHODS ==========

    @api.constrains('date_start', 'date_end', 'next_invoice_date')
    def _check_validity_period(self):
        """Validate date relationships"""
        for rec in self:
            if rec.date_start and rec.next_invoice_date and rec.next_invoice_date < rec.date_start:
                raise ValidationError("Next Invoice Date must be greater than or equal to Start Date")
            if rec.date_end and rec.next_invoice_date and rec.date_end < rec.next_invoice_date:
                raise ValidationError("End Date must be greater than or equal to Next Invoice Date")

    @api.constrains('date_end')
    def _check_end_date(self):
        """Validate that end date is not before start date"""
        for rec in self:
            if rec.date_end and rec.date_start and rec.date_end < rec.date_start:
                raise ValidationError("End date cannot be earlier than the start date.")

    # ========== ACTION METHODS ==========

    def action_to_confirm(self):
        """Confirm the Contract"""
        for rec in self:
            if not rec.contract_line_ids:
                raise ValidationError("Cannot confirm a contract without contract lines.")
            rec._check_security_access()
            rec.write({'state': 'Ongoing'})
            _logger.info("Contract %s confirmed and set to Ongoing state", rec.name)

    def action_to_cancel(self):
        """Cancel the Contract"""
        for rec in self:
            rec._check_security_access()
            rec.write({'state': 'Cancelled'})
            _logger.info("Contract %s cancelled", rec.name)

    def action_generate_invoice(self):
        """Generate invoice based on frequency"""
        for rec in self:
            rec._generate_single_invoice()
    
    def _generate_single_invoice(self):
        """Helper method to generate a single invoice"""
        self.ensure_one()
        
        if not self.contract_line_ids:
            raise ValidationError("Cannot generate an invoice for a contract without contract lines.")
        
        self._check_security_access()
        
        # Check if invoice already exists for this date
        existing_invoice = self.env['account.move'].search([
            ('contract_origin', '=', self.id),
            ('invoice_date', '=', self.next_invoice_date)
        ], limit=1)
        
        if existing_invoice:
            _logger.info("Invoice already exists for contract %s on date %s", self.name, self.next_invoice_date)
            return
        
        _logger.info("Generating invoice for contract %s", self.name)
        
        # Calculate invoice amounts
        base_amount, vat_rate, final_amount = self._calculate_invoice_amounts()
        
        # Create invoice
        invoice_vals = self._prepare_invoice_vals(base_amount, vat_rate, final_amount)
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Update contract
        self.invoice_count = self.env['account.move'].search_count([('contract_origin', '=', self.id)])
        self._update_next_invoice_date()
        
        _logger.info("Invoice %s created successfully for contract %s", invoice.name, self.name)

    def _calculate_invoice_amounts(self):
        """Calculate invoice amounts based on frequency"""
        base_amount = self.untaxed_amount - self.total_discount
        
        # Calculate prorated amount based on frequency
        frequency_divisors = {
            'Monthly': 12,
            'Quarterly': 4,
            'Semi-Annual': 2,
            'Annual': 1,
        }
        divisor = frequency_divisors.get(self.recurring_invoice, 1)
        invoice_amount = base_amount / divisor
        
        # Calculate VAT
        vat_rates = self.contract_line_ids.mapped('vat')
        vat_rate = sum(vat_rates) / len(vat_rates) if vat_rates else 0
        vat_amount = invoice_amount * (vat_rate / 100)
        final_amount = invoice_amount + vat_amount
        
        return invoice_amount, vat_rate, final_amount

    def _prepare_invoice_vals(self, base_amount, vat_rate, final_amount):
        """Prepare invoice values dictionary"""
        first_line = self.contract_line_ids[0]
        return {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.next_invoice_date,
            'invoice_date_due': self.next_invoice_date,
            'contract_origin': self.id,
            'ref': self.reference,
            'invoice_line_ids': [(0, 0, {
                'product_id': first_line.product_id.id,
                'name': f"Subscription Invoice - {self.recurring_invoice}",
                'quantity': 1,
                'price_unit': final_amount,
                'tax_ids': [(6, 0, self.contract_line_ids.mapped('tax_ids').ids)],
                'vat_amt': final_amount - base_amount,
                'vat': vat_rate,
                'total_price': final_amount,
                'analytic_distribution': {first_line.analytic_account_id.id: 100.0}
            })]
        }

    def _update_next_invoice_date(self):
        """Update next invoice date based on frequency"""
        frequency_deltas = {
            'Monthly': relativedelta(months=1),
            'Quarterly': relativedelta(months=3),
            'Semi-Annual': relativedelta(months=6),
            'Annual': relativedelta(years=1),
        }
        delta = frequency_deltas.get(self.recurring_invoice, relativedelta(months=1))
        self.next_invoice_date = self.next_invoice_date + delta

    def _check_security_access(self):
        """Check if user has permission to modify this contract"""
        user = self.env.user
        if not user.user_has_groups('hr_saudi.group_sys_manager') and self.partner_id != user.partner_id:
            raise AccessError("You are not authorized to access this contract.")

    def action_lock(self):
        """Lock subscription contract"""
        for rec in self:
            rec._check_security_access()
            rec.lock = True
            _logger.info("Contract %s locked", rec.name)

    def action_to_unlock(self):
        """Unlock subscription contract"""
        for rec in self:
            rec._check_security_access()
            rec.lock = False
            _logger.info("Contract %s unlocked", rec.name)

    def action_get_invoice(self):
        """Access generated invoices"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('contract_origin', '=', self.id)],
        }

    # ========== CRUD METHODS ==========

    @api.model
    def create(self, vals):
        """Override create to set manual date flag and generate sequence"""
        if 'next_invoice_date' in vals:
            vals['manual_next_invoice_date'] = True
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('subscription.contracts') or 'New'
        return super().create(vals)

    def write(self, vals):
        """Override write to set manual date flag"""
        if 'next_invoice_date' in vals:
            vals['manual_next_invoice_date'] = True
        return super().write(vals)

    # ========== SCHEDULED ACTIONS ==========

    @api.model
    def subscription_contract_state_change(self):
        """Automatic state change and create invoice - called by scheduled action"""
        contracts = self.search([])
        current_date = fields.Date.today()
        
        for contract in contracts:
            try:
                contract._process_contract_state_change(current_date)
            except Exception as e:
                _logger.error("Error processing contract %s: %s", contract.name, str(e))

    def _process_contract_state_change(self, current_date):
        """Process state changes and invoice generation for a single contract"""
        # Check and update contract state
        self._update_contract_state(current_date)
        
        # Generate invoice if due
        if (self.next_invoice_date == current_date and 
            self.state not in ('New', 'Cancelled', 'Expired')):
            self._generate_automated_invoice()

    def _update_contract_state(self, current_date):
        """Update contract state based on dates"""
        if not self.date_end:
            return
            
        expiry_warning_date = self.date_end - timedelta(days=self.contract_reminder or 0)
        
        if expiry_warning_date <= current_date <= self.date_end:
            if self.state != 'Expire Soon':
                self.write({'state': 'Expire Soon'})
                _logger.info("Contract %s set to Expire Soon", self.name)
        elif current_date > self.date_end and self.state != 'Expired':
            self.write({'state': 'Expired'})
            _logger.info("Contract %s set to Expired", self.name)

    def _generate_automated_invoice(self):
        """Generate invoice for automated scheduled action"""
        # Check if invoice already exists for this date
        existing_invoice = self.env['account.move'].search([
            ('contract_origin', '=', self.id),
            ('invoice_date', '=', self.next_invoice_date)
        ], limit=1)
        
        if existing_invoice:
            return
            
        _logger.info("Automatically generating invoice for contract %s", self.name)
        self._generate_single_invoice()

    # ========== OTHER METHODS ==========

    def show_amc_quotation_view(self):
        """Button: Open the related contract form view."""
        self.ensure_one()
        if not self.amc_quotation_id:
            raise ValidationError(_("No contract is linked to this order."))

        return {
            'name': _('Contract'),
            'type': 'ir.actions.act_window',
            'res_model': 'service.sale.order',
            'view_mode': 'form',
            'res_id': self.amc_quotation_id.id,
            'target': 'current',
        }

    def action_print_contract_document(self):
        """Print contract document"""
        return self.env.ref('sales_contract_and_recurring_invoices.action_report_contract_document').report_action(self)

    @api.model
    def number_to_words(self, number, lang='en'):
        """Convert numeric value to words in specified language"""
        try:
            if number is None or number == '':
                _logger.info("number_to_words called → Zero")
                return "Zero"

            n = int(float(number))
            words = num2words(n, lang=lang).capitalize()
            _logger.info("Converted %s → %s in language %s", number, words, lang)
            return words

        except Exception as e:
            _logger.error("number_to_words FAILED for %r: %s", number, e)
            try:
                return str(int(float(number)))
            except Exception:
                return str(number)

    @api.model
    def number_to_words_ar(self, number):
        """Convert numeric value to Arabic words - kept for backward compatibility"""
        return self.number_to_words(number, lang='ar')
