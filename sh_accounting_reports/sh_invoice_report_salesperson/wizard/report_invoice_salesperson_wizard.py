# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import xlwt
import base64
from odoo.exceptions import UserError
import io
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import pytz
from datetime import datetime, timedelta


class InvoiceSalespersonXLS(models.Model):
    _name = 'invoice.report.salesperson.xls'
    _description = "Invoice Salesperson XLS"

    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64, readonly=True)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=invoice.report.salesperson.xls&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class InvoiceSalespersonWizard(models.TransientModel):
    _name = "sh.invoice.report.salesperson.wizard"
    _description = "sh invoice report salesperson wizard model"

    @api.model
    def default_company_ids(self):
        is_allowed_companies = self.env.context.get(
            'allowed_company_ids', False)
        if is_allowed_companies:
            return is_allowed_companies
        return

    date_start = fields.Date(
        string="Start Date", required=True, default=fields.Datetime.now)
    date_end = fields.Date(
        string="End Date", required=True, default=fields.Datetime.now)
    user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="rel_sh_sale_report_salesperson_user_ids",
        string="Salesperson")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancel')
    ], string='Status', default='posted')
    sh_move_type = fields.Selection([('out_invoice', 'Customer Invoice'),
                                     ('out_refund', 'Customer Credit Note'),
                                     ('in_invoice', 'Vendor Bill'),
                                     ('in_refund', 'Vendor Credit Note')], default='out_invoice', string="Invoice Type")
    company_ids = fields.Many2many(
        'res.company', string='Companies', default=default_company_ids)

    @api.model
    def default_get(self, fields):
        rec = super(InvoiceSalespersonWizard, self).default_get(fields)
        search_users = self.env["res.users"].sudo().search(
            [('company_id', 'in', self.env.context.get('allowed_company_ids', False))])
        if self.env.user.has_group('account.group_account_manager'):
            rec.update({
                "user_ids": [(6, 0, search_users.ids)],
            })
        else:
            rec.update({
                "user_ids": [(6, 0, search_users.ids)],
            })
        return rec

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        if self.filtered(lambda c: c.date_end and c.date_start > c.date_end):
            raise ValidationError(_('start date must be less than end date.'))

    def print_report(self):
        datas = self.read()[0]
        return self.env.ref('sh_accounting_reports.sh_invoice_report_salesperson_report').report_action([], data=datas)

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet(
            'Invoice Report by Sales Person', bold_center)
        worksheet.write_merge(
            0, 1, 0, 5, 'Invoice Report by Sales Person', heading_format)
        left = xlwt.easyxf('align: horiz center;font:bold True')
        date_start = False
        date_stop = False
        if self.date_start:
            date_start = fields.Date.from_string(self.date_start)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get(
                'tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Date.from_string(
                fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if self.date_end:
            date_stop = fields.Date.from_string(self.date_end)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)

        worksheet.write_merge(2, 2, 0, 5, date_start.strftime(
            "%m-%d-%y") + " to " + date_stop.strftime("%m-%d-%y"), bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        worksheet.col(2).width = int(18 * 260)
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(33 * 260)
        worksheet.col(5).width = int(15 * 260)
        row = 4
        for user_id in self.user_ids:
            row = row + 2
            worksheet.write_merge(
                row, row, 0, 5, "Sales Person: " + user_id.name, bold_center)
            row = row + 2
            worksheet.write(row, 0, "Invoice Number", bold)
            worksheet.write(row, 1, "Invoice Date", bold)
            worksheet.write(row, 2, "Customer", bold)
            worksheet.write(row, 3, "Total", bold)
            worksheet.write(row, 4, "Amount Invoiced", bold)
            worksheet.write(row, 5, "Amount Due", bold)
            if self.state == 'draft':
                sum_of_amount_total = 0.0
                total_invoice_amount = 0.0
                total_due_amount = 0.0
                domain = [
                    ("invoice_date", ">=", fields.Date.to_string(date_start)),
                    ("invoice_date", "<=", fields.Date.to_string(date_stop)),
                    ("user_id", "=", user_id.id)
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
                if self.state:
                    domain.append(('state', '=', self.state))
                for account_move in self.env['account.move'].sudo().search(domain):
                    row = row + 1
                    sum_of_amount_total = sum_of_amount_total + account_move.amount_total
                    sum_of_invoice_amount = 0.0
                    sum_of_due_amount = 0.0
                    if account_move:
                        for invoice_id in account_move.filtered(lambda inv: inv.state not in ['cancel', 'draft']):
                            sum_of_invoice_amount += invoice_id.amount_total_signed
                            sum_of_due_amount += invoice_id.amount_residual_signed
                            total_invoice_amount += invoice_id.amount_total_signed
                            total_due_amount += invoice_id.amount_residual_signed
                    invoice_date = account_move.invoice_date
                    worksheet.write(row, 0, account_move.name)
                    worksheet.write(row, 1, invoice_date.strftime(
                        "%m-%d-%y"))
                    worksheet.write(row, 2, account_move.partner_id.name)
                    worksheet.write(row, 3, account_move.amount_total)
                    worksheet.write(row, 4, sum_of_invoice_amount)
                    worksheet.write(row, 5, sum_of_due_amount)
                row = row + 1
                worksheet.write(row, 2, "Total", left)
                worksheet.write(row, 3, sum_of_amount_total)
                worksheet.write(row, 4, total_invoice_amount)
                worksheet.write(row, 5, total_due_amount)
            elif self.state == 'posted' or self.state == 'cancel':
                sum_of_amount_total = 0.0
                total_invoice_amount = 0.0
                total_due_amount = 0.0
                domain = [
                    ("invoice_date", ">=", fields.Date.to_string(date_start)),
                    ("invoice_date", "<=", fields.Date.to_string(date_stop)),
                    ("user_id", "=", user_id.id)
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

                if self.state:
                    domain.append(('state', '=', self.state))
                for account_move in self.env['account.move'].sudo().search(domain):
                    row = row + 1
                    sum_of_amount_total = sum_of_amount_total + account_move.amount_total
                    sum_of_invoice_amount = 0.0
                    sum_of_due_amount = 0.0
                    if account_move:
                        for invoice_id in account_move.filtered(lambda inv: inv.state not in ['cancel', 'draft']):
                            sum_of_invoice_amount += invoice_id.amount_total_signed
                            sum_of_due_amount += invoice_id.amount_residual_signed
                            total_invoice_amount += invoice_id.amount_total_signed
                            total_due_amount += invoice_id.amount_residual_signed
                    invoice_date = account_move.invoice_date
                    worksheet.write(row, 0, account_move.name)
                    worksheet.write(row, 1, invoice_date.strftime(
                        "%m-%d-%y"))
                    worksheet.write(row, 2, account_move.partner_id.name)
                    worksheet.write(row, 3, account_move.amount_total)
                    worksheet.write(row, 4, sum_of_invoice_amount)
                    worksheet.write(row, 5, sum_of_due_amount)
                row = row + 1
                worksheet.write(row, 2, "Total", left)
                worksheet.write(row, 3, sum_of_amount_total)
                worksheet.write(row, 4, total_invoice_amount)
                worksheet.write(row, 5, total_due_amount)
        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env['ir.attachment']
        attachment_vals = {
            "name": "Invoice By Sales Person Xls Report.xls",
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search([('name', '=', 'Invoice By Sales Person Xls Report.xls'),
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
