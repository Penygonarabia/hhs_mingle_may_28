from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta


# Payment label mapping (ordinal names)
_ORDINAL_LABELS = [
    'الدفعة الأولى — First Payment',
    'الدفعة الثانية — Second Payment',
    'الدفعة الثالثة — Third Payment',
    'الدفعة الرابعة — Fourth Payment',
    'الدفعة الخامسة — Fifth Payment',
    'الدفعة السادسة — Sixth Payment',
    'الدفعة السابعة — Seventh Payment',
    'الدفعة الثامنة — Eighth Payment',
    'الدفعة التاسعة — Ninth Payment',
    'الدفعة العاشرة — Tenth Payment',
    'الدفعة الحادية عشرة — Eleventh Payment',
    'الدفعة الثانية عشرة — Twelfth Payment',
]

_ORDINAL_LABELS_EN = [
    "First Payment",
    "Second Payment",
    "Third Payment",
    "Fourth Payment",
    "Fifth Payment",
    "Sixth Payment",
    "Seventh Payment",
    "Eighth Payment",
    "Ninth Payment",
    "Tenth Payment",
    "Eleventh Payment",
    "Twelfth Payment",
]

_ORDINAL_LABELS_AR = [
    "الدفعة الأولى",
    "الدفعة الثانية",
    "الدفعة الثالثة",
    "الدفعة الرابعة",
    "الدفعة الخامسة",
    "الدفعة السادسة",
    "الدفعة السابعة",
    "الدفعة الثامنة",
    "الدفعة التاسعة",
    "الدفعة العاشرة",
    "الدفعة الحادية عشرة",
    "الدفعة الثانية عشرة",
]

