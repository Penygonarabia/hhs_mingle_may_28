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
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


class InvoiceReportXLS(models.Model):
    _name = 'sh.invoice.summary.xls'
    _description = 'Invoice Summary Xls Report'
    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64, readonly=True)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sh.invoice.summary.xls&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class InvioceSummaryWizard(models.TransientModel):
    _name = 'sh.invoice.summary.wizard'
    _description = 'Invoice Summary Wizard'

    sh_start_date = fields.Date(
        'Start Date', required=True, default=fields.Datetime.now)
    sh_end_date = fields.Date(
        'End Date', required=True, default=fields.Datetime.now)
    sh_partner_ids = fields.Many2many(
        'res.partner', string='Customers', required=True)
    sh_status = fields.Selection(
        [('draft', 'Draft'), ('posted', 'Posted'), ('cancel', 'Cancel')], string="Status", default='posted')
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
        return self.env.ref('sh_accounting_reports.sh_invoice_summary_action').report_action([], data=datas)

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet(
            'Invoice Summary', bold_center)
        worksheet.write_merge(
            0, 1, 0, 6, 'Invoice Summary', heading_format)
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
            today = user_tz.localize(fields.Datetime.from_string(
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
        worksheet.write_merge(2, 2, 0, 6, date_start.strftime(
            "%d-%m-%y") + " to " + date_stop.strftime(
            "%d-%m-%y"), bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        worksheet.col(2).width = int(18 * 260)
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(33 * 260)
        worksheet.col(5).width = int(15 * 260)
        worksheet.col(6).width = int(15 * 260)
        customer_move_dic = {}
        for partner_id in self.sh_partner_ids:
            move_list = []
            domain = [
                ("invoice_date", ">=", fields.Datetime.to_string(date_start)),
                ("invoice_date", "<=", fields.Datetime.to_string(date_stop)),
                ("partner_id", "=", partner_id.id),
            ]
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
                    domain.append(('move_type', '=', 'in_refund'))
            if self.sh_status:
                if self.sh_status == 'draft':
                    domain.append(('state', '=', 'draft'))
                elif self.sh_status == 'posted':
                    domain.append(('state', '=', 'posted'))
                else:
                    domain.append(('state', '=', 'cancel'))
            search_moves = self.env['account.move'].sudo().search(domain)
            if search_moves:
                for move in search_moves:
                    move_dic = {
                        'invoice_number': move.name,
                        'invoice_date': move.invoice_date,
                        'invoice_currency_id': move.currency_id.symbol,
                        'invoice_amount': move.amount_total,
                        'invoice_paid_amount': move.amount_total - move.amount_residual,
                        'due_amount': move.amount_residual,
                    }
                    move_list.append(move_dic)

            search_partner = self.env['res.partner'].sudo().search([
                ('id', '=', partner_id.id)
            ], limit=1)
            if search_partner:
                customer_move_dic.update(
                    {search_partner.name_get()[0][1]: move_list})
        row = 4
        if customer_move_dic:
            for key in customer_move_dic.keys():
                worksheet.write_merge(
                    row, row, 0, 6, key, bold_center)
                row = row + 2
                total_amount_invoiced = 0.0
                total_amount_paid = 0.0
                total_amount_due = 0.0
                worksheet.write(row, 0, "Invoice Number", bold)
                worksheet.write(row, 1, "Invoice Date", bold)
                worksheet.write(row, 2, "Amount Invoiced", bold)
                worksheet.write(row, 3, "Amount Paid", bold)
                worksheet.write(row, 4, "Amount Due", bold)
                row = row + 1
                for rec in customer_move_dic[key]:
                    worksheet.write(row, 0, rec.get('invoice_number'), center)
                    worksheet.write(row, 1, str(
                        rec.get('invoice_date')), center)
                    worksheet.write(row, 2, str(rec.get(
                        'invoice_currency_id')) + "{:.2f}".format(rec.get('invoice_amount')), center)
                    worksheet.write(row, 3, str(rec.get('invoice_currency_id')) + "{:.2f}".format(rec.get(
                        'invoice_paid_amount')), center)
                    worksheet.write(row, 4, str(rec.get(
                        'invoice_currency_id')) + "{:.2f}".format(rec.get('due_amount')), center)
                    total_amount_invoiced = total_amount_invoiced + \
                        rec.get('invoice_amount')
                    total_amount_paid = total_amount_paid + \
                        rec.get('invoice_paid_amount')
                    total_amount_due = total_amount_due + rec.get('due_amount')
                    row = row + 1
                worksheet.write(row, 1, "Total", left)
                worksheet.write(row, 2, "{:.2f}".format(total_amount_invoiced),
                                bold_center_total)
                worksheet.write(row, 3, "{:.2f}".format(
                    total_amount_paid), bold_center_total)
                worksheet.write(row, 4, "{:.2f}".format(
                    total_amount_due), bold_center_total)
                row = row + 2
        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env['ir.attachment']
        attachment_vals = {
            "name": "Invoice Summary.xls",
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search([('name', '=', 'Invoice Summary.xls'),
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
