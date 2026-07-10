from odoo import http
from odoo.http import request

MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Fixed display order for the TOP (un-drilled) Customer Type breakdown —
# matches the reference PowerBI "Customer Types" page (Dealers, Projects,
# Modern Trade, Whole Sale, Others), not bi_csttypecode order (00 Others, 01
# Dealers, 02 Modern Trade, 03 Whole Sale, 04 Projects) and not alphabetical.
CUSTOMER_TYPE_FIXED = [("01", "Dealers"), ("04", "Projects"), ("02", "Modern Trade"),
                        ("03", "Whole Sale"), ("00", "Others")]

# Drill chain: Customer Types -> Customer Sub-type -> Regions -> Customers ->
# Product Groups -> Product Sub-groups, per the report spec. Every chart on
# the dashboard shares ONE drill path — drilling in any of the 8 charts
# moves every chart (and the KPI tiles) to the next level at once.
LEVELS = ["customerType", "customerSubType", "region", "customer", "productGroup", "productSubGroup"]
LEVEL_COLUMNS = {
    "customerType": ("bi_csttypecode", "bi_csttypedesc"),
    "customerSubType": ("bi_cstsubtypecode", "bi_cstsubtypedesc"),
    "region": ("bi_cstregioncode", "bi_cstregiondesc"),
    "customer": ("bi_cstno", "bi_cstname"),
    "productGroup": ("bi_pgroupcode", "bi_pgroupname"),
    "productSubGroup": ("bi_psgroupcode", "bi_psgroupname"),
}
LEVEL_LABELS = {
    "customerType": "Customer Type", "customerSubType": "Customer Sub-Type", "region": "Region",
    "customer": "Customer", "productGroup": "Product Group", "productSubGroup": "Product Sub-Group",
}


