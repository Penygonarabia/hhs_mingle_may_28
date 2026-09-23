# -*- coding: utf-8 -*-
"""Backs "PBI Dashboards > Loyalty Dashboards > Loyalty Customers Sales
Analysis".

This controller (and its client action, loyalty_sales_analysis_dashboard)
renders the "Sales Dashboard - VQ" pairing — Amount and Qty shown
together per category, ranked by Amount (see pbi_sales_dashboards/
controllers/sales_vq_main.py) — scoped to loyalty customers only, and
reading from transaction_header/transaction_details + their master-data
links.

Drill order: Region -> City -> Main Category -> Sub-Category -> Product
Group -> Product Sub Group -> Customer -> Transaction list (leaf row list).

The 4 product levels (Main Category/Sub-Category/Product Group/Product Sub
Group) are resolved by this controller alone via FC_CTE.
"""

from datetime import date, timedelta

from odoo import http
from odoo.http import request

from .access import menu_allowed

FC_CTE = """
    WITH fc AS (
        WITH cat AS (
            SELECT DISTINCT ON (upper(trim(cat_part)))
                   upper(trim(cat_grp)) AS grp, upper(trim(cat_part)) AS part,
                   trim(cat_grp) AS fr, trim(cat_pgroup) AS pg, trim(cat_psgroup) AS psg
            FROM catalog ORDER BY upper(trim(cat_part)), id
        ),
        d1 AS (
            SELECT DISTINCT ON (trim(code)) id, trim(code) AS code
            FROM product_category
            WHERE (length(parent_path) - length(replace(parent_path, '/', ''))) = 1
              AND NULLIF(trim(code), '') IS NOT NULL
            ORDER BY trim(code), id
        ),
        d2 AS (
            SELECT DISTINCT ON (parent_id, trim(code)) id, parent_id, trim(code) AS code,
                   sub_category
            FROM product_category
            WHERE (length(parent_path) - length(replace(parent_path, '/', ''))) = 2
              AND NULLIF(trim(code), '') IS NOT NULL
            ORDER BY parent_id, trim(code), id
        ),
        d3 AS (
            SELECT DISTINCT ON (pc.parent_id, trim(pc.code))
                   pc.id, pc.parent_id, trim(pc.code) AS code, pc.name, pc.product_family
            FROM product_category pc
            WHERE (length(pc.parent_path) - length(replace(pc.parent_path, '/', ''))) = 3
              AND NULLIF(trim(pc.code), '') IS NOT NULL
            ORDER BY pc.parent_id, trim(pc.code), pc.id
        )
        SELECT cat.part AS part_no, cat.grp AS franchise_code,
               mc.id AS l7_id, mc.maincat_name AS l7_label,
               sc.id AS l8_id, sc.subcat_name AS l8_label,
               d3.id AS l9_id, d3.name AS l9_label,
               pf.id AS lfam_id, pf.pfam_name AS lfam_label
        FROM cat
        LEFT JOIN d1 ON d1.code = cat.fr
        LEFT JOIN d2 ON d2.parent_id = d1.id AND d2.code = cat.pg
        LEFT JOIN d3 ON d3.parent_id = d2.id AND d3.code = cat.psg
        LEFT JOIN sub_category sc ON sc.id = d2.sub_category
        LEFT JOIN main_category mc ON mc.id = sc.subcat_maincategory_id
        LEFT JOIN product_family pf ON pf.id = d3.product_family
    )
"""

AMOUNT_EXPR = """
    CASE WHEN th.trnh_type = '02' THEN (COALESCE(td.trnd_ret, 0) * (COALESCE(td.trnd_price, 0) - COALESCE(td.trnd_disc, 0) - COALESCE(td.trnd_cstspldisc, 0))) * -1
         ELSE (COALESCE(td.trnd_qtyiss, 0) * (COALESCE(td.trnd_price, 0) - COALESCE(td.trnd_disc, 0) - COALESCE(td.trnd_cstspldisc, 0))) END
"""

QTY_EXPR = """
    CASE WHEN th.trnh_type = '02' THEN COALESCE(td.trnd_ret, 0) * -1
         ELSE COALESCE(td.trnd_qtyiss, 0) END
"""