class SubscriptionContracts(models.Model):
    _inherit = 'subscription.contracts'

    # --- Payment Terms Tab Fields ---
    payment_schedule_line_ids = fields.One2many(
        'contract.payment.schedule.line',
        'contract_id',
        string='Payment Schedule',
        copy=False
    )

    annual_contract_value = fields.Float(
        string='Annual Contract Value (SAR)',
        compute='_compute_annual_contract_value',
        store=True,
        digits=(16, 2),
        help='Total contract value including VAT'
    )

    payment_frequency_text = fields.Char(
        string='Payment Frequency',
        compute='_compute_payment_frequency_text',
        store=True,
        help='Description of payment frequency'
    )

    late_payment_note = fields.Text(
        string='Late Payment Policy',
        default=lambda self: self._default_late_payment_note()
    )

    @api.model
    def _default_late_payment_note(self):
        return (
            "Late payments may result in the suspension of services until "
            "the overdue dues are settled, and the first party has the right "
            "to terminate the contract if the second party does not commit "
            "to paying any of the financial dues."
        )

    @api.depends('amount_total')
    def _compute_annual_contract_value(self):
        for rec in self:
            rec.annual_contract_value = rec.amount_total or 0.0

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

    # def action_generate_payment_schedule(self):
    #     """Generate the payment schedule lines based on contract settings."""
    #     self.ensure_one()

    #     # Clear existing schedule lines
    #     self.payment_schedule_line_ids.unlink()

    #     num_installments = self.number_of_installments or 1
    #     total_value = self.annual_contract_value or 0.0

    #     if total_value <= 0 or num_installments <= 0:
    #         return

    #     installment_amount = round(total_value / num_installments, 2)

    #     # Determine start date for payments
    #     start_date = self.next_invoice_date or self.date_start or fields.Date.today()

    #     # Determine interval delta based on frequency
    #     _DELTA_MAP = {
    #         'monthly': relativedelta(months=1),
    #         'quarterly': relativedelta(months=3),
    #         'semi_annual': relativedelta(months=6),
    #         'annual': relativedelta(years=1),
    #     }
    #     delta = _DELTA_MAP.get(self.invoice_interval_duration, relativedelta(months=1))

    #     lines_vals = []
    #     remaining = total_value
    #     for i in range(num_installments):
    #         payment_date = start_date + (delta * i)

    #         # Last installment gets any rounding remainder
    #         if i == num_installments - 1:
    #             amount = round(remaining, 2)
    #         else:
    #             amount = installment_amount
    #             remaining -= amount

    #         # Label: "First Payment", "Second Payment", etc.
    #         if i < len(_ORDINAL_LABELS):
    #             label = f"{_ORDINAL_LABELS[i]} Payment"
    #         else:
    #             label = f"Payment #{i + 1}"

    #         lines_vals.append((0, 0, {
    #             'sequence': (i + 1) * 10,
    #             'name': label,
    #             'payment_date': payment_date,
    #             'amount': amount,
    #             'state': 'pending',
    #         }))

    #     self.write({'payment_schedule_line_ids': lines_vals})


    def action_generate_payment_schedule(self):
        for rec in self:

            # ✅ Only allow in NEW state
            if rec.state != 'New':
                continue

            # ✅ Skip if already invoiced/paid
            if any(line.state in ('invoiced', 'paid') for line in rec.payment_schedule_line_ids):
                continue

            # 🛑 Clear existing schedule safely
            rec.payment_schedule_line_ids = [(5, 0, 0)]

            num_installments = rec.number_of_installments or 1
            total_value = rec.annual_contract_value or 0.0

            if total_value <= 0:
                continue

            installment_amount = total_value / num_installments
            remaining = total_value

            start_date = rec.date_start or fields.Date.today()

            delta_map = {
                'monthly': relativedelta(months=1),
                'quarterly': relativedelta(months=3),
                'semi_annual': relativedelta(months=6),
                'annual': relativedelta(years=1),
            }
            delta = delta_map.get(rec.invoice_interval_duration, relativedelta(months=1))

            lines_vals = []

            for i in range(num_installments):
                payment_date = start_date + (delta * i)

                if i == num_installments - 1:
                    amount = round(remaining, 2)
                else:
                    amount = round(installment_amount, 2)
                    remaining -= amount

                if i < len(_ORDINAL_LABELS_EN):
                    label_en = _ORDINAL_LABELS_EN[i]
                    label_ar = _ORDINAL_LABELS_AR[i]
                else:
                    label_en = f"Payment {i + 1}"
                    label_ar = f"الدفعة {i + 1}"

                lines_vals.append((0, 0, {
                    'sequence': (i + 1) * 10,
                    'name': label_en,
                    'name_ara': label_ar,
                    'payment_date': payment_date,
                    'amount': amount,
                    'state': 'pending',
                }))

            rec.payment_schedule_line_ids = lines_vals

    @api.onchange('date_start', 'invoice_interval_duration', 'number_of_installments')
    def _onchange_generate_payment_schedule(self):
        for rec in self:
            rec.payment_schedule_line_ids = [(5, 0, 0)]  # clear UI cache
            rec.action_generate_payment_schedule()

    name = fields.Char(
        string='Contract No.',
        required=True,
        default='New',
        readonly=True,
        copy=False
    )


    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('subscription.contract') or 'New'

        rec = super().create(vals)
        rec.action_generate_payment_schedule()
        return rec

    def write(self, vals):
        res = super().write(vals)

        trigger_fields = {'date_start', 'invoice_interval_duration', 'number_of_installments'}

        if trigger_fields.intersection(vals.keys()):
            for rec in self:
                # ✅ regenerate AFTER recompute
                rec.action_generate_payment_schedule()

        return res

    @api.onchange('payment_schedule_line_ids')
    def _onchange_payment_schedule_line_ids(self):

        for rec in self:

            if not rec.payment_schedule_line_ids:
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

            # sort lines
            lines = rec.payment_schedule_line_ids.sorted(
                key=lambda l: l.sequence
            )

            previous_date = False

            for idx, line in enumerate(lines):

                # keep manually edited date
                if idx == 0:
                    previous_date = line.payment_date
                    continue

                if not previous_date:
                    continue

                # skip locked lines
                if line.state in ('invoiced', 'paid'):
                    previous_date = line.payment_date
                    continue

                new_date = previous_date + delta

                line.payment_date = new_date

                previous_date = new_date
