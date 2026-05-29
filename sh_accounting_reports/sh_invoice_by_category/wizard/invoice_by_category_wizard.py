# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import xlwt
import base64
from odoo.exceptions import UserError
import io
import pytz
from datetime import datetime, timedelta


class InvoiceByCategoryXLS(models.Model):
    _name = 'sh.invoice.category.xls'
    _description = 'Invoice by Category Xls Report'
    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64, readonly=True)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sh.invoice.category.xls&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class InvoiceByCategoryWizard(models.TransientModel):
    _name = 'sh.invoice.category.wizard'
    _description = 'Invoice By Category Wizard'

    sh_start_date = fields.Date(
        'Start Date', required=True, default=fields.Datetime.now)
    sh_end_date = fields.Date(
        'End Date', required=True, default=fields.Datetime.now)
    sh_category_ids = fields.Many2many('product.category', string='Categories')
    company_ids = fields.Many2many(
        'res.company', default=lambda self: self.env.companies, string="Companies")
    sh_move_type = fields.Selection([('out_invoice', 'Customer Invoice'),
                                     ('out_refund', 'Customer Credit Note'),
                                     ('in_invoice', 'Vendor Bill'),
                                     ('in_refund', 'Vendor Credit Note')], default='out_invoice', string="Invoice Type")

    @api.onchange('sh_move_type')
    def _onchange_move_type(self):
        domain = {}
        if not self.sh_move_type:
            partner_obj = self.env['res.partner'].search([])
            domain = {'sh_partner_ids': [('id', 'in', partner_obj.ids)]}
        else:
            if self.sh_move_type == 'out_invoice' or self.sh_move_type == 'out_refund':
                partner_obj = self.env['res.partner'].search(
                    [('customer_rank', '>', 0)])
                domain = {'sh_partner_ids': [('id', 'in', partner_obj.ids)]}
            elif self.sh_move_type == 'in_invoice' or self.sh_move_type == 'in_refund':
                partner_obj = self.env['res.partner'].search(
                    [('supplier_rank', '>', 0)])
                domain = {'sh_partner_ids': [('id', 'in', partner_obj.ids)]}
        return {'domain': domain}

    @api.constrains('sh_start_date', 'sh_end_date')
    def _check_dates(self):
        if self.filtered(lambda c: c.sh_end_date and c.sh_start_date > c.sh_end_date):
            raise ValidationError(_('start date must be less than end date.'))

    def print_report(self):
        datas = self.read()[0]
        return self.env.ref('sh_accounting_reports.sh_invoice_by_category_action').report_action([], data=datas)

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet(
            'Invoices By Product Category', bold_center)
        worksheet.write_merge(
            0, 1, 0, 8, 'Invoices By Product Category', heading_format)
        left = xlwt.easyxf('align: horiz center;font:bold True')
        center = xlwt.easyxf('align: horiz center;')
        bold_center_total = xlwt.easyxf('align: horiz center;font:bold True')
        date_start = False
        date_stop = False
        if self.sh_start_date:
            date_start = fields.Date.from_string(self.sh_start_date)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Date.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if self.sh_end_date:
            date_stop = fields.Date.from_string(self.sh_end_date)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        worksheet.write_merge(2, 2, 0, 8, date_start.strftime("%m-%d-%y") +
                              " to " + date_stop.strftime("%m-%d-%y"), bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        worksheet.col(2).width = int(18 * 260)
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(33 * 260)
        worksheet.col(5).width = int(15 * 260)
        worksheet.col(6).width = int(15 * 260)
        worksheet.col(7).width = int(15 * 260)
        account_move_obj = self.env["account.move"]
        category_move_dic = {}
        categories = False
        if self.sh_category_ids:
            categories = self.sh_category_ids
        else:
            categories = self.env['product.category'].sudo().search([])
        if categories:
            for category in categories:
                move_list = []

                domain = [
                    ("invoice_date", ">=", fields.Date.to_string(date_start)),
                    ("invoice_date", "<=", fields.Date.to_string(date_stop)),
                ]
                if self.sh_move_type:
                    if self.sh_move_type == 'out_invoice':
                        domain.append(('move_type', '=', 'out_invoice'))
                    elif self.sh_move_type == 'in_invoice':
                        domain.append(('move_type', '=', 'in_invoice'))
                    elif self.sh_move_type == 'out_refund':
                        domain.append(('move_type', '=', 'out_refund'))
                    else:
                        domain.append(('move_type', '=', 'in_refund'))
                if self.company_ids:
                    domain.append(
                        ('company_id', 'in', self.company_ids.ids))
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
                                        'account_currency_id': line.currency_id.symbol
                                    }
                                    if line.tax_ids:
                                        tax_ammount_line = 0.0
                                        for tax in line.tax_ids:
                                            tax_ammount_line += (line.price_unit *
                                                                 tax.amount)/100
                                    else:
                                        tax_amount_line = 0
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
        row = 4
        if category_move_dic:
            for key in category_move_dic.keys():
                total_qty = 0.0
                total_price = 0.0
                total_tax = 0.0
                total_subtotal = 0.0
                total = 0.0
                worksheet.write_merge(
                    row, row, 0, 8, key, bold_center)
                row = row + 2
                worksheet.write(row, 0, "Invoice Number", bold)
                worksheet.write(row, 1, "Invoice Date", bold)
                worksheet.write(row, 2, "Product", bold)
                worksheet.write(row, 3, "Quantity", bold)
                worksheet.write(row, 4, "Price", bold)
                worksheet.write(row, 5, "Tax", bold)
                worksheet.write(row, 6, "Subtotal", bold)
                worksheet.write(row, 7, "Total", bold)
                row = row + 1
                for rec in category_move_dic[key]:
                    total_qty += rec.get('qty')
                    total_price += rec.get('sale_price')
                    total_tax += rec.get('tax')
                    total_subtotal += rec.get('qty', 0.0) * \
                        rec.get('sale_price', 0.0)
                    total += (rec.get('sale_price') *
                              rec.get('qty', '')) + rec.get('tax')
                    worksheet.write(row, 0, rec.get('invoice_number'), center)
                    worksheet.write(row, 1, str(
                        rec.get('invoice_date')), center)
                    worksheet.write(row, 2, rec.get('product'), center)
                    worksheet.write(row, 3, str(
                        "{:.2f}".format(rec.get('qty'))), center)
                    worksheet.write(row, 4, str(rec.get(
                        'account_currency_id')) + str(" {:.2f}".format(rec.get('sale_price'))), center)
                    worksheet.write(row, 5, str(
                        rec.get('account_currency_id')) + str(" {:.2f}".format(rec.get('tax'))), center)
                    worksheet.write(row, 6, str(rec.get('account_currency_id')) + str(
                        " {:.2f}".format(rec.get('sale_price') * rec.get('qty', ''))), center)
                    worksheet.write(row, 7, str(rec.get('account_currency_id')) + str(" {:.2f}".format(
                        (rec.get('sale_price') * rec.get('qty', '')) + rec.get('tax'))), center)
                    row = row + 1
                worksheet.write(row, 2, "Total", bold_center_total)
                worksheet.write(row, 3, "{:.2f}".format(
                    total_qty), bold_center_total)
                worksheet.write(row, 4, "{:.2f}".format(
                    total_price), bold_center_total)
                worksheet.write(row, 5, "{:.2f}".format(
                    total_tax), bold_center_total)
                worksheet.write(row, 6, "{:.2f}".format(
                    total_subtotal), bold_center_total)
                worksheet.write(row, 7, "{:.2f}".format(
                    total), bold_center_total)
                row = row + 2
        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env['ir.attachment']
        attachment_vals = {
            "name": "Invoices By Product Category.xls",
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search([('name', '=', 'Invoices By Product Category.xls'),
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
