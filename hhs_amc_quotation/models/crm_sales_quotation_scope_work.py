from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

# Payment label mapping (ordinal names)
_ORDINAL_LABELS = [
    'First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth',
    'Seventh', 'Eighth', 'Ninth', 'Tenth', 'Eleventh', 'Twelfth',
]
_ORDINAL_LABELS_AR = [
    'الأول', 'الثاني', 'الثالث', 'الرابع', 'الخامس',
    'السادس', 'السابع', 'الثامن', 'التاسع', 'العاشر',
    'الحادي عشر', 'الثاني عشر', 'الثالث عشر', 'الرابع عشر', 'الخامس عشر',
    'السادس عشر', 'السابع عشر', 'الثامن عشر', 'التاسع عشر', 'العشرون'
]


class ServiceSaleOrder(models.Model):
    _inherit = 'service.sale.order'

    scope_line_ids = fields.One2many(
        'sales.order.scope',
        'scope_order_id',
        string="Scope of Work"
    )

    payment_term_ids = fields.One2many(
        'quotation.payment.term',
        'payment_order_id',
        string="Payment Term"
    )

    payment_frequency_text = fields.Char(
        string="Payment Frequency",
        compute="_compute_payment_frequency_text",
        store=True
    )

    late_payment_note = fields.Text(
        string="Late Payment Policy",
        default=lambda self: self._default_late_payment_note()
    )
    
    terms_of_execution = fields.Text(string="Terms of Execution", default = lambda self:(self.env['ir.config_parameter']
        .sudo()
        .get_param('crm_custom_view.terms_of_execution',default='')
    ).replace('\\n', '\n'))
    exclusions_text = fields.Text(string="Exclusions", default = lambda self:self.env['ir.config_parameter'].sudo().get_param('crm_custom_view.exclusions', default='').replace('\\n', '\n'))
    enable_scope = fields.Boolean(string="Enable Scope")

    '''Code Added on March 21 2026 by Vijaya bhaskar'''
    others_text = fields.Text(string="Notes", default = lambda self:self.env['ir.config_parameter'].sudo().get_param('crm_custom_view.notes',default='').replace('\\n', '\n'))


    @api.model
    def _default_late_payment_note(self):
        return (
            "Late payments may result in the suspension of services until "
            "the overdue dues are settled, and the first party has the right "
            "to terminate the contract if the second party does not commit "
            "to paying any of the financial dues."
        )

    late_payment_note = fields.Text(
        string='Late Payment Policy',
        default=lambda self: self._default_late_payment_note()
    )

    annual_quotation_value = fields.Float(
        string="Annual Contract Value",
        compute="_compute_annual_quotation_value",
        store=True,
        digits=(16, 2)
    )

    # 20260408 Gokul
    subject = fields.Text(string="Subject", default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
        'crm_custom_view.subject', default='').replace('\\n', '\n'))
    scope_of_work = fields.Text(string="Scope of Work", default = lambda self : self.env['ir.config_parameter'].sudo().get_param('crm_custom_view.scope_of_work',default='').replace('\\n', '\n'))
    
    others = fields.Text(string="Others",default = lambda self : self.env['ir.config_parameter'].sudo().get_param('crm_custom_view.others_txt', default='').replace('\\n', '\n'))


    @api.depends('grand_total_amount')
    def _compute_annual_quotation_value(self):
        for rec in self:
            rec.annual_quotation_value = rec.grand_total_amount

    @api.depends('invoice_interval_duration')
    def _compute_payment_frequency_text(self):
        _FREQ_MAP = {
            'monthly': ('monthly', '1 month'),
            'quarterly': ('quarterly', '3 months'),
            'semi_annual': ('semi-annually', '6 months'),
            'annual': ('annually', '12 months'),
        }
        for rec in self:
            if rec.invoice_interval_duration and rec.invoice_interval_duration in _FREQ_MAP:
                freq_label, period = _FREQ_MAP[rec.invoice_interval_duration]
                rec.payment_frequency_text = (
                    f"Payment shall be made {freq_label} in advance "
                    f"(every {period})."
                )
            else:
                rec.payment_frequency_text = ''

    @api.onchange('invoice_interval_duration')
    def _onchange_invoice_interval(self):

        for rec in self:

            if not rec.number_of_installments:
                rec.payment_term_ids = [(5, 0, 0)]
                continue

            # SAVE existing first payment date BEFORE clearing
            existing_first_date = False

            if rec.payment_term_ids:
                first_line = rec.payment_term_ids.sorted('sequence')[0]

                if first_line.payment_date:
                    existing_first_date = first_line.payment_date

            # CLEAR OLD ROWS
            rec.payment_term_ids = [(5, 0, 0)]

            num_installments = rec.number_of_installments
            # total_value = rec.annual_quotation_value
            
            '''Code Added on May 13 2026 by Vijaya Bhaskar due to grand total is not added in the payment terms'''
            grand_total = 0.0
            total_value = 0.0
            for line in rec.service_sale_order_line_ids:
                grand_total += line.total_amc
            
            total_value = grand_total


            installment_amount = round(total_value / num_installments, 2)

            # USE edited first payment date if available
            start_date = (
                    existing_first_date
                    or rec.service_sale_quotation_date
                    or fields.Date.today()
            )

            delta_map = {
                'monthly': relativedelta(months=1),
                'quarterly': relativedelta(months=3),
                'semi_annual': relativedelta(months=6),
                'annual': relativedelta(years=1),
            }

            delta = delta_map.get(
                rec.invoice_interval_duration,
                relativedelta(months=1)
            )

            remaining = total_value
            lines = []

            for i in range(num_installments):

                payment_date = start_date + (delta * i)

                if i == num_installments - 1:
                    amount = round(remaining, 2)
                else:
                    amount = installment_amount
                    remaining -= amount

                if i < len(_ORDINAL_LABELS):
                    label = f"{_ORDINAL_LABELS[i]} Payment"
                    label_ar = f"دفعة {_ORDINAL_LABELS_AR[i]}"
                else:
                    label = f"Payment #{i + 1}"
                    label_ar = f"دفعة {i + 1}"

                lines.append((0, 0, {
                    'sequence': (i + 1) * 10,
                    'name': label,
                    'name_arabic': label_ar,
                    'payment_date': payment_date,
                    'amount': amount,
                    'state': 'pending',
                }))

            rec.payment_term_ids = lines

    @api.onchange('service_sale_order_line_ids', 'service_sale_order_line_ids.product_id')
    def _onchange_service_sale_order_line_ids(self):

        for rec in self:

            if not rec.grand_total_amount or not rec.amc_quotation:
                '''Code Added on May 13 2026 by Vijaya Bhaskar due to amount is not added in the order lines then  payment terms also not have'''
                rec.payment_term_ids = [(5,0,0)]

                continue

            num_installments = rec.number_of_installments
            # total_value = rec.annual_quotation_value

            if not num_installments:
                continue

            # Create lines only if empty
            if not rec.payment_term_ids:
                rec._onchange_invoice_interval()
                
            '''Code Added on May 13 2026 by Vijaya Bhaskar due to grand total is not added in the payment terms'''
   
            grand_total = 0.0
            for line in rec.service_sale_order_line_ids:
                grand_total += line.total_amc    
            
            total_value = grand_total    

            installment_amount = round(total_value / num_installments, 2)

            remaining = total_value

            payment_lines = rec.payment_term_ids.sorted('sequence')

            for i, line in enumerate(payment_lines):

                # Last installment adjustment
                if i == num_installments - 1:
                    amount = round(remaining, 2)
                else:
                    amount = installment_amount
                    remaining -= amount

                # ONLY update amount
                line.amount = amount

    @api.onchange('payment_term_ids')
    def _onchange_payment_term_ids(self):

        for rec in self:

            if not rec.payment_term_ids:
                continue

            delta_map = {
                'monthly': relativedelta(months=1),
                'quarterly': relativedelta(months=3),
                'semi_annual': relativedelta(months=6),
                'annual': relativedelta(years=1),
            }

            delta = delta_map.get(
                rec.invoice_interval_duration,
                relativedelta(months=1)
            )

            lines = rec.payment_term_ids.sorted('sequence')

            previous_date = False

            for index, line in enumerate(lines):

                # First row
                if index == 0:

                    if not line.payment_date:
                        line.payment_date = (
                                rec.service_sale_quotation_date
                                or fields.Date.today()
                        )

                    previous_date = line.payment_date
                    continue

                # ALWAYS recalculate next rows
                if previous_date:
                    new_date = previous_date + delta

                    line.payment_date = new_date

                    previous_date = new_date


