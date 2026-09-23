# -*- coding: utf-8 -*-
"""Backs "PBI Dashboards > Loyalty Dashboards > Loyalty Customers Sales
Analysis".

This menu used to point at the generic pbi_sales_dashboards Sales Analysis
client action (tag pbi_dashboards.sales_analysis_dashboard) — same component,
same route, same v_pbi_sales_analysis/bidata source as the plain "PBI
Dashboards > Sales Analysis" menu, with NO loyalty-customer filter anywhere
in it. Clicking it showed sales for every customer, not just loyalty ones.

This controller (and its own client action, loyalty_sales_analysis_dashboard)
replaces that: same "Sales Dashboard - VQ" pairing — Amount and Qty shown
together per category, ranked by Amount (see pbi_sales_dashboards/
controllers/sales_vq_main.py) — but scoped to loyalty customers only, and
reading from transaction_header/transaction_details + their master-data
links rather than bidata, per the report spec for this menu.

The actual join lives in hhs_loyalty_management's loyalty_sales_table_view
(hhs_loyalty_management/models/sales_table_view.py — a real SQL view, not
duplicated here): transaction_header + transaction_details, joined to
res_partner for activate_loyalty_feature/tier_name, to the legacy ERP
customer master (customer -> t_subregions -> t_regionsdesc/t_subregionsdesc)
for region/city — the same mapping loyalty_main.py's REGION_CITY_JOIN uses
and documents, NOT res_partner.work_center_* — and to product_product/
product_category for the product hierarchy. It already nets Credit Notes
(trnh_type='02') against Invoices in its own qty/net_sales CASE expressions,
so a plain SUM here is already the net figure — same "regular formula"
property sales_analysis_view.py's bi_amount/bi_qty have over bidata, just
computed one layer down.

pbi_loyalty_dashboards depends on loyalty_dashboard, which depends on
hhs_loyalty_management, so the view is always installed before this
controller can be reached.

Drill order: Region -> City -> Main Category -> Sub-Category -> Product
Group -> Product Sub Group -> Customer -> Transaction list (leaf row list,
not a group-by level, same as sales_analysis_main.py's own "transactions").

The 4 product levels (Main Category/Sub-Category/Product Group/Product Sub
Group) are resolved by this controller alone, with NO read of anything
pbi_sales_dashboards owns — this dashboard installs and runs with only
pbi_dashboards + loyalty_dashboard (-> hhs_loyalty_management) present.

A naive join straight from product_template.categ_id to
product_category.sub_category was tried first and abandoned: it assumes
categ_id is always the depth-2 "product group" node sub_category sits on,
but it is very often the depth-3 leaf instead, so the join missed on well
under 5% of the parts loyalty customers actually bought.

The FC_CTE below instead walks the SAME depth-based product_category tree
pbi_sales_dashboards' own Sales Dashboard - VQ (sales_sman_fact_view.py)
walks — reimplemented here, not read from there, so nothing breaks if that
module is ever uninstalled:
  1. `cat` reads catalog directly (cat_grp/cat_part/cat_pgroup/cat_psgroup)
     — the ERP's own code for a part's franchise, group and sub-group,
     DISTINCT ON'd the same way sales_analysis_view.py dedupes catalog's 2
     repo-wide duplicate cat_part rows.
  2. `d1`/`d2`/`d3` are product_category filtered to parent_path depth
     1/2/3 respectively (a `/`-count on parent_path, exactly
     sales_sman_fact_view.py's own test) — depth 1 = franchise branch,
     depth 2 = Main Category's own attachment point
     (product_category.sub_category lives here), depth 3 = Product Sub
     Group's attachment point (product_category.product_family lives
     here).
  3. cat.fr/pg/psg are matched to the CORRECTLY-DEPTH node by walking
     d1 -> d2 (child whose code = cat.pg, parent = the matched d1) ->
     d3 (child whose code = cat.psg, parent = the matched d2) — never
     assumed, always the node the ERP code actually names at that tier.
  4. Main Category = main_category via d2.sub_category -> sub_category ->
     main_category (RAC/LCAC(sub_category)/MBT/OTHERS(main_category), the
     same 2 tables pbi_sales_dashboards' own boards read).
     Sub-Category = sub_category itself (one tier finer than Main
     Category, same table).
     Product Group = d3 itself (the depth-3 product_category node).
     Product Sub Group = product_family via d3.product_family.

Confirmed on dbprod: this reproduces sales_sman_fact_view.py's own coverage
exactly — 892 of 1,340 distinct parts loyalty customers bought in 2026
resolve a Main Category, 873 resolve a Product Sub Group, the same counts
v_pbi_sales_sman_fact gave when this controller still read from it.

A part this resolution has no row for (the ~33% by part count, a much
smaller share by sales value — the long tail) drops out of these 4 levels
the same way a row with no city resolved already drops out of City — see
{name_col} IS NOT NULL in _drill_rows/_base_where — while still counting at
Region/City and in the grand total.
"""

