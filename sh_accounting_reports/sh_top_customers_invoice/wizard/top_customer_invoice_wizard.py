# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import operator
import xlwt
import base64
from odoo.exceptions import UserError
import io
import pytz
from datetime import datetime, timedelta


class TopCustomerExcel(models.Model):
    _name = "sh.top.customers.invoice.xls"
    _description = "Top Customer/Vendor XLS"

    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sh.top.customers.invoice.xls&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class TOPCustomerWizard(models.TransientModel):
    _name = "sh.tci.top.customer.wizard"
    _description = 'Top Customers'

    @api.model
    def default_company_ids(self):
        is_allowed_companies = self.env.context.get(
            'allowed_company_ids', False)
        if is_allowed_companies:
            return is_allowed_companies
        return

    type = fields.Selection([
        ('basic', 'Basic'),
        ('compare', 'Compare'),
    ], string="Report Type", default="basic")
    sh_move_type = fields.Selection([('out_invoice', 'Customer Invoice'),
                                     ('out_refund', 'Customer Credit Note'),
                                     ('in_invoice', 'Vendor Bill'),
                                     ('in_refund', 'Vendor Credit Note')], default='out_invoice', string="Invoice Type")
    date_from = fields.Date(
        string='From Date', required=True, default=fields.Datetime.now)
    date_to = fields.Date(string='To Date', required=True,
                          default=fields.Datetime.now)

    date_compare_from = fields.Date(
        string='Compare From Date', default=fields.Datetime.now)
    date_compare_to = fields.Date(
        string='Compare To Date', default=fields.Datetime.now)
    no_of_top_item = fields.Integer(
        string='No of Items', required=True, default=10)
    amount_total = fields.Monetary(string="Total Sales Amount")
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.company.currency_id)
    company_ids = fields.Many2many(
        'res.company', string="Company", default=default_company_ids)

    @api.constrains('date_from', 'date_to')
    def _check_from_to_dates(self):
        if self.filtered(lambda c: c.date_to and c.date_from > c.date_to):
            raise ValidationError(_('from date must be less than to date.'))

    @api.constrains('date_compare_from', 'date_compare_to')
    def _check_compare_from_to_dates(self):
        if self.filtered(lambda c: c.date_compare_to and c.date_compare_from and c.date_compare_from > c.date_compare_to):
            raise ValidationError(
                _('compare from date must be less than compare to date.'))

    def print_top_customer_report(self):
        self.ensure_one()
        # we read self because we use from date and start date in our core bi logic.(in abstract model)
        data = self.read()[0]
        return self.env.ref('sh_accounting_reports.sh_tci_top_customers_report_action').report_action([], data=data)

    def print_top_customer_xls_report(self,):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
        bold_center = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        left = xlwt.easyxf('align: horiz left')
        row = 1
        data = self.read()[0]
        data = dict(data or {})
        account_move_obj = self.env['account.move']
        date_start = False
        date_stop = False
        if self.date_from:
            date_start = fields.Date.from_string(self.date_from)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Date.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if self.date_to:
            date_stop = fields.Date.from_string(self.date_to)
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
        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))
        if self.sh_move_type:
            if self.sh_move_type == 'out_invoice':
                domain.append(('move_type', '=', 'out_invoice'))
            elif self.sh_move_type == 'in_invoice':
                domain.append(('move_type', '=', 'in_invoice'))
            elif self.sh_move_type == 'out_refund':
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

        ##################################
        # for Compare partner from to
        date_start = False
        date_stop = False
        if self.date_compare_from:
            date_start = fields.Date.from_string(self.date_compare_from)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Date.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if self.date_compare_to:
            date_stop = fields.Date.from_string(self.date_compare_to)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        sale_orders = False
        domain = [
            ('invoice_date', '>=', fields.Date.to_string(date_start)),
            ('invoice_date', '<=', fields.Date.to_string(date_stop)),
            ('state', '=', 'posted'),
        ]
        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))
        if self.sh_move_type:
            if self.sh_move_type == 'out_invoice':
                domain.append(('move_type', '=', 'out_invoice'))
            elif self.sh_move_type == 'in_invoice':
                domain.append(('move_type', '=', 'in_invoice'))
            elif self.sh_move_type == 'out_refund':
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

        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        if self.date_from:
            basic_start_date = fields.Date.from_string((self.date_from))

        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Date.from_string(
                fields.Date.context_today(self)))
            basic_start_date = today.astimezone(pytz.timezone('UTC'))
        if self.date_to:
            basic_end_date = fields.Date.from_string((self.date_to))
            # avoid a date_stop smaller than date_start
            if (basic_end_date < basic_start_date):
                basic_end_date = basic_start_date + \
                    timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            basic_end_date = basic_start_date + timedelta(days=1, seconds=-1)
        if self.date_compare_from:
            compare_start_date = fields.Date.from_string(
                (self.date_compare_from))
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Date.from_string(
                fields.Date.context_today(self)))
            compare_start_date = today.astimezone(pytz.timezone('UTC'))
        if self.date_compare_to:
            compare_end_date = fields.Date.from_string((self.date_compare_to))
            # avoid a date_stop smaller than date_start
            if (compare_end_date < compare_start_date):
                compare_end_date = compare_start_date + \
                    timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            compare_end_date = compare_start_date + \
                timedelta(days=1, seconds=-1)

        if self.type == 'basic':
            row = 1
            worksheet = workbook.add_sheet(
                u'Top Customers', cell_overwrite_ok=True)
            worksheet.write_merge(0, 1, 0, 2, 'Top Customers', heading_format)
            worksheet.write(3, 0, 'Date From: ', bold)
            worksheet.write(3, 1, basic_start_date.strftime("%m-%d-%y"))

            worksheet.write(4, 0, 'Date To: ', bold)
            worksheet.write(4, 1, basic_end_date.strftime("%m-%d-%y"))
            worksheet.col(0).width = int(25*260)
            worksheet.col(1).width = int(25*260)
            worksheet.col(2).width = int(14*260)
            row = 6
            worksheet.write(row, 0, "#", bold)
            worksheet.write(row, 1, "Customer", bold)
            worksheet.write(row, 2, "Sales Amount", bold)
            no = 0
            row = 7
            for i in range(len(final_partner_list)):
                no = no+1
                worksheet.write(row, 0, no, left)
                worksheet.write(row, 1, final_partner_list[i], left)
                worksheet.write(row, 2, final_partner_amount_list[i], left)
                row = row+1
        elif self.type == 'compare':
            row = 1
            worksheet = workbook.add_sheet(
                u'Top Customers', cell_overwrite_ok=True)
            worksheet.write_merge(0, 1, 0, 6, 'Top Customers', heading_format)
            worksheet.write(3, 0, 'Date From: ', bold)
            worksheet.write(3, 1, basic_start_date.strftime("%m-%d-%y"))
            worksheet.write(4, 0, 'Date To: ', bold)
            worksheet.write(4, 1, basic_end_date.strftime("%m-%d-%y"))
            worksheet.write(3, 5, 'Compare From Date: ', bold)
            worksheet.write(3, 6, compare_start_date.strftime("%m-%d-%y"))

            worksheet.write(4, 5, 'Compare To Date: ', bold)
            worksheet.write(4, 6, compare_end_date.strftime("%m-%d-%y"))
            row = 7
            worksheet.col(0).width = int(25*260)
            worksheet.col(1).width = int(25*260)
            worksheet.col(2).width = int(14*260)
            worksheet.col(3).width = int(25*260)
            worksheet.col(4).width = int(25*260)
            worksheet.col(5).width = int(14*260)
            worksheet.col(6).width = int(14*260)
            worksheet.write(row, 0, "#", bold)
            worksheet.write(row, 1, "Customer", bold)
            worksheet.write(row, 2, "Sales Amount", bold)
            worksheet.write(row, 4, "#", bold)
            worksheet.write(row, 5, "Compare Customer", bold)
            worksheet.write(row, 6, "Sales Amount", bold)
            row = 8
            for i in range(len(final_partner_list)):
                worksheet.write(row, 0, i+1, left)
                worksheet.write(row, 1, final_partner_list[i], left)
                worksheet.write(row, 2, final_partner_amount_list[i], left)
                row = row+1
            row = 8
            for j in range(len(final_compare_partner_list)):
                worksheet.write(row, 4, j+1, left)
                worksheet.write(row, 5, final_compare_partner_list[j], left)
                worksheet.write(
                    row, 6, final_compare_partner_amount_list[j], left)
                row = row+1
            row = row+2
            worksheet.write_merge(row, row, 0, 2, 'New Customers', bold_center)
            worksheet.write_merge(
                row, row, 4, 6, 'Lost Customers', bold_center)
            row = row+1
            starting_row = row
            for new in new_partner_list:
                worksheet.write_merge(row, row, 0, 2, new, left)
                row = row+1
            for lost in lost_partner_list:
                worksheet.write_merge(
                    starting_row, starting_row, 4, 6, lost, left)
                starting_row = starting_row+1
        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env['ir.attachment']
        attachment_vals = {
            "name": "Top Customer/Vendor Xls Report",
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search([('name', '=', 'Top Customer/Vendor Xls Report'),
                                          ('type', '=', 'binary'),
                                          ('res_model', '=', 'ir.ui.view')],
                                         limit=1)
        if attachment:
            attachment.write(attachment_vals)
        else:
            attachment = IrAttachment.create(attachment_vals)
        # TODO: make user error here
        if not attachment:
            raise UserError('There is no attachments...')

        url = "/web/content/" + str(attachment.id) + "?download=true"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
