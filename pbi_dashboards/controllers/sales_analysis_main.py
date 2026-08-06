from datetime import date, timedelta

from odoo import http
from odoo.http import request

from .access import menu_allowed


def _quarter_start(d):
    q_month = (d.month - 1) // 3 * 3 + 1
    return date(d.year, q_month, 1)


def _prev_quarter_range(d):
    start = _quarter_start(d)
    prev_end = start - timedelta(days=1)
    return _quarter_start(prev_end), prev_end


# Drill order per the report spec: Region -> City -> Main -> Main Sub ->
# Prod Group -> Product Sub Group -> Customer -> Transaction list (the last
# is a leaf row list, not a group-by level — see _transaction_rows). Column
# pairs point at v_pbi_sales_analysis (pbi_dashboards/models/sales_analysis_view.py),
# which already resolves every caption needed.
LEVEL_COLS = {
    "region": ("region_code", "region_name"),
    "city": ("city_code", "city_name"),
    "main": ("main_code", "main_name"),
    "mainSub": ("main_sub_code", "main_sub_name"),
    "prodGroup": ("prod_group_code", "prod_group_name"),
    "productSubGroup": ("product_sub_group_code", "product_sub_group_name"),
    "customer": ("customer_code", "customer_name"),
}
LEVEL_ORDER = ["region", "city", "main", "mainSub", "prodGroup", "productSubGroup", "customer"]


class PbiSalesAnalysisController(http.Controller):
    """Backs "PBI Dashboards > Sales Analysis": two identical drill-down
    reports (Report-1 by Amount, Report-2 by Qty) over the same hierarchy,
    reading from v_pbi_sales_analysis (built on ``bidata`` — the real,
    295k-row sales fact table ``v_bidata_live`` also reads from;
    ``transaction_header``/``transaction_details`` are legacy-import test
    data only). Credit notes are already netted into signed bi_amount/bi_qty
    upstream, so a plain SUM nets them against Invoices — no extra sign
    logic needed here ("subtract the credit notes from invoice amount").
    """

    # ------------------------------------------------------------------
    # low-level helpers
    # ------------------------------------------------------------------
    def _query(self, sql, params=()):
        request.env.cr.execute(sql, params)
        cols = [d[0] for d in request.env.cr.description]
        return [dict(zip(cols, row)) for row in request.env.cr.fetchall()]

    def _has_access(self):
        return menu_allowed("pbi_dashboards.menu_pbi_sales_analysis")

    def _period_range(self, period, date_from=None, date_to=None):
        """(start, end) dates for a Period filter value — same convention as
        the Loyalty Analysis dashboard (pbi_dashboards/controllers/loyalty_main.py)."""
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
    # drill-down rows
    # ------------------------------------------------------------------
    def _base_where(self, date_from, date_to, selected):
        """Clause fragments + params shared by every level: date range plus
        an = filter for every ancestor level the user has already drilled
        into (selected: {level: code})."""
        clauses = ["bi_monthdate BETWEEN %s AND %s"]
        params = [date_from, date_to]
        for lvl in LEVEL_ORDER:
            code = selected.get(lvl)
            if code:
                code_col, _ = LEVEL_COLS[lvl]
                clauses.append(f"{code_col} = %s")
                params.append(code)
        return clauses, params

    def _drill_rows(self, value_col, level, date_from, date_to, selected):
        code_col, name_col = LEVEL_COLS[level]
        clauses, params = self._base_where(date_from, date_to, selected)
        clauses.append(f"{name_col} IS NOT NULL")
        where = " AND ".join(clauses)
        rows = self._query(f"""
            SELECT {code_col} AS code, {name_col} AS label, sum({value_col}) AS value
            FROM v_pbi_sales_analysis
            WHERE {where}
            GROUP BY 1, 2
            ORDER BY 3 DESC
            LIMIT 20
        """, params)
        return [{"code": r["code"], "label": r["label"], "value": float(r["value"] or 0)} for r in rows]

    def _total(self, value_col, date_from, date_to, selected):
        clauses, params = self._base_where(date_from, date_to, selected)
        where = " AND ".join(clauses)
        rows = self._query(f"SELECT sum({value_col}) AS value FROM v_pbi_sales_analysis WHERE {where}", params)
        return float(rows[0]["value"] or 0)

    def _transaction_rows(self, date_from, date_to, selected):
        clauses, params = self._base_where(date_from, date_to, selected)
        where = " AND ".join(clauses)
        rows = self._query(f"""
            SELECT transaction_no, transaction_date, warehouse_name,
                   product_sub_group_name AS part_desc, qty, amount
            FROM v_pbi_sales_analysis
            WHERE {where}
            ORDER BY transaction_date DESC NULLS LAST
            LIMIT 200
        """, params)
        return [{
            "transactionNo": r["transaction_no"], "date": r["transaction_date"],
            "warehouse": r["warehouse_name"], "part": r["part_desc"],
            "qty": int(r["qty"] or 0), "amount": float(r["amount"] or 0),
        } for r in rows]

    def _report_bundle(self, value_col, date_from, date_to):
        return {
            "rows": self._drill_rows(value_col, "region", date_from, date_to, {}),
            "total": self._total(value_col, date_from, date_to, {}),
        }

    # ------------------------------------------------------------------
    # routes
    # ------------------------------------------------------------------
    @http.route('/pbi_dashboards/sales_analysis/data', type='json', auth='user')
    def sales_analysis_data(self, period='this_year', dateFrom=None, dateTo=None):
        if not self._has_access():
            return {'error': 'You do not have access to this dashboard.'}
        try:
            date_from, date_to = self._period_range(period, dateFrom, dateTo)
            return {
                'amount': self._report_bundle('amount', date_from, date_to),
                'qty': self._report_bundle('qty', date_from, date_to),
                'dateFrom': date_from.isoformat(),
                'dateTo': date_to.isoformat(),
            }
        except Exception as e:
            return {'error': str(e)}

    @http.route('/pbi_dashboards/sales_analysis/drill', type='json', auth='user')
    def sales_analysis_drill(self, report='amount', level='city', period='this_year',
                              dateFrom=None, dateTo=None, selected=None):
        if not self._has_access():
            return {'error': 'You do not have access to this dashboard.'}
        if report not in ('amount', 'qty'):
            return {'error': f'Unknown report: {report}'}
        selected = selected or {}
        try:
            date_from, date_to = self._period_range(period, dateFrom, dateTo)
            if level == 'transactions':
                return {
                    'rows': self._transaction_rows(date_from, date_to, selected),
                    'total': self._total(report, date_from, date_to, selected),
                }
            if level not in LEVEL_COLS:
                return {'error': f'Unknown level: {level}'}
            return {
                'rows': self._drill_rows(report, level, date_from, date_to, selected),
                'total': self._total(report, date_from, date_to, selected),
            }
        except Exception as e:
            return {'error': str(e)}
