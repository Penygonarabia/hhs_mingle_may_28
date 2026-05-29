from odoo import fields, models,api,_
from decimal import Decimal,ROUND_UP
from odoo.tools import float_round

class AccountMove(models.Model):
    """ Inheriting account move model to add id of subscription """
    _inherit = 'account.move'

    contract_origin = fields.Integer(string='Subscription Contract',
                                     help='Reference of Subscription Contract')
    subscription_contract_id = fields.Many2one('subscription.contracts',string='Subscription Contracts', help='Subscription Contract Reference')
    untaxed_amount = fields.Monetary(string="Sub Total", compute="_compute_total_amount", store=True)

    vat_amount = fields.Monetary(string="VAT Amount", compute="_compute_total_amount", store=True)

    grand_total_amount = fields.Monetary(string="Total", compute="_compute_total_amount", store=True)
    amount_due = fields.Monetary(
        string="Amount Due",
        compute="_compute_amount_due",
        store=True,  # Recommended for filtering/reporting
        help="Remaining contract amount yet to be invoiced after this invoice"
    )

    def unlink(self):
        for record in self:
            # Ensure `contract_origin` refers to the correct field
            contracts = self.env['subscription.contracts'].search([
                ('id', '=', record.contract_origin)
            ])
            for contract in contracts:
                # Adjust the invoice count
                contract.invoice_count -= 1
        return super(AccountMove, self).unlink()

    @api.depends('invoice_line_ids.quantity', 'invoice_line_ids.price_unit',
                 'invoice_line_ids.vat')
    def _compute_total_amount(self):
        for rec in self:
            rec.untaxed_amount = sum(line.total_price for line in rec.invoice_line_ids)
            rec.untaxed_amount = float_round(rec.untaxed_amount, precision_digits=2)
            rec.vat_amount = sum(line.vat_amt for line in rec.invoice_line_ids)
            rec.vat_amount = float_round(rec.vat_amount, precision_digits=2)
            rec.grand_total_amount = rec.untaxed_amount + rec.vat_amount
            rec.grand_total_amount = float_round(rec.grand_total_amount, precision_digits=2)

    @api.depends(
        'subscription_contract_id',
        'subscription_contract_id.contract_line_ids.total_price',
        'subscription_contract_id.contract_line_ids.vat_amt',
        'subscription_contract_id.invoice_interval_duration',
        'subscription_contract_id.contract_duration_days',
        'move_type',
        'state'
    )
    def _compute_amount_due(self):
        for invoice in self:
            invoice.amount_due = 0.0

            # Only compute for customer invoices linked to a subscription contract
            if invoice.move_type != 'out_invoice' or not invoice.subscription_contract_id:
                continue

            contract = invoice.subscription_contract_id

            # Safety check
            if not contract.contract_line_ids:
                continue

            # Full contract total (untaxed + VAT)
            contract_untaxed = sum(line.total_price for line in contract.contract_line_ids)
            contract_vat = sum(line.vat_amt for line in contract.contract_line_ids)
            contract_grand_total = contract_untaxed + contract_vat

            # Calculate total planned installments
            if not contract.invoice_interval_duration or not contract.contract_duration_days:
                total_installments = 1
            else:
                contract_years = contract.contract_duration_days / 365.0
                if contract.invoice_interval_duration == 'monthly':
                    total_installments = max(1, int(round(contract_years * 12)))
                elif contract.invoice_interval_duration == 'quarterly':
                    total_installments = max(1, int(round(contract_years * 4)))
                elif contract.invoice_interval_duration == 'semi_annual':
                    total_installments = max(1, int(round(contract_years * 2)))
                elif contract.invoice_interval_duration == 'annual':
                    total_installments = max(1, int(round(contract_years)))
                else:
                    total_installments = 1

            # Count how many invoices already exist for this contract (including current one)
            generated_count = self.env['account.move'].search_count([
                ('subscription_contract_id', '=', contract.id),
                ('move_type', '=', 'out_invoice'),
            ])

            # Remaining installments
            remaining_installments = max(0, total_installments - generated_count)

            # Amount due = remaining amount to be billed
            if total_installments > 0:
                per_installment_amount = contract_grand_total / total_installments
                invoice.amount_due = float_round(
                    remaining_installments * per_installment_amount,
                    precision_digits=0
                )

class AccountMoveLine(models.Model):

    _inherit = "account.move.line"

    vat = fields.Float(string='VAT (%)', default=0.0)
    vat_amt = fields.Float(string="VAT")
    total = fields.Float(string='Net Price', compute="_compute_total_amount", store=True)
    total_price = fields.Float(string="Total Price")

    @api.depends('total_price', 'vat_amt')
    def _compute_total_amount(self):
        for rec in self:
            rec.total = float_round(rec.total_price + rec.vat_amt, precision_digits=2)









