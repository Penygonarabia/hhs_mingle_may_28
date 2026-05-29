# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
import xlwt
import base64
from odoo.exceptions import UserError
import io
import pytz
from datetime import date, timedelta
from odoo.exceptions import ValidationError
from odoo import _, api, fields, models


class InvoiceAnalysisReportXLS(models.Model):
    _name = 'sh.invoice.analysis.xls'
    _description = 'Invoices Analysis Xls Report'
    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64, readonly=True)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sh.invoice.analysis.xls&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class InvoicesAnalysisWizard(models.TransientModel):
    _name = 'sh.invoices.analysis.wizard'
    _description = 'Invoices Analysis Wizard'

    sh_start_date = fields.Date(
        'Start Date', required=True, default=fields.Date.today)
    sh_end_date = fields.Date(
        'End Date', required=True, default=fields.Date.today)
    sh_partner_ids = fields.Many2many(
        'res.partner', string='Customers/Vendors', required=True)
    sh_status = fields.Selection([('draft', 'Draft'),
                                  ('posted', 'Posted'),
                                  ('cancel', 'Cancelled'), ], string="Status", default='draft')
    report_by = fields.Selection(
        [('move', 'Account Move'), ('product', 'Products')], string='Report Print By', default='move')
    sh_move_type = fields.Selection([('out_invoice', 'Customer Invoice'),
                                     ('out_refund', 'Customer Credit Note'),
                                     ('in_invoice', 'Vendor Bill'),
                                     ('in_refund', 'Vendor Credit Note')], default='out_invoice', string="Invoice Type")
    sh_product_ids = fields.Many2many('product.product', string='Products')
    company_ids = fields.Many2many(
        'res.company', default=lambda self: self.env.companies, string="Companies")

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
        return self.env.ref('sh_accounting_reports.sh_cus_invoice_analysis_action').report_action([], data=datas)

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet(
            'Customer/Vendor Invoices Analysis', bold_center)
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
        start_date = date_start.strftime('%m-%d-%Y')
        end_date = date_start.strftime('%m-%d-%Y')
        if self.report_by == 'move':
            worksheet.write_merge(
                0, 1, 0, 5, 'Customer/Vendor  Invoices Analysis', heading_format)
            worksheet.write_merge(
                2, 2, 0, 5, start_date + " to " + end_date, bold)
        elif self.report_by == 'product':
            worksheet.write_merge(
                0, 1, 0, 7, 'Customer/Vendor  Invoices Analysis', heading_format)
            worksheet.write_merge(
                2, 2, 0, 7, start_date + " to " + end_date, bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        worksheet.col(2).width = int(18 * 260)
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(33 * 260)
        worksheet.col(5).width = int(15 * 260)
        worksheet.col(6).width = int(15 * 260)
        worksheet.col(7).width = int(15 * 260)
        move_dic_by_move = {}
        move_dic_by_products = {}
        for partner_id in self.sh_partner_ids:
            move_list = []
            domain = [
                ("invoice_date", ">=", fields.Date.to_string(date_start)),
                ("invoice_date", "<=", fields.Date.to_string(date_stop)),
                ("partner_id", "=", partner_id.id),
            ]
            if self.sh_status == 'draft':
                domain.append(('state', 'in', ['draft']))
            elif self.sh_status == 'posted':
                domain.append(('state', 'in', ['posted']))
            elif self.sh_status == 'cancel':
                domain.append(('state', 'in', ['posted']))
            if self.company_ids:
                domain.append(
                    ('company_id', 'in', self.company_ids.ids))
            if self.sh_move_type:
                if self.sh_move_type == 'out_invoice':
                    domain.append(('move_type', '=', 'out_invoice'))
                elif self.sh_move_type == 'in_invoice':
                    domain.append(('move_type', '=', 'in_invoice'))
                elif self.sh_move_type == 'out_refund':
                    domain.append(('move_type', '=', 'out_refund'))
                else:
                    domain.append(('move_typee', '=', 'in_refund'))

            search_moves = self.env['account.move'].sudo().search(domain)
            if search_moves:
                for move in search_moves:
                    if self.report_by == 'move':
                        move_dic = {
                            'invoice_number': move.name,
                            'invoice_date': move.invoice_date,
                            'invoice_amount': move.amount_total,
                            'invoice_user_id': move.invoice_user_id.name,
                            'account_currency_id': move.currency_id.symbol,
                        }
                        paid_amount = 0.0
                        if move.type == 'out_invoice':
                            paid_amount += move.amount_total-move.amount_residual
                        elif move.type == 'out_refund':
                            paid_amount += - \
                                (move.amount_total -
                                    move.amount_residual)
                        move_dic.update({
                            'paid_amount': paid_amount,
                            'balance_amount': move.amount_total - paid_amount
                        })
                        move_list.append(move_dic)
                    elif self.report_by == 'product' and move.invoice_line_ids:
                        invoice_line = False
                        if self.sh_product_ids:
                            invoice_line = move.invoice_line_ids.sudo().filtered(
                                lambda x: x.product_id.id in self.sh_product_ids.ids)
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
                                    'account_currency_id': line.currency_id.symbol,
                                }
                                if line.tax_ids:
                                    tax_ammount_line = 0.0
                                    for tax in line.tax_ids:
                                        tax_ammount_line += (line.price_unit *
                                                             tax.amount)/100
                                else:
                                    tax_amount_line = 0.0
                                move_dic.update({
                                    'tax': tax_ammount_line,
                                })
                                move_list.append(move_dic)
            search_partner = self.env['res.partner'].sudo().search([
                ('id', '=', partner_id.id)
            ], limit=1)
            if search_partner:
                if self.report_by == 'move':
                    move_dic_by_move.update(
                        {search_partner.name_get()[0][1]: move_list})
                elif self.report_by == 'product':
                    move_dic_by_products.update(
                        {search_partner.name_get()[0][1]: move_list})
        row = 4
        if self.report_by == 'move':
            if move_dic_by_move:
                for key in move_dic_by_move.keys():
                    worksheet.write_merge(
                        row, row, 0, 5, key, bold_center)
                    row = row + 2
                    total_invoice_amount = 0.0
                    total_amount_paid = 0.0
                    total_balance = 0.0
                    worksheet.write(row, 0, "Invoice Number", bold)
                    worksheet.write(row, 1, "Invoice Date", bold)
                    worksheet.write(row, 2, "Salesperson", bold)
                    worksheet.write(row, 3, "Invoices Amount", bold)
                    worksheet.write(row, 4, "Amount Paid", bold)
                    worksheet.write(row, 5, "Balance", bold)
                    row = row + 1
                    for rec in move_dic_by_move[key]:
                        worksheet.write(row, 0, rec.get(
                            'invoice_number'), center)
                        worksheet.write(row, 1, str(
                            rec.get('invoice_date')), center)
                        worksheet.write(row, 2, rec.get(
                            'invoice_user_id'), center)
                        worksheet.write(row, 3, str(rec.get(
                            'account_currency_id'))+str("{:.2f}".format(rec.get('invoice_amount'))), center)
                        worksheet.write(row, 4, str(rec.get(
                            'account_currency_id')) + str("{:.2f}".format(rec.get('paid_amount'))), center)
                        worksheet.write(row, 5, str(rec.get(
                            'account_currency_id')) + str("{:.2f}".format(rec.get('balance_amount'))), center)
                        total_invoice_amount = total_invoice_amount + \
                            rec.get('invoice_amount')
                        total_amount_paid = total_amount_paid + \
                            rec.get('paid_amount')
                        total_balance = total_balance + \
                            rec.get('balance_amount')
                        row = row + 1
                    worksheet.write(row, 2, "Total", left)
                    worksheet.write(row, 3, "{:.2f}".format(
                        total_invoice_amount), bold_center_total)
                    worksheet.write(row, 4, "{:.2f}".format(
                        total_amount_paid), bold_center_total)
                    worksheet.write(row, 5, "{:.2f}".format(
                        total_balance), bold_center_total)
                    row = row + 2
        elif self.report_by == 'product':
            if move_dic_by_products:
                for key in move_dic_by_products.keys():
                    worksheet.write_merge(
                        row, row, 0, 7, key, bold_center)
                    row = row + 2
                    total_tax = 0.0
                    total_subtotal = 0.0
                    total_balance = 0.0
                    worksheet.write(row, 0, "Number", bold)
                    worksheet.write(row, 1, "Date", bold)
                    worksheet.write(row, 2, "Product", bold)
                    worksheet.write(row, 3, "Price", bold)
                    worksheet.write(row, 4, "Quantity", bold)
                    worksheet.write(row, 5, "Disc.(%)", bold)
                    worksheet.write(row, 6, "Tax", bold)
                    worksheet.write(row, 7, "Subtotal", bold)
                    row = row + 1
                    for rec in move_dic_by_products[key]:
                        worksheet.write(row, 0, rec.get(
                            'invoice_number'), center)
                        worksheet.write(row, 1, str(
                            rec.get('invoice_date')), center)
                        worksheet.write(row, 2, rec.get(
                            'product_name'), center)
                        worksheet.write(row, 3, (rec.get('price')), center)
                        worksheet.write(row, 4, rec.get('qty'), center)
                        worksheet.write(row, 5, rec.get('discount'), center)
                        worksheet.write(row, 6, rec.get('tax'), center)
                        worksheet.write(row, 7,  str(rec.get(
                            'account_currency_id'))+str("{:.2f}".format(rec.get('subtotal'))), center)
                        total_tax = total_tax + rec.get('tax')
                        total_subtotal = total_subtotal + rec.get('subtotal')
                        row = row + 1
                    worksheet.write(row, 5, "Total", left)
                    worksheet.write(row, 6, "{:.2f}".format(
                        total_tax), bold_center_total)
                    worksheet.write(row, 7, "{:.2f}".format(
                        total_subtotal), bold_center_total)
                    row = row + 2
        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env['ir.attachment']
        attachment_vals = {
            "name": "Customer/Vendor Invoices Analysis.xls",
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search([('name', '=', 'Customer/Vendor Invoices Analysis.xls'),
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