class PbiSalesKpiController(http.Controller):
    """Backs "PBI Dashboards > Sales Dashboards > Sales Analysis" — a KPI
    tile + chart dashboard (MTD/YTD sales vs target vs prior year) reading
    live from ``v_bidata_live``, the same view the existing Sales Dashboard
    reads from. A sibling of that page and of the separate drill-down also
    named "Sales Analysis" (pbi_dashboards/controllers/sales_analysis_main.py),
    nested under its own "Sales Dashboards" menu container.

    Every chart drills down the SAME shared chain (see LEVELS above): the
    breakdown shown is always "children of the current drill path", and the
    KPI tiles are always summed over the current drill path too — so
    drilling in any one chart updates every tile and every other chart in
    lockstep, not just the chart that was clicked.

    The "Customer Groups" filter is a distinct, coarser dimension than
    Customer Type — it isn't exposed on v_bidata_live itself, so it's
    resolved here via a join against ``v_customergroups`` (cst_no ->
    customer_groupdesc), same join pattern sales_analysis_main.py uses for
    the product-hierarchy captions. Only ~3% of customers in bidata have a
    group assigned; picking a specific group narrows to just those rows,
    same as any other filter — "All" (the default) applies no such filter.
    """

    # ------------------------------------------------------------------
    # low-level helpers
    # ------------------------------------------------------------------
    def _query(self, sql, params=()):
        request.env.cr.execute(sql, params)
        cols = [d[0] for d in request.env.cr.description]
        return [dict(zip(cols, row)) for row in request.env.cr.fetchall()]

    def _has_access(self):
        user = request.env.user
        menu = request.env.ref("pbi_dashboards.menu_pbi_sales_kpi_analysis", raise_if_not_found=False)
        if not menu:
            return False
        allowed = request.env["dashboard.rights.menu"].sudo().allowed_menu_ids(user)
        return menu.id in allowed

    # ------------------------------------------------------------------
    # filter options
    # ------------------------------------------------------------------
    def _period_options(self):
        rows = self._query("""
            SELECT DISTINCT bi_year, bi_month FROM v_bidata_live
            WHERE bi_amount IS NOT NULL AND bi_year IS NOT NULL AND bi_month IS NOT NULL
            ORDER BY 1 DESC, 2 DESC
            LIMIT 24
        """)
        return [{"v": f"{r['bi_year']}-{r['bi_month']:02d}", "l": f"{MONTH_ABBR[r['bi_month'] - 1]} {r['bi_year']}"}
                for r in rows]

    def _latest_period(self):
        rows = self._query("""
            SELECT bi_year, bi_month FROM v_bidata_live
            WHERE bi_amount IS NOT NULL AND bi_year IS NOT NULL AND bi_month IS NOT NULL
            ORDER BY bi_year DESC, bi_month DESC LIMIT 1
        """)
        return (rows[0]["bi_year"], rows[0]["bi_month"]) if rows else (None, None)

    def _customer_group_options(self):
        rows = self._query("""
            SELECT DISTINCT customer_groupcode, customer_groupdesc FROM v_customergroups
            WHERE customer_groupcode IS NOT NULL AND customer_groupcode <> '*'
                  AND customer_groupdesc IS NOT NULL
            ORDER BY customer_groupdesc
        """)
        return [{"v": r["customer_groupcode"], "l": r["customer_groupdesc"]} for r in rows]

    # ------------------------------------------------------------------
    # filter clauses
    # ------------------------------------------------------------------
    def _dim_clauses(self, franchise, customer_group, customer_type):
        clauses, params = [], []
        if franchise and franchise != "all":
            clauses.append("bi_franchisename = %s")
            params.append(franchise)
        if customer_type and customer_type != "all":
            clauses.append("bi_csttypedesc = %s")
            params.append(customer_type)
        if customer_group and customer_group != "all":
            clauses.append("bi_cstno IN (SELECT customer_no FROM v_customergroups WHERE customer_groupcode = %s)")
            params.append(customer_group)
        return clauses, params

    def _drill_clauses(self, drill_path):
        """WHERE fragments for every level already selected in the shared
        drill path (see LEVELS) — e.g. having drilled Customer Type ->
        Dealers -> Customer Sub-Type -> Mega Dealer narrows every query
        (tiles AND the next chart's breakdown) to bi_csttypecode='01' AND
        bi_cstsubtypecode='003'."""
        clauses, params = [], []
        for entry in (drill_path or []):
            level = entry.get("level") if isinstance(entry, dict) else None
            code = entry.get("code") if isinstance(entry, dict) else None
            if level not in LEVEL_COLUMNS or code is None:
                continue
            code_col, _ = LEVEL_COLUMNS[level]
            clauses.append(f"{code_col} = %s")
            params.append(code)
        return clauses, params

    def _period_clauses(self, year, month=None, month_lte=None):
        clauses, params = ["bi_year = %s"], [year]
        if month is not None:
            clauses.append("bi_month = %s")
            params.append(month)
        if month_lte is not None:
            clauses.append("bi_month <= %s")
            params.append(month_lte)
        return clauses, params

    # ------------------------------------------------------------------
    # aggregates
    # ------------------------------------------------------------------
    def _sums(self, year, franchise, customer_group, customer_type, drill_path, month=None, month_lte=None):
        clauses, params = self._period_clauses(year, month, month_lte)
        dim_clauses, dim_params = self._dim_clauses(franchise, customer_group, customer_type)
        drill_clauses, drill_params = self._drill_clauses(drill_path)
        clauses += dim_clauses + drill_clauses
        params += dim_params + drill_params
        where = " AND ".join(clauses)
        r = self._query(f"""
            SELECT sum(bi_amount) AS sales, sum(bi_budgetamount) AS budget,
                   sum(bi_qty) AS qty, sum(bi_budgetqty) AS budget_qty
            FROM v_bidata_live WHERE {where}
        """, params)[0]
        return {"sales": float(r["sales"] or 0), "budget": float(r["budget"] or 0),
                "qty": int(r["qty"] or 0), "budgetQty": int(r["budget_qty"] or 0)}

    def _breakdown(self, level, year, franchise, customer_group, customer_type, drill_path, month=None, month_lte=None):
        code_col, name_col = LEVEL_COLUMNS[level]
        clauses, params = self._period_clauses(year, month, month_lte)
        dim_clauses, dim_params = self._dim_clauses(franchise, customer_group, customer_type)
        drill_clauses, drill_params = self._drill_clauses(drill_path)
        clauses += dim_clauses + drill_clauses + [f"{name_col} IS NOT NULL"]
        params += dim_params + drill_params
        where = " AND ".join(clauses)
        rows = self._query(f"""
            SELECT {code_col} AS code, {name_col} AS label, sum(bi_amount) AS sales, sum(bi_budgetamount) AS budget,
                   sum(bi_qty) AS qty, sum(bi_budgetqty) AS budget_qty
            FROM v_bidata_live WHERE {where}
            GROUP BY 1, 2
            ORDER BY 3 DESC
            LIMIT 15
        """, params)

        # The un-drilled Customer Type chart always shows all 5 fixed
        # categories (zero-filled), matching the reference report — every
        # deeper level just shows whatever exists, sorted by sales.
        if level == "customerType" and not drill_path:
            by_code = {r["code"]: r for r in rows}
            out = []
            for code, label in CUSTOMER_TYPE_FIXED:
                r = by_code.get(code)
                out.append({
                    "code": code, "label": label,
                    "sales": float(r["sales"] or 0) if r else 0.0,
                    "budget": float(r["budget"] or 0) if r else 0.0,
                    "qty": int(r["qty"] or 0) if r else 0,
                    "budgetQty": int(r["budget_qty"] or 0) if r else 0,
                })
            return out
        return [{
            "code": r["code"], "label": r["label"],
            "sales": float(r["sales"] or 0), "budget": float(r["budget"] or 0),
            "qty": int(r["qty"] or 0), "budgetQty": int(r["budget_qty"] or 0),
        } for r in rows]

    def _merge_prev_year(self, current, prev):
        prev_by_code = {r["code"]: r for r in prev}
        for row in current:
            p = prev_by_code.get(row["code"])
            row["prevYearSales"] = p["sales"] if p else 0.0
            row["prevYearQty"] = p["qty"] if p else 0

    # ------------------------------------------------------------------
    # bundle
    # ------------------------------------------------------------------
    def _fetch_bundle(self, year, month, franchise, customer_group, customer_type, drill_path):
        has_prev_year = (year - 1) >= 2023
        depth = min(len(drill_path or []), len(LEVELS) - 1)
        level = LEVELS[depth]
        can_drill_further = depth < len(LEVELS) - 1

        mtd_this = self._sums(year, franchise, customer_group, customer_type, drill_path, month=month)
        ytd_this = self._sums(year, franchise, customer_group, customer_type, drill_path, month_lte=month)
        if has_prev_year:
            mtd_last = self._sums(year - 1, franchise, customer_group, customer_type, drill_path, month=month)
            ytd_last = self._sums(year - 1, franchise, customer_group, customer_type, drill_path, month_lte=month)
        else:
            mtd_last = {"sales": 0.0, "budget": 0.0, "qty": 0, "budgetQty": 0}
            ytd_last = {"sales": 0.0, "budget": 0.0, "qty": 0, "budgetQty": 0}

        mtd_breakdown = self._breakdown(level, year, franchise, customer_group, customer_type, drill_path, month=month)
        ytd_breakdown = self._breakdown(level, year, franchise, customer_group, customer_type, drill_path, month_lte=month)
        if has_prev_year:
            mtd_breakdown_prev = self._breakdown(level, year - 1, franchise, customer_group, customer_type, drill_path, month=month)
            ytd_breakdown_prev = self._breakdown(level, year - 1, franchise, customer_group, customer_type, drill_path, month_lte=month)
        else:
            mtd_breakdown_prev = []
            ytd_breakdown_prev = []
        self._merge_prev_year(mtd_breakdown, mtd_breakdown_prev)
        self._merge_prev_year(ytd_breakdown, ytd_breakdown_prev)

        return {
            "period": {"year": year, "month": month, "monthName": MONTH_NAMES[month - 1],
                       "label": f"{MONTH_NAMES[month - 1]} {year}"},
            "hasPrevYear": has_prev_year,
            "kpis": {
                "mtdThisYear": mtd_this["sales"], "mtdTarget": mtd_this["budget"], "mtdLastYear": mtd_last["sales"],
                "mtdQtyThisYear": mtd_this["qty"], "mtdQtyTarget": mtd_this["budgetQty"], "mtdQtyLastYear": mtd_last["qty"],
                "ytdThisYear": ytd_this["sales"], "ytdTarget": ytd_this["budget"], "ytdLastYear": ytd_last["sales"],
                "ytdQtyThisYear": ytd_this["qty"], "ytdQtyTarget": ytd_this["budgetQty"], "ytdQtyLastYear": ytd_last["qty"],
            },
            "breakdown": {"mtd": mtd_breakdown, "ytd": ytd_breakdown},
            "level": level,
            "levelLabel": LEVEL_LABELS[level],
            "canDrillFurther": can_drill_further,
        }

    # ------------------------------------------------------------------
    # route
    # ------------------------------------------------------------------
    @http.route('/pbi_dashboards/sales_kpi/data', type='json', auth='user')
    def sales_kpi_data(self, period=None, franchise='all', customerGroup='all', customerType='all', drillPath=None):
        if not self._has_access():
            return {'error': 'You do not have access to this dashboard.'}
        try:
            year, month = (None, None)
            if period:
                try:
                    y, m = period.split('-')
                    year, month = int(y), int(m)
                except (ValueError, AttributeError):
                    year, month = None, None
            if year is None or month is None:
                year, month = self._latest_period()
            if year is None:
                return {'error': 'No sales data is available.'}

            drill_path = drillPath if isinstance(drillPath, list) else []
            bundle = self._fetch_bundle(year, month, franchise, customerGroup, customerType, drill_path)
            bundle["periodOptions"] = self._period_options()
            bundle["customerGroupOptions"] = self._customer_group_options()
            return bundle
        except Exception as e:
            return {'error': str(e)}
