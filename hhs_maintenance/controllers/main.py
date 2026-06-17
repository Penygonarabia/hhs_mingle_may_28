from odoo import http
from odoo.http import request
import io
import xlsxwriter
import re


class HHSEquipmentTemplate(http.Controller):

    @http.route('/hhs/download/equipment/template', type='http', auth='user')
    def download_equipment_template(self, contract_id=None, **kwargs):

        # ✅ CHECK CONTRACT
        if not contract_id:
            return request.not_found()

        contract = request.env['subscription.contracts'].browse(int(contract_id))
        if not contract:
            return request.not_found()

        # ✅ GET CONTRACT LINES
        contract_lines = request.env['subscription.contracts.line'].search([
            ('subscription_contract_id', '=', contract.id)
        ])

        # ===== CREATE EXCEL =====
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Equipment Template')

        # Create a date format
        date_format = workbook.add_format({'num_format': 'dd-mm-yyyy'})

        # ===== HEADER FORMAT =====
        header_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        # ===== CONTRACT SECTION =====
        sheet.write('A1', 'Contract #')
        sheet.write('B1', contract.name or '')

        sheet.write('A2', 'Customer Name')
        sheet.write('B2', contract.partner_id.name or '')

        sheet.write('A3', 'Project Name')
        sheet.write('B3', contract.reference or '')

        sheet.write('A4', 'Contract Start Date')
        sheet.write('B4', contract.date_start or '', date_format)

        sheet.write('A5', 'Contract End Date')
        sheet.write('B5', contract.date_end or '', date_format)


        # ===== TABLE HEADER =====
        headers = [
            "SNO", "Brand", "Unit Type", "Model",
            "Serial No (Optional)", "Used in Location (Optional)",
            "No of visits per year", "Default Technician Emp Code",
            "Default Technician Name", "Asset Tag", "Batch No"
        ]

        row = 7
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)

        # ===== COLUMN WIDTH =====
        sheet.set_column('A:A', 17)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 30)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 25)
        sheet.set_column('F:F', 25)
        sheet.set_column('G:G', 20)
        sheet.set_column('H:H', 25)
        sheet.set_column('I:I', 25)
        sheet.set_column('J:J', 25)
        sheet.set_column('K:K', 15)

        # ===== DATA =====
        row += 1
        sno = 1

        # Store sequence by product
        asset_counter = {}

        for line in contract_lines:

            qty = int(line.qty_ordered or 1)

            # Product Default Code
            default_code = line.product_id.default_code or 'ITEM'

            # Product Key
            product_key = line.product_id.id

            # Initialize counter
            if product_key not in asset_counter:
                asset_counter[product_key] = 1

            # Repeat for qty_ordered times
            for i in range(qty):

                # Sequence Number
                seq = asset_counter[product_key]

                # Dynamic Asset Tag
                ''''Code Added on June 17 2026 Client asked the customer code for the name instead of usual name'''
                # contract_code = (contract.name or '') \
                # .replace('AMC-J', 'J') \
                # .replace('AMCJ', 'J')
                
                contract_code = contract.customer_code or ''

                asset_tag = f"{contract_code}/{default_code}-{str(seq).zfill(3)}"

                # Increase Counter
                asset_counter[product_key] += 1

                sheet.write(row, 0, sno)  # SNO
                sheet.write(row, 1, line.brand_category_id.name if line.brand_category_id else '')  # Brand
                sheet.write(row, 2, line.product_id.name if line.product_id else '')  # Unit Type

                # Columns 3,4,5 remain blank
                sheet.write(row, 3, '')  # Model
                sheet.write(row, 4, '')  # Serial No
                sheet.write(row, 5, '')  # Location

                sheet.write(row, 6, line.no_of_visits_per_year or 0)  # No of visits per year

                # Columns 7–10 remain blank
                sheet.write(row, 7, '')  # Technician Emp Code
                sheet.write(row, 8, '')  # Technician Name
                sheet.write(row, 9, asset_tag)  # Asset Tag
                sheet.write(row, 10, '')  # Batch No

                row += 1
                sno += 1

        # ===== CLOSE WORKBOOK =====
        workbook.close()
        output.seek(0)

        safe_name = re.sub(r'[^0-9A-Za-z_-]', '_', contract.name or 'Contract')
        filename = f"HHS_Equipment_Template_{safe_name}.xlsx"

        # ===== RETURN RESPONSE =====
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
        )