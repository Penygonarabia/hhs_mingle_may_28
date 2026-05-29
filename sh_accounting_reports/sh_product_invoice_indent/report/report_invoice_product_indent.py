# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, models, fields
import pytz
from datetime import datetime, timedelta


class InvoiceProductIndent(models.AbstractModel):
    _name = 'report.sh_accounting_reports.sh_indent_product_indent_doc'
    _description = 'Invoice product indent report abstract model'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        move_dic = {}
        categories = self.env['product.category'].sudo().browse(
            data.get('sh_category_ids', False))
        partners = self.env['res.partner'].sudo().browse(
            data.get('sh_partner_ids', False))
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
        if partners:
            for partner in partners:
                customer_list = []
                for category in categories:
                    category_dic = {}
                    category_list = []
                    products = self.env['product.product'].sudo().search(
                        [('categ_id', '=', category.id)])
                    for product in products:
                        domain = [
                            ("move_id.invoice_date", ">=",
                             fields.Date.to_string(date_start)),
                            ("move_id.invoice_date", "<=",
                             fields.Date.to_string(date_stop)),
                            ('move_id.partner_id', '=', partner.id),
                            ('product_id', '=', product.id)
                        ]
                        if data.get('sh_status', False):
                            if data.get('sh_status') == 'draft':
                                domain.append(
                                    ('move_id.state', 'in', ['draft']))
                            elif data.get('sh_status') == 'posted':
                                domain.append(
                                    ('move_id.state', 'in', ['posted']))
                            elif data.get('move_id.state') == 'cancel':
                                domain.append(('state', 'in', ['posted']))
                        if data.get('sh_move_type', False):
                            if data.get('sh_move_type') == 'out_invoice':
                                domain.append(
                                    ('move_id.move_type', '=', 'out_invoice'))
                            elif data.get('sh_move_type') == 'in_invoice':
                                domain.append(
                                    ('move_id.move_type', '=', 'in_invoice'))
                            elif data.get('sh_move_type') == 'out_refund':
                                domain.append(
                                    ('move_id.move_type', '=', 'out_refund'))
                            else:
                                domain.append(
                                    ('move_id.move_type', '=', 'in_refund'))

                        if data.get('company_ids', False):
                            domain.append(
                                ('company_id', 'in', data.get('company_ids', False)))
                        move_lines = self.env['account.move.line'].sudo().search(
                            domain).mapped('quantity')
                        product_qty = 0.0
                        if move_lines:
                            for qty in move_lines:
                                product_qty += qty
                            product_dic = {
                                'name': product.name_get()[0][1],
                                'qty': product_qty,
                            }
                            category_list.append(product_dic)
                            category_dic.update({
                                category.display_name: category_list
                            })
                    customer_list.append(category_dic)
                move_dic.update({partner.name_get()[0][1]: customer_list})
        data.update({
            'date_start': data['sh_start_date'],
            'date_end': data['sh_end_date'],
            'move_dic': move_dic,
        })
        return data
