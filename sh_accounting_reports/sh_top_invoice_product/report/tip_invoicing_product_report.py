# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.


from odoo import api, models, fields
import operator
import pytz
from datetime import datetime, timedelta


class TopInvoicingProduct(models.AbstractModel):
    _name = 'report.sh_accounting_reports.sh_top_invoicing_product_doc'
    _description = "top invoicing product report abstract model"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        account_move_line_obj = self.env['account.move.line']
        date_start = False
        date_stop = False
        if data['date_from']:
            date_start = fields.Date.from_string(data['date_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Date.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_to']:
            date_stop = fields.Date.from_string(data['date_to'])
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        domain = [
            ('move_id.state', '=', 'posted'),
        ]
        if data.get('company_ids', False):
            domain.append(('move_id.company_id', 'in',
                           data.get('company_ids', False)))
        if data.get('date_from', False):
            domain.append(('move_id.invoice_date', '>=',
                          fields.Date.to_string(date_start)))
        if data.get('date_to', False):
            domain.append(('move_id.invoice_date', '<=',
                          fields.Date.to_string(date_stop)))
        if data.get('sh_move_type', False):
            if data.get('sh_move_type') == 'out_invoice':
                domain.append(('move_id.move_type', '=', 'out_invoice'))
            elif data.get('sh_move_type') == 'in_invoice':
                domain.append(('move_id.move_type', '=', 'in_invoice'))
            elif data.get('sh_move_type') == 'out_refund':
                domain.append(('move_id.move_type', '=', 'out_refund'))
            else:
                domain.append(('move_id.move_type', '=', 'in_refund'))

        account_move_lines = account_move_line_obj.sudo().search(domain)

        product_total_qty_dic = {}
        if account_move_lines:
            for line in account_move_lines.sorted(key=lambda o: o.product_id.id):
                if line.product_id.name:
                    if product_total_qty_dic.get(line.product_id.name, False):
                        qty = product_total_qty_dic.get(line.product_id.name)
                        qty += line.quantity
                        product_total_qty_dic.update(
                            {line.product_id.name: qty})
                    else:
                        product_total_qty_dic.update(
                            {line.product_id.name: line.quantity})

        final_product_list = []
        final_product_qty_list = []
        if product_total_qty_dic:
            # sort partner dictionary by descending order
            sorted_product_total_qty_list = sorted(
                product_total_qty_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0

            for tuple_item in sorted_product_total_qty_list:
                if data['product_uom_qty'] != 0 and tuple_item[1] >= data['product_uom_qty']:
                    final_product_list.append(tuple_item[0])

                elif data['product_uom_qty'] == 0:
                    final_product_list.append(tuple_item[0])

                final_product_qty_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        ##################################
        # for Compare product from to
        date_start = False
        date_stop = False
        if data.get('date_compare_from'):
            date_start = fields.Date.from_string(
                data.get('date_compare_from'))
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Date.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data.get('date_compare_to'):
            date_stop = fields.Date.from_string(
                data.get('date_compare_to'))
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        account_move_lines = False
        domain = [
            ('move_id.state', '=', 'posted'),
        ]
        if data.get('company_ids', False):
            domain.append(('move_id.company_id', 'in',
                           data.get('company_ids', False)))
        if data.get('date_compare_from', False):
            domain.append(('move_id.invoice_date', '>=',
                           fields.Date.to_string(date_start)))
        if data.get('date_compare_to', False):
            domain.append(('move_id.invoice_date', '<=',
                           fields.Date.to_string(date_stop)))

        if data.get('sh_move_type', False):
            if data.get('sh_move_type') == 'out_invoice':
                domain.append(('move_id.move_type', '=', 'out_invoice'))
            elif data.get('sh_move_type') == 'in_invoice':
                domain.append(('move_id.move_type', '=', 'in_invoice'))
            elif data.get('sh_move_type') == 'out_refund':
                domain.append(('move_id.move_type', '=', 'out_refund'))
            else:
                domain.append(('move_id.move_type', '=', 'in_refund'))

        account_move_lines = account_move_line_obj.sudo().search(domain)

        product_total_qty_dic = {}
        if account_move_lines:
            for line in account_move_lines.sorted(key=lambda o: o.product_id.id):
                if line.product_id.name:
                    if product_total_qty_dic.get(line.product_id.name, False):
                        qty = product_total_qty_dic.get(line.product_id.name)
                        qty += line.quantity
                        product_total_qty_dic.update(
                            {line.product_id.name: qty})
                    else:
                        product_total_qty_dic.update(
                            {line.product_id.name: line.quantity})

        final_compare_product_list = []
        final_compare_product_qty_list = []
        if product_total_qty_dic:
            # sort partner dictionary by descending order
            sorted_product_total_qty_list = sorted(
                product_total_qty_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0

            for tuple_item in sorted_product_total_qty_list:
                if data['product_uom_qty'] != 0 and tuple_item[1] >= data['product_uom_qty']:
                    final_compare_product_list.append(tuple_item[0])

                elif data['product_uom_qty'] == 0:
                    final_compare_product_list.append(tuple_item[0])

                final_compare_product_qty_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        # find lost and new partner here
        lost_product_list = []
        new_product_list = []
        if final_product_list and final_compare_product_list:
            for item in final_product_list:
                if item not in final_compare_product_list:
                    lost_product_list.append(item)

            for item in final_compare_product_list:
                if item not in final_product_list:
                    new_product_list.append(item)

        data.update({'products': final_product_list,
                     'products_qty': final_product_qty_list,
                     'compare_products': final_compare_product_list,
                     'compare_products_qty': final_compare_product_qty_list,
                     'lost_products': lost_product_list,
                     'new_products': new_product_list,
                     })
        return data
