from odoo import models, fields
import io
import base64
import xlsxwriter


class ServiceSaleOrder(models.Model):
    _inherit = 'service.sale.order'

    excel_file = fields.Binary("Excel File")
    excel_filename = fields.Char("Excel Filename")

    def action_print_excel(self):
        self.ensure_one()

        output = io.BytesIO()

        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Quotation')

        # Formats
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter'
        })

        header_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'bg_color': '#D9EAD3'
        })

        cell_format = workbook.add_format({
            'border': 1
        })

        total_format = workbook.add_format({
            'bold': True,
            'border': 1
        })

        amount_format = workbook.add_format({
            'border': 1,
            'num_format': '#,##0.00'
        })

        # Column Widths
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 35)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 25)
        worksheet.set_column('E:V', 18)

        # =====================================================
        # Header
        # =====================================================

        worksheet.merge_range('A1:V1', 'SERVICE QUOTATION', title_format)

        worksheet.write('A3', 'Quotation No', total_format)
        worksheet.write('B3', self.name or '')

        worksheet.write('D3', 'Customer', total_format)
        worksheet.write('E3', self.partner_name or '')

        # worksheet.write('A4', 'Date', total_format)
        # worksheet.write(
        #     'B4',
        #     str(self.date_order.date()) if self.date_order else ''
        # )
        #
        # worksheet.write('D4', 'Salesperson', total_format)
        # worksheet.write('E4', self.user_id.name or '')

        # =====================================================
        # Table Header
        # =====================================================

        row = 6

        headers = [
            # 'S.No',
            'Brand',
            'Product',
            'Contract Type',
            'Price Template',
            'Quantity',
            'No.of Visits/Yr',
            'No.of Emergency Visits',
            'Days Required for PPM',
            'Standard Hours',
            'Total Hours',
            'Total Labor Cost',
            'Labour Selling Price',
            'Unit Cost Price',
            'Unit Selling Price',
            'SP Cost Category',
            'SP Cost',
            'SP Selling Price',
            'Total Selling Price',
            'Per Unit Selling Price',
            'VAT %',
            'VAT Amount',
            'Net Price'
        ]

        for col_num, header in enumerate(headers):
            worksheet.write(row, col_num, header, header_format)

        row += 1
        # sr_no = 1

        # =====================================================
        # Order Lines
        # =====================================================

        for line in self.service_sale_order_line_ids:
            # worksheet.write(row, 0, sr_no, cell_format)

            brand = line.brand_category_id.name if line.brand_category_id else ''

            worksheet.write(row, 0, brand, cell_format)
            worksheet.write(row, 1, line.product_id.display_name or '', cell_format)

            worksheet.write(
                row, 2,
                getattr(line, 'contract_type_id', False) and line.contract_type_id.name or '',
                cell_format
            )

            worksheet.write(
                row, 3,
                line.amc_pricing_id.name if line.amc_pricing_id else '',
                cell_format
            )

            worksheet.write(row, 4, line.product_qty or 0.0, amount_format)
            worksheet.write(row, 5, line.no_of_visits_per_year or 0.0, amount_format)
            worksheet.write(row, 6, line.no_of_emergency_visit or 0.0, amount_format)
            worksheet.write(row, 7, line.days_required_for_rpm or 0.0, amount_format)
            worksheet.write(row, 8, line.standard_hours or 0.0, amount_format)
            worksheet.write(row, 9, line.total_hr or 0.0, amount_format)
            worksheet.write(row, 10, line.total_cost or 0.0, amount_format)

            # Labour Selling Price
            worksheet.write(row, 11, line.total_price or 0.0, amount_format)

            # Unit Cost Price
            worksheet.write(
                row, 12,
                getattr(line, 'unit_cost_price', 0.0),
                amount_format
            )

            # Unit Selling Price
            worksheet.write(
                row, 13,
                getattr(line, 'unit_selling_price', 0.0),
                amount_format
            )

            # SP Cost Category
            worksheet.write(
                row, 14,
                getattr(line, 'spare_parts_cost_per_category', 0.0),
                amount_format
            )

            # SP Cost
            worksheet.write(
                row, 15,
                getattr(line, 'spare_parts_cost', 0.0),
                amount_format
            )

            # SP Selling Price
            worksheet.write(
                row, 16,
                getattr(line, 'spare_parts_selling_price', 0.0),
                amount_format
            )

            # Total Selling Price
            worksheet.write(
                row, 17,
                getattr(line, 'total_selling_price', 0.0),
                amount_format
            )

            # Per Unit Selling Price
            worksheet.write(
                row, 18,
                getattr(line, 'per_unit_selling_price', 0.0),
                amount_format
            )

            worksheet.write(row, 19, line.vat or 0.0, amount_format)
            worksheet.write(row, 20, line.vat_percent or 0.0, amount_format)
            worksheet.write(row, 21, line.total_amc or 0.0, amount_format)

            row += 1

        # =====================================================
        # Totals
        # =====================================================

        row += 2

        worksheet.write(row, 20, 'Sub Total', total_format)
        worksheet.write(
            row,
            21,
            self.untaxed_amount or 0.0,
            amount_format
        )

        row += 1

        worksheet.write(row, 20, 'VAT Amount', total_format)
        worksheet.write(
            row,
            21,
            self.vat_amount or 0.0,
            amount_format
        )

        row += 1

        worksheet.write(row, 20, 'Grand Total', total_format)
        worksheet.write(
            row,
            21,
            self.grand_total_amount or 0.0,
            amount_format
        )

        workbook.close()

        output.seek(0)

        excel_data = base64.b64encode(output.read())

        filename = "%s.xlsx" % (self.name or 'Quotation')

        self.write({
            'excel_file': excel_data,
            'excel_filename': filename,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=service.sale.order&id=%s&field=excel_file&filename_field=excel_filename&download=true' % self.id,
            'target': 'self',
        }
