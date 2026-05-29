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


class InvoiceProductIndentXLS(models.Model):
    _name = 'sh.invoice.product.indent.xls'
    _description = 'Invoice Product Indent Xls Report'
    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64, readonly=True)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sh.invoice.product.indent.xls&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class InvoiceProductIndentWizard(models.TransientModel):
    _name = 'sh.invoice.product.indent.wizard'
    _description = 'Invoice Product Indent Wizard'

    sh_start_date = fields.Date(
        'Start Date', required=True, default=fields.Datetime.now)
    sh_end_date = fields.Date(
        'End Date', required=True, default=fields.Datetime.now)
    sh_partner_ids = fields.Many2many(
        'res.partner', string='Customers', required=True)
    sh_status = fields.Selection([('draft', 'Draft'),
                                  ('posted', 'Posted'),
                                  ('cancel', 'Cancelled'), ], string="Status", default='draft')
    sh_move_type = fields.Selection([('out_invoice', 'Customer Invoice'),
                                     ('out_refund', 'Customer Credit Note'),
                                     ('in_invoice', 'Vendor Bill'),
                                     ('in_refund', 'Vendor Credit Note')], default='out_invoice', string="Invoice Type")
    sh_category_ids = fields.Many2many(
        'product.category', string='Categories', required=True)
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
        return self.env.ref('sh_accounting_reports.sh_invoice_product_indent_action').report_action([], data=datas)

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet(
            'Invoices Product Indent', bold_center)
        worksheet.write_merge(
            0, 1, 0, 1, 'Invoices Product Indent', heading_format)
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
        worksheet.write_merge(2, 2, 0, 1, date_start.strftime("%m-%d-%y") +
                              " to " + date_stop.strftime("%m-%d-%y"), bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        move_dic = {}
        for partner in self.sh_partner_ids:
            customer_list = []
            for category in self.sh_category_ids:
                category_dic = {}
                category_list = []
                products = self.env['product.product'].sudo().search(
                    [('categ_id', '=', category.id)])
                for product in products:
                    domain = [
                        ("move_id.invoice_date", ">=",
                         fields.Datetime.to_string(date_start)),
                        ("move_id.invoice_date", "<=",
                         fields.Datetime.to_string(date_stop)),
                        ('move_id.partner_id', '=', partner.id),
                        ('product_id', '=', product.id)
                    ]
                    if self.sh_status:
                        if self.sh_status == 'draft':
                            domain.append(
                                ('move_id.state', 'in', ['draft']))
                        elif self.sh_status == 'posted':
                            domain.append(
                                ('move_id.state', 'in', ['posted']))
                        elif self.sh_status == 'cancel':
                            domain.append(('state', 'in', ['posted']))
                    if self.sh_move_type:
                        if self.sh_move_type == 'out_invoice':
                            domain.append(
                                ('move_id.move_type', '=', 'out_invoice'))
                        elif self.sh_move_type == 'in_invoice':
                            domain.append(
                                ('move_id.move_type', '=', 'in_invoice'))
                        elif self.sh_move_type == 'out_refund':
                            domain.append(
                                ('move_id.move_type', '=', 'out_refund'))
                        else:
                            domain.append(
                                ('move_id.move_type', '=', 'in_refund'))
                    if self.company_ids:
                        domain.append(
                            ('company_id', 'in', self.company_ids.ids))
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
        row = 4
        if move_dic:
            for key in move_dic.keys():
                worksheet.write(row, 0, key, bold)
                worksheet.write_merge(row, row, 0, 1, key, bold)
                row = row + 2
                for category_data in move_dic[key]:
                    for key_2 in category_data.keys():
                        total = 0.0
                        worksheet.write_merge(row, row, 0, 1, key_2, bold)
                        row = row + 1
                        worksheet.write(row, 0, "Product", bold_center_total)
                        worksheet.write(row, 1, "Quantity", bold_center_total)
                        row = row + 1
                        for record in category_data[key_2]:
                            total = total + record.get('qty')
                            worksheet.write(row, 0, record.get('name'), center)
                            worksheet.write(row, 1, "{:.2f}".format(
                                record.get('qty')), center)
                            row = row + 1
                        worksheet.write(row, 0, "Total", bold_center_total)
                        worksheet.write(row, 1, "{:.2f}".format(
                            total), bold_center_total)
                        row = row + 2
        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env['ir.attachment']
        attachment_vals = {
            "name": "Invoices Product Indent",
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search([('name', '=', 'Invoices Product Indent'),
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
