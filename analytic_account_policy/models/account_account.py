from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import format_date, frozendict



class AcccountAccount(models.Model):
    _inherit = 'account.account'

    analytic_account_policy = fields.Boolean(string='Policy for analytic account',help=("Sets the policy for analytic accounts"))


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self, vals):
        self._onchange_invoice_line_ids_inherit()
        inv_id = super(AccountMove, self).create(vals)
        # if inv_id.move_type in ('out_invoice', 'in_invoice') and inv_id.inv_description:
        #     inv_id.invoice_line_ids.name = inv_id.inv_description
        return inv_id


    @api.onchange('invoice_line_ids')
    def _onchange_invoice_line_ids_inherit(self):
        super()._onchange_quick_edit_line_ids()
        for rec in self.invoice_line_ids:
            analytic_account = rec.analytic_distribution
            for line in self.line_ids:
                if analytic_account:
                    line.write({'analytic_distribution': analytic_account})


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'
    
    
    def _create_invoices(self, sale_orders):
        self.ensure_one()
        if self.advance_payment_method == 'delivered':
            invoices = sale_orders._create_invoices(
            final=self.deduct_down_payments, 
            grouped=not self.consolidated_billing
        )
        
        # Iterate through the invoices and update analytic distribution
            for invoice in invoices:
                for line in invoice.line_ids:
                    if line.account_id.analytic_account_policy:
                        analytic_id = self.sale_order_ids.warehouse_id.analytic_id.id
                        if analytic_id:
                            line.update({'analytic_distribution': {analytic_id: 100}})
            return invoices
            # return sale_orders._create_invoices(final=self.deduct_down_payments, grouped=not self.consolidated_billing)
           
        else:
            self.sale_order_ids.ensure_one()
            self = self.with_company(self.company_id)
            order = self.sale_order_ids

            # Create deposit product if necessary
            if not self.product_id:
                self.company_id.sudo().sale_down_payment_product_id = self.env['product.product'].create(
                    self._prepare_down_payment_product_values()
                )
                self._compute_product_id()

            # Create down payment section if necessary
            SaleOrderline = self.env['sale.order.line'].with_context(sale_no_log_for_new_lines=True)
            if not any(line.display_type and line.is_downpayment for line in order.order_line):
                SaleOrderline.create(
                    self._prepare_down_payment_section_values(order)
                )

            down_payment_lines = SaleOrderline.create(
                self._prepare_down_payment_lines_values(order)
            )

            invoice = self.env['account.move'].sudo().create(
                self._prepare_invoice_values(order, down_payment_lines)
            )
            for line in invoice.line_ids:
                if line.account_id.analytic_account_policy:
                    line.update({'analytic_distribution':{self.sale_order_ids.warehouse_id.analytic_id.id:100}})

            
            # Ensure the invoice total is exactly the expected fixed amount.
            if self.advance_payment_method == 'fixed':
                delta_amount = (invoice.amount_total - self.fixed_amount) * (1 if invoice.is_inbound() else -1)
                if not order.currency_id.is_zero(delta_amount):
                    receivable_line = invoice.line_ids\
                        .filtered(lambda aml: aml.account_id.account_type == 'asset_receivable')[:1]
                    product_lines = invoice.line_ids\
                        .filtered(lambda aml: aml.display_type == 'product')
                    tax_lines = invoice.line_ids\
                        .filtered(lambda aml: aml.tax_line_id.amount_type not in (False, 'fixed'))

                    if product_lines and tax_lines and receivable_line:
                        line_commands = [Command.update(receivable_line.id, {
                            'amount_currency': receivable_line.amount_currency + delta_amount,
                        })]
                        delta_sign = 1 if delta_amount > 0 else -1
                        for lines, attr, sign in (
                            (product_lines, 'price_total', -1),
                            (tax_lines, 'amount_currency', 1),
                        ):
                            remaining = delta_amount
                            lines_len = len(lines)
                            for line in lines:
                                if order.currency_id.compare_amounts(remaining, 0) != delta_sign:
                                    break
                                amt = delta_sign * max(
                                    order.currency_id.rounding,
                                    abs(order.currency_id.round(remaining / lines_len)),
                                )
                                remaining -= amt
                                line_commands.append(Command.update(line.id, {attr: line[attr] + amt * sign}))
                        invoice.line_ids = line_commands

            # Unsudo the invoice after creation if not already sudoed
            invoice = invoice.sudo(self.env.su)
           

            poster = self.env.user._is_internal() and self.env.user.id or SUPERUSER_ID
            invoice.with_user(poster).message_post_with_source(
                'mail.message_origin_link',
                render_values={'self': invoice, 'origin': order},
                subtype_xmlid='mail.mt_note',
            )

            title = _("Down payment invoice")
            order.with_user(poster).message_post(
                body=_("%s has been created", invoice._get_html_link(title=title)),
            )

            return invoice

   




# class AccountMoveline(models.Model):
#     _inherit = 'account.move.line'
#
#     analytic_cd = fields.Boolean(string='Analytic Code')
#
#     @api.onchange('account_id')
#     def _onchange_line_ids(self):
#         for rec in self:
#             if rec.account_id.analytic_account_policy == True:
#                 rec.analytic_cd = True
#             else:
#                 rec.analytic_cd = False


# class SaleAdvancePaymentInv(models.TransientModel):
#     _inherit = 'sale.advance.payment.inv'
#
#     @api.model
#     def create(self, vals):
#         invoice = self.env['account.move']
#         invoice._onchange_invoice_line_ids()
#         print('INVOICEssssssssssssssssss',invoice)
#         inv = super(SaleAdvancePaymentInv, self).create(vals)
#         # if inv_id.move_type in ('out_invoice', 'in_invoice') and inv_id.inv_description:
#         #     inv_id.invoice_line_ids.name = inv_id.inv_description
#         return inv



# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'
#
#     @api.model
#     def create(self, vals):
#
#         line = super(AccountMoveLine, self).create(vals)
#         if line.exclude_from_invoice_tab == True and not line.analytic_account_id:
#             analytic_account = False
#             for li in line.move_id.line_ids:
#                 if li.analytic_account_id:
#                     analytic_account = li.analytic_account_id
#                     break;
#             print('Line:',analytic_account)
#             line.analytic_account_id = analytic_account
#         # if inv_id.move_type in ('out_invoice', 'in_invoice') and inv_id.inv_description:
#         #     inv_id.invoice_line_ids.name = inv_id.inv_description
#         return line
