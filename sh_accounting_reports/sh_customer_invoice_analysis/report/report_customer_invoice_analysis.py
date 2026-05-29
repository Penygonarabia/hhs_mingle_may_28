# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, models, fields
import pytz
from datetime import datetime, timedelta


class CustomerVendorInvoiceAnalysis(models.AbstractModel):
    _name = 'report.sh_accounting_reports.sh_cus_invoice_analy_doc'
    _description = 'Customer/Vendor  Invoices Analysis report abstract model'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        account_move_obj = self.env["account.move"]
        move_dic_by_move = {}
        move_dic_by_products = {}
        date_start = False
        date_stop = False
        if data['sh_start_date']:
            date_start = fields.Date.from_string(
                data['sh_start_date'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.date.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['sh_end_date']:
            date_stop = fields.Date.from_string(data['sh_end_date'])
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        if data.get('sh_partner_ids', False):
            for partner_id in data.get('sh_partner_ids'):
                move_list = []
                domain = [
                    ("invoice_date", ">=", fields.Date.to_string(date_start)),
                    ("invoice_date", "<=", fields.Date.to_string(date_stop)),
                    ("partner_id", "=", partner_id),
                ]
                if data.get('sh_status') == 'draft':
                    domain.append(('state', 'in', ['draft']))
                elif data.get('sh_status') == 'posted':
                    domain.append(('state', 'in', ['posted']))
                elif data.get('sh_status') == 'cancel':
                    domain.append(('state', 'in', ['posted']))
                if data.get('company_ids', False):
                    domain.append(
                        ('company_id', 'in', data.get('company_ids', False)))
                if data.get('sh_move_type', False):
                    if data.get('sh_move_type') == 'out_invoice':
                        domain.append(('move_type', '=', 'out_invoice'))
                    elif data.get('sh_move_type') == 'in_invoice':
                        domain.append(('move_type', '=', 'in_invoice'))
                    elif data.get('sh_move_type') == 'out_refund':
                        domain.append(('move_type', '=', 'out_refund'))
                    else:
                        domain.append(('move_type', '=', 'in_refund'))
                search_moves = account_move_obj.sudo().search(domain)
                if search_moves:
                    for move in search_moves:
                        if data.get('report_by') == 'move':
                            move_dic = {
                                'invoice_number': move.name,
                                'invoice_date': move.invoice_date,
                                'invoice_amount': move.amount_total,
                                'invoice_user_id': move.invoice_user_id.name,
                                'account_currency_id': move.currency_id.id,
                            }
                            paid_amount = 0.0
                            if move.move_type == 'out_invoice':
                                paid_amount += move.amount_total-move.amount_residual
                            elif move.move_type == 'out_refund':
                                paid_amount += - \
                                    (move.amount_total -
                                     move.amount_residual)
                            move_dic.update({
                                'paid_amount': paid_amount,
                                'balance_amount': move.amount_total - paid_amount
                            })
                            move_list.append(move_dic)
                        elif data.get('report_by') == 'product' and move.invoice_line_ids:
                            invoice_line = False
                            if data.get('sh_product_ids'):
                                invoice_line = move.invoice_line_ids.sudo().filtered(
                                    lambda x: x.product_id.id in data.get('sh_product_ids'))
                            else:
                                products = self.env['product.product'].sudo().search(
                                    [])
                                invoice_line = move.invoice_line_ids.sudo().filtered(
                                    lambda x: x.product_id.id in products.ids)
                            if invoice_line:
                                for line in invoice_line:
                                    move_dic = {
                                        'invoice_number': line.move_id.name,
                                        'invoice_date': line.move_id.invoice_date,
                                        'product_name': line.product_id.name_get()[0][1],
                                        'price': line.price_unit,
                                        'qty': line.quantity,
                                        'subtotal': line.price_subtotal,
                                        'account_currency_id': line.currency_id.id,
                                    }
                                    if line.tax_ids:
                                        tax_ammount_line = 0.0
                                        for tax in line.tax_ids:
                                            tax_ammount_line += (line.price_unit *
                                                                 tax.amount)/100
                                    else:
                                        tax_amount_line = 0
                                    move_dic.update({
                                        'tax': tax_ammount_line,
                                    })
                                    move_list.append(move_dic)
                search_partner = self.env['res.partner'].sudo().search([
                    ('id', '=', partner_id)
                ], limit=1)
                if search_partner:
                    if data.get('report_by') == 'move':
                        move_dic_by_move.update(
                            {search_partner.name_get()[0][1]: move_list})
                    elif data.get('report_by') == 'product':
                        move_dic_by_products.update(
                            {search_partner.name_get()[0][1]: move_list})
        data.update({
            'date_start': data['sh_start_date'],
            'date_end': data['sh_end_date'],
            'move_dic_by_move': move_dic_by_move,
            'report_by': data.get('report_by'),
            'move_dic_by_products': move_dic_by_products,
        })
        return data