from datetime import date, timedelta

from odoo import http
from odoo.http import request

from .access import menu_allowed

VIEW = "loyalty_sales_table_view"

# MATERIALIZED, not a plain subquery/CTE: the earlier v_pbi_sales_sman_fact
# version of this join needed it because Postgres badly under-estimated how
# many loyalty_sales_table_view rows would survive the WHERE clause and
# picked a Nested Loop that re-ran the inner query once per probe row
# instead of once total (confirmed: 120s+ timeout without it, ~1s with).
# catalog/product_category are two orders of magnitude smaller than that
# fact table (19.6k and a few hundred rows here vs. 112k), so the same
# failure mode is unlikely, but MATERIALIZED costs nothing when it isn't
# needed and is what stands between "fast" and "silently 100x slower again"
# if this ever runs against a much bigger catalog.
FC_CTE = """
    WITH fc AS MATERIALIZED (
        -- DISTINCT ON (part) alone, not (grp, part): fc is joined below by
        -- part_no only (a part transacts under one franchise in practice —
        -- same assumption FRANCHISE_OPTIONS/the Franchise filter already
        -- make), so fc has to carry exactly one row per part or the join
        -- fans out. A handful of parts are catalogued under more than one
        -- franchise branch (sales_sman_fact_view.py notes ~2 repo-wide);
        -- for those this picks one deterministically (lowest id) rather
        -- than double-count their sales.
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
FROM_CLAUSE = f"""
    {VIEW}
    LEFT JOIN fc ON fc.part_no = upper(trim({VIEW}.trnd_part))
