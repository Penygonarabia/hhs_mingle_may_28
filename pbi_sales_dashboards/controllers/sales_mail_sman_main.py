# -*- coding: utf-8 -*-
"""Backs "PBI Dashboards > Sales Dashboards > Sales Analysis with Salesman".

The 17-page report layout of "Sales Analysis - New"
(sales_mail_main.py / sales_mail_dashboard_new.js) drawn on the data source of
"Sales Dashboard With Salesman" (sales_sman_main.py):

  * ACTUALS come from v_pbi_sales_sman_fact and the TARGET from
    v_pbi_sales_budget_live, exactly as "Sales Dashboard With Salesman" and
    "Sales Dashboard - VQ" read them — through the same BUDGET_TEMP, built by
    the same build_budget_temp(), so the boards can never drift on what a sale
    is or on what its target was. The target is read live rather than off the
    snapshot so a budget entered a minute ago is on the page now instead of
    after the 02:30 refresh.
  * The budget figure REPEATS across the part rows of its tuple, so every
    budget query here groups by budget_key with max() before it sums. See
    sales_sman_main's docstring, and _budget_two_stage there.
  * NOTES ARE WRITTEN ON THE PAGE, not in the deck. Edit Notes saves the
    narrative and its requirement to pbi.dashboard.note; Export PowerPoint
    carries them out into the deck's speaker notes and there is no way back
    in. There used to be -- an Import Notes button posting a deck to an
    import_notes route that matched slide titles back to narrative keys and
    diffed the speaker notes against the computed baseline. It is gone, along
    with the title matchers and the deck's own keywords marker, which had no
    other reader.
  * SALESMAN is a global filter here (Year / Month / Salesman /
    Sub-category View), not a chart dimension — every page narrows with it.
    ⚠️ That filter puts EVERY target on this board out of scope: the budget
    carries no salesman (60.3% of its money sits on '*'), so as soon as one is
    selected the target goes dark board-wide rather than showing a figure that
    is both inflated and patchy. `budgetReliable` in the payload says so.

Dimension mapping, "Sales Analysis - New" -> here. bidata's channel/region/
main-group taxonomy does not exist on the legacy tables, so each page moves to
the nearest real level of the salesman drill chain:

    Sale Type / Channel    ->  Sales Type Group         (l1)
    Department             ->  Partner Classification   (l2)
    Region                 ->  Report Region            (l3)
    Main Group             ->  Main Category            (l7)
    Product Sub-Group      ->  Sub Category             (l8)
    Product Group          ->  Product Group            (l9)

THE CUSTOMER-SIDE GROUPING IS THE SALES TYPE GROUP, not the Partner
Classification, on every page that is about one grouping or draws one set of
customer bars: pages 4, 5, 10, 11, 15, 16 and 17. Three reasons, all of them
measured on dbprod for 2026 YTD:

  * it is complete. l2 leaves SAR 43.4m -- 10.5 pct of the year -- in an
    Unassigned bucket that _top_named then has to skip, so "the largest
    classification" was chosen from a partial ranking. l1 has no NULL at all
    in scope: three groups, SAR 411.9m, and they sum to the KPI tile.
  * it is the level the BUDGET is captured at, so the target bars tie to the
    riyal (SAR 519,780,149 summed per group against the same ungrouped total)
    rather than being a target the chart merely happens to reconcile with.
  * it is the head of the drill chain the two sibling salesman boards open on
    (OPENING_LEVEL in sales_sman_main), so a reader moving between them meets
    the same first cut of the business.

Partner Classification is still the grouping on pages 2, 13 and 14, which are
about the classification itself rather than about the top-line split.

Pages 12 and 15-17 still resolve their filter from the data rather than from a
hardcoded bidata value — the largest Sales Type Group and the largest Main
Category by YTD sales. See _fetch_bundle's `top_stg` / `top_maincat`. That
keeps those pages meaningful on any database rather than silently empty on one
whose categories happen to be named differently.

Three toggle rows, all data-driven: q1..q4 are the quarters up to the selected
month (pages 4 and 5 — the QUARTER is the tab and the categories are the bars,
so one panel answers "who sold what in Q2"), c1..c4 the four biggest Partner
Classifications (pages 13, 14) and r1..r4 the four biggest Regions (pages 15,
16). The slugs are fixed so the template's refs and the notes keys stay stable
across periods; only the labels move.
"""

import json
import logging
import re
from io import BytesIO

from odoo import fields, http
from odoo.http import request

# python-pptx is OPTIONAL — see pbi_dashboards/controllers/optional_deps.py.
# Guarded so this module, and therefore the whole addon, still imports on a
# server that does not have it; without the guard a missing package makes the
# module uninstallable rather than merely making one button unavailable.
try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
except ImportError:  # server without python-pptx
    # Stand-ins, needed only so the module-level constants below still
    # evaluate. Nothing reaches them: every path that draws a slide goes
    # through a route that refuses first (optional_deps.PPTX_AVAILABLE).
    Presentation = None

    def Inches(value):
        return value

    def Pt(value):
        return value

from .access import menu_allowed
from odoo.addons.pbi_dashboards.controllers import optional_deps
from .main import (
    _pptx_marked_text, _pfmt_m, _pfmt, _pshare, MONTH_NAMES,
)
from .sales_pptx import (
    PbiSalesPptx, PPTX_LINE_ACHIEVEMENT, PPTX_LINE_YOY,
    PPTX_TILE_COLORS, PPTX_MARGIN, PPTX_FULL_W,
    _ensure_pptx_loaded,
)


def _ensure_presentation():
    global Presentation, Inches, Pt
    if Presentation is not None:
        _ensure_pptx_loaded()
        return True
    try:
        from pptx import Presentation as _Pres
        from pptx.util import Inches as _Inches, Pt as _Pt
        Presentation = _Pres
        Inches, Pt = _Inches, _Pt
        _ensure_pptx_loaded()
        return True
    except ImportError:
        return False

from .sales_sman_main import (
    FACT_VIEW, BUDGET_TEMP, FRANCHISE, BUDGET_UNSAFE_LEVELS, SCOPES,
    DEFAULT_SCOPE,
    UNASSIGNED, UNASSIGNED_LABEL,
    LEVELS, LEVEL_COLUMNS, LEVEL_ORDER, LEVEL_LABELS,
    budget_basis_for,
    build_budget_temp,
)

_logger = logging.getLogger(__name__)

# Every _pptx_* helper below the data layer is pure presentation — it turns a
# {'label': ..., 'sales': ...} row list into shapes on a slide and never looks
# at where the numbers came from. Reusing that instance rather than
# re-implementing it is what keeps this dashboard's deck byte-comparable with
# "Sales Analysis - New". PbiSalesPptx is the presentation half on its own (see
# sales_pptx.py) — this used to instantiate PbiSalesMailController, which meant
# carrying that board's whole bidata engine along for the ride and, once those
# boards moved to pbi_sales_temp_dashboards, a dependency on the temp module.
# The class holds no state, so one module-level instance is safe.
_PPTX = PbiSalesPptx()

# ---------------------------------------------------------------------------
# Level plumbing. Each entry is (code column, label column) on the snapshot.
# There is no third, budget-side column any more: the budget rides on the same
# rows as the actuals, so a level cannot be wired up on one side and forgotten
# on the other.
# ---------------------------------------------------------------------------
LEVEL_SPEC = {
    'salesTypeGroup': ('l1_code', 'l1_label'),
    'classification': ('l2_code', 'l2_label'),
    'region':         ('l3_code', 'l3_label'),
    'salesman':       ('l5_code', 'l5_label'),
    'mainCategory':   ('l7_code', 'l7_label'),
    'subCategory':    ('l8_code', 'l8_label'),
    'productGroup':   ('l9_code', 'l9_label'),
    # The model family -- ELITE R410 rather than ELITE INDOOR/OUTDOOR R410.
    # See LEVEL_COLUMNS in sales_sman_main for why the sub-group IS the family.
    'productSubGroup': ('lfam_code', 'lfam_label'),
}

# Where the TARGET is grouped (and filtered) by a different column from the
# actuals. Only l1, and the reason is the same one sales_sman_main states at
# BUDGET_LEVEL_COLUMNS: l1 is not part of budget_key, so a budget tuple whose
# parts sold under two sale types would have its whole figure counted once per
# sale type by the max()-per-budget_key de-duplication every budget query here
# runs. The snapshot carries the budget's OWN sale type beside the row's
# (budget_l1_code -- see models/sales_sman_fact_view.py) and every capture
# tuple has exactly one, so grouping the target on that is exact by
# construction. Measured on 2025: 3 tuples, SAR 90,232 double-counted.
#
# It is not merely a nicety here: BUDGET_TEMP does not carry l1_code AT ALL
# (see _BUDGET_TEMP_COLUMNS in sales_sman_main), so a budget query reaching for
# LEVEL_SPEC's column at this level would not be subtly wrong, it would not
# run. Verified on dbprod 2026 YTD: the target summed per sale type group is
# SAR 519,780,149, to the riyal the same as the ungrouped total.
BUDGET_LEVEL_SPEC = {
    'salesTypeGroup': ('budget_l1_code', 'budget_l1_label'),
}

# Fixed toggle slugs. The categories behind them change with the data (see the
# module docstring); the slugs do not, so `refs` in the OWL component and
# `sales_mail_sman_<key>_<slug>` in pbi.dashboard.note stay stable.
CLASS_SLUGS = ['c1', 'c2', 'c3', 'c4']
REGION_SLUGS = ['r1', 'r2', 'r3', 'r4']
# Pages 4 and 5 toggle by QUARTER rather than by category: the quarter is the
# tab and the categories are the bars, which is the way round that lets one
# panel be read as "who sold what in Q2" instead of needing four tabs opened in
# turn to answer it. Four slugs, but only the quarters up to the selected month
# are ever offered -- see _quarter_tabs.
QUARTER_SLUGS = ['q1', 'q2', 'q3', 'q4']

TEMP_FACT = 'pbi_mail_sman_fact'
# The TARGET is not built here at all. BUDGET_TEMP and build_budget_temp are
# imported from sales_sman_main, so this board, "Sales Dashboard With Salesman"
# and "Sales Dashboard - VQ" read one table, built one way, from one view. This
# board used to keep a copy of its own under its own name and with no year
# predicate -- same source view, so the same money, but a second build of it is
# a second thing to keep in step, and it copied every year of the budget to
# read one. Sharing the name is safe: each board is its own route and so its
# own transaction, and a temp table cannot outlive one.

# One entry, and it is a caption rather than a choice: the snapshot is built
# MDA-only, so this names the brand on the PPTX title slide. See FRANCHISE in
# sales_sman_main for why the Franchise control is gone.
FRANCHISE_LABELS = {'MDA': 'Midea'}


def _plist(labels, limit=3):
    """"A", "A and B", "A, B and C", "A, B and 4 others" — for the narrative
    lines that name a handful of categories inline. Capped because the panel
    is 340px wide and an eleven-name list is not a sentence any more."""
    labels = [l for l in labels if l]
    if not labels:
        return ''
    if len(labels) > limit:
        return "%s and %d others" % (", ".join(labels[:limit]), len(labels) - limit)
    if len(labels) == 1:
        return labels[0]
    return "%s and %s" % (", ".join(labels[:-1]), labels[-1])


