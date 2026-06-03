# -*- coding: utf-8 -*-
import base64
import io
import csv
import math

from odoo import models, fields, _
from odoo.exceptions import UserError

try:
    import pandas as pd
    _HAS_PANDAS = True
except Exception:
    _HAS_PANDAS = False

MONTH_MAP = {
    "Jan": "01", "January": "01",
    "Feb": "02", "February": "02",
    "Mar": "03", "March": "03",
    "Apr": "04", "April": "04",
    "May": "05",
    "Jun": "06", "June": "06",
    "Jul": "07", "July": "07",
    "Aug": "08", "August": "08",
    "Sep": "09", "Sept": "09", "September": "09",
    "Oct": "10", "October": "10",
    "Nov": "11", "November": "11",
    "Dec": "12", "December": "12",
}

def _clean_cell(value):
    """Normalize cell values from CSV/Excel into safe stripped strings."""
    if value is None:
        return ""
    try:
        if isinstance(value, float) and math.isnan(value):
            return ""
    except Exception:
        pass
    s = str(value).strip()
    if s.lower() in ("nan", "none", "na", "n/a", "null"):
        return ""
    return s

class SalesTargetImportWizard(models.TransientModel):
    _name = "sales.target.import.wizard"
    _description = "Import Sales Targets from Excel/CSV"

    file = fields.Binary("Upload File", required=True, help="XLSX, XLS or CSV file")
    filename = fields.Char("Filename")
    create_missing = fields.Boolean(
        string="Create missing Dealers / Product Groups / Franchises",
        default=False,
        help="If checked, missing dealers, shops, product groups, subgroups, and franchises will be created automatically."
    )

    def _read_rows_from_file(self, data, filename):
        ext = (filename or "").lower().split(".")[-1]
        if ext in ("xls", "xlsx"):
            if not _HAS_PANDAS:
                raise UserError(_("To import Excel files you must install 'pandas' and 'openpyxl'."))
            df = pd.read_excel(io.BytesIO(data), dtype=object)
            df = df.where(pd.notnull(df), None)
            return [dict(row) for _, row in df.iterrows()]
        else:
            text = data.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            return [row for row in reader]

    def action_import_sales_targets(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_("Please upload a file to import."))

        data = base64.b64decode(self.file)
        try:
            rows = self._read_rows_from_file(data, self.filename or "file.csv")
        except Exception as e:
            raise UserError(_("Failed to read file: %s") % e)

        def cell(r, header):
            return _clean_cell(r.get(header))

        month_headers = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

        errors = []
        created_count = 0
        skipped_rows = 0
        row_no = 1

        years = set()
        for rw in rows:
            year_raw = cell(rw, "Year")
            if year_raw:
                try:
                    year = str(int(float(year_raw)))
                except Exception:
                    year = year_raw
                years.add(year)

        # 🔹 STEP 2: Delete old records for those years
        if years:
            self.env['sales.target'].search([('year', 'in', list(years))]).unlink()
        
        # Cache to avoid repeated DB queries
        dealer_cache = {}
        showroom_cache = {}
        promoter_cache = {}
        region_cache = {}
        city_cache = {}
        franchise_cache = {}
        product_group_cache = {}
        product_subgroup_cache = {}
        product_cache = {}

        for r in rows:
            row_no += 1
            try:
                # Year
                year_raw = cell(r, "Year")
                if not year_raw:
                    errors.append(f"Row {row_no}: Missing Year")
                    skipped_rows += 1
                    continue
                try:
                    year = str(int(float(year_raw)))
                except Exception:
                    year = year_raw

                # Dealer
                dealer_code = cell(r, "Dealer Code")
                dealer_name = cell(r, "Dealer Name")
                dealer_key = dealer_code or dealer_name
                dealer = dealer_cache.get(dealer_key)
                if not dealer:
                    if dealer_code:
                        dealer = self.env['res.partner'].search([('ref', '=', dealer_code)], limit=1)
                    if not dealer and dealer_name:
                        dealer = self.env['res.partner'].search([('name', '=', dealer_name)], limit=1)
                    if not dealer and self.create_missing and dealer_name:
                        dealer = self.env['res.partner'].create({'name': dealer_name, 'ref': dealer_code or False})
                    dealer_cache[dealer_key] = dealer
                if not dealer:
                    errors.append(f"Row {row_no}: {dealer_code} and {dealer_name} Dealer not found")
                    skipped_rows += 1
                    continue

                # Showroom / Shop
                showroom_code = cell(r, "Shop Code")
                showroom_name = cell(r, "Shop Name")
                showroom_key = showroom_code or showroom_name
                showroom = showroom_cache.get(showroom_key)
                if not showroom:
                    if showroom_code:
                        showroom = self.env['promoter.showroom'].search([('code', '=', showroom_code)], limit=1)
                    if not showroom and showroom_name:
                        showroom = self.env['promoter.showroom'].search([('name', '=', showroom_name)], limit=1)
                    if not showroom and self.create_missing and showroom_name:
                        showroom = self.env['promoter.showroom'].create({'name': showroom_name, 'code': showroom_code or False})
                    showroom_cache[showroom_key] = showroom
                if not showroom:
                    errors.append(f"Row {row_no}: {showroom_code} and {showroom_name} Showroom not found")
                    skipped_rows += 1
                    continue

                # Region
                region_name = cell(r, "Region")
                region = None
                if region_name:
                    region = region_cache.get(region_name)
                    if not region:
                        region = self.env['res.region'].search([('name','=',region_name)], limit=1)
                        region_cache[region_name] = region
                if not region:
                    errors.append(f"Row {row_no}: {region_name} Region not found")
                    skipped_rows += 1
                    continue

                # City
                city_name = cell(r, "City")
                city = None
                if city_name:
                    city = city_cache.get(city_name)
                    if not city:
                        city = self.env['res.city'].search([('name','=',city_name)], limit=1)
                        city_cache[city_name] = city
                if not city:
                    errors.append(f"Row {row_no}: {city_name} City not found")
                    skipped_rows += 1
                    continue

                # Location
                location = cell(r, "Location")

                # Promoter
                # promoter_code = (cell(r, "Promoter Code") or "").strip().lower()
                promoter_code = None
                promoter_name = (cell(r, "Promoter Name") or "").strip()
                promoter_key = promoter_code or promoter_name
                promoter = promoter_cache.get(promoter_key)
                # if not promoter:
                #     if promoter_name:
                #         promoter = self.env['res.partner'].search([('name','=', promoter_name)], limit=1)
                #     if not promoter and promoter_name:
                #         promoter_code = self.env['res.users'].search([('partner_id', '=', promoter.id)], limit=1)
                #         promoter_code='pr_'+promoter_code.user_code
                #     promoter_cache[promoter_key] = promoter

                if promoter_name:
                # 1. Find the partner by name
                    partner = self.env['res.partner'].search([('name', '=', promoter_name)], limit=1)

                if partner:
                    # 2. Find the user linked to that partner
                    user = self.env['res.users'].search([('partner_id', '=', partner.id)], limit=1)

                    if user:
                        # 3. Build promoter code with prefix
                        promoter_code = f"pr_{user.user_code}"                        
                        promoter = user  # or partner, depending on what you need to store

                # 4. Cache using promoter_key
                promoter_cache[promoter_key] = promoter

                if not promoter:
                    errors.append(f"Row {row_no}: {promoter_name} Promoter not found")
                    skipped_rows += 1
                    continue


                mobile_no = str(cell(r, "Mobile No") or "").strip() or False

                # Franchise
                franchise_code = cell(r, "Franchise Code")
                franchise_name = cell(r, "Franchise Name")
                franchise_key = franchise_code or franchise_name
                franchise = franchise_cache.get(franchise_key)
                if not franchise and (franchise_code or franchise_name):
                    franchise = self.env['product.category'].search([('code','=',franchise_code)], limit=1)
                    if not franchise and self.create_missing and franchise_name:
                        franchise = self.env['product.category'].create({'code': franchise_code})
                    franchise_cache[franchise_key] = franchise

                if not franchise:
                    errors.append(f"Row {row_no}: {franchise_code} and {franchise_name}   franchise not found")
                    skipped_rows += 1
                    continue

                # Product Group / Subgroup
                pg_code = cell(r, "Product Group")
                pg_name = cell(r, "Product Group Name")

                psg_code = cell(r, "Sub Group")
                psg_name = cell(r, "Sub Group Name")

                psg_name = cell(r, "Sub Group Name") or cell(r, "Sub Group") or cell(r, "Subgroup")
                product_group = None
                product_subgroup = None
                if pg_code:
                    product_group = product_group_cache.get(pg_code)
                    if not product_group:
                        product_group = self.env['product.category'].search([('code','=',pg_code)], limit=1)
                        if not product_group and self.create_missing:
                            product_group = self.env['product.category'].create({'code': pg_code, 'parent_id': product_group.id})
                        product_group_cache[pg_name] = product_group
                if psg_code:
                    product_subgroup = product_subgroup_cache.get(psg_code)
                    if not product_subgroup and product_group:
                        product_subgroup = self.env['product.category'].search([('code','=',psg_code)], limit=1)
                        if not product_subgroup and self.create_missing:
                            product_subgroup = self.env['product.category'].create({'code': psg_code, 'parent_id': product_group.id})
                        product_subgroup_cache[psg_code] = product_subgroup

                model_val = cell(r, "Model") or cell(r, "Product") or cell(r, "Model Name")
                product = None
                if model_val:
                    product = self.env['product.product'].search([('default_code', '=', model_val)], limit=1)
                    if not product:
                        product = self.env['product.product'].search([('name', '=', model_val)], limit=1)

                capacity = cell(r, "Capacity") or cell(r, "Cap") or None

                # Iterate monthly targets
                any_created_for_row = False
                for mh in month_headers:
                    raw_month_val = cell(r, mh)
                    if raw_month_val in ("", None):
                        continue
                    try:
                        qty = float(str(raw_month_val).replace(",", ""))
                    except Exception:
                        qty = 0
                    if not qty:
                        continue
                    month_code = MONTH_MAP.get(mh)
                    if not month_code:
                        continue

                    vals = {
                        "dealer_id": dealer.id,
                        "showroom_id": showroom.id,
                        "promoter_id": promoter.id if promoter else False,
                        "promoter_code": promoter_code if promoter else False,
                        "promoter_name": promoter.name if promoter else False,
                        "franchise_id": franchise.id if franchise else False,
                        "franchise_code": franchise.code if franchise else False,
                        "franchise_name": franchise.name if franchise else False,
                        "group_id": product_group.id if product_group else False,
                        "product_group_code": product_group.code if product_group else False,
                        "product_group_name": product_group.name if product_group else False,
                        "subgroup_id": product_subgroup.id if product_subgroup else False,
                        "subgroup_code": product_subgroup.code if product_subgroup else False,
                        "subgroup_name": product_subgroup.name if product_subgroup else False,
                        "product_id": product.id if product else False,                       
                        "region": region.id if region else False,
                        "city": city.id if city else False,
                        "location": location,
                        "mobile_no": mobile_no,
                        "capacity": capacity,
                        "year": year,
                        "month": month_code,
                        "target_qty": qty,
                    }

                    

                    try:
                        self.env['sales.target'].create(vals)
                        created_count += 1
                        any_created_for_row = True
                    except Exception as e:
                        errors.append(f"Row {row_no} month {mh}: Create failed: {e}")

                   
                if not any_created_for_row:
                    skipped_rows += 1

            except Exception as e:
                errors.append(f"Row {row_no}: Unexpected error: {e}")

        summary = [f"Created {created_count} monthly target rows."]
        if skipped_rows:
            summary.append(f"Skipped {skipped_rows} input rows (no valid months or missing data).")
        if errors:
            summary.append("Errors (first 50):")
            summary += errors[:50]
            raise UserError("\n".join(summary))

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Import successful"),
                "message": "\n".join(summary),
                "type": "success",
                "sticky": False,
            },
        }