class QuotationScopeofWork(models.Model):
    _name = 'sales.order.scope'
    _description = 'Quotation Scope of Work'

    name = fields.Many2one(
        'amc.scope.of.work',
        string="Scope of Work"
    )
    is_selected = fields.Boolean(string="Select")

    # payment_term_id=fields.Char("Payment Term")
    payment_term_id = fields.Many2one(
        'quotation.payment.term',
        string="Payment Term"
    )

    scope_order_id = fields.Many2one(
        'service.sale.order',
        string="Sale Order",
        ondelete='cascade'
    )

    @api.onchange('scope_line_ids')
    def _onchange_scope_lines(self):
        for rec in self:
            lines = []
            master_records = self.env['amc.scope.of.work'].search([
                ('amc_auto_populate', '=', True)
            ])
            for m in master_records:
                lines.append((0, 0, {
                    'name': m.id,
                    'amc_soc_work': m.amc_soc_work,
                    'amc_soc_description': m.amc_soc_description,
                }))

            rec.scope_line_ids = lines
        print("Scope+++++++++++++++++++", lines)

    @api.constrains('name', 'scope_order_id')
    def _check_duplicate_scope(self):
        for rec in self:
            if not rec.name or not rec.scope_order_id:
                continue

            duplicates = self.search([
                ('name', '=', rec.name.id),
                ('scope_order_id', '=', rec.scope_order_id.id),
                ('id', '!=', rec.id)
            ], limit=1)

            if duplicates:
                raise ValidationError(
                    _("You cannot add the same Scope '%s' more than once in this quotation.") % rec.name.display_name
                )


class QuotationPaymentTerm(models.Model):
    _name = 'quotation.payment.term'
    _description = 'Quotation Payment Term'

    payment_order_id = fields.Many2one(
        'service.sale.order',
        string="Payment Order",
        ondelete='cascade'
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    sequence = fields.Integer(string='#', default=10)
    name = fields.Char(string='Payment Label', required=True)
    name_arabic = fields.Char(string='Payment Arabic')
    payment_date = fields.Date(string='Payment Date', required=True)
    amount = fields.Float(string='Amount (SAR)', digits=(16, 2))
    state = fields.Selection([
        ('pending', 'Pending'),
        ('invoiced', 'Invoiced'),
        ('paid', 'Paid'),
    ], string='Status', default='pending')