class PbiSalesMailSmanController(http.Controller):

    # ------------------------------------------------------------------
    # low-level helpers
    # ------------------------------------------------------------------
    def _query(self, sql, params=()):
        request.env.cr.execute(sql, params)
        cols = [d[0] for d in request.env.cr.description]
        return [dict(zip(cols, row)) for row in request.env.cr.fetchall()]

    def _has_access(self):
        return menu_allowed("pbi_dashboards.menu_pbi_sales_mail_dashboard_sman")

    def _safe(self, label, fn, default):
        """One page's query failing shouldn't 500 the whole report.

        A SAVEPOINT, not the plain cr.rollback() sales_mail_main uses: the
        actuals for every page live in a TEMP TABLE created earlier in this
        same transaction (see _build_fact), and a full rollback would drop it
        — turning one broken page into seventeen.
        """
        try:
            with request.env.cr.savepoint(flush=False):
                return fn()
        except Exception as e:
            _logger.warning("sales_mail_sman_main: %s failed: %s", label, e)
            return default

    def _sub_field(self, sub_mode):
        """Regular -> the l7/l8 columns, Manager -> l7m/l8m. The snapshot
        carries both readings, so the switch is a choice of column, not a
        different build. Whitelisted, never interpolated from the request."""
        return 'm' if sub_mode == 'manager' else ''

    def _fact_available(self):
        request.env.cr.execute("SELECT to_regclass('public.%s')" % FACT_VIEW)
        return bool(request.env.cr.fetchone()[0])

    def _budget_available(self):
        """Whether there is any target to draw.

        Asked of the LIVE budget view rather than the snapshot, so that the
        first budget ever entered turns the target on immediately instead of at
        the next 02:30 refresh — the same reason the figures themselves are
        read from there. v_sales_budget_month belongs to sales_budget, NOT a
        dependency of this module, so on a database without it the view is
        simply empty and the board draws its charts with no target rather than
        failing.

        Since BUDGET_TEMP became the shared, year-scoped build this reads
        "there is a target for the years on screen" rather than "this database
        has a budget somewhere" — see build_budget_temp. That is the question
        the flag is actually asked, and it is the same answer the other two
        salesman boards give."""
        if not self._fact_available():
            return False
        request.env.cr.execute(
            "SELECT EXISTS (SELECT 1 FROM %s)" % BUDGET_TEMP)
        return bool(request.env.cr.fetchone()[0])

    def _budget_reliable(self, salesman, filters=()):
        """False as soon as the board is narrowed by something the budget does
        not carry."""
        if salesman and salesman != 'all':
            try:
                request.env.cr.execute(
                    "SELECT EXISTS (SELECT 1 FROM %s WHERE l5_code = %%s AND (budget_value <> 0 OR budget_qty <> 0))" % BUDGET_TEMP,
                    [str(salesman)]
                )
                if not request.env.cr.fetchone()[0]:
                    return False
            except Exception:
                return False
        for level, _code in (filters or []):
            if level in BUDGET_UNSAFE_LEVELS:
                return False
        return True

    # ------------------------------------------------------------------
    # fact table
    # ------------------------------------------------------------------
    def _build_fact(self, sub_mode, year, salesman, scope=DEFAULT_SCOPE,
                    selection=None):
        """Copy this request's slice of the snapshot into a temp table, once.

        This board runs roughly thirty aggregates over the same rows (seventeen
        pages x this-year / last-year / target). Reading each off the
        materialised view would re-scan the whole snapshot thirty times; copying
        the two years and one salesman this request cares about, then
        ANALYZE-ing, gives every one of them a table Postgres has measured.
        There is no franchise clause: the snapshot is MDA-only.
        ON COMMIT DROP ties its life to the request.

        The Regular/Manager switch is applied here, by aliasing the chosen
        l7/l8 or l7m/l8m pair to l7_*/l8_*, so LEVEL_SPEC and every query
        downstream stay mode-agnostic.
        """
        cr = request.env.cr
        m = self._sub_field(sub_mode)          # '' or 'm', whitelisted
        cols = (
            "yr, mth, franchise_code, franchise_label, part_no, part_label, "
            "l1_code, l1_label, l2_code, l2_label, l3_code, l3_label, "
            "l4_code, l4_label, l5_code, l5_label, l6_code, l6_label, "
            "l7{m}_code AS l7_code, l7{m}_label AS l7_label, "
            "l8{m}_code AS l8_code, l8{m}_label AS l8_label, "
            "l9_code, l9_label, lfam_code, lfam_label, "
            "qty, amount, budget_key, budget_qty, budget_value"
        ).format(m=m)
        clauses, params = ["f.yr IN (%s, %s)"], [year, year - 1]
        # Whitelisted lookup, never interpolated from the request.
        sc = SCOPES.get(scope if scope in SCOPES else DEFAULT_SCOPE)
        if sc:
            clauses.append(sc)
        if salesman and salesman != 'all':
            clauses.append("f.l5_code = %s")
            params.append(salesman)
        if selection:
            for lv, code in selection.items():
                if code in (None, "", "all") or lv == 'salesman':
                    continue
                col_name = LEVEL_COLUMNS.get(lv, (None,))[0]
                if not col_name:
                    continue
                if str(code) == UNASSIGNED:
                    clauses.append("f.%s IS NULL" % col_name)
                else:
                    clauses.append("f.%s = %%s" % col_name)
                    params.append(str(code))
        cr.execute("DROP TABLE IF EXISTS " + TEMP_FACT)
        cr.execute(
            "CREATE TEMP TABLE " + TEMP_FACT + " ON COMMIT DROP AS "
            "SELECT " + cols + " FROM " + FACT_VIEW + " f WHERE " +
            " AND ".join(clauses), params)
        cr.execute("CREATE INDEX ON " + TEMP_FACT + " (budget_key)")
        cr.execute("ANALYZE " + TEMP_FACT)
        build_budget_temp(cr, year, m)

    # ------------------------------------------------------------------
    # filter clauses
    #
    # Filters are carried as (level, code) pairs rather than as SQL. They used
    # to need expressing twice — once against the fact table's l<n>_code and
    # once against v_sales_budget_month's own column — and a page whose two
    # halves disagreed read as a target that was simply wrong, with nothing on
    # screen to say so. Both measures now sit on the same rows, so _fact_filters
    # is the only builder and that whole class of drift is gone.
    # ------------------------------------------------------------------
    @staticmethod
    def _period_window(month, mode):
        """mode: 'month' | 'qtd' | 'ytd' -> (month_gte, month_lte), inclusive."""
        if mode == 'month':
            return month, month
        if mode == 'qtd':
            qstart = ((month - 1) // 3) * 3 + 1
            return qstart, month
        return 1, month

    @staticmethod
    def _budget_columns(level):
        """(code, label) columns for the TARGET at this level.

        LEVEL_SPEC everywhere except where BUDGET_LEVEL_SPEC overrides it --
        today only salesTypeGroup, see that constant."""
        return BUDGET_LEVEL_SPEC.get(level) or LEVEL_SPEC[level]

    def _fact_filters(self, filters):
        return self._filter_clauses(filters, LEVEL_SPEC)

    def _budget_filters(self, filters):
        """The same filters, expressed against the budget's own columns.

        A page narrowed to one sale type group must narrow the target to the
        budget CAPTURED as that group, not to the budget that happened to sell
        as it -- the same distinction sales_sman_main draws, and the reason
        BUDGET_LEVEL_SPEC is used for filtering as well as for grouping."""
        return self._filter_clauses(filters, LEVEL_SPEC, BUDGET_LEVEL_SPEC)

    @staticmethod
    def _filter_clauses(filters, spec, override=None):
        clauses, params = [], []
        for level, code in (filters or []):
            col = 'f.%s' % ((override or {}).get(level) or spec[level])[0]
            if code is None or str(code) == UNASSIGNED:
                clauses.append("%s IS NULL" % col)
            else:
                clauses.append("%s = %%s" % col)
                params.append(str(code))
        return clauses, params

    # ------------------------------------------------------------------
    # aggregates
    # ------------------------------------------------------------------
    _MEASURE_COLS = (
        "COALESCE(sum(f.amount) FILTER (WHERE f.yr = %s), 0) AS sales, "
        "COALESCE(sum(f.qty)    FILTER (WHERE f.yr = %s), 0) AS qty, "
        "COALESCE(sum(f.amount) FILTER (WHERE f.yr = %s), 0) AS prev_sales, "
        "COALESCE(sum(f.qty)    FILTER (WHERE f.yr = %s), 0) AS prev_qty"
    )

    @staticmethod
    def _measure_params(year):
        return [year, year, year - 1, year - 1]

    @staticmethod
    def _row(code, label, actual=None, budget=None):
        lbl = label
        if lbl and (str(lbl).upper() in ('ACWTSPLIT', 'ACWTS') or 'ACWTSPLIT' in str(lbl).upper()):
            lbl = 'Split'
        return {
            'code': str(code), 'label': lbl,
            'sales': float((actual or {}).get('sales') or 0),
            'qty': float((actual or {}).get('qty') or 0),
            'prevYearSales': float((actual or {}).get('prev_sales') or 0),
            'prevYearQty': float((actual or {}).get('prev_qty') or 0),
            'budget': float((budget or {}).get('amount') or 0),
            'budgetQty': float((budget or {}).get('qty') or 0),
            # Set only where the target was shared down from a parent level
            # rather than captured -- see _budget_allocated. The narrative on
            # those pages says so in words; this is the same fact in a form a
            # chart can act on.
            'budgetAllocated': bool((budget or {}).get('allocated')),
        }

    def _sums_ty_ly(self, ctx, mode, filters=()):
        """Company (or filtered) totals: this year, last year and target, over
        the selected month / quarter-to-date / year-to-date window."""
        year, month = ctx['year'], ctx['month']
        gte, lte = self._period_window(month, mode)
        fc, fp = self._fact_filters(filters)
        row = self._query(
            "SELECT " + self._MEASURE_COLS + " FROM " + TEMP_FACT + " f "
            "WHERE f.mth BETWEEN %s AND %s" + ("".join(" AND " + c for c in fc)),
            self._measure_params(year) + [gte, lte] + fp)[0]
        budget = self._budget_total(ctx, mode, filters)
        return self._row('x', '', row, budget)

    _BUDGET_INNER = "max(f.budget_qty) AS bq, max(f.budget_value) AS bv"

    def _budget_where(self, ctx, filters, months=None):
        """Period + filters for a budget query over the temp fact table.

        Only the CURRENT year, unlike the actuals' two: last year's budget is
        history this report never draws, and letting it into the same figure
        would roughly double every Target.

        budget_key IS NOT NULL drops the rows that have sales and no target;
        they would otherwise form a key of their own and add a phantom
        zero-budget group to the outer sum.
        """
        clauses, params = ["f.yr = %s", "f.budget_key IS NOT NULL"], [ctx['year']]
        if months is not None:
            clauses.append("f.mth BETWEEN %s AND %s")
            params += [months[0], months[1]]
        if ctx.get('salesman') and ctx['salesman'] != 'all':
            clauses.append("f.l5_code = %s")
            params.append(str(ctx['salesman']))
        fc, fp = self._budget_filters(filters)
        return clauses + fc, params + fp

    def _budget_total(self, ctx, mode, filters=()):
        if not ctx['hasBudget']:
            return {}
        gte, lte = self._period_window(ctx['month'], mode)
        clauses, params = self._budget_where(ctx, filters, (gte, lte))
        row = self._query(
            "SELECT COALESCE(sum(t.bv), 0) AS amount, COALESCE(sum(t.bq), 0) AS qty FROM ("
            "SELECT f.budget_key, " + self._BUDGET_INNER +
            " FROM " + BUDGET_TEMP + " f WHERE " + " AND ".join(clauses) +
            " GROUP BY f.budget_key) t", params)[0]
        return {'amount': row['amount'], 'qty': row['qty']}

    def _budget_breakdown(self, ctx, mode, level, filters=(), group_level=None):
        """Target per category (optionally per (group, category) pair), plus the
        caption — so a category with a target and no sales still draws a bar and
        still has a name.

        Two stages, always. The snapshot repeats one budget figure across every
        part row of its tuple, so it is collapsed per budget_key first and only
        then summed per category. Written as a single GROUP BY it would not
        error, it would silently return a multiple of the real target.
        """
        if not ctx['hasBudget']:
            return {}
        # A level the budget was never captured at gets a share of its parent's
        # instead -- see _budget_allocated. Pages 7 and 17 are both cut by
        # product sub-group, and until this was here they drew real sales
        # against a flat zero target, which reads as a total miss rather than
        # as "not measured here".
        if level in BUDGET_UNSAFE_LEVELS:
            return self._budget_allocated(ctx, mode, level, filters, group_level)
        code_col, label_col = self._budget_columns(level)
        gte, lte = self._period_window(ctx['month'], mode)
        clauses, params = self._budget_where(ctx, filters, (gte, lte))
        inner = ["COALESCE(f.{c}::text, %s) AS code".format(c=code_col),
                 "max(f.{l}) AS label".format(l=label_col)]
        inner_group, outer_group, head = ["1"], ["t.code"], [UNASSIGNED]
        outer = ["t.code", "max(t.label) AS label"]
        if group_level:
            gcode_col = self._budget_columns(group_level)[0]
            inner.insert(0, "COALESCE(f.{c}::text, %s) AS grp".format(c=gcode_col))
            inner_group = ["1", "2"]
            outer.insert(0, "t.grp")
            outer_group = ["t.grp", "t.code"]
            head = [UNASSIGNED, UNASSIGNED]
        rows = self._query(
            "SELECT " + ", ".join(outer) +
            ", COALESCE(sum(t.bv), 0) AS amount, COALESCE(sum(t.bq), 0) AS qty FROM ("
            "SELECT " + ", ".join(inner) + ", f.budget_key, " + self._BUDGET_INNER +
            " FROM " + BUDGET_TEMP + " f WHERE " + " AND ".join(clauses) +
            " GROUP BY " + ", ".join(inner_group) + ", f.budget_key) t"
            " GROUP BY " + ", ".join(outer_group),
            head + params)
        if not group_level:
            return {str(r['code']): {'amount': r['amount'], 'qty': r['qty'],
                                     'label': r['label']} for r in rows}
        out = {}
        for r in rows:
            out.setdefault(str(r['grp']), {})[str(r['code'])] = {
                'amount': r['amount'], 'qty': r['qty'], 'label': r['label']}
        return out

    def _budget_allocated(self, ctx, mode, level, filters=(), group_level=None):
        """A target for a level the budget was never captured at, shared down
        from its parent by each category's actual mix.

        DERIVED, and the reader is told: the rows this returns carry
        allocated=True, which the page turns into an "(allocated)" note on the
        target series. It is not a target anyone set for a product sub-group;
        it is that sub-group's share of one set for its product group.

        Same three rules as the salesman board's own allocation, and for the
        same reasons -- see _budget_allocated_breakdown in sales_sman_main:

          * THE WEIGHT IS LAST YEAR. Weighting by this year makes the
            allocation circular: every bar in a group then reports the same
            achievement as the group, and the comparison the target exists for
            disappears.
          * THE FALLBACK IS PER CATEGORY, not per group. A sub-group that sold
            nothing last year is weighted on this year rather than handed a
            zero beside real sales.
          * NEGATIVE SALES ARE CLAMPED. A category whose net is a refund has no
            claim on a share of the target, and a negative weight would hand it
            a negative one.

        Allocation preserves the total: a parent's shares sum to that parent's
        target, so the bars still add up to the Target tile. A parent with a
        target and no sales either year has nothing to weight, and its target
        lands on Unassigned rather than being quietly dropped.
        """
        basis = budget_basis_for(level)
        if basis == level or basis in BUDGET_UNSAFE_LEVELS:
            return {}
        basis_budget = self._budget_breakdown(ctx, mode, basis, filters,
                                              group_level=group_level)
        if not basis_budget:
            return {}
        mix = self._allocation_mix(ctx, mode, basis, level, filters, group_level)
        if group_level:
            return {grp: self._share_out(basis_budget.get(grp) or {},
                                         mix.get(grp) or {})
                    for grp in basis_budget}
        return self._share_out(basis_budget, mix)

    def _allocation_mix(self, ctx, mode, basis, level, filters=(),
                        group_level=None):
        """Sales per (basis category, level category) -- this year and last --
        keyed the same way the budget it weights is."""
        year, month = ctx['year'], ctx['month']
        gte, lte = self._period_window(month, mode)
        code_col, label_col = LEVEL_SPEC[level]
        basis_col = LEVEL_SPEC[basis][0]
        fc, fp = self._fact_filters(filters)
        select = ["COALESCE(f.{c}::text, %s) AS basis".format(c=basis_col),
                  "COALESCE(f.{c}::text, %s) AS code".format(c=code_col),
                  "max(f.{l}) AS label".format(l=label_col)]
        head = [UNASSIGNED, UNASSIGNED]
        group = ["1", "2"]
        if group_level:
            gcol = LEVEL_SPEC[group_level][0]
            select.insert(0, "COALESCE(f.{c}::text, %s) AS grp".format(c=gcol))
            head.insert(0, UNASSIGNED)
            group = ["1", "2", "3"]
        rows = self._query(
            "SELECT " + ", ".join(select) + ", "
            # greatest(x, 0) for the same reason the salesman board clamps:
            # credit notes make a category's sales negative.
            "COALESCE(sum(greatest(f.amount, 0)) FILTER (WHERE f.yr = %s), 0) AS cur_amount, "
            "COALESCE(sum(greatest(f.qty, 0))    FILTER (WHERE f.yr = %s), 0) AS cur_qty, "
            "COALESCE(sum(greatest(f.amount, 0)) FILTER (WHERE f.yr = %s), 0) AS prev_amount, "
            "COALESCE(sum(greatest(f.qty, 0))    FILTER (WHERE f.yr = %s), 0) AS prev_qty"
            " FROM " + TEMP_FACT + " f WHERE f.mth BETWEEN %s AND %s" +
            ("".join(" AND " + c for c in fc)) +
            " GROUP BY " + ", ".join(group),
            head + [year, year, year - 1, year - 1] + [gte, lte] + fp)
        out = {}
        for r in rows:
            bucket = out
            if group_level:
                bucket = out.setdefault(str(r['grp']), {})
            bucket.setdefault(str(r['basis']), []).append({
                'code': str(r['code']), 'label': r['label'],
                'cur_amount': float(r['cur_amount'] or 0),
                'cur_qty': float(r['cur_qty'] or 0),
                'prev_amount': float(r['prev_amount'] or 0),
                'prev_qty': float(r['prev_qty'] or 0),
            })
        return out

    @staticmethod
    def _share_out(basis_budget, mix_by_basis):
        """Distribute each basis category's target across its children."""
        out, labels = {}, {}
        for rows in mix_by_basis.values():
            for r in rows:
                labels[r['code']] = r['label']

        def add(code, key, value):
            slot = out.setdefault(code, {'amount': 0.0, 'qty': 0.0,
                                         'label': labels.get(code, code),
                                         'allocated': True})
            slot[key] += value

        for basis_code, target in basis_budget.items():
            rows = mix_by_basis.get(basis_code) or []
            for key, meas in (('amount', 'amount'), ('qty', 'qty')):
                pot = float((target or {}).get(key) or 0)
                if not pot:
                    continue
                weights = {}
                for r in rows:
                    w = r['prev_' + meas] or r['cur_' + meas]
                    if w > 0:
                        weights[r['code']] = weights.get(r['code'], 0.0) + w
                total = sum(weights.values())
                if not total:
                    add(UNASSIGNED, key, pot)
                    continue
                for code, w in weights.items():
                    add(code, key, pot * w / total)
        if UNASSIGNED in out:
            out[UNASSIGNED]['label'] = UNASSIGNED_LABEL
        return out

    @staticmethod
    def _labels_for(level, codes, budget_by_code=None):
        """Display names for codes that reached us from the budget side only.

        This used to be a second query per dimension table, keyed off
        LEVEL_LABEL_SOURCE. The snapshot carries the caption beside the code, so
        _budget_breakdown already returned it and there is nothing left to look
        up — which also removes the class of bug where the two sides captioned
        the same category differently (partner_classification's complete_name
        "[003]-Mega Dealer" against pc_classification1 "Mega Dealer").
        """
        out = {}
        for code in (codes or []):
            entry = (budget_by_code or {}).get(str(code))
            if entry and entry.get('label'):
                out[str(code)] = entry['label']
        return out

    def _merge(self, actual_rows, budget_by_code, level, sub_mode, limit=None,
               fixed_codes=None):
        """Attach targets to the actuals, keeping budget-only categories.

        A category with a target but no sales must still draw a bar, or the
        Target tile stops tallying with the chart beneath it. Sorting is by
        This-Year sales descending, which is how every chart here reads left
        to right; `limit` is applied after the merge so a budget-only
        category can still make the cut.
        """
        by_code = {str(r['code']): r for r in actual_rows}
        for code, b in (budget_by_code or {}).items():
            str_code = str(code)
            if str_code in by_code:
                by_code[str_code]['budget'] = float(b['amount'] or 0)
                by_code[str_code]['budgetQty'] = float(b['qty'] or 0)
                # Carried over with the figure it qualifies. A row built by
                # _row picks this up itself; a row that already existed on the
                # actuals side is filled in here, and missing it left every
                # allocated target on the page looking captured.
                by_code[str_code]['budgetAllocated'] = bool(b.get('allocated'))
                continue
            if not b['amount'] and not b['qty']:
                continue
            row = self._row(code, None, None, b)
            actual_rows.append(row)
            by_code[str_code] = row
        missing = [r['code'] for r in actual_rows if not r['label']]
        if missing:
            labels = self._labels_for(level, missing, budget_by_code)
            for r in actual_rows:
                if not r['label']:
                    r['label'] = labels.get(str(r['code'])) or labels.get(r['code']) or (
                        UNASSIGNED_LABEL if str(r['code']) == UNASSIGNED else r['code'])
        if fixed_codes is not None:
            # Zero-fill so a category with no activity this period still gets a
            # 0-value bar instead of vanishing from a chart whose category set
            # the reader expects to be stable across the MTD/YTD pair.
            #
            # Adds only — it never drops a category that ISN'T in the list, and
            # that asymmetry is deliberate. The bidata report's fixed_labels
            # filters, because its four channels are the whole taxonomy; here
            # the list is "the categories with YTD activity", and a category
            # carrying an MTD target but no YTD sales is exactly the row that
            # would go missing — taking the chart out of step with the Target
            # tile above it, silently.
            for code, label in fixed_codes:
                str_code = str(code)
                if str_code not in by_code:
                    row = self._row(code, label)
                    actual_rows.append(row)
                    by_code[str_code] = row
        actual_rows.sort(key=lambda r: r['sales'], reverse=True)
        return actual_rows[:limit] if limit else actual_rows

    def _breakdown(self, ctx, mode, level, filters=(), limit=None, fixed_codes=None):
        year, month = ctx['year'], ctx['month']
        gte, lte = self._period_window(month, mode)
        code_col, label_col = LEVEL_SPEC[level]
        fc, fp = self._fact_filters(filters)
        rows = self._query(
            "SELECT COALESCE(f.{code}::text, %s) AS code, max(f.{label}) AS label, ".format(
                code=code_col, label=label_col) + self._MEASURE_COLS +
            " FROM " + TEMP_FACT + " f WHERE f.mth BETWEEN %s AND %s" +
            ("".join(" AND " + c for c in fc)) +
            " GROUP BY 1",
            [UNASSIGNED] + self._measure_params(year) + [gte, lte] + fp)
        out = []
        for r in rows:
            row = self._row(r['code'], r['label'], r)
            if not (row['sales'] or row['qty'] or row['prevYearSales'] or row['prevYearQty']):
                continue
            out.append(row)
        budget = self._budget_breakdown(ctx, mode, level, filters)
        return self._merge(out, budget, level, ctx['subMode'], limit, fixed_codes)

    def _breakdown_multi(self, ctx, mode, group_level, group_codes, level,
                         filters=(), limit=None, fixed_codes=None):
        """One grouped query instead of one query per toggle state.

        The four-state pages used to be four full passes over the fact rows
        each; grouping by (toggle value, category) answers all four at once
        and the caller slices the result.
        """
        year, month = ctx['year'], ctx['month']
        gte, lte = self._period_window(month, mode)
        code_col, label_col = LEVEL_SPEC[level]
        gcode_col = LEVEL_SPEC[group_level][0]
        fc, fp = self._fact_filters(filters)
        rows = self._query(
            "SELECT COALESCE(f.{grp}::text, %s) AS grp, COALESCE(f.{code}::text, %s) AS code, "
            "max(f.{label}) AS label, ".format(grp=gcode_col, code=code_col, label=label_col) +
            self._MEASURE_COLS +
            " FROM " + TEMP_FACT + " f WHERE f.mth BETWEEN %s AND %s" +
            ("".join(" AND " + c for c in fc)) +
            " GROUP BY 1, 2",
            [UNASSIGNED, UNASSIGNED] + self._measure_params(year) + [gte, lte] + fp)
        by_grp = {}
        for r in rows:
            row = self._row(r['code'], r['label'], r)
            if not (row['sales'] or row['qty'] or row['prevYearSales'] or row['prevYearQty']):
                continue
            by_grp.setdefault(str(r['grp']), []).append(row)
        budget = self._budget_breakdown(ctx, mode, level, filters, group_level=group_level)
        out = {}
        for code in group_codes:
            grp_rows = by_grp.get(str(code)) or by_grp.get(code) or []
            grp_budget = budget.get(str(code)) or budget.get(code) or {}
            out[code] = self._merge(grp_rows, grp_budget,
                                    level, ctx['subMode'], limit, fixed_codes)
        return out

    def _by_quarter(self, ctx, filters=(), group_level=None, group_codes=()):
        """Calendar-year Q1 through the quarter holding the selected month.

        This-Year actuals are capped at the selected month, so picking an
        earlier month never leaks later actuals into the current quarter;
        Target and Last Year stay full-quarter, which is what makes the
        comparison worth drawing. Quarters entirely beyond the selected month
        are omitted rather than shown as a misleading zero.
        """
        year, month = ctx['year'], ctx['month']
        current_q = (month - 1) // 3 + 1
        cols = ("COALESCE(sum(f.amount) FILTER (WHERE f.yr = %s AND f.mth <= %s), 0) AS sales, "
                "COALESCE(sum(f.qty)    FILTER (WHERE f.yr = %s AND f.mth <= %s), 0) AS qty, "
                "COALESCE(sum(f.amount) FILTER (WHERE f.yr = %s), 0) AS prev_sales, "
                "COALESCE(sum(f.qty)    FILTER (WHERE f.yr = %s), 0) AS prev_qty")
        mparams = [year, month, year, month, year - 1, year - 1]
        fc, fp = self._fact_filters(filters)
        where = " WHERE true" + ("".join(" AND " + c for c in fc))
        if group_level:
            gcol = LEVEL_SPEC[group_level][0]
            rows = self._query(
                "SELECT COALESCE(f.{grp}, %s) AS grp, ((f.mth - 1) / 3 + 1) AS quarter, ".format(grp=gcol) +
                cols + " FROM " + TEMP_FACT + " f" + where + " GROUP BY 1, 2",
                [UNASSIGNED] + mparams + fp)
        else:
            rows = self._query(
                "SELECT ((f.mth - 1) / 3 + 1) AS quarter, " + cols +
                " FROM " + TEMP_FACT + " f" + where + " GROUP BY 1", mparams + fp)

        budget = self._quarter_budget(ctx, filters, group_level)

        def build(actual_by_q, budget_by_q):
            out = []
            for q in range(1, current_q + 1):
                a = actual_by_q.get(q)
                b = budget_by_q.get(q)
                row = self._row('Q%d' % q, 'Q%d' % q, a, b)
                out.append(row)
            return out

        if not group_level:
            return build({r['quarter']: r for r in rows}, budget)
        by_grp = {}
        for r in rows:
            by_grp.setdefault(str(r['grp']), {})[r['quarter']] = r
        return {code: build(by_grp.get(code, {}), (budget or {}).get(code, {}))
                for code in group_codes}

    def _quarter_budget(self, ctx, filters=(), group_level=None):
        """Target per quarter, same two stages. budget_key embeds the month, so
        collapsing per key inside a quarter and summing across keys gives the
        quarter's real total rather than a repeat of one month's."""
        if not ctx['hasBudget']:
            return {}
        clauses, params = self._budget_where(ctx, filters)
        inner = ["((f.mth - 1) / 3 + 1) AS quarter"]
        inner_group, outer, outer_group, head = ["1"], ["t.quarter"], ["t.quarter"], []
        if group_level:
            gcode_col = self._budget_columns(group_level)[0]
            inner.insert(0, "COALESCE(f.{c}::text, %s) AS grp".format(c=gcode_col))
            inner_group = ["1", "2"]
            outer.insert(0, "t.grp")
            outer_group = ["t.grp", "t.quarter"]
            head = [UNASSIGNED]
        rows = self._query(
            "SELECT " + ", ".join(outer) +
            ", COALESCE(sum(t.bv), 0) AS amount, COALESCE(sum(t.bq), 0) AS qty FROM ("
            "SELECT " + ", ".join(inner) + ", f.budget_key, " + self._BUDGET_INNER +
            " FROM " + BUDGET_TEMP + " f WHERE " + " AND ".join(clauses) +
            " GROUP BY " + ", ".join(inner_group) + ", f.budget_key) t"
            " GROUP BY " + ", ".join(outer_group),
            head + params)
        if not group_level:
            return {r['quarter']: {'amount': r['amount'], 'qty': r['qty']} for r in rows}
        out = {}
        for r in rows:
            out.setdefault(str(r['grp']), {})[r['quarter']] = {
                'amount': r['amount'], 'qty': r['qty']}
        return out

    def _by_quarter_level(self, ctx, level, filters=(), fixed_codes=None, limit=None):
        """The quarterly view with the axes the other way round: one row list
        per QUARTER, broken down by `level`.

        _by_quarter answers "how did this category move across the year";
        this answers "who sold what in this quarter", which is the question
        pages 4 and 5 are actually put on a page to answer -- the quarter is
        the tab and the categories are the bars.

        The measure rules are _by_quarter's, unchanged and for the same
        reason: This-Year actuals are capped at the selected month so a
        part-finished quarter does not borrow later months, while Last Year
        and Target stay full-quarter, which is what makes the comparison worth
        drawing at all. Quarters beyond the selected month are omitted rather
        than drawn as a zero.
        """
        year, month = ctx['year'], ctx['month']
        current_q = (month - 1) // 3 + 1
        code_col, label_col = LEVEL_SPEC[level]
        cols = ("COALESCE(sum(f.amount) FILTER (WHERE f.yr = %s AND f.mth <= %s), 0) AS sales, "
                "COALESCE(sum(f.qty)    FILTER (WHERE f.yr = %s AND f.mth <= %s), 0) AS qty, "
                "COALESCE(sum(f.amount) FILTER (WHERE f.yr = %s), 0) AS prev_sales, "
                "COALESCE(sum(f.qty)    FILTER (WHERE f.yr = %s), 0) AS prev_qty")
        mparams = [year, month, year, month, year - 1, year - 1]
        fc, fp = self._fact_filters(filters)
        where = " WHERE true" + ("".join(" AND " + c for c in fc))
        rows = self._query(
            "SELECT ((f.mth - 1) / 3 + 1) AS quarter, "
            "COALESCE(f.{code}, %s) AS code, max(f.{label}) AS label, ".format(
                code=code_col, label=label_col) + cols +
            " FROM " + TEMP_FACT + " f" + where + " GROUP BY 1, 2",
            [UNASSIGNED] + mparams + fp)
        by_q = {}
        for r in rows:
            row = self._row(r['code'], r['label'], r)
            if not (row['sales'] or row['qty'] or row['prevYearSales'] or row['prevYearQty']):
                continue
            by_q.setdefault(r['quarter'], []).append(row)
        budget = self._quarter_level_budget(ctx, level, filters)
        return {q: self._merge(by_q.get(q, []), budget.get(q, {}), level,
                               ctx['subMode'], limit, fixed_codes)
                for q in range(1, current_q + 1)}

    def _quarter_level_budget(self, ctx, level, filters=()):
        """Target per (quarter, category), the same two stages as every other
        budget query here, and full-quarter for the same reason _quarter_budget
        is. The caption comes back with it so a category carrying a target and
        no sales still draws a named bar."""
        if not ctx['hasBudget']:
            return {}
        code_col, label_col = self._budget_columns(level)
        clauses, params = self._budget_where(ctx, filters)
        rows = self._query(
            "SELECT t.quarter, t.code, max(t.label) AS label,"
            " COALESCE(sum(t.bv), 0) AS amount, COALESCE(sum(t.bq), 0) AS qty FROM ("
            "SELECT ((f.mth - 1) / 3 + 1) AS quarter, COALESCE(f.{c}::text, %s) AS code, "
            "max(f.{l}) AS label, f.budget_key, ".format(c=code_col, l=label_col) +
            self._BUDGET_INNER +
            " FROM " + BUDGET_TEMP + " f WHERE " + " AND ".join(clauses) +
            " GROUP BY 1, 2, f.budget_key) t"
            " GROUP BY t.quarter, t.code",
            [UNASSIGNED] + params)
        out = {}
        for r in rows:
            out.setdefault(r['quarter'], {})[str(r['code'])] = {
                'amount': r['amount'], 'qty': r['qty'], 'label': r['label']}
        return out

    # ------------------------------------------------------------------
    # derived shaping
    # ------------------------------------------------------------------
    def _append_total_row(self, rows, label='Total'):
        if not rows:
            return rows
        total = {'code': label, 'label': label}
        for key in ('sales', 'budget', 'qty', 'budgetQty', 'prevYearSales', 'prevYearQty'):
            total[key] = sum((r.get(key) or 0) for r in rows)
        return rows + [total]

    @staticmethod
    def _split_total_row(rows):
        """(categories, [total]) — page 2's trend arrays carry the Total row
        _append_total_row put on the end, and both surfaces draw it apart from
        the categories now: it is their sum, so one shared value axis left
        every real category flattened against the baseline, and its
        Achievement%/YoY% point rode the same two lines as theirs. Returns an
        empty second list when there is no Total row (an empty breakdown)."""
        rows = list(rows or [])
        rest = [r for r in rows if r.get('label') != 'Total']
        total = [r for r in rows if r.get('label') == 'Total']
        return rest, total[:1]

    def _with_pct(self, rows):
        """achievementPct (This Year as % of Target) and yoyPct (as % of Last
        Year) — the two secondary-axis line series on the page-2 combo charts."""
        for r in rows:
            r['achievementPct'] = (r['sales'] / r['budget'] * 100) if r.get('budget') else None
            r['yoyPct'] = (r['sales'] / r['prevYearSales'] * 100) if r.get('prevYearSales') else None
        return rows

    # ------------------------------------------------------------------
    # filter options
    # ------------------------------------------------------------------
    def _year_options(self):
        """Off the snapshot, which is already scoped to what this board draws.

        The current year is always listed, because that is the year the
        dashboard opens on: a default the dropdown cannot display would leave
        the control showing one year while the charts drew another.
        """
        this_year = self._default_period()[0]
        if not self._fact_available():
            return [{'v': this_year, 'l': str(this_year)}]
        rows = self._query(
            "SELECT DISTINCT yr FROM " + FACT_VIEW +
            " WHERE yr IS NOT NULL ORDER BY 1 DESC LIMIT 10")
        years = [r['yr'] for r in rows]
        if this_year not in years:
            years.append(this_year)
            years.sort(reverse=True)
        return [{'v': y, 'l': str(y)} for y in years]

    @staticmethod
    def _franchise_label(code):
        """Brand name for a trnd_group code, falling back to the code itself.

        Names match the bidata dashboards' own FRANCHISE_OPTIONS so the two sets
        of reports read the same. The fallback stays for any franchise that
        enters scope later without a brand name here — an option labelled by its
        code beats an option nobody can select.
        """
        return FRANCHISE_LABELS.get(code, code)

    def _salesman_options(self, year, scope=DEFAULT_SCOPE):
        """Every salesman with in-scope sales in the two years on screen.

        Read off the snapshot, not the temp fact table: that one already has the
        salesman filter applied, so it could only ever list the one selected.
        part_no IS NOT NULL drops the budget-only rows, which carry no salesman
        and would otherwise add an empty option to the top of the list.
        """
        if not self._fact_available():
            return [{'v': 'all', 'l': 'All'}]
        sc = SCOPES.get(scope if scope in SCOPES else DEFAULT_SCOPE)
        rows = self._query(
            "SELECT l5_code AS code, max(l5_label) AS label FROM " + FACT_VIEW + " f"
            " WHERE f.yr = ANY(%s) AND f.part_no IS NOT NULL"
            "   AND f.l5_code IS NOT NULL AND f.l5_code <> ''" +
            (" AND " + sc if sc else "") +
            " GROUP BY 1 ORDER BY 2", ([year, year - 1],))
        return [{'v': 'all', 'l': 'All'}] + [
            {'v': r['code'], 'l': r['label'] or r['code']} for r in rows]

    def _default_period(self):
        """The month the board opens on: the one BEFORE the current one.

        The current month is the month being invoiced, so for most of it the
        board opened on a part-finished picture -- on the 1st, on nothing at
        all. Last month is the most recent COMPLETE one, which is what a
        reader coming to a sales report actually wants to see first; the
        current month is always one click away on the Month control.

        Still a calendar answer rather than "the newest month with sales",
        which is what this replaced long ago: that opened on a different month
        depending on how far behind invoicing was, and cost a scan of the facts
        to work out. This costs nothing and gives everyone the same month.

        context_today, not date.today(): the server may run well away from the
        user's timezone, and rolling a day early would step the whole board
        back an extra month for the first few hours of every month.
        """
        today = fields.Date.context_today(request.env.user)
        return (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)

    # ------------------------------------------------------------------
    # narratives
    #
    # Every panel gets a MULTI-LINE analysis rather than the one leader
    # sentence this board started with: one line per angle — mix and
    # concentration, target, year-on-year, and the tail — and each line is
    # dropped entirely when the data behind it is missing. That last part
    # matters more here than on the bidata boards: picking a Salesman blanks
    # the budget (see _budget_reliable), and a target sentence reading "0% of
    # a 0.0M target" is worse than no target sentence at all.
    #
    # One output line == one <p> in the .narrative panel (narrativeHtml in
    # sales_mail_sman_dashboard.js splits blocks on newlines) and one
    # paragraph in the PPTX notes sidebar, whose text frame is
    # TEXT_TO_FIT_SHAPE — so length costs nothing on either surface. Figures
    # are left unmarked here; _pptx_marked_text bolds them on the way out.
    # ------------------------------------------------------------------
    @staticmethod
    def _ngrowth(now, before):
        """% change against a prior figure, or None when there is no base to
        compare with — which is what every caller tests before writing its
        clause, rather than printing a meaningless 0%."""
        return ((now - before) / before * 100) if before else None

    def _narr_breakdown(self, rows, dim_label, value_key='sales',
                        budget_key='budget', prev_key='prevYearSales'):
        """Commentary on one category breakdown, in up to four lines.

        The rows are whatever the chart on that page draws, so the numbers
        quoted here always tally with the bars beside them — including the
        zero-filled categories, which is exactly why the tail line calls out
        who recorded nothing rather than silently ignoring them.
        """
        rows = [r for r in rows if r.get(value_key) is not None and r.get('label') != 'Total']
        if not rows:
            return "No data available for %s." % dim_label
        fmt = _pfmt_m if value_key in ('sales', 'prevYearSales') else _pfmt
        unit = '' if value_key in ('sales', 'prevYearSales') else ' units'
        val = lambda r: r.get(value_key) or 0
        ranked = sorted(rows, key=val, reverse=True)
        active = [r for r in ranked if val(r) > 0]
        total = sum(val(r) for r in ranked)
        lines = []

        # -- 1. who leads, and how concentrated the mix is ----------------
        if active:
            top = active[0]
            s = ("%s leads %s at %s%s, %s of the %s%s shown"
                 % (top['label'], dim_label, fmt(val(top)), unit,
                    _pshare(val(top), total), fmt(total), unit))
            if len(active) > 3:
                top3 = sum(val(r) for r in active[:3])
                s += ("; %s together hold %s of it"
                      % (_plist([r['label'] for r in active[:3]]), _pshare(top3, total)))
                # Only worth naming the remainder when it survives rounding —
                # "leaving 0% to be split between the other 6" is noise.
                rest = round((total - top3) / total * 100) if total else 0
                if rest:
                    s += (", leaving %s to be split between the other %d"
                          % (_pshare(total - top3, total), len(active) - 3))
            elif len(active) > 1:
                s += ", ahead of %s at %s%s" % (active[1]['label'], fmt(val(active[1])), unit)
            lines.append(s + ".")
        else:
            lines.append("No %s recorded any activity in this period." % dim_label)

        # -- 2. against target -------------------------------------------
        with_budget = [r for r in ranked if r.get(budget_key)]
        if with_budget:
            plan = sum(r.get(budget_key) or 0 for r in with_budget)
            done = sum(val(r) for r in with_budget)
            ahead = [r for r in with_budget if val(r) >= (r.get(budget_key) or 0)]
            worst = min(with_budget, key=lambda r: val(r) - (r.get(budget_key) or 0))
            short = (worst.get(budget_key) or 0) - val(worst)
            if len(with_budget) == 1:
                # The whole plan sits on one category, so the group sentence and
                # the widest-gap sentence would say the same thing twice.
                only = with_budget[0]
                s = ("%s is the only one carrying a target: %s%s against %s%s, %.0f%% — %s by %s%s"
                     % (only['label'], fmt(val(only)), unit, fmt(plan), unit,
                        done / plan * 100 if plan else 0,
                        'short' if short > 0 else 'ahead', fmt(abs(short)), unit))
            else:
                s = ("Against target, %d of the %d carrying a plan are at or above it and the "
                     "group sits at %.0f%% overall (%s%s against %s%s)"
                     % (len(ahead), len(with_budget), done / plan * 100 if plan else 0,
                        fmt(done), unit, fmt(plan), unit))
                if short > 0:
                    s += ("; %s is the widest gap, %s%s short of its %s%s target (%.0f%%)"
                          % (worst['label'], fmt(short), unit, fmt(worst.get(budget_key)), unit,
                             val(worst) / worst[budget_key] * 100))
            lines.append(s + ".")

        # -- 3. against last year ----------------------------------------
        with_prev = [r for r in ranked if r.get(prev_key)]
        if with_prev:
            base = sum(r.get(prev_key) or 0 for r in with_prev)
            now = sum(val(r) for r in with_prev)
            change = self._ngrowth(now, base)
            s = ("Versus last year the comparable %s are %s %.0f%% (%s%s against %s%s)"
                 % (dim_label, 'up' if change >= 0 else 'down', abs(change),
                    fmt(now), unit, fmt(base), unit))
            growth = lambda r: self._ngrowth(val(r), r.get(prev_key)) or 0
            best, laggard = max(with_prev, key=growth), min(with_prev, key=growth)
            # Deliberately neutral: whole groups here are often down year on
            # year, and "led by X at -5%" reads as a contradiction.
            s += ", strongest %s at %+.0f%%" % (best['label'], growth(best))
            if laggard is not best:
                s += ", weakest %s at %+.0f%%" % (laggard['label'], growth(laggard))
            lines.append(s + ".")

        # -- 4. the tail --------------------------------------------------
        idle = [r for r in ranked if val(r) <= 0]
        if active and (len(active) > 1 or idle):
            bits = []
            if len(active) > 1:
                low = active[-1]
                bits.append("%s is the smallest contributor at %s%s (%s of the total)"
                            % (low['label'], fmt(val(low)), unit, _pshare(val(low), total)))
            if idle:
                bits.append("%s recorded nothing this period"
                            % _plist([r['label'] for r in idle]))
            lines.append(", and ".join(bits) + ".")

        return "\n".join(lines)

    def _narr_total_company(self, mtd_row, ytd_row):
        """Page 1: the month and the year read side by side.

        Value and volume are reported together on every line because they
        routinely disagree here — which is the point of the closing
        price-per-unit clause, the only place on the report that says whether
        growth came from selling more or from selling dearer.
        """
        if not mtd_row or not ytd_row:
            return "No data available."
        lines = []
        for row, label in ((mtd_row, 'This month'), (ytd_row, 'Year-to-date')):
            sales, qty = row.get('sales') or 0, row.get('qty') or 0
            plan, plan_qty = row.get('budget') or 0, row.get('budgetQty') or 0
            prev, prev_qty = row.get('prevYearSales') or 0, row.get('prevYearQty') or 0

            s = "%s: %s in value on %s units" % (label, _pfmt_m(sales), _pfmt(qty))
            if plan:
                gap = sales - plan
                s += (". That is %.0f%% of the %s target, %s by %s"
                      % (sales / plan * 100, _pfmt_m(plan),
                         'ahead' if gap >= 0 else 'short', _pfmt_m(abs(gap))))
            if plan_qty:
                s += ("%s volume reached %.0f%% of the %s-unit target"
                      % (';' if plan else '.', qty / plan_qty * 100, _pfmt(plan_qty)))
            lines.append(s + ".")

            moves = []
            change = self._ngrowth(sales, prev)
            if change is not None:
                moves.append("value %s %.0f%% on %s"
                             % ('up' if change >= 0 else 'down', abs(change), _pfmt_m(prev)))
            change_qty = self._ngrowth(qty, prev_qty)
            if change_qty is not None:
                moves.append("volume %s %.0f%% on %s units"
                             % ('up' if change_qty >= 0 else 'down', abs(change_qty), _pfmt(prev_qty)))
            if moves:
                s = "%s versus last year: %s" % (label, " and ".join(moves))
                if qty and prev_qty and sales and prev:
                    asp, asp_prev = sales / qty, prev / prev_qty
                    drift = self._ngrowth(asp, asp_prev)
                    s += (", at %s per unit against %s — average realised value %s %.0f%%"
                          % (_pfmt(asp), _pfmt(asp_prev),
                             'up' if drift >= 0 else 'down', abs(drift)))
                lines.append(s + ".")

        # -- how the month sits inside the year ---------------------------
        ytd_sales, ytd_qty = ytd_row.get('sales') or 0, ytd_row.get('qty') or 0
        if ytd_sales:
            s = ("The month carries %s of the year-to-date value and %s of its units"
                 % (_pshare(mtd_row.get('sales') or 0, ytd_sales),
                    _pshare(mtd_row.get('qty') or 0, ytd_qty)))
            mtd_plan, ytd_plan = mtd_row.get('budget') or 0, ytd_row.get('budget') or 0
            if mtd_plan and ytd_plan:
                mtd_achv = (mtd_row.get('sales') or 0) / mtd_plan * 100
                ytd_achv = ytd_sales / ytd_plan * 100
                s += (", and is running %s the year-to-date pace against target (%.0f%% vs %.0f%%)"
                      % ('ahead of' if mtd_achv >= ytd_achv else 'behind', mtd_achv, ytd_achv))
            lines.append(s + ".")
        return "\n".join(lines)

    def _narr_quarterly(self, rows, dim_label, through_label=None):
        """Pages 3/4/5: the quarterly bars, read as a sequence.

        `through_label` is the selected month, and the caveat it drives is not
        cosmetic — _by_quarter caps This-Year actuals at that month while
        Target and Last Year stay full-quarter, so the newest quarter's bars
        are not like for like and a momentum read on them would be wrong.
        """
        rows = [r for r in rows
                if (r.get('sales') or r.get('budget') or r.get('prevYearSales'))]
        if not rows:
            return "No data available for %s." % dim_label
        lines = []
        total = sum(r.get('sales') or 0 for r in rows)
        total_qty = sum(r.get('qty') or 0 for r in rows)

        # -- 1. the shape of the year -------------------------------------
        split = ", ".join("%s %s (%s)" % (r['label'], _pfmt_m(r.get('sales') or 0),
                                          _pshare(r.get('sales') or 0, total))
                          for r in rows)
        lines.append("%s: %s booked on %s units so far — %s."
                     % (dim_label, _pfmt_m(total), _pfmt(total_qty), split))

        # -- 2. peak and momentum -----------------------------------------
        best = max(rows, key=lambda r: r.get('sales') or 0)
        s = "%s is the strongest quarter at %s" % (best['label'], _pfmt_m(best.get('sales') or 0))
        if len(rows) > 1:
            latest, before = rows[-1], rows[-2]
            step = self._ngrowth(latest.get('sales') or 0, before.get('sales') or 0)
            if step is not None:
                s += ("; %s is tracking %s %.0f%% on %s (%s against %s)"
                      % (latest['label'], 'up' if step >= 0 else 'down', abs(step),
                         before['label'], _pfmt_m(latest.get('sales') or 0),
                         _pfmt_m(before.get('sales') or 0)))
                if through_label:
                    s += (", counted only through %s while its target and last-year bars "
                          "cover the full quarter" % through_label)
        lines.append(s + ".")

        # -- 3. against target --------------------------------------------
        with_budget = [r for r in rows if r.get('budget')]
        if with_budget:
            plan = sum(r['budget'] for r in with_budget)
            done = sum(r.get('sales') or 0 for r in with_budget)
            hit = [r for r in with_budget if (r.get('sales') or 0) >= r['budget']]
            s = ("Against target, %d of %d quarters landed at or above plan and the run "
                 "stands at %.0f%% (%s against %s)"
                 % (len(hit), len(with_budget), done / plan * 100 if plan else 0,
                    _pfmt_m(done), _pfmt_m(plan)))
            worst = min(with_budget, key=lambda r: (r.get('sales') or 0) - r['budget'])
            gap = worst['budget'] - (worst.get('sales') or 0)
            if gap > 0:
                s += "; %s is the widest gap at %s short" % (worst['label'], _pfmt_m(gap))
            lines.append(s + ".")

        # -- 4. against last year ------------------------------------------
        with_prev = [r for r in rows if r.get('prevYearSales')]
        if with_prev:
            base = sum(r['prevYearSales'] for r in with_prev)
            now = sum(r.get('sales') or 0 for r in with_prev)
            change = self._ngrowth(now, base)
            s = ("Versus last year the same quarters are %s %.0f%% (%s against %s)"
                 % ('up' if change >= 0 else 'down', abs(change), _pfmt_m(now), _pfmt_m(base)))
            growth = lambda r: self._ngrowth(r.get('sales') or 0, r.get('prevYearSales')) or 0
            strongest, weakest = max(with_prev, key=growth), min(with_prev, key=growth)
            if strongest is not weakest:
                s += (", strongest in %s at %+.0f%% and weakest in %s at %+.0f%%"
                      % (strongest['label'], growth(strongest),
                         weakest['label'], growth(weakest)))
            lines.append(s + ".")

        return "\n".join(lines)

    def _combined_narrative(self, narratives, base_key, labels):
        parts = ["%s\n%s" % ((label or slug).upper(), narratives['%s_%s' % (base_key, slug)])
                 for slug, label in labels.items() if narratives.get('%s_%s' % (base_key, slug))]
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # bundle
    # ------------------------------------------------------------------
    def _tabs(self, rows, slugs):
        """Turn a breakdown into the toggle row with valid rows where chart values > 0.

        Tabs with 0 or empty values are excluded, so only active categories with
        positive values are shown.
        """
        picked = [r for r in rows if r.get('label') != 'Total' and ((r.get('sales') or 0) > 0 or (r.get('qty') or 0) > 0)][:len(slugs)]
        tabs = []
        for i, r in enumerate(picked):
            tabs.append({'v': slugs[i], 'l': r['label'], 'code': r['code']})
        return tabs

    @staticmethod
    def _quarter_tabs(month):
        """Q1 through the quarter holding the selected month, as a toggle row.

        Short by design rather than padded to four: an unpadded slug simply
        has no button and no printed page, where a "--" tab would offer the
        reader a quarter that has not happened. The four REFS still exist in
        the template -- the component skips the ones whose panel is not
        rendered -- so the slugs stay fixed the way CLASS_SLUGS and
        REGION_SLUGS are.
        """
        current_q = (month - 1) // 3 + 1
        return [{'v': QUARTER_SLUGS[q - 1], 'l': 'Q%d' % q, 'code': q}
                for q in range(1, current_q + 1)]

    @staticmethod
    def _top_named(rows):
        """The largest REAL category, and its label.

        Skips the Unassigned bucket deliberately. Unassigned is a legitimate,
        drillable slice everywhere else on this report, but it is the wrong
        thing for the four pages that are ABOUT one category: on the product
        side it is not merely uninformative but empty by construction — a row
        with no Main Category has no Sub Category either, so page 12 filtered
        to Unassigned can only ever draw one bar labelled Unassigned.

        Under the AC-product-group scope this is no longer the common case it
        was: scoping on product_category.code at depth 2 means every in-scope
        row HAS a depth-2 category, and all of those chain through to a main
        category -- 0 of 34,218 rows for 2025 and 0 of 12,421 for 2026 come
        back Unassigned at l7, where under the old catalogflags-'10' scope
        12,789 of 2026's 22,534 lines carried no product category at all and
        Unassigned was the single largest bucket by value. The guard stays: it
        costs nothing, and a category that stops resolving would put these four
        pages straight back into that state.
        """
        for r in rows or []:
            if r.get('label') == 'Total' or r.get('code') == UNASSIGNED:
                continue
            return r['code'], r['label']
        return None, '—'

    def _fetch_bundle(self, year, month, salesman, sub_mode,
                      scope=DEFAULT_SCOPE, selection=None):
        # SET LOCAL scopes to this transaction only. Postgres JIT-compiles
        # these multi-FILTER aggregates and then spends more time generating
        # code than scanning — the same finding as sales_kpi_main.py and
        # sales_sman_main.py, and with ~30 such queries here it dominates.
        request.env.cr.execute("SET LOCAL jit = off")
        self._build_fact(sub_mode, year, salesman, scope, selection)

        # hasBudget is the ONE switch every page consults, and it is false both
        # when there is no budget at all and when the current scope makes the
        # budget meaningless — a salesman selection, above all. Folding the two
        # into one flag is deliberate: seventeen pages each deciding for
        # themselves is seventeen chances for a tile and the bars beneath it to
        # disagree about whether a target exists.
        budget_ok = self._budget_available() and self._budget_reliable(salesman)
        ctx = {'year': year, 'month': month, 'franchise': FRANCHISE,
               'salesman': salesman, 'subMode': sub_mode,
               'hasBudget': budget_ok}
        month_label = "%s %s" % (MONTH_NAMES[month - 1], year)
        quarter = (month - 1) // 3 + 1

        # -- KPI tiles ---------------------------------------------------
        mtd = self._safe('kpi.mtd', lambda: self._sums_ty_ly(ctx, 'month'), self._row('x', ''))
        ytd = self._safe('kpi.ytd', lambda: self._sums_ty_ly(ctx, 'ytd'), self._row('x', ''))
        kpis = {
            'mtdThisYear': mtd['sales'], 'mtdTarget': mtd['budget'], 'mtdLastYear': mtd['prevYearSales'],
            'mtdQtyThisYear': mtd['qty'], 'mtdQtyTarget': mtd['budgetQty'], 'mtdQtyLastYear': mtd['prevYearQty'],
            'ytdThisYear': ytd['sales'], 'ytdTarget': ytd['budget'], 'ytdLastYear': ytd['prevYearSales'],
            'ytdQtyThisYear': ytd['qty'], 'ytdQtyTarget': ytd['budgetQty'], 'ytdQtyLastYear': ytd['prevYearQty'],
        }

        # -- the categories every "hardcoded" page resolves to ------------
        # Page 1's tiles are company-wide; these decide what pages 5, 12, 15,
        # 16 and 17 are ABOUT. Computed from YTD actuals so the report always
        # leads with whatever is actually largest this year.
        stg_ytd = self._safe('saleTypeGroups.ytd', lambda: self._breakdown(ctx, 'ytd', 'salesTypeGroup'), [])
        class_ytd = self._safe('classifications.ytd', lambda: self._breakdown(ctx, 'ytd', 'classification'), [])
        region_ytd = self._safe('regions.ytd', lambda: self._breakdown(ctx, 'ytd', 'region'), [])
        maincat_ytd = self._safe('mainCategories.ytd', lambda: self._breakdown(ctx, 'ytd', 'mainCategory'), [])
        prodgroup_ytd = self._safe('prodgroup.ytd', lambda: self._breakdown(ctx, 'ytd', 'productGroup'), [])

        class_tabs = self._tabs(stg_ytd, CLASS_SLUGS)
        region_tabs = self._tabs(region_ytd, REGION_SLUGS)
        quarter_tabs = self._quarter_tabs(month)
        top_class, top_class_label = self._top_named(class_ytd)
        top_stg, top_stg_label = self._top_named(stg_ytd)
        top_maincat, top_maincat_label = self._top_named(maincat_ytd)
        class_filter = [('classification', top_class)] if top_class is not None else []
        # Pages 2, 5, 13, 14, 15, 16 and 17 are ABOUT customer groupings, and
        # use the Sales Type Group -- which is what "department" means on these
        # boards. Partner Classification leaves SAR 43.4m of 2026 in an
        # Unassigned bucket that _top_named has to skip and carries 0 targets on
        # top categories in 2026; l1 has no such bucket and its target ties to
        # the riyal across all pages. See BUDGET_LEVEL_SPEC.
        #
        # A customer-side tier was tried here and removed -- see OPENING_LEVEL
        # in sales_sman_main. It matched the client's own report bar for bar,
        # but it claimed the word "department" for a different taxonomy from the
        # one the boards already used it for.
        stg_filter = [('salesTypeGroup', top_stg)] if top_stg is not None else []
        maincat_filter = [('mainCategory', top_maincat)] if top_maincat is not None else []

        class_codes = [t['code'] for t in class_tabs]
        region_codes = [t['code'] for t in region_tabs]
        # Zero-fill sets are the FULL category list, not the four toggle tabs.
        # A subset here would quietly drop bars, and the bars on these pages
        # have to keep adding up to the KPI tile above them.
        #
        # UNASSIGNED IS NOT ZERO-FILLED. It is not a category, it is the
        # residue of rows whose category did not resolve, and zero-filling it
        # put an empty bar on every tab that had none — three of page 15's four
        # regions drew a 0/0/0 "Unassigned" beside RAC and MBT, and
        # _narr_breakdown then named it as a contributor. It still draws
        # wherever it carries real money, because that is a number the reader
        # has to see; it just no longer draws where it carries nothing.
        def _fill(rows):
            return [(r['code'], r['label']) for r in rows if r['code'] != UNASSIGNED]

        stg_fixed = _fill(stg_ytd)
        class_fixed = _fill(class_ytd)
        region_fixed = _fill(region_ytd)
        maincat_fixed = _fill(maincat_ytd)
        prodgroup_fixed = _fill(prodgroup_ytd)

        def by_tab(result, tabs):
            """{slug: rows} from the {code: rows} a _multi call returns —
            padded slugs have no code and get an empty list."""
            return {t['v']: (result.get(t['code']) or result.get(str(t['code'])) or []) if t['code'] is not None else []
                    for t in tabs}

        def by_quarter_tab(result):
            """{slug: rows} from the {quarter number: rows} _by_quarter_level
            returns."""
            return {t['v']: result.get(t['code'], []) for t in quarter_tabs}

        # -- Page 1: total company ---------------------------------------
        total_company = {'mtd': [mtd], 'ytd': [ytd]}

        # -- Page 2: sales type group & region performance trends --------
        class_trend = self._safe('class_trend', lambda: self._with_pct(
            self._append_total_row(list(stg_ytd))), [])
        region_trend = self._safe('region_trend', lambda: self._with_pct(
            self._append_total_row(self._breakdown(ctx, 'ytd', 'region',
                                                   fixed_codes=region_fixed or None))), [])

        # -- Page 3/4/5: quarterly progression ---------------------------
        # Page 3 keeps the quarter on the x-axis: it is the company's own
        # sequence, and there is nothing to break it down by. Pages 4 and 5
        # turn it round -- the QUARTER is the tab, the categories are the bars
        # -- so one panel answers "who sold what in Q2" instead of asking the
        # reader to open four tabs and hold four charts in their head. See
        # _by_quarter_level.
        quarterly_company = self._safe('quarterly_company', lambda: self._by_quarter(ctx), [])
        quarterly_stg = self._safe('quarterly_saletypegroup', lambda: by_quarter_tab(
            self._by_quarter_level(ctx, 'salesTypeGroup',
                                   fixed_codes=stg_fixed or None)),
            {t['v']: [] for t in quarter_tabs})
        quarterly_region = self._safe('quarterly_region', lambda: by_quarter_tab(
            self._by_quarter_level(ctx, 'region',
                                   fixed_codes=region_fixed or None)),
            {t['v']: [] for t in quarter_tabs})

        # -- Pages 6-9: product categories -------------------------------
        main_categories = {
            'mtd': self._safe('mainCategories.mtd', lambda: self._breakdown(
                ctx, 'month', 'productGroup', fixed_codes=prodgroup_fixed or None), []),
            'ytd': prodgroup_ytd,
        }
        acwtsplit_code = None
        for r in prodgroup_ytd or []:
            c = str(r.get('code') or '').upper().replace(' ', '').replace('-', '')
            l = str(r.get('label') or '').upper().replace(' ', '').replace('-', '')
            # Match the product group whose product_category.code is 'ACWTS'
            # (AC Window & Split). The code stored in l9_code is the numeric DB
            # id whose product_category.code value is 'ACWTS', so we check
            # both 'ACWTSPLIT' (legacy / label-embedded) and 'ACWTS' (the real
            # code).  Also catch label variants: "Window & Split" / "Window and
            # Split" both normalise to contain WINDOW and SPLIT.
            if ('ACWTSPLIT' in c or 'ACWTSPLIT' in l or
                    'ACWTS' in c or 'ACWTS' in l or
                    ('WINDOW' in l and 'SPLIT' in l) or
                    'SPLIT' in l or 'SPLIT' in c):
                acwtsplit_code = r['code']
                break
        if acwtsplit_code is None:
            acwtsplit_code = 'ACWTS'

        acwtsplit_filter = [('productGroup', acwtsplit_code)]
        # BY FAMILY, NOT BY SUB-GROUP. product.category splits a split AC into
        # its indoor and outdoor halves, so this page used to draw ELITE twice
        # -- ELITE INDOOR R410 and ELITE OUTDOOR R410 as separate bars -- where
        # the client's own page shows one ELITE. The family tier merges them
        # (see product.family), and the page now reads bar for bar against the
        # deck: ELITE 124,264,547, MISSION XTREME 61,963,502, SUPERCOOL
        # 43,365,733, OLYMPUS 38,567,758, BIG CAPACITY 30,011,729.
        subcats_top8 = self._safe('subcats_top8', lambda: self._breakdown(
            ctx, 'ytd', 'productSubGroup', filters=acwtsplit_filter, limit=10), [])

        # -- Pages 10-11: sales type groups ------------------------------
        # Was Partner Classification. The two pages are the customer-side
        # counterpart of pages 6/9 (product side), and the Sales Type Group is
        # the level that grouping is captured and budgeted at -- so these bars
        # now tie to the Target tile above them at every code, and the SAR
        # 43.4m Unassigned slice classification carried is gone.
        sale_type_groups = {
            'mtd': self._safe('saleTypeGroups.mtd', lambda: self._breakdown(
                ctx, 'month', 'salesTypeGroup', fixed_codes=stg_fixed or None), []),
            'ytd': [r for r in stg_ytd if r.get('label') != 'Total'],
        }

        # -- Page 6 right-side & Page 12: productGroup breakdown for LCAC items (VRF, Concealed, Cassette, Package, Free Stand)
        lcac_subcats_mtd = self._safe('lcacSubcats.mtd', lambda: self._breakdown(
            ctx, 'month', 'productGroup'), [])
        lcac_subcats_ytd = self._safe('lcacSubcats.ytd', lambda: self._breakdown(
            ctx, 'ytd', 'productGroup'), [])

        is_lcac_group = lambda d: any(k in str(d.get('label','')).lower() for k in ('cassette', 'concealed', 'vrf', 'package', 'stand', 'floor'))

        def _clean_lcac_items(rows):
            cleaned = []
            for r in rows:
                if is_lcac_group(r):
                    item = dict(r)
                    lbl = str(item.get('label') or '')
                    if 'floor' in lbl.lower() or 'stand' in lbl.lower():
                        item['label'] = 'Free Stand'
                    elif 'package' in lbl.lower():
                        item['label'] = 'Package'
                    cleaned.append(item)
            return cleaned

        filtered_mtd = _clean_lcac_items(lcac_subcats_mtd)
        filtered_ytd = _clean_lcac_items(lcac_subcats_ytd)

        lcac_subcats = {
            'mtd': filtered_mtd if filtered_mtd else lcac_subcats_mtd,
            'ytd': filtered_ytd if filtered_ytd else lcac_subcats_ytd,
        }

        topcat_subcats = {
            'mtd': filtered_mtd if filtered_mtd else lcac_subcats_mtd,
            'ytd': filtered_ytd if filtered_ytd else lcac_subcats_ytd,
        }

        # -- Pages 13-14: by sales type group (toggle) -------------------
        # class_codes are the tabs off stg_ytd, so the level MUST be the one
        # stg_ytd was broken down by -- filtering one level's codes against
        # another's ids empties both pages.
        top3_by_class = self._safe('top3_by_class', lambda: by_tab(
            self._breakdown_multi(ctx, 'ytd', 'salesTypeGroup',
                                  [c for c in class_codes if c is not None],
                                  'productGroup', limit=8), class_tabs),
            {t['v']: [] for t in class_tabs})
        regions_by_class = self._safe('regions_by_class', lambda: by_tab(
            self._breakdown_multi(ctx, 'ytd', 'salesTypeGroup',
                                  [c for c in class_codes if c is not None],
                                  'region', fixed_codes=region_fixed or None), class_tabs),
            {t['v']: [] for t in class_tabs})

        # -- Pages 15: Dealers by region — sub-categories / product groups (windows, split & LCAC) -
        dealers_code = next((r['code'] for r in stg_ytd if r.get('label') and 'dealer' in str(r['label']).lower()), None)
        dealers_filter = [('salesTypeGroup', dealers_code)] if dealers_code is not None else []

        raw_stg_region_subcats_l8 = self._safe('stg_region_subcats_l8', lambda: by_tab(
            self._breakdown_multi(ctx, 'ytd', 'region',
                                  [c for c in region_codes if c is not None],
                                  'subCategory',
                                  filters=dealers_filter), region_tabs),
            {t['v']: [] for t in region_tabs})

        raw_stg_region_pg_l9 = self._safe('stg_region_pg_l9', lambda: by_tab(
            self._breakdown_multi(ctx, 'ytd', 'region',
                                  [c for c in region_codes if c is not None],
                                  'productGroup',
                                  filters=dealers_filter), region_tabs),
            {t['v']: [] for t in region_tabs})

        is_ws_p15 = lambda d: d.get('code') in ('Window', 'Split', 'ACWIN', 'ACSPL') or any(k in str(d.get('label','')).lower() for k in ('window', 'split'))
        is_lcac_p15 = lambda d: any(k in str(d.get('label','')).lower() for k in ('cassette', 'concealed', 'vrf', 'package', 'stand', 'floor', 'lcac'))

        def _clean_and_combine_region_cats(subcat_rows, pg_rows):
            combined = {}
            for r in pg_rows:
                lbl = str(r.get('label') or '')
                if is_ws_p15(r):
                    item = dict(r)
                    norm_lbl = item.get('label') or ''
                    if 'window' in lbl.lower():
                        norm_lbl = 'Window'
                    elif 'split' in lbl.lower():
                        norm_lbl = 'Split'

                    if norm_lbl in combined:
                        c = combined[norm_lbl]
                        c['sales'] += item.get('sales', 0)
                        c['qty'] += item.get('qty', 0)
                        c['prevYearSales'] += item.get('prevYearSales', 0)
                        c['prevYearQty'] += item.get('prevYearQty', 0)
                        c['budget'] += item.get('budget', 0)
                        c['budgetQty'] += item.get('budgetQty', 0)
                    else:
                        item['label'] = norm_lbl
                        combined[norm_lbl] = item

            for r in subcat_rows:
                lbl = str(r.get('label') or '')
                if is_lcac_p15(r) or 'lcac' in lbl.lower():
                    item = dict(r)
                    norm_lbl = item.get('label') or ''
                    if 'floor' in lbl.lower() or 'stand' in lbl.lower():
                        norm_lbl = 'Free Stand'
                    elif 'package' in lbl.lower():
                        norm_lbl = 'Package'
                    elif 'lcac' in lbl.lower():
                        norm_lbl = 'LCAC'

                    if norm_lbl in combined:
                        c = combined[norm_lbl]
                        c['sales'] += item.get('sales', 0)
                        c['qty'] += item.get('qty', 0)
                        c['prevYearSales'] += item.get('prevYearSales', 0)
                        c['prevYearQty'] += item.get('prevYearQty', 0)
                        c['budget'] += item.get('budget', 0)
                        c['budgetQty'] += item.get('budgetQty', 0)
                    else:
                        item['label'] = norm_lbl
                        combined[norm_lbl] = item
                elif not is_ws_p15(r):
                    item = dict(r)
                    norm_lbl = item.get('label') or ''
                    if norm_lbl not in combined:
                        combined[norm_lbl] = item

            res = list(combined.values())
            if not res:
                all_rows = pg_rows + subcat_rows
                for r in all_rows:
                    lbl = str(r.get('label') or '')
                    item = dict(r)
                    norm_lbl = item.get('label') or ''
                    if norm_lbl not in combined:
                        combined[norm_lbl] = item
                res = list(combined.values())
            res.sort(key=lambda x: x.get('sales', 0), reverse=True)
            return res

        stg_region_maincats = {
            t['v']: _clean_and_combine_region_cats(
                raw_stg_region_subcats_l8.get(t['v'], []),
                raw_stg_region_pg_l9.get(t['v'], [])
            )
            for t in region_tabs
        }
        stg_region_subcats = self._safe('stg_region_subcats', lambda: by_tab(
            self._breakdown_multi(ctx, 'ytd', 'region',
                                  [c for c in region_codes if c is not None],
                                  'productSubGroup',
                                  filters=dealers_filter + [('productGroup', acwtsplit_code)],
                                  limit=8), region_tabs),
            {t['v']: [] for t in region_tabs})

        # -- Page 17: product sub-groups of Projects sales type group (top 10) -----
        projects_code = next((r['code'] for r in stg_ytd if r.get('label') and 'project' in str(r['label']).lower()), None)
        projects_filter = [('salesTypeGroup', projects_code)] if projects_code is not None else stg_filter
        stg_productgroups = self._safe('stg_productgroups', lambda: self._breakdown(
            ctx, 'ytd', 'productSubGroup', filters=projects_filter, limit=10), [])

        bundle = {
            'period': {'year': year, 'month': month, 'monthName': MONTH_NAMES[month - 1],
                       'label': month_label, 'quarter': quarter,
                       'quarterLabel': 'Q%d %s' % (quarter, year)},
            'hasPrevYear': True,
            'hasBudget': ctx['hasBudget'],
            'budgetReliable': ctx['hasBudget'],
            # So the client can say WHY the target is dark instead of leaving a
            # blank the reader has to guess at.
            'budgetHiddenBy': ('Salesman' if (salesman and salesman != 'all' and not ctx['hasBudget'])
                               else None),
            'scope': scope if scope in SCOPES else DEFAULT_SCOPE,
            'kpis': kpis,
            'classTabs': class_tabs,
            'regionTabs': region_tabs,
            'quarterTabs': quarter_tabs,
            'topClassLabel': top_class_label,
            'topSaleTypeGroupLabel': top_stg_label,
            'topMainCategoryLabel': top_maincat_label,
            'franchise': FRANCHISE,
            'salesman': salesman,
            'subCategoryMode': sub_mode,
            'totalCompany': total_company,
            'classTrend': class_trend,
            'regionTrend': region_trend,
            'quarterlyCompany': quarterly_company,
            'quarterlySaleTypeGroup': quarterly_stg,
            'quarterlyRegion': quarterly_region,
            'mainCategories': main_categories,
            'subcatsTop8': subcats_top8,
            'saleTypeGroups': sale_type_groups,
            'topcatSubcats': topcat_subcats,
            'lcacSubcats': lcac_subcats,
            'top3ByClass': top3_by_class,
            'regionsByClass': regions_by_class,
            'stgRegionMaincats': stg_region_maincats,
            'stgRegionSubcats': stg_region_subcats,
            'stgProductgroups': stg_productgroups,
        }

        class_labels = {t['v']: t['l'] for t in class_tabs}
        region_labels = {t['v']: t['l'] for t in region_tabs}
        quarter_labels = {t['v']: t['l'] for t in quarter_tabs}
        prodgroup_ytd_all = main_categories['ytd']
        is_ws = lambda d: d.get('code') in ('Window', 'Split', 'ACWIN', 'ACSPL') or any(k in str(d.get('label','')).lower() for k in ('window', 'split'))
        ytd_ws = [d for d in prodgroup_ytd_all if is_ws(d)] or prodgroup_ytd_all[:2]
        sub_ytd = lcac_subcats.get('ytd') or topcat_subcats.get('ytd') or []
        ytd_lc = [d for d in sub_ytd if not is_ws(d)] or sub_ytd or [d for d in prodgroup_ytd_all if not is_ws(d)]
        grouped_maincats_ytd = ytd_ws + ytd_lc

        narratives = {
            'total-company': self._narr_total_company(mtd, ytd),
            'class-region-trends': self._narr_breakdown(class_trend, 'sales type groups') + "\n" +
                                   self._narr_breakdown(region_trend, 'regions'),
            'quarterly-company': self._narr_quarterly(quarterly_company, 'The company',
                                                      through_label=month_label),
            'main-categories': self._narr_breakdown(main_categories['ytd'], 'product groups'),
            'subcats-top8': self._narr_breakdown(subcats_top8, 'Split product sub-groups'),
            'subcats-distribution': self._narr_breakdown(subcats_top8, 'Split product sub-groups'),
            'maincats-distribution': self._narr_breakdown(grouped_maincats_ytd, 'product groups'),
            'saletypegroups': self._narr_breakdown(sale_type_groups['ytd'], 'sales type groups'),
            'saletypegroups-distribution': self._narr_breakdown(sale_type_groups['ytd'], 'sales type groups'),
            'topcat-subcats': self._narr_breakdown(topcat_subcats['ytd'], 'LCAC product groups'),
            'stg-productgroups': self._narr_breakdown(stg_productgroups, 'product sub-groups'),
        }
        # Pages 4 and 5 read as a BREAKDOWN now, not as a sequence: each panel
        # is one quarter's categories, so _narr_quarterly -- which talks about
        # momentum from one bar to the next -- would be describing a set of
        # categories as if they were a timeline.
        for slug, label in quarter_labels.items():
            narratives['quarterly-saletypegroup_%s' % slug] = self._narr_breakdown(
                quarterly_stg.get(slug, []), 'sales type groups in %s' % label)
            narratives['quarterly-region_%s' % slug] = self._narr_breakdown(
                quarterly_region.get(slug, []), 'regions in %s' % label)
        for slug, label in class_labels.items():
            narratives['top3-by-class_%s' % slug] = self._narr_breakdown(
                top3_by_class.get(slug, []), 'product groups',
                value_key='qty', budget_key='budgetQty', prev_key='prevYearQty')
            narratives['regions-by-class_%s' % slug] = self._narr_breakdown(
                regions_by_class.get(slug, []), 'regions',
                value_key='qty', budget_key='budgetQty', prev_key='prevYearQty')
        for slug, label in region_labels.items():
            narratives['stg-region-maincats_%s' % slug] = self._narr_breakdown(
                stg_region_maincats.get(slug, []), 'product groups')
            narratives['stg-region-subcats_%s' % slug] = self._narr_breakdown(
                stg_region_subcats.get(slug, []), 'product sub-groups')

        # A combined key per toggle PAGE as well as per tab, so a section
        # whose note is written about the page as a whole has a baseline of
        # its own rather than borrowing the first tab's.
        for base, labels in (('quarterly-saletypegroup', quarter_labels),
                             ('quarterly-region', quarter_labels),
                             ('top3-by-class', class_labels),
                             ('regions-by-class', class_labels),
                             ('stg-region-maincats', region_labels),
                             ('stg-region-subcats', region_labels)):
            narratives[base] = self._combined_narrative(narratives, base, labels)

        # Plain text is what the PPTX sidebar builder expects (it marks
        # internally); the marked form is for on-screen display and as the
        # baseline import_notes diffs against. Marking twice would corrupt the
        # round-trip, so bundle['narratives'] is only ever marked here.
        bundle['narrativesPlain'] = narratives
        bundle['narratives'] = {k: _pptx_marked_text(v) for k, v in narratives.items()}
        return bundle

    # ------------------------------------------------------------------
    # notes
    # ------------------------------------------------------------------
    def _note_scope(self, period, franchise, salesman):
        """pbi.dashboard.note is keyed (key, year, franchise, customer_type,
        region) — reuse its spare customer_type column to carry the salesman,
        so notes written against one salesman's view never leak into
        another's."""
        return [('year', '=', period), ('franchise', '=', franchise),
                ('customer_type', '=', salesman or 'all'), ('region', '=', 'all')]

    # Two kinds of row share pbi.dashboard.note, told apart by the key alone:
    #
    #   sales_mail_sman_<section>            the note text shown in place of
    #                                        the computed narrative
    #   sales_mail_sman_req::<section>       the requirement written above it
    #                                        — what that section is meant to
    #                                        cover, an instruction to whoever
    #                                        writes the note next month
    #
    # A prefix rather than a new column on the shared model: pbi.dashboard.note
    # is owned by this module but read by every board that stores notes, and a
    # schema change would need a module upgrade on each database to add the
    # column. "::" cannot occur in a narrative key (they are slugs like
    # ``quarterly-saletypegroup_q1``), so the two namespaces cannot collide.
    NOTE_PREFIX = 'sales_mail_sman_'
    REQ_INFIX = 'req::'

    def _note_keys(self, key):
        """(note row key, requirement row key) for one narrative section."""
        return (self.NOTE_PREFIX + key, self.NOTE_PREFIX + self.REQ_INFIX + key)

    def _fetch_notes_map(self, period, franchise, salesman):
        """{section: text} for the note overrides only — requirement rows live
        under the same prefix and are filtered out here, so neither the board's
        narrative panels nor the PPTX export ever sees one."""
        notes = request.env['pbi.dashboard.note'].sudo().search(
            self._note_scope(period, franchise, salesman) + [('key', 'like', self.NOTE_PREFIX + '%')])
        head = len(self.NOTE_PREFIX)
        return {n.key[head:]: n.text for n in notes
                if not n.key[head:].startswith(self.REQ_INFIX)}

    def _fetch_requirements_map(self, period, franchise, salesman):
        """{section: text} for the requirement written above each note."""
        prefix = self.NOTE_PREFIX + self.REQ_INFIX
        notes = request.env['pbi.dashboard.note'].sudo().search(
            self._note_scope(period, franchise, salesman) + [('key', 'like', prefix + '%')])
        return {n.key[len(prefix):]: n.text for n in notes}

    # The requirement dropdown's own entries — the ones added from the board,
    # beside the predefined list the JS carries. They are NOT scoped to a
    # period or a salesman the way notes are: a house rule for what a section
    # must cover outlives the month it was first written in, so the row sits
    # on an all-'*' scope of its own, which no _note_scope search can match.
    # One row holding a JSON array rather than a row per entry: the list is
    # rewritten whole on every add and remove, so there are no orphan keys to
    # collect and no index to keep in step.
    PRESET_KEY = 'sales_mail_sman_reqpresets'
    PRESET_SCOPE = [('year', '=', '*'), ('franchise', '=', '*'),
                    ('customer_type', '=', '*'), ('region', '=', '*')]
    PRESET_MAX = 50
    PRESET_MAX_LEN = 500

    def _fetch_requirement_presets(self):
        row = request.env['pbi.dashboard.note'].sudo().search(
            self.PRESET_SCOPE + [('key', '=', self.PRESET_KEY)], limit=1)
        if not row:
            return []
        try:
            data = json.loads(row.text)
        except ValueError:
            _logger.warning("sales_mail_sman_main: requirement preset row is not JSON")
            return []
        return [x for x in data if isinstance(x, str) and x.strip()]

    @http.route('/pbi_dashboards/sales_mail_sman/requirement_presets', type='json', auth='user')
    def sales_mail_sman_requirement_presets(self, add=None, remove=None, **kw):
        """Add one entry to the requirement dropdown, or drop one, and return
        the list as it now stands. Called with neither, it just reads."""
        if not self._has_access():
            return {'error': 'You do not have access to this dashboard.'}
        presets = self._fetch_requirement_presets()
        add = (add or '').strip()[:self.PRESET_MAX_LEN]
        remove = (remove or '').strip()
        if remove:
            presets = [p for p in presets if p != remove]
        if add and add not in presets:
            # Oldest out first: the dropdown is a working list, not an archive,
            # and an unbounded one would eventually be unusable.
            presets = (presets + [add])[-self.PRESET_MAX:]
        if add or remove:
            self._write_note_row(self.PRESET_SCOPE, self.PRESET_KEY,
                                 json.dumps(presets) if presets else '',
                                 '*', '*', '*', region='*')
        return {'presets': presets}

    # ------------------------------------------------------------------
    # route
    # ------------------------------------------------------------------
    def _resolve(self, period, salesman, sub_mode, scope=DEFAULT_SCOPE):
        year = month = None
        if period:
            try:
                y, m = period.split('-')
                year, month = int(y), int(m)
            except (ValueError, AttributeError):
                year = month = None
        if year is None or month is None:
            year, month = self._default_period()
        sub_mode = 'manager' if sub_mode == 'manager' else 'regular'
        return year, month, FRANCHISE, (salesman or 'all'), sub_mode

    def _level_filter_options(self, selection, month):
        code_cols = [LEVEL_COLUMNS[lv][0] for lv in LEVELS]
        label_cols = [LEVEL_COLUMNS[lv][1] for lv in LEVELS]

        flags, flag_params = [], []
        for idx, level in enumerate(LEVELS):
            code = (selection or {}).get(level)
            if code in (None, "", "all"):
                flags.append("true")
            elif str(code) == UNASSIGNED:
                flags.append("f.%s IS NULL" % code_cols[idx])
            else:
                flags.append("f.%s = " % code_cols[idx] + "%s")
                flag_params.append(str(code))

        params = [month]

        carried = ", ".join("f.%s, f.%s" % (code_cols[i], label_cols[i])
                            for i in range(len(LEVELS)))
        picks = ", ".join("(%s) AS m%d" % (flags[i], i + 1)
                          for i in range(len(LEVELS)))
        misses = " + ".join("(NOT m%d)::int" % (i + 1)
                            for i in range(len(LEVELS)))

        branches = []
        for idx, level in enumerate(LEVELS):
            branches.append(
                "SELECT '{lv}' AS lvl, COALESCE({code}, ".format(
                    lv=level, code=code_cols[idx]) + "%s" +
                ") AS code, max({label}) AS label FROM scoped "
                "WHERE misses = 0 OR (misses = 1 AND NOT m{n}) "
                "GROUP BY 1, 2".format(label=label_cols[idx], n=idx + 1))

        sql = ("WITH matched AS (SELECT {carried}, {picks} "
               "FROM {fact} f WHERE f.mth <= %s AND f.part_no IS NOT NULL), "
               "scoped AS (SELECT matched.*, ({misses}) AS misses FROM matched) ".format(
                   carried=carried, picks=picks, misses=misses, fact=TEMP_FACT) +
               " UNION ALL ".join(branches) + " ORDER BY 1, 3")

        out = {level: [] for level in LEVELS}
        for row in self._query(sql, flag_params + params +
                               [UNASSIGNED] * len(LEVELS)):
            code = str(row["code"])
            out[row["lvl"]].append({
                "v": code,
                "l": row["label"] or (UNASSIGNED_LABEL if code == UNASSIGNED else code),
            })
        return out

    @http.route('/pbi_dashboards/sales_mail_sman/data', type='json', auth='user')
    def sales_mail_sman_data(self, period=None, salesman='all',
                             subCategoryMode='regular', scope=DEFAULT_SCOPE,
                             levelFilters=None, **kw):
        # **kw swallows `franchise`, which the board no longer sends -- see the
        # same note on sales_sman_main.sales_sman_data.
        if not self._has_access():
            return {'error': 'You do not have access to this dashboard.'}
        try:
            year, month, franchise, salesman, sub_mode = self._resolve(
                period, salesman, subCategoryMode, scope)
            selection = {lv: (levelFilters or {}).get(lv, 'all') for lv in LEVELS}
            bundle = self._fetch_bundle(year, month, salesman, sub_mode, scope, selection)
            bundle['notes'] = self._fetch_notes_map(
                "%s-%02d" % (year, month), franchise, salesman)
            bundle['requirements'] = self._fetch_requirements_map(
                "%s-%02d" % (year, month), franchise, salesman)
            bundle['requirementPresets'] = self._fetch_requirement_presets()
            bundle['yearOptions'] = self._year_options()
            bundle['salesmanOptions'] = self._salesman_options(year, scope)
            bundle['levelFilterOptions'] = self._level_filter_options(selection, month)
            # What the browser needs to know about this server's optional
            # packages, so a control it cannot serve renders disabled with a
            # message instead of failing when pressed.
            bundle['capabilities'] = optional_deps.capabilities()
            return bundle
        except Exception as e:
            _logger.exception("sales_mail_sman_main: data route failed")
            return {'error': str(e)}

    # ------------------------------------------------------------------
    # PPTX export — chart/slide rendering is reused wholesale from
    # sales_mail_main (see _PPTX); only the page list is ours.
    # ------------------------------------------------------------------
    def _pptx_tiles_slide(self, prs, layout, kpis, period_label, franchise, salesman_label):
        slide = prs.slides.add_slide(layout)
        tb = slide.shapes.add_textbox(Inches(0.4), Inches(0.2), Inches(12.5), Inches(0.55))
        p = tb.text_frame.paragraphs[0]
        p.text = "Sales Analysis with Salesman"
        p.font.size = Pt(28)
        p.font.bold = True
        franchise_label = ("All Franchises" if franchise == 'all'
                           else self._franchise_label(franchise))
        sub = slide.shapes.add_textbox(Inches(0.4), Inches(0.75), Inches(12.5), Inches(0.35))
        sub.text_frame.paragraphs[0].text = (
            "Source: transaction_header / transaction_details  ·  %s  ·  %s  ·  %s"
            % (franchise_label, salesman_label, period_label))
        sub.text_frame.paragraphs[0].font.size = Pt(13)

        def kpi_row(top, title, mtd, ytd, fmt_fn):
            htb = slide.shapes.add_textbox(Inches(PPTX_MARGIN), Inches(top), Inches(4), Inches(0.3))
            htb.text_frame.paragraphs[0].text = title
            htb.text_frame.paragraphs[0].font.bold = True
            htb.text_frame.paragraphs[0].font.size = Pt(15)
            tiles_top, tiles_h, gap = top + 0.35, 1.6, 0.15
            tiles = _PPTX._pptx_kpi_block(fmt_fn, *mtd, 'MTD') + _PPTX._pptx_kpi_block(fmt_fn, *ytd, 'YTD')
            w = (PPTX_FULL_W - (len(tiles) - 1) * gap) / len(tiles)
            for i, tile in enumerate(tiles):
                _PPTX._pptx_add_kpi_tile(slide, PPTX_MARGIN + i * (w + gap), tiles_top, w,
                                         tiles_h, tile, PPTX_TILE_COLORS[i % 3])
            return tiles_top + tiles_h

        next_top = kpi_row(1.3, "Value",
                           (kpis['mtdThisYear'], kpis['mtdTarget'], kpis['mtdLastYear']),
                           (kpis['ytdThisYear'], kpis['ytdTarget'], kpis['ytdLastYear']), _pfmt_m)
        kpi_row(next_top + 0.3, "Quantity",
                (kpis['mtdQtyThisYear'], kpis['mtdQtyTarget'], kpis['mtdQtyLastYear']),
                (kpis['ytdQtyThisYear'], kpis['ytdQtyTarget'], kpis['ytdQtyLastYear']), _pfmt)
        return slide

    def _build_pptx(self, year, month, franchise, salesman, sub_mode):
        bundle = self._fetch_bundle(year, month, salesman, sub_mode)
        narratives = bundle['narrativesPlain']
        notes_override = self._fetch_notes_map("%s-%02d" % (year, month), franchise, salesman)
        period_label = bundle['period']['label']
        class_tabs, region_tabs = bundle['classTabs'], bundle['regionTabs']
        quarter_tabs = bundle['quarterTabs']
        top_stg = bundle['topSaleTypeGroupLabel']
        top_maincat = bundle['topMainCategoryLabel']
        salesman_label = 'All Salesmen' if salesman == 'all' else next(
            (o['l'] for o in self._salesman_options(year) if o['v'] == salesman), salesman)

        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        blank = prs.slide_layouts[6]

        self._pptx_tiles_slide(prs, blank, bundle['kpis'], period_label, franchise, salesman_label)

        def page_slide(title, notes_key, specs, stacked=False):
            override = notes_override.get(notes_key)
            text, marked = (override, True) if override else (narratives.get(notes_key, ''), False)
            _PPTX._pptx_add_multi_chart_slide(prs, blank, title, text, specs, stacked=stacked,
                                              notes_already_marked=marked)

        prev_year = year - 1 if isinstance(year, int) else (int(year) - 1 if str(year).isdigit() else 'Last Year')
        value_series = [('budget', 'Target'), ('sales', 'A. %s' % year), ('prevYearSales', 'A. %s' % prev_year)]
        qty_series = [('budgetQty', 'Target'), ('qty', 'A. %s' % year), ('prevYearQty', 'A. %s' % prev_year)]
        trend_lines = [('achievementPct', 'Vs. Target', PPTX_LINE_ACHIEVEMENT),
                       ('yoyPct', 'Vs. %s' % prev_year, PPTX_LINE_YOY)]

        tc = bundle['totalCompany']
        page_slide("1. Total Company (%s)" % period_label, 'total-company', [
            bar(tc['mtd'], value_series, "%s - Value" % period_label),
            bar(qsort(tc['mtd']), qty_series, "%s - Quantity" % period_label),
            bar(tc['ytd'], value_series, "%s YTD - Value" % year),
            bar(qsort(tc['ytd']), qty_series, "%s YTD - Quantity" % year),
        ])

        # Four cells, not two: the Total sits beside its categories rather
        # than inside their chart, mirroring the web page's narrow Total slot
        # (see _split_total_row). The 2x2 grid reads left-to-right per row —
        # sales type groups above, regions below.
        class_rows, class_total = self._split_total_row(bundle['classTrend'])
        region_rows, region_total = self._split_total_row(bundle['regionTrend'])
        page_slide("2. Sales Type Group & Region Performance Trends (%s)" % period_label,
                   'class-region-trends', [
                       combo(class_rows, value_series, trend_lines, "By Sales Type Group"),
                       bar(class_total, value_series, "Total"),
                       combo(region_rows, value_series, trend_lines, "By Region — %s" % top_stg),
                       bar(region_total, value_series, "Total — %s" % top_stg),
                   ])

        page_slide("3. Quarterly Sales Progression — Company (%s)" % year, 'quarterly-company', [
            bar(bundle['quarterlyCompany'], value_series),
        ])

        for tab in quarter_tabs:
            page_slide("4. Sales Type Groups by Quarter (%s) — %s" % (year, tab['l']),
                       'quarterly-saletypegroup_%s' % tab['v'],
                       [bar(bundle['quarterlySaleTypeGroup'].get(tab['v'], []), value_series, tab['l'])])

        for tab in quarter_tabs:
            page_slide("5. Regions by Quarter — %s (%s) — %s" % (top_stg, year, tab['l']),
                       'quarterly-region_%s' % tab['v'],
                       [bar(bundle['quarterlyRegion'].get(tab['v'], []), value_series, tab['l'])])

        mc = bundle['mainCategories']
        page_slide("6. Main Categories (%s)" % period_label, 'main-categories', [
            bar(mc['mtd'], value_series, period_label),
            bar(mc['ytd'], value_series, "%s YTD" % year),
        ], stacked=True)

        page_slide("7. Split Product Sub-Groups — Top 10 (YTD %s)" % period_label, 'subcats-top8', [
            bar(bundle['subcatsTop8'], value_series, "Value"),
            bar(qsort(bundle['subcatsTop8']), qty_series, "Quantity"),
        ], stacked=True)

        page_slide("8. Split Product Sub-Groups Distribution — LY vs TY (Top 10, YTD %s)" % period_label,
                   'subcats-distribution', [
                       pie(bundle['subcatsTop8'], 'prevYearSales', "Last Year"),
                       pie(bundle['subcatsTop8'], 'sales', "This Year"),
                   ])

        prodgroup_ytd_pptx = mc['ytd']
        is_ws_pptx = lambda d: d.get('code') in ('Window', 'Split', 'ACWIN', 'ACSPL') or any(k in str(d.get('label','')).lower() for k in ('window', 'split'))
        ytd_ws_pptx = [d for d in prodgroup_ytd_pptx if is_ws_pptx(d)] or prodgroup_ytd_pptx[:2]
        sub_ytd_pptx = bundle.get('lcacSubcats', {}).get('ytd') or bundle.get('topcatSubcats', {}).get('ytd') or []
        ytd_lc_pptx = [d for d in sub_ytd_pptx if not is_ws_pptx(d)] or sub_ytd_pptx or [d for d in prodgroup_ytd_pptx if not is_ws_pptx(d)]
        grouped_maincats_ytd_pptx = ytd_ws_pptx + ytd_lc_pptx

        page_slide("9. Main Categories Distribution — LY vs TY (YTD %s)" % period_label,
                   'maincats-distribution', [
                       pie(grouped_maincats_ytd_pptx, 'prevYearSales', "Last Year"),
                       pie(grouped_maincats_ytd_pptx, 'sales', "This Year"),
                   ])

        stg = bundle['saleTypeGroups']
        page_slide("10. Sales Type Groups (%s)" % period_label, 'saletypegroups', [
            bar(stg['mtd'], value_series, "%s - Value" % period_label),
            bar(qsort(stg['mtd']), qty_series, "%s - Quantity" % period_label),
            bar(stg['ytd'], value_series, "%s YTD - Value" % year),
            bar(qsort(stg['ytd']), qty_series, "%s YTD - Quantity" % year),
        ])

        page_slide("11. Sales Type Groups Distribution — LY vs TY (YTD %s)" % period_label,
                   'saletypegroups-distribution', [
                       pie(stg['ytd'], 'prevYearSales', "Value — Last Year"),
                       pie(stg['ytd'], 'sales', "Value — This Year"),
                       pie(qsort(stg['ytd']), 'prevYearQty', "Qty — Last Year"),
                       pie(qsort(stg['ytd']), 'qty', "Qty — This Year"),
                   ])

        ts = bundle['topcatSubcats']
        page_slide("12. LCAC Product Groups (%s)" % period_label,
                   'topcat-subcats', [
                       bar(ts['mtd'], value_series, period_label),
                       bar(ts['ytd'], value_series, "%s YTD" % year),
                   ], stacked=True)

        for tab in class_tabs:
            rows = bundle['top3ByClass'].get(tab['v'], [])
            page_slide("13. Product Groups by Sales Type Group (YTD %s) — %s" % (period_label, tab['l']),
                       'top3-by-class_%s' % tab['v'],
                       [bar(rows, value_series, "Value"), bar(qsort(rows), qty_series, "Quantity")],
                       stacked=True)

        for tab in class_tabs:
            rows = bundle['regionsByClass'].get(tab['v'], [])
            page_slide("14. Regions by Sales Type Group (YTD %s) — %s" % (period_label, tab['l']),
                       'regions-by-class_%s' % tab['v'],
                       [bar(rows, value_series, "Value"), bar(qsort(rows), qty_series, "Quantity")],
                       stacked=True)

        for tab in region_tabs:
            page_slide("15. Dealers Sales by Region — Product Groups (YTD %s) — %s"
                       % (period_label, tab['l']),
                       'stg-region-maincats_%s' % tab['v'],
                       [bar(bundle['stgRegionMaincats'].get(tab['v'], []), value_series, tab['l'])])

        for tab in region_tabs:
            page_slide("16. Dealers Sales by Region — Product Sub-Groups (Split) (YTD %s) — %s"
                       % (period_label, tab['l']),
                       'stg-region-subcats_%s' % tab['v'],
                       [bar(bundle['stgRegionSubcats'].get(tab['v'], []), value_series, tab['l'])])

        page_slide("17. Top Sales Type Group — Product Groups: %s (YTD %s)" % (top_stg, period_label),
                   'stg-productgroups', [
                       bar(bundle['stgProductgroups'], value_series, "Value"),
                       bar(qsort(bundle['stgProductgroups']), qty_series, "Quantity"),
                   ], stacked=True)

        stream = BytesIO()
        prs.save(stream)
        return stream.getvalue()

    @http.route('/pbi_dashboards/sales_mail_sman/export.pptx', type='http', auth='user')
    def export_pptx(self, period=None, salesman='all',
                    subCategoryMode='regular', **kwargs):
        if not self._has_access():
            return request.not_found()
        if not optional_deps.is_pptx_available() or not _ensure_presentation():
            # A readable page, not a traceback: this route opens in a new tab,
            # so whatever it returns is what the user reads.
            return request.make_response(
                optional_deps.pptx_unavailable_message(),
                headers=[('Content-Type', 'text/plain; charset=utf-8')], status=503)
        year, month, franchise, salesman, sub_mode = self._resolve(
            period, salesman, subCategoryMode)
        try:
            data = self._build_pptx(year, month, franchise, salesman, sub_mode)
        except Exception as e:
            _logger.exception("sales_mail_sman_main: PPTX export failed")
            return request.make_response("Error building PPTX: %s" % e, status=500)
        headers = [
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'),
            ('Content-Disposition', 'attachment; filename="Sales_Analysis_with_Salesman.pptx"'),
            ('Content-Length', len(data)),
        ]
        return request.make_response(data, headers=headers)

    # ------------------------------------------------------------------
    # in-place note editing
    # ------------------------------------------------------------------
    def _write_note_row(self, scope, db_key, text, period, franchise, salesman, region='all'):
        """Upsert one pbi.dashboard.note row, or delete it when text is blank.

        Blank means "no override": the section falls back to the narrative the
        dashboard computes from the current figures. Keeping an empty row would
        show an empty panel instead."""
        Note = request.env['pbi.dashboard.note'].sudo()
        existing = Note.search(scope + [('key', '=', db_key)], limit=1)
        if not text:
            existing.unlink()
            return
        if existing:
            existing.text = text
        else:
            Note.create({'key': db_key, 'year': period, 'franchise': franchise,
                         'customer_type': salesman or 'all', 'region': region,
                         'text': text})

    @http.route('/pbi_dashboards/sales_mail_sman/save_notes', type='json', auth='user')
    def sales_mail_sman_save_notes(self, period=None, salesman='all', notes=None,
                                   requirements=None, **kw):
        """Save the board's edited notes and their requirements.

        Both payloads are {section: text}, and an empty string deletes that
        row. The browser, not this route, decides when a note has stopped
        being an override: it holds the computed narrative for every section
        already (bundle['narratives'], in the marked form it displays), and
        re-deriving it here would mean rebuilding the whole seventeen-page
        bundle — a full board load — on every save.
        """
        if not self._has_access():
            return {'error': 'You do not have access to this dashboard.'}
        year, month, franchise, salesman, _sub_mode = self._resolve(period, salesman, 'regular')
        period = "%s-%02d" % (year, month)
        scope = self._note_scope(period, franchise, salesman)

        # Section keys are slugs the board itself emits. Anything else is
        # refused rather than written: a key carrying the "req::" infix would
        # otherwise let a note be filed as a requirement, or vice versa.
        def _sections(payload):
            out = {}
            for key, text in (payload or {}).items():
                if not re.match(r'^[A-Za-z0-9_-]+$', key or ''):
                    continue
                out[key] = (text or '').strip()
            return out

        notes = _sections(notes)
        requirements = _sections(requirements)
        try:
            for key, text in notes.items():
                self._write_note_row(scope, self._note_keys(key)[0], text,
                                     period, franchise, salesman)
            for key, text in requirements.items():
                self._write_note_row(scope, self._note_keys(key)[1], text,
                                     period, franchise, salesman)
        except Exception as e:
            _logger.exception("sales_mail_sman_main: saving notes failed")
            return {'error': 'Could not save the notes — %s' % e}
        return {'notes': notes, 'requirements': requirements}
