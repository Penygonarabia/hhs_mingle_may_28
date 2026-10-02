# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError

class QuotationXlsx(models.AbstractModel):
    _name = 'report.crm_commercial.quotation_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Quotation Excel Export'

    def generate_xlsx_report(self, workbook, data, quotations):
        for quotation in quotations:
            if not self.env.user.allow_export_quotation and not self.env.user.has_group('crm_commercial.group_crm_commercial_manager'):
                raise UserError(_("You are not authorized to export quotation data to Excel."))

            sheet = workbook.add_worksheet(quotation.name[:31])
            bold = workbook.add_format({'bold': True, 'bg_color': '#002060', 'font_color': 'white'})
            header_title = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#002060'})
            num_fmt = workbook.add_format({'num_format': '#,##0.00'})

            sheet.write(0, 0, f"Quotation: {quotation.name}", header_title)
            sheet.write(1, 0, f"Project Name: {quotation.project_name or ''}")
            sheet.write(2, 0, f"Customer: {quotation.partner_id.name if quotation.partner_id else ''}")

            headers = [
                'Product Group', 'Product Category', 'Sale Type', 'Part No',
                'Stock', 'Qty', 'Unit Cost (B)', 'Sale Price', 'Discount %',
                'DSI', 'SMC', 'Spl Spt', 'VAT', 'Amount'
            ]
            for col_idx, h in enumerate(headers):
                sheet.write(4, col_idx, h, bold)

            row_idx = 5
            for line in quotation.line_ids:
                sheet.write(row_idx, 0, line.product_group_id.name if line.product_group_id else '')
                sheet.write(row_idx, 1, line.product_category_id.name if line.product_category_id else '')
                sheet.write(row_idx, 2, line.sale_type_id.name if line.sale_type_id else '')
                sheet.write(row_idx, 3, line.product_id.display_name if line.product_id else '')
                sheet.write(row_idx, 4, line.stock_qty, num_fmt)
                sheet.write(row_idx, 5, line.qty, num_fmt)
                sheet.write(row_idx, 6, line.unit_cost, num_fmt)
                sheet.write(row_idx, 7, line.sale_price, num_fmt)
                sheet.write(row_idx, 8, line.discount_percent, num_fmt)
                sheet.write(row_idx, 9, line.dsi, num_fmt)
                sheet.write(row_idx, 10, line.smc, num_fmt)
                sheet.write(row_idx, 11, line.special_support, num_fmt)
                sheet.write(row_idx, 12, line.vat_amount, num_fmt)
                sheet.write(row_idx, 13, line.amount, num_fmt)
                row_idx += 1

            # Summary Costing Section
            row_idx += 1
            sheet.write(row_idx, 0, "Total Selling Price (A)", header_title)
            sheet.write(row_idx, 1, quotation.total_selling_price, num_fmt)
            row_idx += 1
            sheet.write(row_idx, 0, "Total Cost (B)", header_title)
            sheet.write(row_idx, 1, quotation.total_cost, num_fmt)
            row_idx += 1
            sheet.write(row_idx, 0, "Gross Margin", header_title)
            sheet.write(row_idx, 1, quotation.gross_margin, num_fmt)
            row_idx += 1
            sheet.write(row_idx, 0, "Gross Margin (%)", header_title)
            sheet.write(row_idx, 1, quotation.gross_margin_percent, num_fmt)


class PipelineProjectXlsx(models.AbstractModel):
    _name = 'report.crm_commercial.pipeline_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Pipeline Project Excel Export'

    def generate_xlsx_report(self, workbook, data, leads):
        sheet = workbook.add_worksheet('Pipeline Projects')
        bold = workbook.add_format({'bold': True, 'bg_color': '#002060', 'font_color': 'white'})
        num_fmt = workbook.add_format({'num_format': '#,##0.00'})

        headers = [
            'Lead No', 'Warehouse', 'Project Name', 'Customer / Name', 'Email',
            'Phone', 'Lead Value', 'Tags', 'Assigned Salesman', 'Status',
            'Source', 'Created On'
        ]
        for col_idx, h in enumerate(headers):
            sheet.write(0, col_idx, h, bold)

        quotations = self.env['crm.commercial.quotation'].search([
            ('state', 'not in', ['confirmed', 'expired', 'cancelled']),
            ('ignore_for_reporting', '=', False)
        ])

        row_idx = 1
        for q in quotations:
            sheet.write(row_idx, 0, q.name)
            sheet.write(row_idx, 1, q.warehouse_id.name if q.warehouse_id else '')
            sheet.write(row_idx, 2, q.project_name or '')
            sheet.write(row_idx, 3, q.partner_id.name if q.partner_id else q.to_name)
            sheet.write(row_idx, 4, q.email or '')
            sheet.write(row_idx, 5, q.phone or '')
            sheet.write(row_idx, 6, q.total_amount, num_fmt)
            sheet.write(row_idx, 7, ", ".join(q.tag_ids.mapped('name')))
            sheet.write(row_idx, 8, q.assigned_id.name if q.assigned_id else '')
            sheet.write(row_idx, 9, q.state)
            sheet.write(row_idx, 10, q.quotation_type_id.name if q.quotation_type_id else '')
            sheet.write(row_idx, 11, str(q.date or ''))
            row_idx += 1
