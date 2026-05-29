# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import operator
from odoo.exceptions import UserError
import io
import xlwt
import base64
from io import BytesIO
import pytz
from datetime import datetime, timedelta


class TopinvoicingProductExcel(models.Model):
    _name = "sh.tip.invoicing.products"
    _description = "Top Invoicing XLS"

    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sh.tip.invoicing.products&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class TopinvoicingWizard(models.TransientModel):
    _name = "sh.tip.top.invoicing.product.wizard"
    _description = 'Top invoicing product Transient model to just filter products'

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
    product_uom_qty = fields.Float(string="Total Qty. Sold")
    company_ids = fields.Many2many(
        'res.company', string="Companies", default=default_company_ids)
    sh_move_type = fields.Selection([('out_invoice', 'Customer Invoice'),
                                     ('out_refund', 'Customer Credit Note'),
                                     ('in_invoice', 'Vendor Bill'),
                                     ('in_refund', 'Vendor Credit Note')], default='out_invoice', string="Invoice Type")

    @api.constrains('date_from', 'date_to')
    def _check_from_to_dates(self):
        if self.filtered(lambda c: c.date_to and c.date_from > c.date_to):
            raise ValidationError(_('from date must be less than to date.'))

    @api.constrains('date_compare_from', 'date_compare_to')
    def _check_compare_from_to_dates(self):
        if self.filtered(lambda c: c.date_compare_to and c.date_compare_from and c.date_compare_from > c.date_compare_to):
            raise ValidationError(
                _('compare from date must be less than compare to date.'))

    @api.constrains('no_of_top_item')
    def _check_no_of_top_item(self):
        if self.filtered(lambda c: c.no_of_top_item <= 0):
            raise ValidationError(
                _('No of items must be positive. or not zero'))

    def filter_top_invoicing_product(self):
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
            ('move_id.state', '=', 'posted'),
        ]
        if self.company_ids:
            domain.append(('move_id.company_id', 'in', self.company_ids.ids))
        if self.date_from:
            domain.append(('move_id.invoice_date', '>=',
                          fields.Date.to_string(date_start)))
        if self.date_to:
            domain.append(('move_id.invoice_date', '<=',
                          fields.Date.to_string(date_stop)))

        # search move line product and add into product_qty_dictionary
        account_move_lines = self.env['account.move.line'].sudo().search(
            domain)
        product_qty_dic = {}
        if account_move_lines:
            for line in account_move_lines.sorted(key=lambda r: r.product_id.id):
                if line.product_id.id:
                    if product_qty_dic.get(line.product_id.id, False):
                        qty = product_qty_dic.get(line.product_id.id)
                        qty += line.quantity
                        product_qty_dic.update({line.product_id.id: qty})
                    else:
                        product_qty_dic.update(
                            {line.product_id.id: line.quantity})

        # remove all the old  records before creating new one.
        top_invoicing_product_obj = self.env['sh.tip.top.invoicing.product']
        search_records = top_invoicing_product_obj.sudo().search([])
        if search_records:
            search_records.unlink()

        if product_qty_dic:
            # sort product qty dictionary by descending order
            sorted_product_qty_list = sorted(
                product_qty_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0
            for tuple_item in sorted_product_qty_list:
                top_invoicing_product_obj.sudo().create({
                    'product_id': tuple_item[0],
                    'qty': tuple_item[1]
                })
                # only create record by user limit
                counter += 1
                if counter >= self.no_of_top_item:
                    break

    def print_top_invoicing_product_report(self):
        self.ensure_one()
        # we read self because we use from date and start date in our core bi logic.(in abstract model)
        data = self.read()[0]

        return self.env.ref('sh_accounting_reports.sh_top_invoicing_product_report_action').report_action([], data=data)

    def print_top_invoicing_product_xls_report(self):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
        bold_center = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        left = xlwt.easyxf('align: horiz left')
        row = 1

        worksheet = workbook.add_sheet(
            u'Top Invoicing Products', cell_overwrite_ok=True)
        if self.type == 'basic':
            worksheet.write_merge(
                0, 1, 0, 2, 'Top Invoicing Products', heading_format)
        if self.type == 'compare':
            worksheet.write_merge(
                0, 1, 0, 6, 'Top Invoicing Products', heading_format)
        data = self.read()[0]
        data = dict(data or {})
        user_tz = self.env.user.tz or pytz.utc
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
        if self.type == 'compare':
            if self.date_compare_from:
                compare_start_date = fields.Date.from_string(
                    self.date_compare_from)
            else:
                user_tz = pytz.timezone(self.env.context.get(
                    'tz') or self.env.user.tz or 'UTC')
                today = user_tz.localize(fields.Date.from_string(
                    fields.Date.context_today(self)))
                compare_start_date = today.astimezone(pytz.timezone('UTC'))

            if self.date_compare_to:
                compare_end_date = fields.Date.from_string(
                    self.date_compare_to)

                if (compare_end_date < compare_start_date):
                    compare_end_date = compare_start_date + \
                        timedelta(days=1, seconds=-1)
            else:
                user_tz = pytz.timezone(self.env.context.get(
                    'tz') or self.env.user.tz or 'UTC')
                today = user_tz.localize(fields.Date.from_string(
                    fields.Date.context_today(self)))
                compare_end_date = today.astimezone(pytz.timezone('UTC'))

        if self.type == 'basic' or self.type == 'compare':
            worksheet.write(3, 0, 'Date From: ', bold)
            worksheet.write(3, 1, date_start.strftime("%m-%d-%y"))

            worksheet.write(4, 0, 'Date To: ', bold)
            worksheet.write(4, 1, date_stop.strftime("%m-%d-%y"))

        account_move_line_obj = self.env['account.move.line']
        ##################################
        # for product from to
        domain = [
            ('move_id.state', '=', 'posted'),
        ]
        if self.company_ids:
            domain.append(('move_id.company_id', 'in',
                           self.company_ids.ids))
        if self.date_from:
            domain.append(('move_id.invoice_date', '>=',
                           fields.Date.to_string(self.date_from)))
        if self.date_to:
            domain.append(('move_id.invoice_date', '<=',
                           fields.Date.to_string(self.date_to)))
        if self.sh_move_type:
            if self.sh_move_type == 'out_invoice':
                domain.append(('move_id.move_type', '=', 'out_invoice'))
            elif self.sh_move_type == 'in_invoice':
                domain.append(('move_id.move_type', '=', 'in_invoice'))
            elif self.sh_move_type == 'out_refund':
                domain.append(('move_id.move_type', '=', 'out_refund'))
            else:
                domain.append(('move_id.move_type', '=', 'in_refund'))

        search_move_lines = account_move_line_obj.sudo().search(domain)
        product_total_qty_dic = {}
        if search_move_lines:
            for line in search_move_lines.sorted(key=lambda o: o.product_id.id):
                if line.product_id.name:
                    if product_total_qty_dic.get(line.product_id.name, False):
                        qty = product_total_qty_dic.get(
                            line.product_id.name)
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
            if self.type == 'basic' or self.type == 'compare':
                worksheet.col(0).width = int(25 * 260)
                worksheet.col(1).width = int(25 * 260)
                worksheet.col(2).width = int(14 * 260)

                worksheet.write(6, 0, "#", bold)
                worksheet.write(6, 1, "Product", bold)
                worksheet.write(6, 2, "Qty Sold", bold)
                row = 6
            no = 0
            for tuple_item in sorted_product_total_qty_list:
                no += 1
                row += 1
                if self.product_uom_qty != 0 and tuple_item[1] >= self.product_uom_qty:
                    final_product_list.append(tuple_item[0])
                    if self.type == 'basic' or self.type == 'compare':
                        for product in final_product_list:
                            worksheet.write(row, 0, no, left)
                            worksheet.write(row, 1, product)

                elif self.product_uom_qty == 0:
                    final_product_list.append(tuple_item[0])
                    if self.type == 'basic' or self.type == 'compare':
                        for product in final_product_list:
                            worksheet.write(row, 0, no, left)
                            worksheet.write(row, 1, product)

                final_product_qty_list.append(tuple_item[1])
                if self.type == 'basic' or self.type == 'compare':
                    for product_qty in final_product_qty_list:
                        worksheet.write(row, 2, product_qty)
                # only show record by user limit
                counter += 1
                if counter >= self.no_of_top_item:
                    break

        ##################################
        # for Compare product from to
        if self.type == 'compare':

            worksheet.write(3, 5, 'Compare From Date: ', bold)
            worksheet.write(3, 6, compare_start_date.strftime("%m-%d-%y"))

            worksheet.write(4, 5, 'Compare To Date: ', bold)
            worksheet.write(4, 6, compare_end_date.strftime("%m-%d-%y"))
            search_move_lines = False
            domain = [
                ('move_id.state', '=', 'posted'),
            ]
            if self.company_ids:
                domain.append(('move_id.company_id', 'in',
                               self.company_ids.ids))
            if self.date_compare_from:
                domain.append(('move_id.invoice_date', '>=',
                               fields.Date.to_string(self.date_compare_from)))
            if self.date_compare_to:
                domain.append(('move_id.invoice_date', '<=',
                               fields.Date.to_string(self.date_compare_to)))
            if self.sh_move_type:
                if self.sh_move_type == 'out_invoice':
                    domain.append(('move_id.move_type', '=', 'out_invoice'))
                elif self.sh_move_type == 'in_invoice':
                    domain.append(('move_id.move_type', '=', 'in_invoice'))
                elif self.sh_move_type == 'out_refund':
                    domain.append(('move_id.move_type', '=', 'out_refund'))
                else:
                    domain.append(('move_id.move_type', '=', 'in_refund'))

            search_move_lines = account_move_line_obj.sudo().search(domain)

            product_total_qty_dic = {}
            if search_move_lines:
                for line in search_move_lines.sorted(key=lambda o: o.product_id.id):
                    if line.product_id.name:
                        if product_total_qty_dic.get(line.product_id.name, False):
                            qty = product_total_qty_dic.get(
                                line.product_id.name)
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
                if self.type == 'compare':
                    worksheet.col(4).width = int(25 * 260)
                    worksheet.col(5).width = int(25 * 260)
                    worksheet.col(6).width = int(14 * 260)

                    worksheet.write(6, 4, "#", bold)
                    worksheet.write(6, 5, "Compare Product", bold)
                    worksheet.write(6, 6, "Qty Sold", bold)

                row = 6
                no = 0
                for tuple_item in sorted_product_total_qty_list:
                    no += 1
                    row += 1
                    if self.product_uom_qty != 0 and tuple_item[1] >= self.product_uom_qty:
                        final_compare_product_list.append(tuple_item[0])
                        if self.type == 'compare':
                            for compare_partner in final_compare_product_list:
                                worksheet.write(row, 4, no, left)
                                worksheet.write(row, 5, compare_partner)
                    elif self.product_uom_qty == 0:
                        final_compare_product_list.append(tuple_item[0])
                        if self.type == 'compare':
                            for compare_partner in final_compare_product_list:
                                worksheet.write(row, 4, no, left)
                                worksheet.write(row, 5, compare_partner)

                    final_compare_product_qty_list.append(tuple_item[1])
                    if self.type == 'compare':
                        for compare_product_qty in final_compare_product_qty_list:
                            worksheet.write(row, 6, compare_product_qty)
                    # only show record by user limit
                    counter += 1
                    if counter >= self.no_of_top_item:
                        break

        row += 2
        # find lost and new partner here
        if self.type == 'compare':
            worksheet.write_merge(row, row, 0, 2, 'New Products', bold_center)
            worksheet.write_merge(row, row, 4, 6, 'Lost Products', bold_center)
            row = row + 1
            row_after_heading = row
            lost_product_list = []
            new_product_list = []
            if final_product_list and final_compare_product_list:
                for item in final_compare_product_list:
                    if item not in final_product_list:
                        new_product_list.append(item)
                for new in new_product_list:
                    worksheet.write_merge(row, row, 0, 2, new)
                    row = row+1
                row = row_after_heading
                for item in final_product_list:
                    if item not in final_compare_product_list:
                        lost_product_list.append(item)
                for lost in lost_product_list:
                    worksheet.write_merge(row, row, 4, 6, lost)
                    row = row+1

        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env['ir.attachment']
        attachment_vals = {
            "name": "Top Invoicing Products Xls Report",
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search([('name', '=', 'Top Invoicing Products Xls Report'),
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