FROM_CLAUSE = """
    transaction_header th
    JOIN transaction_details td ON td.trnd_no = th.trnh_no AND td.trnd_whouse = th.trnh_whouse
    JOIN res_partner rp ON rp.ref = th.trnh_cstno
    LEFT JOIN fc ON fc.part_no = upper(trim(td.trnd_part))
    LEFT JOIN customer rrc ON rrc.cst_no = th.trnh_cstno
    LEFT JOIN res_city rrhc ON rrhc.id = th.trnh_cityid
    LEFT JOIN res_city rrcc ON upper(trim(rrcc.code)) = upper(trim(rrc.cst_subregion))
    LEFT JOIN res_region rr ON rr.id = COALESCE(th.trnh_rptregionid, rrhc.report_region, rrcc.report_region)
"""

LEVEL_COLS = {
    "region": ("rr.id", "rr.name ->> 'en_US'"),
    "city": ("COALESCE(rrhc.id, rrcc.id)", "COALESCE(rrhc.name, rrcc.name) ->> 'en_US'"),
    "mainCategory": ("fc.l7_id", "fc.l7_label"),
    "subCategory": ("fc.l8_id", "fc.l8_label"),
    "productGroup": ("fc.l9_id", "fc.l9_label"),
    "productSubGroup": ("fc.lfam_id", "fc.lfam_label"),
    "customer": ("th.trnh_cstno", "th.trnh_cstname"),
}
LEVEL_ORDER = ["region", "city", "mainCategory", "subCategory", "productGroup", "productSubGroup", "customer"]

FRANCHISE_OPTIONS = (
    ("MDA", "Midea"),
    ("BKO", "Beko"),
    ("CDY", "Candy"),
    ("ASK", "Alaska"),
    ("SMG", "Smeg"),
    ("RUD", "Ruud"),
)


def _quarter_start(d):
    q_month = (d.month - 1) // 3 * 3 + 1
    return date(d.year, q_month, 1)


def _prev_quarter_range(d):
    start = _quarter_start(d)
    prev_end = start - timedelta(days=1)
    return _quarter_start(prev_end), prev_end


