from odoo import http
from odoo.http import request

from .sales_mail_main import AMOUNT_EXPR, PRODUCT_SCOPE_CODES

MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# "Customer Type" (top, un-drilled level) is keyed off bi_csttypecode, but
# resolved against ``t_cstclasstypedesc`` (cs_code/cs_desc, cs_lang='1' for
# English) — NOT sales_mail_main.py's CHANNEL_DIM_EXPR/CHANNEL_FIXED_CODES
# (t_salpurgroup-based). Those two lookup tables use overlapping-looking
# codes ('01'-'04') for DIFFERENT category sets (t_salpurgroup: Dealers/
# Projects/Key Accounts/Corporate Sales vs. t_cstclasstypedesc: Dealers/
# Modern Trade/Whole Sale/Projects/Others) — confirmed against live dbprod
# data that bi_csttypecode's actual values ('00'-'04', plus a 5-row '*'
# sentinel) match t_cstclasstypedesc's cs_code range exactly, while
# t_salpurgroup has no '00' code at all and uses '05' for a category
# ("Applied Business") bidata never carries. Reusing CHANNEL_DIM_EXPR here
# (an earlier revision of this file did) therefore mislabeled every
# non-Dealers customer type — e.g. code '02' (2,789+ rows of real "Modern
# Trade" customers) rendered as "Projects" — so this level was switched to
# its own t_cstclasstypedesc-backed expression instead.
CUSTOMER_TYPE_EXPR = """
    COALESCE((SELECT cs_desc FROM t_cstclasstypedesc
              WHERE cs_lang = '1' AND cs_code = bi_csttypecode LIMIT 1), 'Others')
"""
# Fixed display order for the TOP (un-drilled) breakdown, same 5-category
# wording as t_cstclasstypedesc itself (Dealers, Modern Trade, Whole Sale,
# Projects, Others) — 'Others' (cs_code '00') is a genuine ~1% slice of
# bidata (2,789 rows on live dbprod data), not a catch-all for missing data,
# so it's listed alongside the other 4 rather than dropped.
CUSTOMER_TYPE_FIXED_CODES = [
    ("01", "Dealers"), ("02", "Modern Trade"), ("03", "Whole Sale"), ("04", "Projects"), ("00", "Others"),
]
SALES_TYPE_GROUP_CODES = {label: code for code, label in CUSTOMER_TYPE_FIXED_CODES}

# bi_cstname is baked into bidata itself and shows raw Arabic script for a
# chunk of customers — NOT something a join here causes. Same recovery join
# as pbi_dashboards/models/sales_analysis_view.py's identical customer_name
# expression (see that file's docstring for why cst_lang alone can't be
# trusted): only substitute in a customerdesc row when bidata's own name is
# Arabic, and only when THAT row has no Arabic characters at all either.
CUSTOMER_NAME_EXPR = """
    CASE WHEN bi_cstname ~ '[؀-ۿ]'
         THEN COALESCE((SELECT cst_name FROM customerdesc cd
                         WHERE cd.cst_no = bi_cstno AND cd.cst_name !~ '[؀-ۿ]'
                         ORDER BY cd.cst_lang ASC LIMIT 1), bi_cstname)
         ELSE bi_cstname END
"""