"""

# Invoice/Credit Note only — the same pair "Points issued" nets and the
# promotion-participation queries treat as "participated" in loyalty_main.py.
# Redeem/Expiry/Adjustment (trnh_type 98/97/99) aren't sales.
DOC_TYPES = ("Invoice", "Credit Note")

# code_col/name_col are raw SQL fragments (not necessarily plain column
# names), same convention loyalty_main.py's REGION_DIM/CITY_DIM use.
LEVEL_COLS = {
    "region": ("region", "region"),
    "city": ("city", "city"),
    "mainCategory": ("fc.l7_id", "fc.l7_label"),
    "subCategory": ("fc.l8_id", "fc.l8_label"),
    "productGroup": ("fc.l9_id", "fc.l9_label"),
    "productSubGroup": ("fc.lfam_id", "fc.lfam_label"),
    "customer": ("trnh_cstno", "trnh_cstname"),
}
LEVEL_ORDER = ["region", "city", "mainCategory", "subCategory", "productGroup", "productSubGroup", "customer"]

# v matches v_pbi_sales_sman_fact.franchise_code exactly. Midea (MDA) is
# the default per the report spec — this is fundamentally a Midea board, the
# same way pbi_sales_dashboards' Sales Dashboard With Salesman/VQ boards are
# hardcoded MDA-only (sales_sman_main.py's FRANCHISE = "MDA") — but unlike
# those, every other franchise transacted by loyalty customers stays pickable
# rather than being excluded outright.
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
        # SET LOCAL, not a global/session change — scoped to this request's
        # own transaction only, and every query this controller runs joins
        # the same fc CTE. Necessary because the planner badly under-
        # estimates how many loyalty_sales_table_view rows survive the
        # WHERE clause (it isn't the one deciding what to build fc from) and
        # picks a Nested Loop assuming a single cheap probe; the actual row
        # count turns that into tens of millions of comparisons. Confirmed
        # on dbprod: forcing the Hash Join the planner would otherwise use
        # (SET enable_nestloop=off) took the exact same query from ~8.6s to
        # ~1.1s — this is a join-strategy fix, not new data or a rewrite.
        request.env.cr.execute("SET LOCAL enable_nestloop = off")
        request.env.cr.execute(sql, params)
        cols = [d[0] for d in request.env.cr.description]
        return [dict(zip(cols, row)) for row in request.env.cr.fetchall()]

    def _has_access(self):
        return menu_allowed("pbi_dashboards.menu_pbi_sales_analysis")

    def _period_range(self, period, date_from=None, date_to=None):
        """(start, end) dates for a Period filter value — same convention as
        the Loyalty Analysis dashboard (loyalty_main.py) and the plain Sales
        Analysis dashboard (sales_analysis_main.py)."""
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
    def _base_where(self, date_from, date_to, selected, franchise_code=None):
        """Clause fragments + params shared by every level: loyalty-customer
        gate, sales doc types, date range, the optional top Franchise filter,
        plus an = filter for every ancestor level the user has already
        drilled into (selected: {level: code})."""
        clauses = [
            "activate_loyalty_feature = true",
            "trnh_type IN %s",
            "trnh_date BETWEEN %s AND %s",
        ]
        params = [DOC_TYPES, date_from, date_to]
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

    def _drill_rows(self, level, date_from, date_to, selected, franchise_code=None):
        code_col, name_col = LEVEL_COLS[level]
        clauses, params = self._base_where(date_from, date_to, selected, franchise_code)
        clauses.append(f"{name_col} IS NOT NULL")
        where = " AND ".join(clauses)
        rows = self._query(f"""
            {FC_CTE}
            SELECT {code_col} AS code, {name_col} AS label,
                   sum(net_sales) AS amount, sum(qty) AS qty
            FROM {FROM_CLAUSE}
            WHERE {where}
            GROUP BY 1, 2
            ORDER BY 3 DESC
            LIMIT 15
        """, params)
        return [{"code": r["code"], "label": r["label"],
                  "amount": float(r["amount"] or 0), "qty": float(r["qty"] or 0)} for r in rows]

    def _total(self, date_from, date_to, selected, franchise_code=None):
        clauses, params = self._base_where(date_from, date_to, selected, franchise_code)
        where = " AND ".join(clauses)
        rows = self._query(f"{FC_CTE} SELECT sum(net_sales) AS amount, sum(qty) AS qty FROM {FROM_CLAUSE} WHERE {where}", params)
        return {"amount": float(rows[0]["amount"] or 0), "qty": float(rows[0]["qty"] or 0)}

    def _transaction_rows(self, date_from, date_to, selected, franchise_code=None):
        clauses, params = self._base_where(date_from, date_to, selected, franchise_code)
        where = " AND ".join(clauses)
        rows = self._query(f"""
            {FC_CTE}
            SELECT trnh_no, trnh_date, trnh_whouse, trnd_desc, qty, net_sales
            FROM {FROM_CLAUSE}
            WHERE {where}
            ORDER BY trnh_date DESC NULLS LAST
            LIMIT 200
        """, params)
        return [{
            "transactionNo": r["trnh_no"], "date": r["trnh_date"].isoformat() if r["trnh_date"] else None,
            "warehouse": r["trnh_whouse"], "part": r["trnd_desc"],
            "qty": float(r["qty"] or 0), "amount": float(r["net_sales"] or 0),
        } for r in rows]

    # ------------------------------------------------------------------
    # routes
    # ------------------------------------------------------------------
    @http.route('/pbi_dashboards/loyalty_sales_analysis/data', type='json', auth='user')
    def loyalty_sales_analysis_data(self, period='this_year', dateFrom=None, dateTo=None, franchise='MDA'):
        if not self._has_access():
            return {'error': 'You do not have access to this dashboard.'}
        try:
            date_from, date_to = self._period_range(period, dateFrom, dateTo)
            return {
                'rows': self._drill_rows('region', date_from, date_to, {}, franchise),
                'total': self._total(date_from, date_to, {}, franchise),
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
                return {
                    'rows': self._transaction_rows(date_from, date_to, selected, franchise),
                    'total': self._total(date_from, date_to, selected, franchise),
                }
            if level not in LEVEL_COLS:
                return {'error': f'Unknown level: {level}'}
            return {
                'rows': self._drill_rows(level, date_from, date_to, selected, franchise),
                'total': self._total(date_from, date_to, selected, franchise),
            }
        except Exception as e:
            return {'error': str(e)}
