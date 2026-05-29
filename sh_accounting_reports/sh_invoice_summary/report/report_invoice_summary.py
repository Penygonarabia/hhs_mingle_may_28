# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, models, fields
import pytz
from datetime import datetime, timedelta


class InvoiceSummary(models.AbstractModel):
    _name = 'report.sh_accounting_reports.sh_invoice_summary_doc'
    _description = 'Invoice Summary report abstract model'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        account_move_obj = self.env["account.move"]
        customer_move_dic = {}
        date_start = False
        date_stop = False
        if data['sh_start_date']:
            date_start = fields.Date.from_string(data['sh_start_date'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(
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
                if data.get('sh_status', False):
                    if data.get('sh_status') == 'draft':
                        domain.append(('state', '=', 'draft'))
                    elif data.get('sh_status') == 'posted':
                        domain.append(('state', '=', 'posted'))
                    else:
                        domain.append(('state', '=', 'cancel'))
                search_moves = account_move_obj.sudo().search(domain)
                if search_moves:
                    for move in search_moves:
                        move_dic = {
                            'invoice_number': move.name,
                            'invoice_date': move.invoice_date,
                            'invoice_currency_id': move.currency_id.id,
                            'invoice_amount': move.amount_total,
                            'invoice_paid_amount': move.amount_total - move.amount_residual,
                            'due_amount': move.amount_residual,
                        }
                        move_list.append(move_dic)

                search_partner = self.env['res.partner'].sudo().search([
                    ('id', '=', partner_id)
                ], limit=1)
                if search_partner:
                    customer_move_dic.update(
                        {search_partner.name_get()[0][1]: move_list})
        data.update({
            'date_start': data['sh_start_date'],
            'date_end': data['sh_end_date'],
            'customer_move_dic': customer_move_dic
        })
        return data