# Drill chain: Customer Type -> Customer Sub-type -> Regions -> Customers ->
# Product Groups -> Product Sub-groups, per the report spec. Every chart on
# the dashboard shares ONE drill path — drilling in any of the 8 charts
# moves every chart (and the KPI tiles) to the next level at once. The
# Salesman level (and its level-nav button) was removed entirely at the
# user's request — to bring it back, re-add "salesman" between "customer"
# and "productGroup" below, plus the matching LEVEL_COLUMNS/LEVEL_LABELS
# entries and JS LEVEL_ORDER/LEVEL_FILTER_LABELS/LEVEL_NAV_LABELS.
LEVELS = ["salesTypeGroup", "customerSubType", "region", "customer", "productGroup", "productSubGroup"]
LEVEL_COLUMNS = {
    "salesTypeGroup": ("bi_csttypecode", f"({CUSTOMER_TYPE_EXPR})"),
    "customerSubType": ("bi_cstsubtypecode", "bi_cstsubtypedesc"),
    "region": ("bi_cstregioncode", "bi_cstregiondesc"),
    "customer": ("bi_cstno", f"({CUSTOMER_NAME_EXPR})"),
    "productGroup": ("bi_pgroupcode", "bi_pgroupname"),
    "productSubGroup": ("bi_psgroupcode", "bi_psgroupname"),
}
LEVEL_LABELS = {
    "salesTypeGroup": "Customer Type", "customerSubType": "Customer Sub-Type", "region": "Region",
    "customer": "Customer", "productGroup": "Product Group", "productSubGroup": "Product Sub-Group",
}

# Base scope for every query here — which bi_franchisecode/bi_pgroupcode
# combinations are even in scope for this dashboard, independent of whichever
# one (if any) the Franchise filter narrows to. The MDA (Midea) branch reuses
# sales_mail_main.py's own PRODUCT_SCOPE_CODES verbatim (not the older,
# slightly different 10-code list this used to carry, which silently
# under/over-counted vs. Sales Mail Content — e.g. full-year 2025 YTD Amount
# came out 405.5M here vs. 601.0M there before this fix, confirmed by diffing
# the two code lists against live dbprod data) so the two dashboards agree on
# the same Midea figures. The bi_cstno NOT LIKE 'V%%' exclusion is likewise
# copied from BASE_SCOPE_SQL there. BKO/CDY have no Sales Mail Content
# equivalent to cross-check against, so their whitelists are unchanged.
_FRANCHISE_SCOPE_SQL = """
    bi_cstno NOT LIKE 'V%%'
    AND ((bi_franchisecode = 'MDA' AND bi_pgroupcode = ANY(%s))
     OR (bi_franchisecode = 'BKO' AND bi_pgroupcode = ANY(%s))
     OR (bi_franchisecode = 'CDY' AND bi_pgroupcode = ANY(%s)))
"""
_FRANCHISE_SCOPE_PARAMS = [
    PRODUCT_SCOPE_CODES,
    ["BKOBI", "BKOCM", "BKOCO", "BKODW", "BKOFZ", "BKOLA", "BKORF", "BKOSA"],
    ["CDYBI", "CDYLA", "CDYSA"],
]