class PbiLoyaltySalesAnalysisController(http.Controller):

    # ------------------------------------------------------------------
    # low-level helpers
    # ------------------------------------------------------------------
    def _query(self, sql, params=()):
        request.env.cr.execute("SET LOCAL enable_nestloop = off; SET LOCAL jit = off;")
        request.env.cr.execute(sql, params)
        cols = [d[0] for d in request.env.cr.description]
        return [dict(zip(cols, row)) for row in request.env.cr.fetchall()]

    def _has_access(self):
        return menu_allowed("pbi_dashboards.menu_pbi_sales_analysis")

    def _period_range(self, period, date_from=None, date_to=None):
        """(start, end) dates for a Period filter value."""
        today = date.today()
        if period == "custom":
            def _parse(v, default):
                try:
                    return date.fromisoformat(v) if v else default
                except (TypeError, ValueError):
                    return default
            start = _parse(date_from, today)
            end = _parse(date_to, today)
            return (start, end) if start <= end else (end, start)
        if period == "this_week":
            return today - timedelta(days=today.weekday()), today
        if period == "this_month":
            return today.replace(day=1), today
        if period == "this_quarter":
            return _quarter_start(today), today
        if period == "this_year":
            return today.replace(month=1, day=1), today
        if period == "last_week":
            this_week_start = today - timedelta(days=today.weekday())
            return this_week_start - timedelta(days=7), this_week_start - timedelta(days=1)
        if period == "last_month":
            end = today.replace(day=1) - timedelta(days=1)
            return end.replace(day=1), end
        if period == "last_quarter":
            return _prev_quarter_range(today)
        if period == "last_year":
            return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
        return today.replace(month=1, day=1), today  # fallback: this_year

    # ------------------------------------------------------------------
    # drill-down rows & totals
    # ------------------------------------------------------------------
    def _base_where(self, date_from, date_to, selected, franchise_code=None):
        """Clause fragments + params shared by every level."""
        clauses = [
            "rp.activate_loyalty_feature = true",
            "th.trnh_type IN ('01', '02')",
            "th.trnh_date BETWEEN %s AND %s",
        ]
        params = [date_from.strftime("%Y%m%d"), date_to.strftime("%Y%m%d")]
        if franchise_code and franchise_code != "all":
            clauses.append("fc.franchise_code = %s")
            params.append(franchise_code)
        for lvl in LEVEL_ORDER:
            code = selected.get(lvl)
            if code:
                code_col, _ = LEVEL_COLS[lvl]
                clauses.append(f"{code_col} = %s")
                params.append(code)
        return clauses, params

    def _drill_rows_and_total(self, level, date_from, date_to, selected, franchise_code=None):
        code_col, name_col = LEVEL_COLS[level]
        clauses, params = self._base_where(date_from, date_to, selected, franchise_code)
        clauses.append(f"{name_col} IS NOT NULL")
        where = " AND ".join(clauses)
        rows = self._query(f"""
            {FC_CTE},
            grouped AS (
                SELECT {code_col} AS code, {name_col} AS label,
                       sum({AMOUNT_EXPR}) AS amount,
                       sum({QTY_EXPR}) AS qty
                FROM {FROM_CLAUSE}
                WHERE {where}
                GROUP BY 1, 2
            )
            SELECT code, label, amount, qty,
                   sum(amount) OVER () AS total_amount,
                   sum(qty) OVER () AS total_qty
            FROM grouped
            ORDER BY amount DESC
            LIMIT 15
        """, params)
        if not rows:
            return {"rows": [], "total": {"amount": 0.0, "qty": 0.0}}
        total = {"amount": float(rows[0]["total_amount"] or 0), "qty": float(rows[0]["total_qty"] or 0)}
        row_data = [
            {"code": r["code"], "label": r["label"], "amount": float(r["amount"] or 0), "qty": float(r["qty"] or 0)}
            for r in rows
        ]
        return {"rows": row_data, "total": total}

    def _transaction_rows_and_total(self, date_from, date_to, selected, franchise_code=None):
        clauses, params = self._base_where(date_from, date_to, selected, franchise_code)
        where = " AND ".join(clauses)
        rows = self._query(f"""
            {FC_CTE},
            trans AS (
                SELECT th.trnh_no AS trnh_no,
                       to_date(th.trnh_date, 'YYYYMMDD') AS trnh_date,
                       th.trnh_whouse AS trnh_whouse,
                       td.trnd_desc,
                       {QTY_EXPR} AS qty,
                       {AMOUNT_EXPR} AS net_sales
                FROM {FROM_CLAUSE}
                WHERE {where}
            )
            SELECT trnh_no, trnh_date, trnh_whouse, trnd_desc, qty, net_sales,
                   sum(net_sales) OVER () AS total_amount,
                   sum(qty) OVER () AS total_qty
            FROM trans
            ORDER BY trnh_date DESC NULLS LAST
            LIMIT 200
        """, params)
        if not rows:
            return {"rows": [], "total": {"amount": 0.0, "qty": 0.0}}
        total = {"amount": float(rows[0]["total_amount"] or 0), "qty": float(rows[0]["total_qty"] or 0)}
        row_data = [{
            "transactionNo": r["trnh_no"],
            "date": r["trnh_date"].isoformat() if r["trnh_date"] else None,
            "warehouse": r["trnh_whouse"],
            "part": r["trnd_desc"],
            "qty": float(r["qty"] or 0),
            "amount": float(r["net_sales"] or 0),
        } for r in rows]
        return {"rows": row_data, "total": total}

    # ------------------------------------------------------------------
    # routes
    # ------------------------------------------------------------------
    @http.route('/pbi_dashboards/loyalty_sales_analysis/data', type='json', auth='user')
    def loyalty_sales_analysis_data(self, period='this_year', dateFrom=None, dateTo=None, franchise='MDA'):
        if not self._has_access():
            return {'error': 'You do not have access to this dashboard.'}
        try:
            date_from, date_to = self._period_range(period, dateFrom, dateTo)
            result = self._drill_rows_and_total('region', date_from, date_to, {}, franchise)
            return {
                'rows': result['rows'],
                'total': result['total'],
                'dateFrom': date_from.isoformat(),
                'dateTo': date_to.isoformat(),
            }
        except Exception as e:
            return {'error': str(e)}

    @http.route('/pbi_dashboards/loyalty_sales_analysis/drill', type='json', auth='user')
    def loyalty_sales_analysis_drill(self, level='city', period='this_year', dateFrom=None, dateTo=None,
                                      selected=None, franchise='MDA'):
        if not self._has_access():
            return {'error': 'You do not have access to this dashboard.'}
        selected = selected or {}
        try:
            date_from, date_to = self._period_range(period, dateFrom, dateTo)
            if level == 'transactions':
                return self._transaction_rows_and_total(date_from, date_to, selected, franchise)
            if level not in LEVEL_COLS:
                return {'error': f'Unknown level: {level}'}
            return self._drill_rows_and_total(level, date_from, date_to, selected, franchise)
        except Exception as e:
            return {'error': str(e)}
