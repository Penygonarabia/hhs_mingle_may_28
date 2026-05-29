# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.


from odoo import api, models, fields
import operator
import pytz
from datetime import datetime, timedelta


class TopCustomerReport(models.AbstractModel):
    _name = 'report.sh_accounting_reports.sh_tci_top_customers_doc'
    _description = "top customer/Vendor  abstract model"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        account_move_obj = self.env['account.move']
        currency_id = False
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
            ('invoice_date', '>=', fields.Date.to_string(date_start)),
            ('invoice_date', '<=', fields.Date.to_string(date_stop)),
            ('state', '=', 'posted'),
        ]
        if data.get('company_ids', False):
            domain.append(('company_id', 'in', data.get('company_ids', False)))
        if data.get('sh_move_type', False):
            if data.get('sh_move_type') == 'out_invoice':
                domain.append(('move_type', '=', 'out_invoice'))
            elif data.get('sh_move_type') == 'in_invoice':
                domain.append(('move_type', '=', 'in_invoice'))
            elif data.get('sh_move_type') == 'out_refund':
                domain.append(('move_type', '=', 'out_refund'))
            else:
                domain.append(('move_type', '=', 'in_refund'))

        account_moves = account_move_obj.sudo().search(domain)
        partner_total_amount_dic = {}
        if account_moves:
            for move in account_moves.sorted(key=lambda o: o.partner_id.id):
                if move.currency_id:
                    currency_id = move.currency_id

                if partner_total_amount_dic.get(move.partner_id.name, False):
                    amount = partner_total_amount_dic.get(
                        move.partner_id.name)
                    amount += move.amount_total
                    partner_total_amount_dic.update(
                        {move.partner_id.name: amount})
                else:
                    partner_total_amount_dic.update(
                        {move.partner_id.name: move.amount_total})

        final_partner_list = []
        final_partner_amount_list = []
        if partner_total_amount_dic:
            # sort partner dictionary by descending order
            sorted_partner_total_amount_list = sorted(
                partner_total_amount_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0

            for tuple_item in sorted_partner_total_amount_list:
                if data['amount_total'] != 0 and tuple_item[1] >= data['amount_total']:
                    final_partner_list.append(tuple_item[0])

                elif data['amount_total'] == 0:
                    final_partner_list.append(tuple_item[0])

                final_partner_amount_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        account_moves = False
        date_start = False
        date_stop = False
        if data['date_compare_from']:
            date_start = fields.Date.from_string(data['date_compare_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Date.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_compare_to']:
            date_stop = fields.Date.from_string(data['date_compare_to'])
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        domain = [
            ('invoice_date', '>=', fields.Date.to_string(date_start)),
            ('invoice_date', '<=', fields.Date.to_string(date_stop)),
            ('state', '=', 'posted'),
        ]
        if data.get('company_ids', False):
            domain.append(('company_id', 'in', data.get('company_ids', False)))
        if data.get('sh_move_type', False):
            if data.get('sh_move_type') == 'out_invoice':
                domain.append(('move_type', '=', 'out_invoice'))
            elif data.get('sh_move_type') == 'in_invoice':
                domain.append(('move_type', '=', 'in_invoice'))
            elif data.get('sh_move_type') == 'out_refund':
                domain.append(('move_type', '=', 'out_refund'))
            else:
                domain.append(('move_type', '=', 'in_refund'))

        account_moves = account_move_obj.sudo().search(domain)

        partner_total_amount_dic = {}
        if account_moves:
            for move in account_moves.sorted(key=lambda o: o.partner_id.id):
                if move.currency_id:
                    currency_id = move.currency_id

                if partner_total_amount_dic.get(move.partner_id.name, False):
                    amount = partner_total_amount_dic.get(
                        move.partner_id.name)
                    amount += move.amount_total
                    partner_total_amount_dic.update(
                        {move.partner_id.name: amount})
                else:
                    partner_total_amount_dic.update(
                        {move.partner_id.name: move.amount_total})

        final_compare_partner_list = []
        final_compare_partner_amount_list = []
        if partner_total_amount_dic:
            # sort compare partner dictionary by descending order
            sorted_partner_total_amount_list = sorted(
                partner_total_amount_dic.items(), key=operator.itemgetter(1), reverse=True)

            counter = 0
            for tuple_item in sorted_partner_total_amount_list:
                if data['amount_total'] != 0 and tuple_item[1] >= data['amount_total']:
                    final_compare_partner_list.append(tuple_item[0])

                elif data['amount_total'] == 0:
                    final_compare_partner_list.append(tuple_item[0])

                final_compare_partner_amount_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        # find lost and new partner here
        lost_partner_list = []
        new_partner_list = []
        if final_partner_list and final_compare_partner_list:
            for item in final_partner_list:
                if item not in final_compare_partner_list:
                    lost_partner_list.append(item)

            for item in final_compare_partner_list:
                if item not in final_partner_list:
                    new_partner_list.append(item)

#       finally update data dictionary
        if not currency_id:
            self.env.company.sudo().currency_id

        data.update({'partners': final_partner_list,
                     'partners_amount': final_partner_amount_list,
                     'compare_partners': final_compare_partner_list,
                     'compare_partners_amount': final_compare_partner_amount_list,
                     'lost_partners': lost_partner_list,
                     'new_partners': new_partner_list,
                     'currency': currency_id,
                     })
        return data
