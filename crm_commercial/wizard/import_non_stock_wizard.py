# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import base64
import io
import os


class ImportNonStockWizard(models.TransientModel):
    _name = 'crm.commercial.import.non.stock.wizard'
    _description = 'Import Non-Stock Items Wizard'

    excel_file = fields.Binary(string='Upload Excel File', required=True)
    filename = fields.Char(string='Filename')

    def action_download_sample(self):
        """Generates or fetches sample Excel template matching user's exact specification."""
        try:
            import xlsxwriter
            output = io.BytesIO()
            wb = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = wb.add_worksheet('Non-Stock Items')

            # Formatting
            f_head = wb.add_format({
                'bold': True,
                'bg_color': '#008080',
                'font_color': '#FFFFFF',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            f_cell = wb.add_format({'border': 1})
            f_num = wb.add_format({'border': 1, 'num_format': '#,##0.00'})

            headers = [
                'Part No *',
                'Item Name *',
                'Long Description',
                'Capacity',
                'Selling Price',
                'Cost Price',
                'Main Group',
                'Product Category *',
                'Unit',
                'Accessories'
            ]
            col_widths = [16, 36, 45, 12, 15, 15, 16, 28, 12, 16]

            ws.set_row(0, 24)
            for col_idx, (header, width) in enumerate(zip(headers, col_widths)):
                ws.write(0, col_idx, header, f_head)
                ws.set_column(col_idx, col_idx, width)

            sample_rows = [
                ['PART-001', 'Sample ACWTSplit Product', 'Detailed description of the acwtsplit product',
                 '1', 100.0, 80.0, 'MDA', 'ACWTSplit', 'PCS', '2'],
                ['PART-002', 'Sample ALASKA WATER DISPENSER Product', 'Detailed description of the alaska water dispenser product',
                 '1', 150.0, 120.0, 'ASK', 'ALASKA WATER DISPENSER', 'PCS', '34'],
                ['PART-003', 'Sample CHILLER Product', 'Detailed description of the chiller product',
                 '1', 200.0, 160.0, 'MDA', 'CHILLER', 'PCS', 'ABVU'],
            ]

            for row_idx, row_data in enumerate(sample_rows, start=1):
                for col_idx, val in enumerate(row_data):
                    if isinstance(val, (int, float)):
                        ws.write_number(row_idx, col_idx, val, f_num)
                    else:
                        ws.write(row_idx, col_idx, str(val), f_cell)

            wb.close()
            output.seek(0)
            file_data = base64.b64encode(output.read())

            attachment = self.env['ir.attachment'].sudo().create({
                'name': 'Sample_Import_Non_Stock.xlsx',
                'type': 'binary',
                'datas': file_data,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            })
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
        except Exception:
            # Fallback to static bundled asset URL
            return {
                'type': 'ir.actions.act_url',
                'url': '/crm_commercial/static/description/sample_non_stock_import.xlsx',
                'target': 'self',
            }

    def _read_excel_rows(self, file_content):
        rows = []
        # Try openpyxl first (.xlsx)
        try:
            import openpyxl
            wb = openpyxl.load_workbook(filename=io.BytesIO(file_content), data_only=True)
            sheet = wb.active
            for r in sheet.iter_rows(values_only=True):
                row_vals = [str(cell if cell is not None else '').strip() for cell in r]
                if any(row_vals):
                    rows.append(row_vals)
            if rows:
                return rows
        except Exception:
            pass

        # Fallback to xlrd (.xls)
        try:
            import xlrd
            workbook = xlrd.open_workbook(file_contents=file_content)
            sheet = workbook.sheet_by_index(0)
            for row_idx in range(sheet.nrows):
                row_vals = [str(sheet.cell_value(row_idx, col)).strip() for col in range(sheet.ncols)]
                if any(row_vals):
                    rows.append(row_vals)
            if rows:
                return rows
        except Exception as e:
            raise ValidationError(_("Invalid Excel file format: %s") % str(e))

        raise ValidationError(_("The uploaded Excel file contains no data."))

    def _map_headers(self, header_row):
        """Map header strings to logical field keys."""
        mapping = {}
        for idx, h in enumerate(header_row):
            h_norm = h.lower().replace('*', '').replace('_', ' ').replace('-', ' ').strip()
            if 'part' in h_norm or 'code' in h_norm:
                mapping['part_no'] = idx
            elif 'item' in h_norm or 'name' in h_norm or 'product' in h_norm and 'category' not in h_norm:
                mapping['name'] = idx
            elif 'long' in h_norm or 'desc' in h_norm:
                mapping['long_description'] = idx
            elif 'cap' in h_norm:
                mapping['capacity'] = idx
            elif 'sell' in h_norm or 'sale' in h_norm:
                mapping['sale_price'] = idx
            elif 'cost' in h_norm:
                mapping['cost_price'] = idx
            elif 'main' in h_norm or 'group' in h_norm:
                mapping['main_group'] = idx
            elif 'categ' in h_norm:
                mapping['category'] = idx
            elif 'unit' in h_norm or 'uom' in h_norm:
                mapping['unit'] = idx
            elif 'access' in h_norm:
                mapping['accessories'] = idx
        return mapping

    def action_import_file(self):
        """Imports excel rows into crm.commercial.item.approval staging model."""
        self.ensure_one()
        if not self.excel_file:
            raise ValidationError(_("Please upload an Excel file."))

        file_content = base64.b64decode(self.excel_file)
        rows = self._read_excel_rows(file_content)

        if not rows:
            raise ValidationError(_("The uploaded file does not contain any readable data."))

        # Identify header row and map columns
        header_mapping = self._map_headers(rows[0])
        # If row 0 matched at least 2 key columns (part_no, name, or category), treat as header
        has_header = ('part_no' in header_mapping or 'name' in header_mapping) and len(header_mapping) >= 2
        data_rows = rows[1:] if has_header else rows

        col_part_no = header_mapping.get('part_no', 0)
        col_name = header_mapping.get('name', 1)
        col_desc = header_mapping.get('long_description', 2)
        col_cap = header_mapping.get('capacity', 3)
        col_sale = header_mapping.get('sale_price', 4)
        col_cost = header_mapping.get('cost_price', 5)
        col_mg = header_mapping.get('main_group', 6)
        col_cat = header_mapping.get('category', 7)
        col_unit = header_mapping.get('unit', 8)
        col_acc = header_mapping.get('accessories', 9)

        imported_count = 0
        ApprovalModel = self.env['crm.commercial.item.approval'].sudo()
        CategoryModel = self.env['product.category'].sudo()
        MainGroupModel = self.env['t.mainproducts'].sudo()
        UomModel = self.env['uom.uom'].sudo()

        default_category = CategoryModel.search([], limit=1)
        default_uom = self.env.ref('uom.product_uom_unit', raise_if_not_found=False) or UomModel.search([], limit=1)

        def get_val(row, col_idx):
            if 0 <= col_idx < len(row):
                return str(row[col_idx] or '').strip()
            return ''

        for row in data_rows:
            part_no = get_val(row, col_part_no)
            name = get_val(row, col_name)
            long_desc = get_val(row, col_desc)
            capacity = get_val(row, col_cap)
            sale_str = get_val(row, col_sale)
            cost_str = get_val(row, col_cost)
            mg_val = get_val(row, col_mg)
            cat_val = get_val(row, col_cat)
            unit_val = get_val(row, col_unit)
            accessories = get_val(row, col_acc)

            # Skip empty lines
            if not part_no and not name:
                continue

            # Fallbacks for required fields
            if not part_no:
                part_no = name
            if not name:
                name = part_no

            try:
                sale_price = float(sale_str) if sale_str else 0.0
            except Exception:
                sale_price = 0.0

            try:
                cost_price = float(cost_str) if cost_str else 0.0
            except Exception:
                cost_price = 0.0

            # 1. Main Group
            main_grp = False
            if mg_val:
                main_grp = MainGroupModel.search([
                    '|', ('mp_code', '=ilike', mg_val), ('mp_grp', '=ilike', mg_val)
                ], limit=1)

            # 2. Product Category from Main Group:
            # If main group is MDA -> Product Category is Media / Midea
            prod_category = ApprovalModel._resolve_product_category(mg_val or (main_grp.mp_code if main_grp else ''))

            # 3. Product Group from Excel Column H (e.g. ACWTSplit):
            prod_group = ApprovalModel._resolve_product_group(cat_val, prod_category)

            # 4. Unit of Measure:
            # If unit is PCS -> Unit of Measure is PCS
            uom = ApprovalModel._resolve_uom(unit_val)

            # 5. Base category
            categ = prod_group or prod_category or default_category

            vals = {
                'part_no': part_no,
                'name': name,
                'long_description': long_desc,
                'capacity': capacity,
                'sale_price': sale_price,
                'cost_price': cost_price,
                'main_group_name': mg_val,
                'main_grp_id': main_grp.id if main_grp else False,
                'category_name': cat_val,
                'product_category_id': prod_category.id if prod_category else False,
                'product_group_id': prod_group.id if prod_group else False,
                'category_id': categ.id if categ else default_category.id,
                'unit_name': unit_val,
                'uom_id': uom.id if uom else default_uom.id,
                'accessories': accessories,
                'state': 'draft',
            }

            # Check if pending draft approval exists for this part_no
            existing = ApprovalModel.search([('part_no', '=', part_no), ('state', '=', 'draft')], limit=1)
            if existing:
                existing.write(vals)
            else:
                ApprovalModel.create(vals)

            imported_count += 1

        if imported_count == 0:
            raise ValidationError(_("No valid records could be imported from the Excel file."))

        # Redirect user directly to Item Approvals screen so items are immediately visible
        return {
            'name': _('Item Approvals'),
            'type': 'ir.actions.act_window',
            'res_model': 'crm.commercial.item.approval',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [],
            'context': {
                'search_default_filter_pending': 1,
            },
            'target': 'current',
        }
