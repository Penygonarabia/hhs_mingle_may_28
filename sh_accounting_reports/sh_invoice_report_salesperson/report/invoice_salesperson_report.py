# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.


from odoo import api, models, fields
import pytz
from datetime import datetime, timedelta


class InvoiceSalespersonReport(models.AbstractModel):
    _name = 'report.sh_accounting_reports.sh_salesperson_report_doc'
    _description = "invoice person report abstract model"

    @api.model
    def _get_report_values(self, docids, data=None):

        account_move_obj = self.env["account.move"]

        user_order_dic = {}
        user_list = []
        currency = False
        date_start = False
        date_stop = False
        if data['date_start']:
            date_start = fields.Date.from_string(data['date_start'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Date.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_end']:
            date_stop = fields.Date.from_string(data['date_end'])
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)

        if data.get('user_ids', False):
            for user_id in data.get('user_ids'):
                order_list = []
                domain = [
                    ("invoice_date", ">=", fields.Date.to_string(date_start)),
                    ("invoice_date", "<=", fields.Date.to_string(date_stop)),
                    ("user_id", "=", user_id)
                ]
                if data.get('company_ids', False):
                    domain.append(
                        ('company_id', 'in', data.get('company_ids', False)))
                if data.get('state', False):
                    domain.append(('state', '=', data.get('state', False)))
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
                if account_moves:
                    for move in account_moves:
                        if not currency:
                            currency = move.currency_id
                        order_dic = {
                            'invoice_number': move.name,
                            'invoice_date': move.invoice_date,
                            'customer': move.partner_id.name if move.partner_id else "",
                            'total': move.amount_total,
                            'paid_amount': 0.0,
                            'due_amount': 0.0,
                        }
                        if move:
                            sum_of_invoice_amount = 0.0
                            sum_of_due_amount = 0.0
                            for invoice_id in move.filtered(lambda inv: inv.state not in ['cancel', 'draft']):
                                sum_of_invoice_amount += invoice_id.amount_total_signed
                                sum_of_due_amount += invoice_id.amount_residual_signed

                            order_dic.update({
                                "paid_amount": sum_of_invoice_amount,
                                "due_amount": sum_of_due_amount,
                            })

                        order_list.append(order_dic)

                search_user = self.env['res.users'].sudo().search([
                    ('id', '=', user_id)
                ], limit=1)
                if search_user:
                    user_order_dic.update({search_user.name: order_list})
                    user_list.append(search_user.name)

        if not currency:
            currency = self.env.company.sudo().currency_id

        data = {
            'date_start': data['date_start'],
            'date_end': data['date_end'],
            'user_order_dic': user_order_dic,
            'user_list': user_list,
            'currency': currency,
        }
        return data
