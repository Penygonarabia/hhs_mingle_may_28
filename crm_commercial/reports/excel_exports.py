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
            
            # Formats
            title_format = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter'})
            header_format = workbook.add_format({'bold': True, 'bg_color': '#f0f0f0', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            bold = workbook.add_format({'bold': True})
            bold_right = workbook.add_format({'bold': True, 'align': 'right'})
            bold_border = workbook.add_format({'bold': True, 'border': 1})
            bold_border_right = workbook.add_format({'bold': True, 'border': 1, 'align': 'right'})
            bold_border_center = workbook.add_format({'bold': True, 'border': 1, 'align': 'center'})
            
            border = workbook.add_format({'border': 1})
            border_center = workbook.add_format({'border': 1, 'align': 'center'})
            border_right = workbook.add_format({'border': 1, 'align': 'right'})
            
            currency = quotation.env.company.currency_id.name or 'SAR'
            num_fmt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
            curr_fmt = workbook.add_format({'border': 1, 'num_format': f'"{currency}" #,##0.00'})
            curr_bold_fmt = workbook.add_format({'bold': True, 'border': 1, 'num_format': f'"{currency}" #,##0.00'})
            pct_fmt = workbook.add_format({'border': 1, 'num_format': '0.00%'})
            
            # Column widths
            sheet.set_column('A:A', 5)
            sheet.set_column('B:B', 15)
            sheet.set_column('C:C', 35)
            sheet.set_column('D:D', 12)
            sheet.set_column('E:E', 8)
            sheet.set_column('F:F', 15)
            sheet.set_column('G:G', 10)
            sheet.set_column('H:H', 25)
            sheet.set_column('I:N', 15)
            
            # Title
            sheet.merge_range('A1:N1', '', title_format)
            sheet.merge_range('A2:N2', 'PROPOSAL', title_format)
            sheet.merge_range('A3:N3', '', title_format)
            
            # Header info
            sheet.write('A4', 'To:', bold)
            customer_name = quotation.to_name or (quotation.partner_id.name if quotation.partner_id else '')
            sheet.write('A5', customer_name)
            sheet.write('A6', quotation.city or '')
            
            sheet.write('G4', quotation.name or '', bold)
            sheet.write('G5', 'Date:', bold)
            sheet.write('H5', str(quotation.date) if quotation.date else '')
            sheet.write('G6', 'Open Till:', bold)
            sheet.write('H6', str(quotation.expiry_date) if quotation.expiry_date else '')
            sheet.write('G7', 'proposal_profile_agent:', bold)
            sheet.write('H7', quotation.assigned_id.name if quotation.assigned_id else '')
            
            sheet.merge_range('A8:N8', '')

            # Table Headers
            headers = [
                '#', 'Item', 'Description / Details', 'Current Stock', 'Qty', 
                'Rate', 'Discount', 'Tax', 'Tax Amount', 'Amount', 
                'Profit', 'Profit(%)', 'Cost Price', 'DSI Amount'
            ]
            row_idx = 8
            for col_idx, h in enumerate(headers):
                sheet.write(row_idx, col_idx, h, header_format)
                
            # Lines
            row_idx += 1
            line_num = 1
            for line in quotation.line_ids:
                if line.display_type:
                    sheet.merge_range(row_idx, 0, row_idx, 13, line.name or '', bold_border)
                    row_idx += 1
                    continue
                    
                # Calculations
                discounted_rate = line.sale_price * (1.0 - (line.discount_percent / 100.0))
                net_amount = line.qty * discounted_rate
                cost_price = line.qty * line.unit_cost
                dsi_amount = net_amount * (quotation.dsi_percent / 100.0) if quotation.dsi_type != 'zero' else 0.0
                profit = net_amount - cost_price - dsi_amount
                profit_pct = (profit / net_amount) if net_amount else 0.0
                
                sheet.write(row_idx, 0, line_num, border_center)
                sheet.write(row_idx, 1, line.product_id.default_code if line.product_id else '', border)
                sheet.write(row_idx, 2, line.product_id.name if line.product_id else (line.name or ''), border)
                sheet.write(row_idx, 3, line.stock_qty, num_fmt)
                sheet.write(row_idx, 4, line.qty, num_fmt)
                sheet.write(row_idx, 5, line.sale_price, curr_fmt)
                sheet.write(row_idx, 6, f"{line.discount_percent}%", border_center)
                sheet.write(row_idx, 7, f"STANDARD DOMESTIC PURCHASES|{line.vat_percent}%", border_center)
                sheet.write(row_idx, 8, line.vat_amount, curr_fmt)
                sheet.write(row_idx, 9, net_amount, curr_fmt)
                sheet.write(row_idx, 10, profit, curr_fmt)
                sheet.write(row_idx, 11, profit_pct, pct_fmt)
                sheet.write(row_idx, 12, cost_price, num_fmt)
                sheet.write(row_idx, 13, dsi_amount, num_fmt)
                
                line_num += 1
                row_idx += 1
                
            # Summary Section
            sub_total = sum(l.qty * l.sale_price * (1.0 - (l.discount_percent / 100.0)) for l in quotation.line_ids if not l.display_type)
            
            sheet.merge_range(row_idx, 0, row_idx, 12, 'Sub Total', bold_border_right)
            sheet.write(row_idx, 13, sub_total, curr_fmt)
            row_idx += 1
            
            sheet.merge_range(row_idx, 0, row_idx, 12, 'STANDARD DOMESTIC PURCHASES', bold_border_right)
            sheet.write(row_idx, 13, quotation.total_vat, curr_fmt)
            row_idx += 1
            
            sheet.merge_range(row_idx, 0, row_idx, 12, 'Total', bold_border_right)
            sheet.write(row_idx, 13, quotation.total_amount, curr_bold_fmt)
            row_idx += 2
            
            sheet.merge_range(row_idx, 0, row_idx, 12, 'Total Cost Price', bold_border_right)
            sheet.write(row_idx, 13, quotation.total_cost, num_fmt)
            row_idx += 1
            
            sheet.merge_range(row_idx, 0, row_idx, 12, 'Total DSI Amount', bold_border_right)
            sheet.write(row_idx, 13, quotation.total_dsi, num_fmt)
            row_idx += 1
            
            sheet.merge_range(row_idx, 0, row_idx, 12, 'Profit Margin', bold_border_right)
            sheet.write(row_idx, 13, quotation.gross_margin, num_fmt)
            row_idx += 1
            
            sheet.merge_range(row_idx, 0, row_idx, 12, 'Profit Margin (%)', bold_border_right)
            sheet.write(row_idx, 13, (quotation.gross_margin_percent / 100.0) if quotation.gross_margin_percent else 0.0, pct_fmt)


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
