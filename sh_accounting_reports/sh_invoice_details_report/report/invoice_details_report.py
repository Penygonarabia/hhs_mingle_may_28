# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from datetime import timedelta
import pytz
from odoo import api, fields, models


class ReportInvoiceDetails(models.AbstractModel):
    _name = 'report.sh_accounting_reports.sh_invoice_details_report_doc'
    _description = "Invoice details abstract model"

    @api.model
    def get_invoice_details(self, date_start=False, date_stop=False, move_type=False, company_ids=False, state=False):
        """ Serialise the orders of the day information

        params: date_start, date_stop string representing the datetime of order
        """

        if date_start:
            date_start = fields.Date.from_string(date_start)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Date.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if date_stop:
            date_stop = fields.Date.from_string(date_stop)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        if company_ids:
            domain = [
                ('invoice_date', '>=', fields.Date.to_string(date_start)),
                ('invoice_date', '<=', fields.Date.to_string(date_stop)),
                ('company_id', 'in', company_ids.ids)
            ]
        else:
            domain = [
                ('invoice_date', '>=', fields.Date.to_string(date_start)),
                ('invoice_date', '<=', fields.Date.to_string(date_stop)),
            ]
        if state:
            if state == 'posted':
                domain.append(('state', '=', 'posted'))
            elif state == 'draft':
                domain.append(('state', '=', 'draft'))
            else:
                domain.append(('state', '=', 'cancel'))
        if move_type:
            if move_type == 'out_invoice':
                domain.append(('move_type', '=', 'out_invoice'))
            elif move_type == 'in_invoice':
                domain.append(('move_type', '=', 'in_invoice'))
            elif move_type == 'out_refund':
                domain.append(('move_type', '=', 'out_refund'))
            else:
                domain.append(('move_type', '=', 'in_refund'))

        moves = self.env['account.move'].sudo().search(domain)
        user_currency = self.env.company.currency_id
        total = 0.0
        products_sold = {}
        taxes = {}
        invoice_id_list = []
        for move in moves:
            if user_currency != move.currency_id:
                total += move.currency_id.compute(
                    move.amount_total, user_currency)
            else:
                total += move.amount_total
            currency = move.currency_id
            for line in move.invoice_line_ids:
                if not line.display_type:
                    key = (line.product_id, line.price_unit, line.discount)
                    products_sold.setdefault(key, 0.0)
                    products_sold[key] += line.quantity

                    if line.tax_ids:
                        line_taxes = line.tax_ids.compute_all(line.price_unit * (1 - (line.discount or 0.0) / 100.0), currency,
                                                              line.quantity, product=line.product_id, partner=line.move_id.partner_id or False)
                        for tax in line_taxes['taxes']:
                            taxes.setdefault(
                                tax['id'], {'name': tax['name'], 'total': 0.0})
                            taxes[tax['id']]['total'] += tax['amount']

            if move:
                f_invoices = move.filtered(
                    lambda inv: inv.state not in ['draft', 'cancel'])
                if f_invoices:
                    invoice_id_list += f_invoices.ids

        account_payment_obj = self.env["account.payment"]
        account_journal_obj = self.env["account.journal"]

        search_journals = account_journal_obj.sudo().search([
            ('type', 'in', ['bank', 'cash'])
        ])

        journal_wise_total_payment_list = []
        if invoice_id_list and search_journals:
            for journal in search_journals:
                invoice_domain = [
                    ('id', 'in', invoice_id_list)
                ]
                invoices = self.env['account.move'].sudo().search(
                    invoice_domain)
                for invoice in invoices:
                    payment_domain = []
                    payment_domain.append(
                        ("payment_type", "in", ["inbound", "outbound"]))
                    payment_domain.append(("ref", "=", invoice.name))
                    payment_domain.append(("journal_id", "=", journal.id))
                    payments = account_payment_obj.sudo().search(payment_domain)
                    paid_total = 0.0
                    if payments:
                        for payment in payments:
                            paid_total += payment.amount

                    journal_wise_total_payment_list.append(
                        {"name": journal.name, "total": paid_total})
        else:
            journal_wise_total_payment_list = []

        result = {}
        if journal_wise_total_payment_list:
            for data in journal_wise_total_payment_list:
                if data['name'] not in result:
                    result[data['name']] = data['total']
                else:
                    for key, val in result.items():
                        if key == data['name']:
                            result[data['name']] = val + data['total']
                            break
        if result:
            journal_wise_total_payment_list = [result]
        else:
            result = {"Bank": 0.00, "Cash": 0.00}
            journal_wise_total_payment_list = [result]
        var = {
            'currency_precision': user_currency.decimal_places,
            'total_paid': user_currency.round(total),
            'payments': journal_wise_total_payment_list,
            'company_name': self.env.company.name,
            'taxes': taxes.values(),
            'products': sorted([{
                'product_id': product.id,
                'product_name': product.name,
                'code': product.default_code,
                'quantity': qty,
                'price_unit': price_unit,
                'discount': discount,
                'uom': product.uom_id.name
            } for (product, price_unit, discount), qty in products_sold.items()], key=lambda l: l['product_name'])
        }
        return var

    @ api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        company_ids = self.env['res.company'].browse(data['company_ids'])
        data.update(self.get_invoice_details(
            data['date_start'], data['date_stop'], data['sh_move_type'], company_ids, data['sh_state']))
        return data
