# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, models, fields
import pytz
from datetime import datetime, timedelta


class InvoiceByCategory(models.AbstractModel):
    _name = 'report.sh_accounting_reports.sh_invoice_by_category_doc'
    _description = 'Invoice by category report abstract model'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        account_move_obj = self.env["account.move"]
        category_move_dic = {}
        categories = False
        date_start = False
        date_stop = False
        if data['sh_start_date']:
            date_start = fields.Date.from_string(data['sh_start_date'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Date.from_string(
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
        if data.get('sh_category_ids', False):
            categories = self.env['product.category'].sudo().browse(
                data.get('sh_category_ids', False))
        else:
            categories = self.env['product.category'].sudo().search([])
        if categories:
            for category in categories:
                move_list = []
                domain = [
                    ("invoice_date", ">=", fields.Date.to_string(date_start)),
                    ("invoice_date", "<=", fields.Date.to_string(date_stop)),
                ]
                if data.get('sh_move_type', False):
                    if data.get('sh_move_type') == 'out_invoice':
                        domain.append(('move_type', '=', 'out_invoice'))
                    elif data.get('sh_move_type') == 'in_invoice':
                        domain.append(('move_type', '=', 'in_invoice'))
                    elif data.get('sh_move_type') == 'out_refund':
                        domain.append(('move_type', '=', 'out_refund'))
                    else:
                        domain.append(('move_type', '=', 'in_refund'))
                if data.get('company_ids', False):
                    domain.append(
                        ('company_id', 'in', data.get('company_ids', False)))
                search_moves = account_move_obj.sudo().search(domain)
                if search_moves:
                    for move in search_moves:
                        if move.invoice_line_ids:
                            move_dic = {}
                            for line in move.invoice_line_ids:
                                if line.product_id.categ_id.id == category.id:
                                    line_dic = {
                                        'invoice_number': move.name,
                                        'invoice_date': move.invoice_date,
                                        'product': line.product_id.name_get()[0][1],
                                        'qty': line.quantity,
                                        'sale_price': line.price_unit,
                                        'account_currency_id': line.currency_id.id
                                    }
                                    tax_ammount_line = 0.0
                                    if line.tax_ids:
                                        for tax in line.tax_ids:
                                            tax_ammount_line += (line.price_unit *
                                                                 tax.amount)/100
                                    line_dic.update({
                                        'tax': tax_ammount_line,
                                    })
                                    if move_dic.get(line.product_id.id, False):
                                        qty = move_dic.get(
                                            line.product_id.id)['qty']
                                        qty = qty + line.quantity
                                        line_dic.update({
                                            'qty': qty,
                                        })
                                    move_dic.update(
                                        {line.product_id.id: line_dic})
                            for key, value in move_dic.items():
                                move_list.append(value)
                category_move_dic.update({category.display_name: move_list})
        data.update({
            'date_start': data['sh_start_date'],
            'date_end': data['sh_end_date'],
            'category_move_dic': category_move_dic,
        })
        return data
