from odoo import api, fields, models, _
from odoo.tools import date_utils
from odoo.tools.safe_eval import datetime
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, time, date
from dateutil.relativedelta import relativedelta
from odoo.osv import expression
import logging
from num2words import num2words
import re
_logger = logging.getLogger(__name__)


class SubscriptionContracts(models.Model):
    """ Model for subscription contracts """
    _name = 'subscription.contracts'
    _description = 'Subscription Contracts'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "name desc"


    name = fields.Char(string='Contract No.', required=True,
                       help='Name of Contract')
    reference = fields.Char(string='Project Name', help='Contract reference')
    partner_id = fields.Many2one('res.partner', string="Customer",
                                 help='Customer for this contract')
    recurring_period = fields.Integer(string='Contract Period',
                                      help='Recurring period of '
                                           'subscription contract')
    recurring_period_interval = fields.Selection([
        ('Days', 'Days'),
        ('Weeks', 'Weeks'),
        ('Months', 'Months'),
        ('Years', 'Years'),
    ], help='Recurring interval of subscription contract', string="Contract Interval")

    contract_reminder = fields.Integer(
        string='Contract Expiration Reminder (Days)',
        help='Expiry reminder of subscription contract in days.')

    # Keep as regular field to avoid migration issues
    recurring_invoice = fields.Integer(
        string='Invoice Interval (Days)',
        default=30,
        help='Recurring invoice interval in days'
    )

    # New selection: choose duration (drives invoice_interval)
    invoice_interval_duration = fields.Selection(
        [
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('semi_annual', 'Semi-Annual'),
            ('annual', 'Annual'),
        ],
        string="Invoice Frequency",
        required=True,
        default='monthly',
        help="Select the interval duration for invoicing."
    )

    # Add this field to track number of installments
    number_of_installments = fields.Integer(
        string="Number of Installments",
        compute="_compute_number_of_installments",
        store=True,
        help="Number of invoices to be generated during the contract period"
    )

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

    # Contract duration in days
    contract_duration_days = fields.Integer(
        string="Contract Duration Days",
        compute="_compute_contract_duration_days",
        store=True,
        help="Number of days between Start Date and End Date"
    )

    current_reference = fields.Integer(compute='_compute_sale_order_lines',
                                       string='Current Subscription Id',
                                       help='Current Subscription id')
    lock = fields.Boolean(string='Lock', default=False,
                          help='Lock subscription contract so that further'
                               ' modifications are not possible.')
    state = fields.Selection([
        ('New', 'New'),
        ('Ongoing', 'Ongoing'),
        ('Expire Soon', 'Expire Soon'),
        ('Expired', 'Expired'),
        ('Cancelled', 'Cancelled'),
        ('terminate','Terminate')
        
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

    contract_type = fields.Selection([('maintenance', 'Maintenance'), ('construction', 'Construction')],
                                     string="Contract Type")
    travel_hours = fields.Float(string="Travel Hours")
    gross_profit = fields.Float(string="Gross Profit")
    entitlement_prevent = fields.Integer(string="Total Preventive Count")
    entitlement_correct = fields.Integer(string="Total Corrective Count")
    actuals_up_to_date_prevent = fields.Date(string="Actuals Upto Date")
    actuals_up_to_date_correct = fields.Date(string="Actuals Upto Date")
    balance_prevent = fields.Integer(string="Balance preventive Count", compute = "_compute_actual_prevent_count", store=True)
    balance_correct = fields.Integer(string="Balance Corrective Count", compute = "_compute_actual_prevent_count", store=True)
    paid_visit = fields.Integer(string="Paid Visit")
    quotation_ref = fields.Char(string="Quotation Reference")
    payment_term_id = fields.Many2one('account.payment.term', string="Payment Terms")
    show_product_fields = fields.Boolean(string="Show Product Fields", compute="_compute_show_product_fields")
    customer_name = fields.Char(string="Name")
    signature = fields.Binary(string="Signature")
    date = fields.Date(string="Date")
    stamp = fields.Binary(string="Stamp")
    contact_person = fields.Char(string="Contact  Persons")
    contact_persons=fields.Char(string="Contact Person")
    contact_persons_mobile=fields.Char(string="Contact Person Mobile")
    mobile_no = fields.Char(string="Mobile No.")
    additional_info = fields.Char(string="Additional Information")
    actual_prevent_count = fields.Integer(string="Actual Preventive Count", compute="_compute_actual_prevent_count", store=True)
    actual_correct_count = fields.Integer(string="Actual Corrective Count", compute="_compute_actual_prevent_count", store=True)
    paid_visit_count = fields.Integer(string="Paid Visit", store=True)

    add_paid_service_price = fields.Float(string="Additional Paid Service Price")
    id_party = fields.Char(string="ID")
    job_position = fields.Char(string="Job Position")
    email = fields.Char(string="Email Id")
    site_address = fields.Char(string="Site Address")
    equipment = fields.Char(string="Equipment")
    service_coordinator_mobile = fields.Char(string="Service Coordinator Mobile Number")
    service_coordinator_person = fields.Char(string="Service Coordinator Contact Person")

    # attachment_image_ids = fields.One2many(
    #     'subscription.contract.image',
    #     'contract_id',
    #     string='Attachment Images'
    # )

    attachment1 = fields.Binary("Quotation")
    attachment1_filename = fields.Char("File Name")

    attachment2 = fields.Binary("Contract")
    attachment2_filename = fields.Char("File Name")

    attachment3 = fields.Binary("C.R.")
    attachment3_filename = fields.Char("File Name")

    attachment4 = fields.Binary("VAT")
    attachment4_filename = fields.Char("File Name")

    attachment5 = fields.Binary("National Address")
    attachment5_filename = fields.Char("File Name")

    attachment6 = fields.Binary("Company’s Representative")
    attachment6_filename = fields.Char("File Name")

    # Link to service sale order
    amc_quotation_id = fields.Many2one(
        'service.sale.order',
        string="AMC Quotation",
        help="Related Service Sale Order"
    )
    project_id = fields.Many2one(
        # mar 19
        "project.project",
        string="Project",
        domain=[("related_to_amc", "=", True)],
        default=lambda self: self.env["project.project"].search([("related_to_amc", "=", True)], limit=1).id if "project.project" in self.env else False,
    )
    
    '''Code Added on July 24 2026 by vijaya bhaskar client asked the Termination date and reason'''
    
    termination_reason = fields.Text(string = "Reason for Termination")
    
    termination_date = fields.Date(string = "Termination Date")
    
    termination_button_click_bool = fields.Boolean(default = False)
    
    def action_to_termination(self):
        # if not self.termination_reason:
        #     raise ValidationError("Please Enter Reason for Termination")
        #
        # self.write({
        #             'state':'terminate',
        #             'termination_date' : fields.Date.today()
        #             })
        
        self.ensure_one()
        return {
            
            'name' : 'Termination Wizard',
            'res_model' : 'contract.termination.wizard',
            'view_mode' :'form',
            'target' : 'new',
            'type' :'ir.actions.act_window',
            'context' :{
                'default_contract_id':self.id,
                }
            
                 
            } 
    
   
    additional_document_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="subscription_contract_additional_document_rel",
        column1="contract_id",
        column2="attach_document_id",
        string="Additional Document(s)",
        help="Multiple Images and Pdf is attached here",
        domain="[('mimetype','in',['image/jpeg','image/png','image/gif','application/pdf'])]",
    )
    
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="subscription_contract_rel",
        column1="contract_id",
        column2="attachment_id",
        string="Payment Attachment",
        help="Multiple Images and Pdf is attached here",
        domain="[('mimetype','in',['image/jpeg','image/png','image/gif','application/pdf'])]",
    )

    
    
    # Internal mapping used for conversion between duration label and months to add
    _DURATION_TO_MONTHS = {
        'monthly': 1,
        'quarterly': 3,
        'semi_annual': 6,
        'annual': 12,
    }

    def get_payment_term_text(self):
        mapping = {
            'monthly': ('Monthly', 1),
            'quarterly': ('Quarterly', 3),
            'semi_annual': ('Semi-annual', 6),
            'annual': ('Annual', 12),
        }

        label, months = mapping.get(
            self.invoice_interval_duration,
            ('Custom', 0)
        )
        return f"{label} in advance (every {months} month{'s' if months > 1 else ''})"
        
    def get_payment_term_text_ar(self):
        mapping = {
            'monthly': "شهرياً مقدماً (كل شهر)",
            'quarterly': "كل ثلاثة أشهر مقدماً (كل 3 أشهر)",
            'semi_annual': "كل ستة أشهر مقدماً (كل 6 أشهر)",
            'annual': "سنوياً مقدماً (كل 12 شهراً)",
        }
        return mapping.get(self.invoice_interval_duration, "")

    @api.depends('contract_line_ids', 'contract_line_ids.actual_prevent_count',
                 'contract_line_ids.actual_correct_count', 'balance_prevent', 'balance_correct',
                 'contract_line_ids.paid_visit_count')
    def _compute_actual_prevent_count(self):
        for rec in self:
            prevent_count = 0
            correct_count = 0
            paid_visit_count = 0
            for line in rec.contract_line_ids:
                if line.actual_prevent_count:
                    prevent_count += line.actual_prevent_count
                if line.actual_correct_count:
                    correct_count += line.actual_correct_count
                if line.paid_visit_count:
                    paid_visit_count += line.paid_visit_count
            rec.actual_prevent_count = prevent_count
            rec.actual_correct_count = correct_count
            rec.balance_prevent = rec.entitlement_prevent - rec.actual_prevent_count
            rec.balance_correct = rec.entitlement_correct - rec.actual_correct_count
            rec.paid_visit_count = paid_visit_count

            # INVOICE CALCULATION METHODS - Use onchange instead of compute to avoid migration issues

    @api.onchange('invoice_interval_duration')
    def _onchange_invoice_interval_duration(self):
        """When user selects invoice frequency, update recurring_invoice."""
        for rec in self:
            if not rec.invoice_interval_duration:
                rec.recurring_invoice = 30  # default monthly
            else:
                # Set fixed intervals based on frequency
                if rec.invoice_interval_duration == 'monthly':
                    rec.recurring_invoice = 30
                elif rec.invoice_interval_duration == 'quarterly':
                    rec.recurring_invoice = 90
                elif rec.invoice_interval_duration == 'semi_annual':
                    rec.recurring_invoice = 180
                elif rec.invoice_interval_duration == 'annual':
                    rec.recurring_invoice = 365

            # Trigger computation of number of installments
            rec._compute_number_of_installments()

    @api.depends('invoice_interval_duration', 'contract_duration_days')
    def _compute_number_of_installments(self):
        """
        Compute number of installments based on contract duration and invoice frequency.
        """
        for rec in self:
            if not rec.invoice_interval_duration or not rec.contract_duration_days:
                rec.number_of_installments = 1
                continue

            # Calculate based on contract duration in years (approximate)
            contract_years = rec.contract_duration_days / 365.0

            if rec.invoice_interval_duration == 'monthly':
                rec.number_of_installments = max(1, int(contract_years * 12))
            elif rec.invoice_interval_duration == 'quarterly':
                rec.number_of_installments = max(1, int(contract_years * 4))
            elif rec.invoice_interval_duration == 'semi_annual':
                rec.number_of_installments = max(1, int(contract_years * 2))
            elif rec.invoice_interval_duration == 'annual':
                rec.number_of_installments = max(1, int(contract_years))
            else:
                rec.number_of_installments = 1

    @api.depends('date_start', 'date_end')
    def _compute_contract_duration_days(self):
        """Compute contract duration in days based on start and end dates."""
        for rec in self:
            if rec.date_start and rec.date_end:
                start_date = rec.date_start
                end_date = rec.date_end
                if start_date and end_date:
                    delta = end_date - start_date
                    # rec.contract_duration_days = delta.days if delta.days >= 0 else 0
                    '''Code Added on April 10 2026 by Vijaya Bhaskar for semi annual start date and end date is one year format. '''
                    rec.contract_duration_days = (delta + relativedelta(days=1)).days if delta.days >= 0 else 0
            else:
                rec.contract_duration_days = 0

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
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
        if self.env.user.has_group('selling_cost_price_restrict.group_product_price_user'):
            self.show_product_fields = True
        else:
            self.show_product_fields = False

    # @api.depends(
    #     'service_sale_order_line_ids.product_qty',
    #     'service_sale_order_line_ids.price_unit',
    #     'service_sale_order_line_ids.total_selling_price',
    #     'service_sale_order_line_ids.discount',
    #     'service_sale_order_line_ids.vat_percent'
    # )
    # def _compute_amount_total(self):
    #     for rec in self:

    #         untaxed = sum(line.total_selling_price for line in rec.service_sale_order_line_ids)

    #         discount = sum(
    #             (line.price_unit * line.product_qty * line.discount / 100)
    #             for line in rec.service_sale_order_line_ids
    #         )

    #         vat = sum(line.vat_percent for line in rec.service_sale_order_line_ids)

    #         rec.untaxed_amount = untaxed
    #         rec.total_discount = discount
    #         rec.vat_amount = vat
    #         rec.amount_total = untaxed - discount + vat

    @api.depends('contract_line_ids',
        'contract_line_ids.qty_ordered',
        'contract_line_ids.price_unit',
        'contract_line_ids.total_selling_price',
        'contract_line_ids.discount',
        'contract_line_ids.vat_amt'
    )
    def _compute_amount_total(self):
        for rec in self:

            untaxed = sum(line.total_selling_price for line in rec.contract_line_ids)

            discount = sum(
                (line.price_unit * line.qty_ordered * line.discount / 100)
                for line in rec.contract_line_ids
            )

            vat = sum(line.vat_amt for line in rec.contract_line_ids)

            rec.untaxed_amount = untaxed
            rec.total_discount = discount
            rec.vat_amount = vat
            rec.amount_total = untaxed - discount + vat

    @api.constrains('date_start', 'date_end', 'next_invoice_date')
    def _check_validity_period(self):
        for rec in self:
            if rec.date_start and rec.next_invoice_date:
                if rec.next_invoice_date < rec.date_start:
                    raise ValidationError("Please check Next Invoice Date is always greater than Start Date")
            # if rec.date_end and rec.next_invoice_date:
            #     if rec.date_end < rec.next_invoice_date:
            #         raise ValidationError("Please check End date is always  greater than Next Invoice Date")

    def action_to_confirm(self):
        """ Confirm the Contract """
        if not self.contract_line_ids:
            raise ValidationError("Cannot generate an invoice for a contract without contract lines.")
        
        '''Code Added on June 09 2026 by Vijaya Bhaskar'''
        if not self.customer_code:
            raise ValidationError(_("Please create the customer in the Penygon Application and enter the same customer code here  "))
        
        '''Code Added on July 27 2026 by Vijaya Bhaskar client asked for warwhouse Remove mandatory in save . It should applicable in Confirm (Same as Customer code) '''
        if not self.warehouse_id:
            raise ValidationError(_("Please enter the warehouse")) 
        
        missing = []
        required_fields = {
            'customer_name' : _("Customer Name"),
            'mobile_no' : _("Mobile No."),
            'email' :_('Email Id'),
            'job_position' : _('Job Position'),
            'contact_persons' : _('Contact Person'),
            'contact_persons_mobile' : _('Contact Person Mobile'),
            'service_coordinator_person' : _('Service Coordinator Contact Person'),
            'service_coordinator_mobile' :_('Service Coordinator Mobile Number'),
         
            }
        
        for field_name,label in required_fields.items():
            if not self[field_name]:
                missing.append(label)
                
        if missing:
            raise ValidationError(
                _("Please fill the following Company Representative fields before confirming:\n\n- %s")
            % "\n- ".join(missing)
                )        
        
        
        missing_attachment = []
        
        attachment_required_field = {
            
            'attachment1_filename' : _('Quotation'),
            'attachment2_filename' : _('Contract'),
            'attachment3_filename' : _('C.R.'),
            'attachment4_filename' : _('VAT'),
            'attachment5_filename' : _('National Address'),
            'attachment6_filename' : _('Company Representative'),
            
            
            }
        
        for field_name,label in attachment_required_field.items():
            if not self[field_name]:
                missing_attachment.append(label)
                
        if  missing_attachment:
            raise ValidationError(
                _("Please fill the following Attachment fields before confirming:\n\n- %s")
            % "\n- ".join(missing_attachment)
                )        
        
                   
        
        
        '''Client Asked same Bring Number Auto Number generation Original one Code Added on June 25 2026 '''
        # '''Code Added on June 22 2026 by Vijaya bhaskar due to original name is updated when we create the contract'''
        # if self.date_start and self.name:
        #     yymm = self.date_start.strftime('%y%m')
        #     # Replace only the YYMM portion before the last 4 sequence digits
        #     self.name = re.sub(
        #         r'(\d{4})(\d{4})$',
        #         lambda m: f'{yymm}{m.group(2)}',
        #         self.name
        #     )
        
        self.write({'state': 'Ongoing'})
        
        
    '''Code Added on June 17 2026 by Vijaya Bhaskar customer code is unique'''
    # @api.constrains('customer_code')
    # def _check_customercode(self):
    #     for rec in self:
    #         if rec.customer_code:
    #             duplicate = self.env['res.partner'].search([
    #                 ('ref', '=', rec.customer_code),
    #                 ('id', '!=', rec.id)
    #             ], limit=1)
    #
    #             if duplicate:
    #                 raise ValidationError(
    #                     _("Customer code '%s' is already associated with customer '%s'.")
    #                     % (rec.customer_code, duplicate.display_name)
    #                 )    

    def action_to_cancel(self):
        """ Cancel the Contract """
        self.write({'state': 'Cancelled'})

    def action_generate_invoice(self):
        """
        Generate installment-based customer invoice
        - Single invoice line
        - Installment service product from settings
        - Quantity = 1
        - VAT calculated using Odoo tax engine (compute_all)
        - Custom fields populated: total_price, vat, vat_amt, total
        """
        self.ensure_one()

        # ---------------------------------------------------------
        # 1. Validations
        # ---------------------------------------------------------
        if not self.contract_line_ids:
            raise ValidationError(_("Cannot generate invoice without contract lines."))

        if not self.next_invoice_date:
            raise ValidationError(_("Next invoice date is not set."))

        if self.number_of_installments <= 0:
            raise ValidationError(_("Number of installments must be greater than zero."))
        
        '''Code Added on June 09 2026 by Vijaya Bhaskar'''
        if not self.customer_code:
            raise ValidationError(_("Please create the customer in the Penygon Application and enter the same customer code here"))
        
        '''Code Added on July 27 2026 by Vijaya Bhaskar client asked for warwhouse Remove mandatory in save . It should applicable in Confirm (Same as Customer code) '''
        if not self.warehouse_id:
            raise ValidationError(_("Please enter the warehouse")) 
        
        
        # Prevent duplicate invoice
        existing_invoice = self.env['account.move'].search([
            ('contract_origin', '=', self.id),
            ('invoice_date', '=', self.next_invoice_date),
            ('move_type', '=', 'out_invoice')
        ], limit=1)

        if existing_invoice:
            raise ValidationError(
                _("Invoice already exists for %s.") % self.next_invoice_date
            )

        # ---------------------------------------------------------
        # 2. Get Installment Product (product.template → variant)
        # ---------------------------------------------------------
        installment_template_id = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'machine_repair_management.installment_product_id',
                default=0
            )
        )

        if not installment_template_id:
            raise ValidationError(_("Please configure Installment Product in Settings."))

        installment_template = self.env['product.template'].browse(installment_template_id)

        if not installment_template.exists():
            raise ValidationError(_("Configured Installment Product is invalid."))

        installment_product = installment_template.product_variant_id

        # ---------------------------------------------------------
        # 3. Calculate total contract amount
        # ---------------------------------------------------------
        '''Code Added on March 21 2026 by Vijaya Bhaskar'''
        total_contract_amount = sum(
            line.total_selling_price for line in self.contract_line_ids
        )


        if total_contract_amount <= 0:
            raise ValidationError(_("Contract total must be greater than zero."))

        # ---------------------------------------------------------
        # 4. Calculate installment amount
        # ---------------------------------------------------------
        installment_amount = total_contract_amount / self.number_of_installments

        # ---------------------------------------------------------
        # 5. Determine PERIOD dates (CORRECT FORWARD LOGIC)
        # ---------------------------------------------------------
        start_date = self.next_invoice_date
        invoice_date = start_date  # invoice date = period start

        if self.invoice_interval_duration == 'monthly':
            period_end_date = start_date + relativedelta(months=1) - relativedelta(days=1)
            interval_label = "Monthly"
            next_delta = relativedelta(months=1)

        elif self.invoice_interval_duration == 'quarterly':
            period_end_date = start_date + relativedelta(months=3) - relativedelta(days=1)
            interval_label = "Quarterly"
            next_delta = relativedelta(months=3)

        elif self.invoice_interval_duration == 'semi_annual':
            period_end_date = start_date + relativedelta(months=6) - relativedelta(days=1)
            interval_label = "Semi-Annual"
            next_delta = relativedelta(months=6)

        elif self.invoice_interval_duration == 'annual':
            period_end_date = start_date + relativedelta(years=1) - relativedelta(days=1)
            interval_label = "Annual"
            next_delta = relativedelta(years=1)

        else:
            period_end_date = start_date + relativedelta(months=1) - relativedelta(days=1)
            interval_label = "Monthly"
            next_delta = relativedelta(months=1)

        # ---------------------------------------------------------
        # 6. Invoice line description (FIXED END DATE)
        # ---------------------------------------------------------
        product_name = installment_product.name

        line_name = (
            f"{product_name} - {interval_label}\n"
            f"Period: {start_date.strftime('%d-%m-%Y')} "
            f"to {period_end_date.strftime('%d-%m-%Y')}"
        )

        # ---------------------------------------------------------
        # 7. Create invoice (single line)
        # ---------------------------------------------------------
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            # 'invoice_date': invoice_date,
            # code added on July 10 2026  client asked invocie date as today date
            'invoice_date': fields.Date.today(),
            'invoice_date_due': invoice_date,
            'subscription_contract_id': self.id,
            'contract_origin': self.id,
            'ref': self.reference or '',
            'invoice_line_ids': [(0, 0, {
                'product_id': installment_product.id,
                'name': line_name,
                'quantity': 1,
                'price_unit': installment_amount,
                'discount': 0.0,
                'tax_ids': [(6, 0, installment_product.taxes_id.ids)],
            })],
            
            'customer_code' :self.customer_code or False,
            'warehouse_id' :self.warehouse_id.id or False,
            'work_center_id' :self.work_center_id.id or False,
            'work_center_group_id' : self.work_center_group_id.id or False,
            'sales_person_user_id' : self.sales_person_user_id.id or False,
            'invoice_txt' :self.invoice_txt,
            'partner_name' : self.partner_name or False,
            'customer_name' : self.amc_quotation_id.partner_name if self.partner_id.additional_identification_scheme == 'TIN' and self.amc_quotation_id else self.customer_name,
            'street' : self.street or '',
            'street2' : self.street2 or '',
            'customer_city_id' : self.customer_city_id.id or '',
            'district_id' : self.district_id.id or '',
            'state_id' : self.state_id.id or '',
            'country_id' : self.country_id.id or '',
            'zip' : self.zip or '',
        })

        # ---------------------------------------------------------
        # 8. Compute VAT (based on total_price)
        # ---------------------------------------------------------
        line = invoice.invoice_line_ids[:1]

        base_amount = installment_amount

        taxes_result = line.tax_ids.compute_all(
            base_amount,
            currency=invoice.currency_id,
            quantity=1,
            product=line.product_id,
            partner=invoice.partner_id,
        )

        vat_amount = sum(t['amount'] for t in taxes_result.get('taxes', []))
        final_total = base_amount + vat_amount

        tax = line.tax_ids[:1]
        vat_percentage = tax.amount if tax and tax.amount_type == 'percent' else 0.0

        # ---------------------------------------------------------
        # 9. Write custom fields
        # ---------------------------------------------------------
        line.write({
            'total_price': base_amount,
            'vat': vat_percentage,
            'vat_amt': vat_amount,
            'total': final_total,
        })

        # ---------------------------------------------------------
        # 10. Update invoice count
        # ---------------------------------------------------------
        self.invoice_count = self.env['account.move'].search_count([
            ('contract_origin', '=', self.id),
            ('move_type', '=', 'out_invoice')
        ])

        # ---------------------------------------------------------
        # 11. Advance next invoice date
        # ---------------------------------------------------------
        self.next_invoice_date += next_delta

        # ---------------------------------------------------------
        # 12. Open invoice
        # ---------------------------------------------------------
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
            'target': 'current',
            'name': _('Customer Invoice'),
        }


    def action_lock(self):
        """ Lock subscription contract """
        self.lock = True

    def action_to_unlock(self):
        """ Unlock subscription contract """
        self.lock = False

    def action_get_invoice(self):
        """ Access generated invoices """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('contract_origin', '=', self.id)],
        }

    @api.depends('partner_id')
    def _compute_invoice_count(self):
        """ Compute the count of invoices generated """
        self.invoice_count = self.env['account.move'].search_count([
            ('contract_origin', '=', self.id)
        ])

    @api.depends('invoices_active')
    def _compute_invoice_active(self):
        """ Check invoice count to display the invoice smart button """
        invoice_count = self.env['account.move'].search_count([
            ('contract_origin', '=', self.id)
        ])
        if invoice_count != 0:
            self.invoices_active = True
        else:
            self.invoices_active = False

    manual_next_invoice_date = fields.Boolean(
        string='Manual Next Invoice Date',
        default=False,
        help='If set, the next invoice date will not be recomputed automatically'
    )

    @api.depends('date_start', 'recurring_invoice', 'recurring_period', 'recurring_period_interval')
    def _compute_next_invoice_date(self):
        for rec in self:
            if not rec.date_start:
                rec.next_invoice_date = False
                rec.date_end = False
                continue

            # IMPORTANT:
            # next_invoice_date should stay as date_start
            # until invoice is generated
            if not rec.next_invoice_date:
                rec.next_invoice_date = rec.date_start

            # date_end is still computed
            period = int(rec.recurring_period or 0)
            if rec.recurring_period_interval == 'Days':
                rec.date_end = rec.date_start + relativedelta(days=period) - relativedelta(days=1)
            elif rec.recurring_period_interval == 'Weeks':
                rec.date_end = rec.date_start + relativedelta(weeks=period) - relativedelta(days=1)
            elif rec.recurring_period_interval == 'Months':
                rec.date_end = rec.date_start + relativedelta(months=period) - relativedelta(days=1)
            elif rec.recurring_period_interval == 'Years':
                rec.date_end = rec.date_start + relativedelta(years=period) - relativedelta(days=1)
            else:
                rec.date_end = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'next_invoice_date' in vals:
                vals['manual_next_invoice_date'] = True
            if 'invoice_interval_duration' not in vals:
                vals['invoice_interval_duration'] = 'monthly'
            if (
                    self.env["ir.config_parameter"]
                            .sudo()
                            .get_param("machine_repair_management.sequence_creation_bool")
                    == "True"
            ):
                if vals.get('name', 'New') == 'New':
                    now = datetime.now()
                    current_month = now.month
                    current_year = now.year
                    year_str = now.strftime("%y")
                    month_str = now.strftime("%m")

                    # project_id = vals.get("project_id")
                    # amc_id = vals.get("amc_project_id")
                    # is_quotation = vals.get("is_quotation")
                    #
                    # if is_quotation:
                    #     sequence_code = "quotation.machine.repair.support"
                    # elif amc_id and amc_id != project_id:
                    #     sequence_code = "amc.machine.repair.support"
                    # else:
                    #     sequence_code = "machine.repair.support"
                    sequence_code = "crm.contract.creation"
                    sequence = self.env["ir.sequence"].search(
                        [("code", "=", sequence_code)], limit=1
                    )

                    loc = "AMC-"
                    number = 1
                    contract_search = self.env['service.sale.order'].search([('id', '=', vals.get('amc_quotation_id'))],
                                                                            limit=1)
                    crm_search = self.env['crm.lead'].search([('id', '=', contract_search.crm_id.id)], limit=1)
                    location_id = crm_search.customer_city_id.def_work_center_id.id
                    if sequence and sequence.use_date_range and sequence.use_location_wise:
                        for date_range in sequence.date_range_ids:
                            if (
                                    date_range.date_from.month == current_month and
                                    date_range.date_from.year == current_year
                                    and date_range.work_center_id.id == location_id
                            ):
                                loc = date_range.location_code
                                number = date_range.number_next_actual
                                date_range.number_next_actual += 1
                                break

                        seq = f"{sequence.prefix}{loc}{year_str}{month_str}{str(number).zfill(4)}"

                        if self.env["subscription.contracts"].search([("name", "=", seq)], limit=1):
                            raise ValidationError(f"Sequence '{seq}' already exists.")

                        vals["name"] = seq

                    elif sequence and sequence.use_date_range:
                        for date_range in sequence.date_range_ids:
                            if (
                                    date_range.date_from.year == current_year
                            ):
                                loc = date_range.location_code
                                number = date_range.number_next_actual
                                date_range.number_next_actual += 1
                                break

                        seq = f"{sequence.prefix}{loc}{year_str}{month_str}{str(number).zfill(4)}"

                        if self.env["subscription.contracts"].search([("name", "=", seq)], limit=1):
                            raise ValidationError(f"Sequence '{seq}' already exists.")

                        vals["name"] = seq

                    else:
                        vals["name"] = (
                                self.env["ir.sequence"].next_by_code(sequence_code)
                                or "New"
                        )

        return super().create(vals_list)

    # @api.model
    # def create(self, vals):
    #     if 'next_invoice_date' in vals:
    #         vals['manual_next_invoice_date'] = True
    #     if vals.get('name', 'New') == 'New':
    #         vals['name'] = self.env['ir.sequence'].next_by_code('subscription.contracts') or 'New'
    #
    #     # Set default invoice interval duration if not provided
    #     if 'invoice_interval_duration' not in vals:
    #         vals['invoice_interval_duration'] = 'monthly'
    #
    #     return super().create(vals)

    # def write(self, vals):
    #     if 'next_invoice_date' in vals:
    #         vals['manual_next_invoice_date'] = True
    #     return super().write(vals)
    
    '''Code Added on July 04 2026 Number generation based on the month of the start date '''
    def write(self, vals):
        
        res = super().write(vals)
        
        if 'next_invoice_date' in vals:
            vals['manual_next_invoice_date'] = True
          
        if 'date_start' in vals:
            
            '''Client Asked same Bring Number Auto Number generation based on the month of the start date Added on July 04 2026 '''

            yymm = self.date_start.strftime('%y%m')
            # Replace only the YYMM portion before the last 4 sequence digits
            self.name = re.sub(
                r'(\d{4})(\d{4})$',
                lambda m: f'{yymm}{m.group(2)}',
                self.name
            )
            
               
        return res


    # @api.model
    # def subscription_contract_state_change(self):
    #     """ Automatic state change and create invoice """
    #     records = self.env['subscription.contracts'].search([])
    #     for rec in records:
    #         end_date = rec.date_end
    #         expiry_reminder = rec.contract_reminder
    #         expiry_warning_date = date_utils.subtract(end_date,
    #                                                   days=int(
    #                                                       expiry_reminder))
    #         current_date = fields.Date.today()
    #         next_invoice_date = rec.next_invoice_date
    #         if expiry_warning_date <= current_date <= end_date:
    #             rec.write({'state': 'Expire Soon'})
    #         if end_date == current_date:
    #             rec.write({'state': 'Expired'})
    #         if next_invoice_date == current_date and rec.state not in ('New', 'Cancelled', 'Expired'):
    #             date_search = self.env['account.move'].search(
    #                 [('contract_origin', '=', rec.id), ('invoice_date', '=', rec.next_invoice_date)])
    #             if not date_search:
    #
    #                 data = rec.env['account.move'].create([
    #                     {
    #                         'move_type': 'out_invoice',
    #                         'partner_id': rec.partner_id.id,
    #                         'invoice_date': fields.date.today(),
    #                         'invoice_date_due': next_invoice_date,
    #                         'contract_origin': rec.id,
    #                         'ref': rec.reference,
    #                     }])
    #                 for line in rec.contract_line_ids:
    #                     data.write({
    #                         'invoice_line_ids': [(0, 0, {
    #                             'product_id': line.product_id.id,
    #                             'name': line.description,
    #                             'quantity': line.qty_ordered,
    #                             'price_unit': line.price_unit,
    #                             'tax_ids': line.tax_ids,
    #                             'discount': line.discount,
    #                             'analytic_distribution': {line.analytic_account_id.id: 100.0}
    #                         })],
    #                     })
    #                 rec.invoice_count = rec.env['account.move'].search_count([
    #                     ('contract_origin', '=', rec.id)])
    #
    #                 # Calculate next invoice date based on invoice interval duration
    #                 if rec.invoice_interval_duration == 'monthly':
    #                     rec.next_invoice_date = rec.next_invoice_date + relativedelta(months=1)
    #                 elif rec.invoice_interval_duration == 'quarterly':
    #                     rec.next_invoice_date = rec.next_invoice_date + relativedelta(months=3)
    #                 elif rec.invoice_interval_duration == 'semi_annual':
    #                     rec.next_invoice_date = rec.next_invoice_date + relativedelta(months=6)
    #                 elif rec.invoice_interval_duration == 'annual':
    #                     rec.next_invoice_date = rec.next_invoice_date + relativedelta(years=1)
    #                 else:
    #                     rec.next_invoice_date = rec.next_invoice_date + relativedelta(months=1)

    @api.model
    def subscription_contract_state_change(self):
        """Cron: Automatic state change & installment-based invoice creation"""
        contracts = self.env['subscription.contracts'].search([])
        today = fields.Date.today()

        for rec in contracts:
            # -------------------------------------------------
            # 1. Contract state handling
            # -------------------------------------------------
            if rec.date_end:
                reminder_days = int(rec.contract_reminder or 0)
                expiry_warning_date = rec.date_end - relativedelta(days=reminder_days)

                if expiry_warning_date <= today < rec.date_end:
                    rec.state = 'Expire Soon'
                elif today > rec.date_end:
                    rec.state = 'Expired'
                    continue

            # -------------------------------------------------
            # 2. Invoice trigger condition
            # -------------------------------------------------
            if (
                    rec.next_invoice_date != today or
                    rec.state in ('New', 'Cancelled', 'Expired')
            ):
                continue

            # Prevent duplicate invoice
            existing_invoice = self.env['account.move'].search([
                ('contract_origin', '=', rec.id),
                ('invoice_date', '=', rec.next_invoice_date),
                ('move_type', '=', 'out_invoice')
            ], limit=1)

            if existing_invoice:
                continue

            # -------------------------------------------------
            # 2.1 Stop if installments already completed
            # -------------------------------------------------
            created_invoice_count = self.env['account.move'].search_count([
                ('contract_origin', '=', rec.id),
                ('move_type', '=', 'out_invoice'),
            ])

            if created_invoice_count >= rec.number_of_installments:
                rec.write({'state': 'Expired'})
                continue

            # -------------------------------------------------
            # 3. Installment product (from settings)
            # -------------------------------------------------
            template_id = int(
                self.env['ir.config_parameter'].sudo().get_param(
                    'machine_repair_management.installment_product_id', default=0
                )
            )
            if not template_id:
                continue

            installment_product = (
                self.env['product.template']
                .browse(template_id)
                .product_variant_id
            )

            # -------------------------------------------------
            # 4. Installment amount
            # -------------------------------------------------
            total_contract_amount = sum(rec.contract_line_ids.mapped('total_price'))

            if not total_contract_amount or rec.number_of_installments <= 0:
                continue

            installment_amount = total_contract_amount / rec.number_of_installments

            # -------------------------------------------------
            # 5. Period calculation
            # -------------------------------------------------
            start_date = rec.next_invoice_date
            invoice_date = start_date

            if rec.invoice_interval_duration == 'monthly':
                period_end_date = start_date + relativedelta(months=1) - relativedelta(days=1)
                next_delta = relativedelta(months=1)
                label = 'Monthly'

            elif rec.invoice_interval_duration == 'quarterly':
                period_end_date = start_date + relativedelta(months=3) - relativedelta(days=1)
                next_delta = relativedelta(months=3)
                label = 'Quarterly'

            elif rec.invoice_interval_duration == 'semi_annual':
                period_end_date = start_date + relativedelta(months=6) - relativedelta(days=1)
                next_delta = relativedelta(months=6)
                label = 'Semi-Annual'

            elif rec.invoice_interval_duration == 'annual':
                period_end_date = start_date + relativedelta(years=1) - relativedelta(days=1)
                next_delta = relativedelta(years=1)
                label = 'Annual'

            else:
                period_end_date = start_date + relativedelta(months=1) - relativedelta(days=1)
                next_delta = relativedelta(months=1)
                label = 'Monthly'

            product_name = installment_product.name

            line_name = (
                f"{product_name} - {label}\n"
                f"Period: {start_date.strftime('%d-%m-%Y')} "
                f"to {period_end_date.strftime('%d-%m-%Y')}"
            )

            # -------------------------------------------------
            # 6. Create invoice
            # -------------------------------------------------
            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': rec.partner_id.id,
                'invoice_date': invoice_date,
                'invoice_date_due': invoice_date,
                'contract_origin': rec.id,
                'ref': rec.reference or '',
                'invoice_line_ids': [(0, 0, {
                    'product_id': installment_product.id,
                    'name': line_name,
                    'quantity': 1,
                    'price_unit': installment_amount,
                    'tax_ids': [(6, 0, installment_product.taxes_id.ids)],
                })],
            })

            # -------------------------------------------------
            # 7. VAT calculation
            # -------------------------------------------------
            line = invoice.invoice_line_ids[0]

            taxes = line.tax_ids.compute_all(
                installment_amount,
                currency=invoice.currency_id,
                quantity=1,
                product=line.product_id,
                partner=invoice.partner_id,
            )

            vat_amt = sum(t['amount'] for t in taxes.get('taxes', []))
            vat_percent = line.tax_ids[0].amount if line.tax_ids else 0.0

            line.write({
                'total_price': installment_amount,
                'vat': vat_percent,
                'vat_amt': vat_amt,
                'total': installment_amount + vat_amt,
            })

            # -------------------------------------------------
            # 8. Invoice count
            # -------------------------------------------------
            rec.invoice_count = self.env['account.move'].search_count([
                ('contract_origin', '=', rec.id),
                ('move_type', '=', 'out_invoice')
            ])

            # -------------------------------------------------
            # 9. Advance next invoice date (SAFE & FINAL)
            # -------------------------------------------------
            if rec.next_invoice_date < rec.date_end:
                rec.with_context(skip_invoice_date_check=True).write({
                    'next_invoice_date': rec.next_invoice_date + next_delta
                })
            else:
                rec.write({'state': 'Expired'})

    @api.depends('current_reference')
    def _compute_sale_order_lines(self):
        """ Get sale order line of contract lines """
        self.current_reference = self.id

        product_id = self.contract_line_ids.mapped('product_id')
        sale_order_line = self.env['sale.order.line'].search([
            ('order_partner_id', '=', self.partner_id.id)
        ])
        for rec in sale_order_line:
            rec_date = rec.create_date.date()
            if self.date_start <= rec_date <= self.date_end:
                if rec.product_id in product_id:
                    rec.contract_id = self.id

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
        return self.env.ref('sales_contract_and_recurring_invoices.action_report_contract_document').report_action(self)
    
    def action_download_word_document(self):
        ids_str = ','.join(map(str, self.ids))
        url = f'/contract/download_word/{ids_str}'
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
    
    @api.model
    def number_to_words(self, number):
        try:
            if number is None or number == '':
                _logger.info("number_to_words called → Zero")
                return "Zero"

            n = int(float(number))
            words = num2words(n, lang='en').capitalize()

            _logger.info("Converted %s → %s", number, words)

            return words

        except Exception as e:
            _logger.error("number_to_words FAILED for %r: %s", number, e)

            try:
                fallback = str(int(float(number)))
                return fallback
            except Exception:
                return str(number)

    @api.model
    def number_to_words_ar(self, number):
        """Convert numeric value to Arabic words."""
        try:
            if number is None or number == '':
                return "صفر"

            n = int(float(number))
            return num2words(n, lang='ar')

        except Exception as e:
            _logger.error("number_to_words_ar FAILED for %r: %s", number, e)
            try:
                return str(int(float(number)))
            except:
                return str(number)

    # contract_payment_line_ids = fields.One2many(
    #     'contract.payment.schedule.line',
    #     'contract_id',
    #     string='Contract payment details',
    #     help='Products to be added in the contract payment'
    # )



class SubscriptionContractImage(models.Model):
    _name = 'subscription.contract.image'
    _description = 'Subscription Contract Images'

    contract_id = fields.Many2one(
        'subscription.contracts',
        string='Contract',
        ondelete='cascade'
    )

    name = fields.Char("Description")
    image = fields.Image(
        string="Image",
        attachment=True
    )