class PbiSalesKpiController(http.Controller):
    """Backs "PBI Dashboards > Sales Dashboards > Sales Analysis" — a KPI
    tile + chart dashboard (MTD/YTD sales vs target vs prior year) reading
    live from ``bidata`` directly, the same table sales_mail_main.py reads
    from and the same AMOUNT_EXPR formula it uses (see that module's
    docstrings for why: raw bi_amount is too sparse to sum on its own). A
    sibling of the plain Sales Dashboard and of the separate drill-down also
    named "Sales Analysis" (pbi_dashboards/controllers/sales_analysis_main.py),
    nested under its own "Sales Dashboards" menu container.

    Every chart drills down the SAME shared chain (see LEVELS above): the
    breakdown shown is always "children of the current drill path", and the
    KPI tiles are always summed over the current drill path too — so
    drilling in any one chart updates every tile and every other chart in
    lockstep, not just the chart that was clicked.

    The top (un-drilled) level, displayed as "Customer Type" (level key
    "salesTypeGroup"), is keyed off bi_csttypecode and resolved against
    ``t_cstclasstypedesc`` (Dealers/Modern Trade/Whole Sale/Projects/Others
    — see CUSTOMER_TYPE_EXPR/CUSTOMER_TYPE_FIXED_CODES above for why NOT
    sales_mail_main.py's t_salpurgroup-based CHANNEL_DIM_EXPR). A separate
    "Customer" level (individual bi_cstno/bi_cstname) sits between Region
    and Product Group in the drill chain — see LEVELS below.

    The "Customer Groups" filter is a distinct, coarser dimension than Sales
    Type Group — it isn't a bidata column at all, so it's resolved here via a
    join against ``v_customergroups`` (cst_no -> customer_groupdesc), same
    join pattern sales_analysis_main.py uses for the product-hierarchy
    captions. Only ~3% of customers in bidata have a group assigned; picking
    a specific group narrows to just those rows, same as any other filter —
    "All" (the default) applies no such filter.
    """

    # ------------------------------------------------------------------
    # low-level helpers
    # ------------------------------------------------------------------
    def _query(self, sql, params=()):
        request.env.cr.execute(sql, params)
        cols = [d[0] for d in request.env.cr.description]
        return [dict(zip(cols, row)) for row in request.env.cr.fetchall()]

    def _has_access_for(self, menu_xmlid):
        user = request.env.user
        menu = request.env.ref(menu_xmlid, raise_if_not_found=False)
        if not menu:
            return False
        allowed = request.env["dashboard.rights.menu"].sudo().allowed_menu_ids(user)
        return menu.id in allowed

    def _has_access(self):
        return self._has_access_for("pbi_dashboards.menu_pbi_sales_kpi_analysis")

    def _has_access_new(self):
        return self._has_access_for("pbi_dashboards.menu_pbi_sales_kpi_analysis_new")

    # ------------------------------------------------------------------
    # filter options
    # ------------------------------------------------------------------
    def _year_options(self):
        # bi_qty IS NOT NULL, not bi_amount — matching sales_mail_main.py's
        # own _year_options exactly. Confirmed against live dbprod data that
        # raw bi_amount is only ever populated for 2024, while bi_qty (what
        # AMOUNT_EXPR is actually built from) covers 2024 through the
        # present — filtering on bi_amount here would silently drop every
        # later year from the dropdown even though real sales exist.
        rows = self._query(f"""
            SELECT DISTINCT bi_year FROM bidata
            WHERE bi_qty IS NOT NULL AND bi_year IS NOT NULL AND {_FRANCHISE_SCOPE_SQL}
            ORDER BY 1 DESC LIMIT 8
        """, _FRANCHISE_SCOPE_PARAMS)
        return [{"v": r["bi_year"], "l": str(r["bi_year"])} for r in rows]

    def _latest_period(self):
        rows = self._query(f"""
            SELECT bi_year, bi_month FROM bidata
            WHERE bi_qty IS NOT NULL AND bi_year IS NOT NULL AND bi_month IS NOT NULL
                  AND {_FRANCHISE_SCOPE_SQL}
            ORDER BY bi_year DESC, bi_month DESC LIMIT 1
        """, _FRANCHISE_SCOPE_PARAMS)
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
    def _dim_clauses(self, franchise, customer_group, sales_type_group):
        clauses, params = [], []
        if franchise and franchise != "all":
            clauses.append("bi_franchisename = %s")
            params.append(franchise)
        if sales_type_group and sales_type_group != "all":
            code = SALES_TYPE_GROUP_CODES.get(sales_type_group)
            if code:
                clauses.append("bi_csttypecode = %s")
                params.append(code)
        if customer_group and customer_group != "all":
            clauses.append("bi_cstno IN (SELECT customer_no FROM v_customergroups WHERE customer_groupcode = %s)")
            params.append(customer_group)
        return clauses, params

    def _drill_clauses(self, drill_path):
        """WHERE fragments for every level already selected in the shared
        drill path (see LEVELS) — e.g. having drilled Sales Type Group ->
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
    def _sums(self, year, franchise, customer_group, sales_type_group, drill_path, month=None, month_lte=None):
        clauses, params = self._period_clauses(year, month, month_lte)
        dim_clauses, dim_params = self._dim_clauses(franchise, customer_group, sales_type_group)
        drill_clauses, drill_params = self._drill_clauses(drill_path)
        clauses = clauses + [_FRANCHISE_SCOPE_SQL] + dim_clauses + drill_clauses
        params = params + _FRANCHISE_SCOPE_PARAMS + dim_params + drill_params
        where = " AND ".join(clauses)
        r = self._query(f"""
            SELECT sum({AMOUNT_EXPR}) AS sales, sum(bi_budgetamount) AS budget,
                   sum(bi_qty) AS qty,
                   sum(bi_budgetqty) AS budget_qty
            FROM bidata WHERE {where}
        """, params)[0]
        return {"sales": float(r["sales"] or 0), "budget": float(r["budget"] or 0),
                "qty": int(r["qty"] or 0), "budgetQty": int(r["budget_qty"] or 0)}

    def _breakdown(self, level, year, franchise, customer_group, sales_type_group, drill_path, month=None, month_lte=None):
        code_col, name_col = LEVEL_COLUMNS[level]
        clauses, params = self._period_clauses(year, month, month_lte)
        dim_clauses, dim_params = self._dim_clauses(franchise, customer_group, sales_type_group)
        drill_clauses, drill_params = self._drill_clauses(drill_path)
        # salesTypeGroup's name_col is CUSTOMER_TYPE_EXPR, a correlated
        # t_cstclasstypedesc subquery COALESCEd to 'Others' — it can never be
        # NULL, so the "IS NOT NULL" filter every other (plain-column) level
        # needs would just be a second, redundant evaluation of that same
        # subquery per row (confirmed via EXPLAIN ANALYZE on live dbprod
        # data: ~80ms of otherwise-pointless extra work per breakdown query).
        # Skip it for that one level only.
        not_null_clause = [] if level == "salesTypeGroup" else [f"({name_col}) IS NOT NULL"]
        # bi_cstno carries the literal sentinel '*' (not NULL, so the check
        # above doesn't catch it) on 3 live budget/target-only rows not
        # attributed to any individual customer. Same '*'-as-"unassigned"
        # convention this file already excludes for Customer Groups (see
        # _customer_group_options) and previously for the Salesman level
        # (bi_salesmancode/bi_salesmanname, 15,772 such rows) before that
        # level was removed.
        if level == "customer":
            not_null_clause.append(f"{code_col} <> '*'")
        clauses = clauses + [_FRANCHISE_SCOPE_SQL] + dim_clauses + drill_clauses + not_null_clause
        params = params + _FRANCHISE_SCOPE_PARAMS + dim_params + drill_params
        where = " AND ".join(clauses)
        rows = self._query(f"""
            SELECT {code_col} AS code, {name_col} AS label, sum({AMOUNT_EXPR}) AS sales, sum(bi_budgetamount) AS budget,
                   sum(bi_qty) AS qty, sum(bi_budgetqty) AS budget_qty
            FROM bidata WHERE {where}
            GROUP BY 1, 2
            ORDER BY 3 DESC
            LIMIT 15
        """, params)

        # The un-drilled, UNFILTERED Customer Type chart always shows all 5
        # fixed categories (zero-filled) — CUSTOMER_TYPE_FIXED_CODES only
        # supplies that fixed SET (so a category with zero sales this period
        # still gets a bar), not the display ORDER: every level's bars sort
        # by sales descending (the ORDER BY 3 DESC above), and this one
        # shouldn't be the odd one out just because its rows start from a
        # fixed list instead of the query result directly.
        # Once a specific sales_type_group is picked from that same dropdown
        # (a WHERE bi_csttypecode=%s filter, not a drill), the query above
        # already narrows to just that one group — zero-filling the other 4
        # here on top of that would re-add them back as bogus 0-value bars,
        # which is exactly the "others show up as 0" bug this guard avoids.
        if level == "salesTypeGroup" and not drill_path and (not sales_type_group or sales_type_group == "all"):
            by_code = {r["code"]: r for r in rows}
            out = []
            for code, label in CUSTOMER_TYPE_FIXED_CODES:
                r = by_code.get(code)
                out.append({
                    "code": code, "label": label,
                    "sales": float(r["sales"] or 0) if r else 0.0,
                    "budget": float(r["budget"] or 0) if r else 0.0,
                    "qty": int(r["qty"] or 0) if r else 0,
                    "budgetQty": int(r["budget_qty"] or 0) if r else 0,
                })
            out.sort(key=lambda o: o["sales"], reverse=True)
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

    def _natural_level(self, drill_path):
        """The level after the DEEPEST dimension actually drilled so far —
        keyed by level NAME, not by len(drill_path)/list position. Plain
        sequential drilling (one entry per level, in LEVELS order) makes
        this identical to the old len(drill_path) shortcut, but the level-
        jump nav (sales_kpi_dashboard.js jumpToLevel) can view a level
        without drilling into it, so a later drillPath can have fewer
        entries than its "position" would suggest, or skip levels the user
        jumped past — going by the deepest LEVEL NAME present keeps the
        chain resuming at the right next level either way."""
        drilled_idxs = [LEVELS.index(e["level"]) for e in (drill_path or [])
                         if isinstance(e, dict) and e.get("level") in LEVELS]
        depth = min((max(drilled_idxs) + 1) if drilled_idxs else 0, len(LEVELS) - 1)
        return LEVELS[depth]

    # ------------------------------------------------------------------
    # bundle
    # ------------------------------------------------------------------
    def _fetch_bundle(self, year, month, franchise, customer_group, sales_type_group, drill_path, level_filter_code=None, view_level=None):
        # SET LOCAL scopes to this transaction only (auto-reverts at commit,
        # no persistent/database-wide change) — same fix as
        # sales_mail_main.py's identical line, for the identical reason:
        # EXPLAIN ANALYZE showed Postgres JIT-compiling each of this bundle's
        # multi-CASE-WHEN AMOUNT_EXPR aggregate queries (792ms of which
        # ~620ms was JIT generation/inlining/optimization, confirmed on live
        # dbprod data), even though the actual scan+aggregate only takes
        # ~150ms. With ~10 such queries per request (sums x4, breakdown x4,
        # plus the option-list queries), that overhead alone was the
        # dominant cost behind slow initial loads and slow drill-down/
        # level-nav clicks after the bidata-direct migration.
        request.env.cr.execute("SET LOCAL jit = off")
        has_prev_year = (year - 1) >= 2023
        # view_level (set by the level-jump nav — "go straight to Regions"
        # etc. without drilling through every level in between) overrides
        # the natural next-level-after-what's-drilled default for JUST this
        # request's grouping; it never touches drill_path itself, so the
        # breadcrumb and every already-applied filter stay exactly as they
        # were, and drilling further from here still extends drill_path
        # normally (see onCategoryClick in sales_kpi_dashboard.js).
        level = view_level if view_level in LEVELS else self._natural_level(drill_path)
        can_drill_further = LEVELS.index(level) < len(LEVELS) - 1

        # The level-filter dropdown (see sales_kpi_dashboard.js selectLevelFilter)
        # narrows every tile/chart to one category of the CURRENT level without
        # drilling — real drill-down only ever happens by clicking a bar/slice.
        # Implemented as one extra same-level WHERE clause (piggybacking
        # _drill_clauses' code_col=%s pattern) that's added to the query path
        # but deliberately kept OUT of `level`/`depth`/`drill_path` itself, so
        # the breadcrumb, dropdown label and grouping level all stay put.
        effective_path = list(drill_path or [])
        if level_filter_code not in (None, 'all', ''):
            effective_path.append({"level": level, "code": level_filter_code})

        mtd_this = self._sums(year, franchise, customer_group, sales_type_group, effective_path, month=month)
        ytd_this = self._sums(year, franchise, customer_group, sales_type_group, effective_path, month_lte=month)
        if has_prev_year:
            mtd_last = self._sums(year - 1, franchise, customer_group, sales_type_group, effective_path, month=month)
            ytd_last = self._sums(year - 1, franchise, customer_group, sales_type_group, effective_path, month_lte=month)
        else:
            mtd_last = {"sales": 0.0, "budget": 0.0, "qty": 0, "budgetQty": 0}
            ytd_last = {"sales": 0.0, "budget": 0.0, "qty": 0, "budgetQty": 0}

        mtd_breakdown = self._breakdown(level, year, franchise, customer_group, sales_type_group, effective_path, month=month)
        ytd_breakdown = self._breakdown(level, year, franchise, customer_group, sales_type_group, effective_path, month_lte=month)
        if has_prev_year:
            mtd_breakdown_prev = self._breakdown(level, year - 1, franchise, customer_group, sales_type_group, effective_path, month=month)
            ytd_breakdown_prev = self._breakdown(level, year - 1, franchise, customer_group, sales_type_group, effective_path, month_lte=month)
        else:
            mtd_breakdown_prev = []
            ytd_breakdown_prev = []
        self._merge_prev_year(mtd_breakdown, mtd_breakdown_prev)
        self._merge_prev_year(ytd_breakdown, ytd_breakdown_prev)

        # The dropdown's OWN option list must always list every category at
        # this level, regardless of which one (if any) is currently selected
        # — so when a quick filter is active, re-derive it from the
        # unfiltered drill_path instead of reusing the (now single-row)
        # mtd_breakdown above. No extra query in the common unfiltered case.
        if level_filter_code not in (None, 'all', ''):
            level_option_rows = self._breakdown(level, year, franchise, customer_group, sales_type_group, drill_path, month=month)
        else:
            level_option_rows = mtd_breakdown
        level_options = [{"v": str(r["code"]), "l": r["label"]} for r in level_option_rows]

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
            "levelOptions": level_options,
        }

    # ------------------------------------------------------------------
    # route
    # ------------------------------------------------------------------
    def _sales_kpi_data(self, has_access, period=None, franchise='all', customerGroup='all', salesTypeGroup='all', drillPath=None, levelFilterCode=None, viewLevel=None):
        if not has_access:
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
            bundle = self._fetch_bundle(year, month, franchise, customerGroup, salesTypeGroup, drill_path, levelFilterCode, viewLevel)
            bundle["yearOptions"] = self._year_options()
            bundle["customerGroupOptions"] = self._customer_group_options()
            return bundle
        except Exception as e:
            return {'error': str(e)}

    @http.route('/pbi_dashboards/sales_kpi/data', type='json', auth='user')
    def sales_kpi_data(self, period=None, franchise='all', customerGroup='all', salesTypeGroup='all', drillPath=None, levelFilterCode=None, viewLevel=None):
        return self._sales_kpi_data(self._has_access(), period, franchise, customerGroup, salesTypeGroup, drillPath, levelFilterCode, viewLevel)

    # Backs "Sales Dashboard - New" — same bidata-direct engine/bundle as
    # above (Amount/Qty toggle and chart-row layout are purely client-side,
    # see sales_kpi_dashboard_new.js), gated by its own menu grant
    # (menu_pbi_sales_kpi_analysis_new) rather than reusing "Sales
    # Dashboard"'s, per this module's one-grant-per-leaf convention.
    @http.route('/pbi_dashboards/sales_kpi_new/data', type='json', auth='user')
    def sales_kpi_data_new(self, period=None, franchise='all', customerGroup='all', salesTypeGroup='all', drillPath=None, levelFilterCode=None, viewLevel=None):
        return self._sales_kpi_data(self._has_access_new(), period, franchise, customerGroup, salesTypeGroup, drillPath, levelFilterCode, viewLevel)
