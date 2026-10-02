# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import base64
import io
import openpyxl
import xlrd

class ImportNonStockWizard(models.Model):
    _name = 'crm.commercial.import.non.stock.wizard'
    _description = 'Import Non-Stock Items Wizard'

    excel_file = fields.Binary(string='Upload Excel File')
    filename = fields.Char(string='Filename')

    def action_download_sample(self):
        """Generates sample Excel file format for non-stock item import."""
        return {
            'type': 'ir.actions.act_url',
            'url': '/crm_commercial/static/description/sample_non_stock_import.xlsx',
            'target': 'new',
        }

    def _read_excel_rows(self, file_content):
        rows = []
        try:
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

        try:
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

    def action_import_file(self):
        self.ensure_one()
        if not self.excel_file:
            raise ValidationError(_("Please upload an Excel file."))

        file_content = base64.b64decode(self.excel_file)
        rows = self._read_excel_rows(file_content)

        imported_count = 0
        for row in rows[1:]:
            code = row[0] if len(row) > 0 else ''
            name = row[1] if len(row) > 1 else ''
            categ_name = row[2] if len(row) > 2 else ''
            try:
                cost = float(row[3]) if len(row) > 3 and row[3] else 0.0
            except Exception:
                cost = 0.0
            try:
                price = float(row[4]) if len(row) > 4 and row[4] else 0.0
            except Exception:
                price = 0.0

            if not name:
                continue

            categ = self.env['product.category'].search([('name', '=', categ_name)], limit=1) if categ_name else self.env['product.category'].search([], limit=1)

            product = self.env['product.product'].create({
                'name': name,
                'default_code': code,
                'categ_id': categ.id if categ else False,
                'standard_price': cost,
                'lst_price': price,
                'non_stock_item': True,
                'approval_state': 'draft',
            })
            imported_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import Successful'),
                'message': _('Successfully imported %s non-stock items for approval.') % imported_count,
                'type': 'success',
                'sticky': False,
            }
        }
