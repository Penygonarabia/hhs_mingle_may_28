# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import base64
import io
import openpyxl
import xlrd

class ImportMaterialListWizard(models.Model):
    _name = 'crm.commercial.import.material.list.wizard'
    _description = 'Import Material List Wizard'

    quotation_id = fields.Many2one('crm.commercial.quotation', string='Quotation', required=True)
    excel_file = fields.Binary(string='Upload Excel File')
    filename = fields.Char(string='Filename')

    def action_download_template(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/crm_commercial/download_material_template',
            'target': 'self',
        }

    def _read_excel_rows(self, file_content):
        rows = []
        # Try openpyxl first (.xlsx)
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

        # Fallback to xlrd (.xls)
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

    def action_import_material_list(self):
        self.ensure_one()
        if not self.excel_file:
            raise ValidationError(_("Please upload an Excel file."))

        file_content = base64.b64decode(self.excel_file)
        rows = self._read_excel_rows(file_content)

        if len(rows) < 2:
            raise ValidationError(_("The uploaded Excel file contains no data rows."))

        header_row = [str(c).lower().strip() for c in rows[0]]
        is_new_format = any(k in header_row for k in ['model', 'quantity', 'unit price', 'description'])

        for row in rows[1:]:
            if is_new_format:
                model_code = row[0] if len(row) > 0 else ''
                try:
                    qty = float(row[1]) if len(row) > 1 and row[1] else 1.0
                except Exception:
                    qty = 1.0
                description = row[2] if len(row) > 2 else ''
                try:
                    sale_price = float(row[3]) if len(row) > 3 and row[3] else 0.0
                except Exception:
                    sale_price = 0.0
                try:
                    discount = float(row[4]) if len(row) > 4 and row[4] else 0.0
                except Exception:
                    discount = 0.0

                part_no_or_name = model_code or description
                if not part_no_or_name:
                    continue

                product = self.env['product.product'].search([
                    '|', ('default_code', '=', model_code), ('name', '=', description or model_code)
                ], limit=1) if model_code or description else False

                if not product and model_code:
                    product = self.env['product.product'].search([('name', '=', model_code)], limit=1)

                if not product:
                    product = self.env['product.product'].create({
                        'name': description or model_code,
                        'default_code': model_code if model_code else False,
                        'lst_price': sale_price if sale_price > 1.0 else 0.0,
                        'non_stock_item': True,
                        'approval_state': 'draft',
                    })

                # Determine Product Category & Product Group from Product Variant fields
                prod_cat = getattr(product, 'product_group_id', False) or getattr(product, 'product_category_id', False) or product.categ_id

                category_rec = False
                group_rec = False
                if prod_cat:
                    cat = prod_cat
                    while cat:
                        if cat.use_for_crm_commercial:
                            if cat.parent_id and not category_rec:
                                category_rec = cat
                            if not cat.parent_id and not group_rec:
                                group_rec = cat
                        cat = cat.parent_id

                if not category_rec and prod_cat and prod_cat.use_for_crm_commercial:
                    category_rec = prod_cat

                if not group_rec and category_rec and category_rec.parent_id:
                    c = category_rec
                    while c.parent_id:
                        c = c.parent_id
                    group_rec = c

                cat_discount = category_rec.default_discount_percent if category_rec and category_rec.default_discount_percent else 0.0

                # If Excel discount is 0 or 1 (sample values), take discount % from product category discount
                if discount <= 1.0:
                    line_discount = cat_discount
                else:
                    line_discount = discount

                unit_sale_price = sale_price if sale_price > 1.0 else product.lst_price

                self.env['crm.commercial.quotation.line'].create({
                    'quotation_id': self.quotation_id.id,
                    'product_group_id': group_rec.id if group_rec else False,
                    'product_category_id': category_rec.id if category_rec else False,
                    'product_id': product.id,
                    'qty': qty,
                    'unit_cost': product.standard_price,
                    'sale_price': unit_sale_price,
                    'discount_percent': line_discount,
                })
            else:
                product_group_name = row[0] if len(row) > 0 else ''
                product_categ_name = row[1] if len(row) > 1 else ''
                part_no_or_name = row[2] if len(row) > 2 else ''
                try:
                    qty = float(row[3]) if len(row) > 3 and row[3] else 1.0
                except Exception:
                    qty = 1.0
                try:
                    sale_price = float(row[4]) if len(row) > 4 and row[4] else 0.0
                except Exception:
                    sale_price = 0.0
                try:
                    discount = float(row[5]) if len(row) > 5 and row[5] else 0.0
                except Exception:
                    discount = 0.0

                if not part_no_or_name:
                    continue

                product = self.env['product.product'].search(['|', ('default_code', '=', part_no_or_name), ('name', '=', part_no_or_name)], limit=1)
                if not product:
                    product = self.env['product.product'].create({
                        'name': part_no_or_name,
                        'lst_price': sale_price if sale_price > 1.0 else 0.0,
                        'non_stock_item': True,
                        'approval_state': 'draft',
                    })

                group = self.env['product.category'].search(['|', ('code', '=', product_group_name), ('name', '=', product_group_name), ('use_for_crm_commercial', '=', True), ('parent_id', '=', False)], limit=1) if product_group_name else False
                categ_domain = [('use_for_crm_commercial', '=', True), ('exclude_category', '=', False)]
                if group:
                    categ_domain += [('parent_id', 'child_of', group.id), ('id', '!=', group.id)]
                if product_categ_name:
                    categ_domain += ['|', ('code', '=', product_categ_name), ('name', '=', product_categ_name)]
                    categ = self.env['product.category'].search(categ_domain, limit=1)
                else:
                    categ = getattr(product, 'product_group_id', False) or product.categ_id

                if not group and categ and categ.parent_id:
                    c = categ
                    while c.parent_id:
                        c = c.parent_id
                    group = c

                cat_discount = categ.default_discount_percent if categ and categ.default_discount_percent else 0.0
                if discount <= 1.0:
                    line_discount = cat_discount
                else:
                    line_discount = discount

                unit_sale_price = sale_price if sale_price > 1.0 else product.lst_price

                self.env['crm.commercial.quotation.line'].create({
                    'quotation_id': self.quotation_id.id,
                    'product_group_id': group.id if group else False,
                    'product_category_id': categ.id if categ else False,
                    'product_id': product.id,
                    'qty': qty,
                    'unit_cost': product.standard_price,
                    'sale_price': unit_sale_price,
                    'discount_percent': line_discount,
                })

        self.quotation_id.action_recalculate()
        return {'type': 'ir.actions.act_window_close'}
