# -*- coding: utf-8 -*-
"""Backs "PBI Dashboards > Sales Dashboards > Sales Dashboard With Salesman".

Same look and interaction model as "Sales Dashboard - New"
(sales_kpi_main.py / sales_kpi_dashboard_new.js), on a longer drill chain and a
different data source:

  * EVERYTHING — actuals AND target — comes from ONE pre-built snapshot,
    v_pbi_sales_sman_fact (pbi_dashboards/models/sales_sman_fact_view.py). It
    carries all eleven levels as code+label pairs, sales qty/value, and budget
    qty/value already attached. Read its docstring before changing anything
    here; the two rules that matter are repeated below.
  * TEN drill levels, plus a Regular/Manager switch that changes which
    product-category field feeds levels 7 and 8.

THE BUDGET REPEATS — max() BEFORE YOU SUM
-----------------------------------------
The budget was never captured per part, so the snapshot attaches one figure per
(month x classification x region x city x customer x product group) tuple to
every part row in that tuple. `budget_key` names the tuple. A plain
SUM(budget_value) therefore reads several times the real target; every budget
query here groups by budget_key with max() first and sums that. _budget_sums
and _budget_breakdown are the only two places this happens — keep it that way.

THE TARGET IS NOT VALID AT EVERY LEVEL
--------------------------------------
Measured on 2025 against the true budget of SAR 676,460,596: levels 2,3,4,6,7,8,9
come back exact, level 1 within 0.01%, but salesman reads 110.3%, product
sub-group 280.1% and part 750.7% — because the budget genuinely carries no
salesman, no sub-group and no part. BUDGET_UNSAFE_LEVELS names them, and both
the tiles and the bars go dark rather than draw a number that is 2.8x wrong.
`budgetReliable` in the payload tells the client which it is.

See docs/sales_salesman_10_levels_data_plan.md, sections 9 and 10.
"""

from odoo import fields, http
from odoo.http import request

from .access import menu_allowed

MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]

LEVELS = ["salesTypeGroup", "partnerClassification", "reportRegion", "city",
          "salesman", "customer", "mainCategory", "subCategory",
          "productGroup", "productSubGroup"]
LEVEL_ORDER = LEVELS

# Where the boards open. The client opens on the same level; the two are kept in
# step by the server sending `level` back on every reply.
#
# This was Partner Classification for as long as Sales Type Group had no target
# to show -- opening every session on the one level with its target tiles dark.
# Both halves of that are now fixed: l1 left BUDGET_UNSAFE_LEVELS once the
# capture carried a real sale type, and its bars measure exact against the true
# budget once the target is grouped on the budget's OWN sale type rather than
# the sale's (see BUDGET_LEVEL_COLUMNS). So the boards open at the head of the
# chain, which is also where a reader starts.
#
# SALES TYPE GROUP IS WHAT "DEPARTMENT" MEANS HERE. A customer-side tier was
# tried above it briefly -- the ERP's customer class type, which is what HHS's
# own monthly report is cut by -- and removed: in the pbi dashboards the
# department IS the sales type group, and carrying two levels that both claimed
# the word made the boards and the business disagree about a term they share.
# The customer class type survives as master data (Sales > Configuration >
# Partner Class Type) for whoever wants it; no board reads it.
OPENING_LEVEL = "salesTypeGroup"

LEVEL_LABELS = {
    "salesTypeGroup": "Sales Type Group",
    "partnerClassification": "Partner Classification",
    "reportRegion": "Region",
    "city": "City",
    "salesman": "Salesman",
    "customer": "Customer",
    "mainCategory": "Main Category",
    "subCategory": "Sub Category",
    "productGroup": "Product Group",
    "productSubGroup": "Product Sub-Group",
}

# The snapshot every query on this board reads. Built and refreshed by
# pbi_dashboards/models/sales_sman_fact_view.py; never queried directly here --
# _build_fact copies the request's slice into a temp table first.
FACT_VIEW = "v_pbi_sales_sman_fact"

# The TARGET is read from here, not from the snapshot. Same budget, same
# budget_key, same de-duplication -- but a plain view over v_sales_budget_month
# rather than a column inside a matview rebuilt at 02:30, so a budget entered a
# minute ago is on the chart now. Built beside the snapshot in
# models/sales_sman_fact_view.py; verified against it on dbprod at every
# budget-safe level, SAR 676,460,596 either way with no bucket differing.
#
# No scope clause is applied to it, and none is needed: the budget is scoped to
# the product groups that have in-scope sales when the view is built, so it is
# in scope by construction. That is exactly what the verification above
# measured -- the snapshot side of it was filtered on in_scope and the two
# still agreed to the riyal.
BUDGET_LIVE_VIEW = "v_pbi_sales_budget_live"

# The live view, materialised ONCE per request into a temp table the budget
# queries actually read. The view has to be evaluated to be live, and that costs
# ~116ms; a page runs several budget queries and was paying it every time.
# Copied here at the same moment the fact snapshot is, the page pays it once and
# every query after that is an indexed lookup -- live data at the old speed.
#
# ONE NAME, ONE BUILD, EVERY SALES BOARD. "Sales Dashboard With Salesman",
# "Sales Dashboard - VQ" and "Sales Analysis with Salesman" all read the target
# through this table, built by build_budget_temp() below. The mail board used to
# keep its own copy under its own name and with no year predicate; two builds of
# the same target are two chances for the boards to answer "what is the target"
# differently, which is the one thing the budget code is written to prevent.
# Sharing the NAME is safe because no request can hold two of these at once --
# each board is its own route and so its own transaction, and VQ does not build
# one of its own at all (it calls PbiSalesSmanController._data, which builds
# this one).
BUDGET_TEMP = "pbi_sman_budget"

# The columns of the temp fact table that anything filters, joins or groups on
# -- so the only ones ANALYZE has to build statistics for. Deliberately not the
# ten labels: each is selected and grouped beside its own code, so the planner
# reads the code's n_distinct and never the label's histogram. See _build_fact.
# A TOTAL order for chart rows, so a tie never decides itself.
#
# Every breakdown was sorted on one measure alone, and Python's sort is stable,
# so tied rows kept whatever order the database happened to return -- which is
# a property of the plan, not of the data. Trimming the ANALYZE in _build_fact
# changed a plan and swapped RAC and LCAC on one chart: both are budget-only
# rows at Manager/Sub Category, both sit at amount 0, and nothing had ever said
# which came first. Every figure was identical; only the two bars had traded
# places, and they could have traded back on any other day for any other reason.
#
# So the measures are ranked, and then the code breaks what is left. A code is
# unique within a breakdown, so the order is fully determined by the rows
# themselves and the same data always draws the same chart.
def _order_key(row, primary="amount"):
    return (-(row.get(primary) or 0.0),
            -(row.get("budgetAmount") or 0.0),
            -(row.get("prevYearAmount") or 0.0),
            str(row.get("code") or ""))


ANALYZE_COLUMNS = ", ".join(
    ["yr", "mth", "part_no", "budget_key", "budget_l1_code", "lfam_code"] +
    ["l%d_code" % i for i in range(1, 10)])

# Product scope. 'acgroups' is what the board shows and stays the default: the
# Midea AC product groups, by product_category.code, excluding 'V' customers.
# See the snapshot's docstring for the exact test. 'all' drops it, keeping only
# the MDA franchise the snapshot is built on, and is offered ONLY in developer
# mode, because the two are not comparable and the difference is not a rounding
# error: SAR 600,980,882 in scope against SAR 477,434,542 for every MDA line in
# 2025 -- LOWER, because the lines outside the scope are the customer/promo
# discount pseudo-parts (CSTDISC at -136.7m, AC promo discount at -13.5m) that
# carry negative money, plus installation, service charges, shipping and spares.
# Whitelisted here rather than interpolated from the request.
SCOPES = {
    "acgroups": "f.in_scope",
    "all": None,
}
DEFAULT_SCOPE = "acgroups"

# Both salesman boards are Midea boards: the snapshot is built MDA-only (the
# whole budget is MDA, and the twelve in-scope product groups are all Midea AC),
# so there is nothing for a Franchise control to choose between and neither
# board offers one. The value is still threaded through the payload and, on
# "Sales Analysis with Salesman", into the pbi.dashboard.note key -- notes
# written before the control was removed stay attached to their pages.
FRANCHISE = "MDA"

# Columns on that snapshot, one code + one label per level.
LEVEL_COLUMNS = {
    "salesTypeGroup": ("l1_code", "l1_label"),
    "partnerClassification": ("l2_code", "l2_label"),
    "reportRegion": ("l3_code", "l3_label"),
    "city": ("l4_code", "l4_label"),
    "salesman": ("l5_code", "l5_label"),
    "customer": ("l6_code", "l6_label"),
    "mainCategory": ("l7_code", "l7_label"),
    "subCategory": ("l8_code", "l8_label"),
    "productGroup": ("l9_code", "l9_label"),
    # PRODUCT SUB-GROUP IS THE MODEL FAMILY -- ELITE R410, not ELITE INDOOR
    # R410 and ELITE OUTDOOR R410 as two bars. product.category splits a split
    # AC into the halves it ships as, which is a fact about the warehouse and
    # not about the market; the business, the client's monthly report and the
    # ERP's own reporting all read one bar per model. The indoor/outdoor tier
    # was carried below this one for a while and drew nobody's chart.
    #
    # It is also what makes the target here CAPTURED rather than allocated: the
    # budget file states the family (erp_subgroup_code) on 98.2 pct of its 2025
    # value, and stated the indoor/outdoor tier on 17.7 pct.
    "productSubGroup": ("lfam_code", "lfam_label"),
}

# Where the BUDGET is grouped by a different column from the actuals. Only l1,
# and only because l1 is not in budget_key: a budget tuple whose parts sold
# under two sale types would otherwise have its whole figure counted once per
# sale type by the max()-per-budget_key de-duplication. The snapshot carries the
# budget's own sale type beside the row's (budget_l1_code -- see
# models/sales_sman_fact_view.py), and grouping the target on that is exact,
# because every capture tuple has exactly one. Cost of not doing it, measured on
# 2025: 3 tuples, SAR 90,232 double-counted, l1 target bars 0.018 pct over their
# own tile -- and, once salesman and sub-group started ALLOCATING from l1, that
# same overshoot inherited by every allocated bar.
#
# Used for grouping AND for filtering: drilling into "Projects" must narrow the
# target to the budget captured as Projects, not to the budget that happened to
# sell as Projects.
BUDGET_LEVEL_COLUMNS = {
    "salesTypeGroup": ("budget_l1_code", "budget_l1_label"),
}

# Levels the budget CANNOT be shown at, and it is not close. The two-stage
# max() de-duplication is only sound where the chart groups at or above the
# grain the budget was captured at; below it, one budget figure lands on several
# bars at once. Measured on 2025 against the true budget of SAR 676,460,596:
#
#     l2 l3 l4 l6 l7 l8 l9    100.0%   exact
#     l1 salesTypeGroup       100.0%   exact, once the budget carries a sales
#                                       type at all -- see below
#     l5 salesman             110.3%   and PATCHY: 2 of the top 6 salesmen by
#                                       2025 sales have no budget row at all
#
# productSubGroup measured 280.1 pct here while it meant the indoor/outdoor
# tier, which the budget never stated. It now means the model family, which the
# budget does state, and it is exact.
#
# Drawing a target 2.8x too large is worse than drawing none, so both the tiles
# and the bars go dark instead. Not a defect in the snapshot -- the budget
# genuinely carries no salesman and no sub-group.
#
# L1 IS BUDGETABLE AGAIN, and was briefly not. It is worth knowing why, because
# the failure was on the capture side and could return.
#
# The budget used to carry ONE salestype_group_id across all 57,005 month-rows,
# the '*' sentinel: the client's export states the OLD Customer Type
# (BD_CSTTYPE), not a sales type group, and sales_budget refused to guess
# between two colliding code sets. So no target could be attributed to a sale
# type at all -- 100% of it sat under "Others" while "Projects" read a flat
# zero, including the SAR 160.4m that was Projects money.
#
# sales_budget now maps the one customer type whose meaning is settled
# (04 -> Projects; see CST_TYPE_TO_SALESTYPE_REF there for the evidence and for
# why the other three stay on the sentinel), so l1 carries a real target and
# this level shows it. What was NOT done, and must not be: deriving l1 from the
# partner classification. "Projects - Open" is only 34.2% sale-type Projects in
# the 2026 actuals and most sale-type-Projects quantity sits under "AC
# Specialist" -- independent taxonomies that merely share a word.
#
# If a future file lands with its sale types unmapped, the symptom is a zero
# target under every group but "Others", and the fix belongs in the import.
BUDGET_UNSAFE_LEVELS = set()

# A level can also go unsafe for ONE YEAR, because a budget file was captured at
# a different grain from the one before it, and that cannot be a constant.
#
# 2026 is the case that forced this. Its budget carries ten "customer" codes --
# JEDDLR, JEDPRJ, KHODLR, KHOPRJ, QASDLR, QASPRJ, RYDDLR, RYDPRJ, MODTRADE,
# WHSALE -- which are channels, not customers, and match no customer that sells:
#
#     share of the year's target whose customer code also has sales
#     2024   60.5%      2025   65.0%      2026   0.0%
#
# So the whole SAR 519.8m YTD target sat on ten phantom bars while every real
# customer drew a zero target beside real sales -- the Customer chart read as a
# 100% miss for everyone. The tiles were right, no bar was.
#
# The threshold sits well below 2024 and 2025 and well above a file that names a
# different dimension entirely; it is a smell test, not a tolerance. A level
# that fails it is treated exactly like a BUDGET_UNSAFE_LEVELS one for that
# year: no target, and the board says which year and which level.
BUDGET_RESOLVE_MIN = 0.25

# Where an allocated target comes FROM. Sales Type Group is the deepest level
# the 2026 budget is captured at that every level below can be weighted inside:
# the capture carries a real sale type on every row (no '*' sentinel left --
# see the L1 note above), it measures exact against the true target, and it
# splits the year 67.3 / 32.7 rather than sitting in one bucket, so allocating
# within it is not the same as allocating globally.
BUDGET_BASIS_LEVEL = "salesTypeGroup"

# Where a PARTICULAR unsafe level's allocated target comes from, when the
# default above is not the right parent. Empty today: the only level left in
# BUDGET_UNSAFE_LEVELS is salesman, whose parent IS the sale type group.
BUDGET_BASIS_FOR_LEVEL = {}


def budget_basis_for(level):
    """The level an allocated target for `level` is shared out from."""
    return BUDGET_BASIS_FOR_LEVEL.get(level, BUDGET_BASIS_LEVEL)

# Levels whose budget code comes off the budget side of the snapshot and could
# therefore be captured at a grain of its own.
BUDGET_GRAIN_LEVELS = ("salesman", "partnerClassification", "reportRegion", "city",
                       "customer", "productGroup")

# Why a level shows no target, in the board's own words. Phrased as what the
# CAPTURE does not carry rather than what the board will not draw: the reader's
# next question is always "why", and "not measured here" does not answer it.
BUDGET_UNSAFE_REASON = {
    "salesman": "the budget is not captured per salesman",
}

UNASSIGNED = "__none__"
UNASSIGNED_LABEL = "Unassigned"

# A DIFFERENT sentinel from UNASSIGNED, and the difference matters. "Unassigned"
# is a real, drillable selection -- the rows with no value at this level, i.e.
# IS NULL. "Others" is a display roll-up of many real categories that fell below
# the chart's bar cap, so drilling into it would be meaningless; the JS refuses
# the click on this code.
OTHERS = "__others__"
OTHERS_LABEL = "Others"

# Bars a chart shows by name before the rest are rolled into OTHERS. Every level
# is capped, so the bars always sum to the KPI tile above them.
CHART_BARS = 15

# The levels both salesman boards read as a RANKING rather than as a breakdown
# of a total -- "who are my top ten salesmen", "my top ten customers". Ten bars
# each, picked by This Year sales and drawn biggest first, with no Others row:
# ten means ten.
#
# Still passed in by each route rather than applied here, because how many bars
# a board shows is that board's decision and a third board reading this engine
# may want a different answer. Both boards happen to want this one.
#
# The other six levels keep CHART_BARS, the target-aware selection and the
# Others roll-up that makes the bars add up to the tiles. Partner Classification
# and Region are small, closed sets where a top ten would mean nothing -- and
# Sales Type Group, which the boards now open on, has two members.
#
# Ranking on This Year alone is a deliberate trade against the target; see
# _collapse_others. Salesman and Product Sub-group carry no captured budget at
# all, so their bars are allocated anyway; at Customer and Product Group a
# category with a big target and no sales this year now falls out of the ten.
# The measure a ranked level is ranked ON. Whitelisted, never interpolated, and
# defaulted rather than required: a board with no Amount/Quantity control sends
# nothing and gets the value ranking, which is what "top ten" means unqualified.
MEASURES = ("amount", "qty")
DEFAULT_MEASURE = "amount"

BAR_CAPS = {
    "salesman": 10,
    "customer": 10,
    "productGroup": 10,
    "productSubGroup": 10,
}

# The menu each route gating this engine is tied to. The gate mirrors the
# menu's own visibility (see access.py), so a second board reading the same
# engine needs its own menu here rather than borrowing this one's -- a user
# granted "Sales Dashboard - VQ" and not "Sales Dashboard With Salesman" must
# be able to fetch the first and not the second.
MENU_SMAN = "pbi_sales_dashboards.menu_pbi_sales_kpi_analysis_sman"


# The live view's columns, with the Regular/Manager pair aliased down to
# l7_*/l8_* the way _build_fact does it on the actuals. {m} is whitelisted to
# '' or 'm' by _sub_field and never reaches here as text from a request.
#
# THIS IS WHAT KEEPS BOTH HALVES IN ONE TAXONOMY. Before it, the fact table
# aliased the chosen pair and the budget temp did not, so Manager sub-mode
# compared merged-reading sales against the regular reading of the target.
# Aliasing here instead of teaching every budget query about the sub-mode keeps
# them all mode-agnostic -- the same reason _build_fact aliases rather than
# branching -- and means a board cannot get one half right and the other wrong.
_BUDGET_TEMP_COLUMNS = (
    "yr, mth, budget_key, budget_qty, budget_value, franchise_code, "
    "budget_l1_code, budget_l1_label, "
    "l2_code, l2_label, l3_code, l3_label, l4_code, l4_label, "
    "l5_code, l5_label, "
    "l6_code, l6_label, "
    "l7{m}_code AS l7_code, l7{m}_label AS l7_label, "
    "l8{m}_code AS l8_code, l8{m}_label AS l8_label, "
    "l9_code, l9_label, lfam_code, lfam_label"
)


def build_budget_temp(cr, year, m=''):
    """Materialise the live budget view into BUDGET_TEMP for this request.

    THE ONE PLACE ANY SALES BOARD BUILDS ITS TARGET. Every budget-carrying
    board calls this and reads BUDGET_TEMP afterwards, so "what is the target"
    has exactly one answer, one scope and one query plan across the whole menu.

    Built eagerly rather than lazily, so that every budget query in the request
    sees one consistent copy taken at one instant -- two queries straddling
    someone else's budget save would otherwise disagree.

    The same two years the fact slice carries, and for the same reason: every
    budget query in a request is year-scoped to one of them, so the other years
    were evaluated, copied, indexed and then never read. The predicate pushes
    down into sales_budget_line's own scan, which is where the view's cost is --
    553ms to 387ms.

    It does narrow _budget_available() from "this database has budgets" to "this
    database has budgets for the years on screen". That is the question the flag
    is actually asked: hasBudget=True on the strength of a 2024 file, with every
    target on a 2027 chart drawn as zero, would be the bug rather than the
    feature.

    ``m`` is the Regular/Manager switch ('' or 'm'), applied here by aliasing
    the chosen l7/l8 pair -- see _BUDGET_TEMP_COLUMNS. Every budget query
    downstream reads l7_code/l8_code and stays mode-agnostic, exactly as the
    actuals' own temp table arranges.
    """
    cr.execute("DROP TABLE IF EXISTS " + BUDGET_TEMP)
    cr.execute("CREATE TEMP TABLE " + BUDGET_TEMP + " ON COMMIT DROP AS "
               "SELECT " + _BUDGET_TEMP_COLUMNS.format(m=('m' if m == 'm' else '')) +
               " FROM " + BUDGET_LIVE_VIEW +
               " WHERE yr IN (%s, %s)", [year, year - 1])
    cr.execute("CREATE INDEX ON " + BUDGET_TEMP + " (budget_key)")
    # Narrow ANALYZE for the same reason the fact table's is narrow, and
    # budget_key is the only column anything joins or groups on here.
    cr.execute("ANALYZE " + BUDGET_TEMP + " (budget_key)")


class PbiSalesSmanController(http.Controller):

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _budget_columns(level):
        """The (code, label) columns the TARGET is read through at a level --
        the actuals' own pair unless BUDGET_LEVEL_COLUMNS overrides it."""
        return BUDGET_LEVEL_COLUMNS.get(level) or LEVEL_COLUMNS[level]

    def _query(self, sql, params=()):
        request.env.cr.execute(sql, params)
        cols = [d[0] for d in request.env.cr.description]
        return [dict(zip(cols, row)) for row in request.env.cr.fetchall()]

    def _has_access(self, menu_xmlid=MENU_SMAN):
        return menu_allowed(menu_xmlid)

    def _sub_field(self, sub_mode):
        """Regular -> the l7/l8 columns, Manager -> l7m/l8m.

        The snapshot carries BOTH readings side by side, so the switch is a
        choice of column here rather than a different build of the facts.
        Whitelisted, never interpolated from the request.
        """
        return 'm' if sub_mode == 'manager' else ''

    def _fact_available(self):
        """The snapshot is created on module install/upgrade. Resolve it at
        runtime so a database that has not been upgraded yet renders an empty
        board with a message rather than a traceback."""
        request.env.cr.execute("SELECT to_regclass('public.%s')" % FACT_VIEW)
        return bool(request.env.cr.fetchone()[0])

    def _budget_available(self):
        """Whether the snapshot carries any target at all. It is built from
        v_sales_budget_month, which lives in sales_budget -- NOT a
        dependency of this module -- so on a database without that module the
        snapshot exists with budget_key NULL throughout, and the board should
        show its charts with no target rather than fail."""
        if not self._fact_available():
            return False
        request.env.cr.execute(
            "SELECT EXISTS (SELECT 1 FROM %s)" % BUDGET_TEMP)
        return bool(request.env.cr.fetchone()[0])

    # The unsafe set for THIS request. A class attribute so every helper can
    # read it without being handed the year, replaced per instance by
    # _fetch_bundle once the year's grain has been measured. Safe because a
    # controller instance serves one request: Odoo makes one per dispatch, and
    # the VQ route makes its own before delegating.
    _unsafe_levels = BUDGET_UNSAFE_LEVELS

    def _budget_grain_unsafe(self, year):
        """Levels where THIS year's budget was captured at a different grain.

        One pass over the temp fact table per request. For each level, the share
        of the de-duplicated target whose code also appears on a row that
        actually sold; below BUDGET_RESOLVE_MIN the budget is keyed on something
        that is not this level, and drawing it against this level's bars is
        drawing it against the wrong dimension. See the constant for the case
        that forced this and for the measured shares.

        max(budget_value) per budget_key first, exactly as _budget_two_stage
        does -- the figure repeats across the parts of its tuple, and counting
        it once per part would weight the test by how many parts a tuple has.
        """
        unsafe = set()
        if not self._budget_available():
            return unsafe
        levels = list(BUDGET_GRAIN_LEVELS)
        cols = [self._budget_columns(lv)[0] for lv in levels]

        # One pass, not one per level. This was five separate statements over
        # the same year of the same temp table -- each with its own DISTINCT
        # scan, its own join and its own GROUP BY over every budget_key -- and
        # together they cost 150-240ms of every request, drill-downs included,
        # to answer five yes/no questions.
        #
        # The shape is _sums_both_years' shape, and for the same reason: the
        # scan is what costs, so scan once and split the answers with FILTER.
        # Each level keeps its own `selling` set and its own resolves flag; the
        # arithmetic per level is unchanged, and so is the verdict.
        selling = ", ".join(
            "s{n} AS (SELECT DISTINCT {col} AS code FROM src"
            "         WHERE amount <> 0 AND {col} IS NOT NULL)".format(n=i, col=c)
            for i, c in enumerate(cols))
        joins = " ".join(
            "LEFT JOIN s{n} ON s{n}.code = f.{col}".format(n=i, col=c)
            for i, c in enumerate(cols))
        flags = ", ".join(
            "bool_or(s{n}.code IS NOT NULL) AS r{n}".format(n=i)
            for i in range(len(cols)))
        oks = ", ".join(
            "COALESCE(sum(bv) FILTER (WHERE r{n}), 0) AS ok{n}".format(n=i)
            for i in range(len(cols)))
        rows = self._query(
            "WITH src AS (SELECT * FROM pbi_sman_fact WHERE yr = %s), "
            + selling + ", k AS ("
            "  SELECT f.budget_key, max(f.budget_value) AS bv, " + flags +
            "  FROM src f " + joins +
            "  WHERE f.budget_key IS NOT NULL"
            "  GROUP BY f.budget_key) "
            "SELECT COALESCE(sum(bv), 0) AS total, " + oks + " FROM k", [year])
        row = rows[0] if rows else None
        if not row:
            return unsafe
        total = float(row["total"] or 0)
        # No target for the year at all is not a grain failure -- there is
        # simply nothing to draw, and _budget_available already says so.
        if not total:
            return unsafe
        for i, level in enumerate(levels):
            if float(row["ok%d" % i] or 0) / total < BUDGET_RESOLVE_MIN:
                unsafe.add(level)
        return unsafe

    def _budget_reason(self, level, year):
        """The sentence the board puts under a chart with no target."""
        if level in BUDGET_UNSAFE_REASON:
            return BUDGET_UNSAFE_REASON[level]
        if level in self._unsafe_levels:
            return "the %s budget is not captured per %s" % (
                year, LEVEL_LABELS[level].lower())
        return None

    def _budget_reliable(self, entries, level=None):
        """False as soon as ANY unsafe level is in play -- as the level being
        charted, or as a filter/drill narrowing the rows.

        The filter case matters as much as the display case and is easier to
        miss: drilling into one salesman leaves only that salesman's rows, and
        the budget on them is whatever the tuples he happened to sell into
        carried. Summing that is not "his target"; there is no such number.
        """
        if level in self._unsafe_levels:
            return False
        for entry in (entries or []):
            if isinstance(entry, dict) and entry.get("level") in self._unsafe_levels:
                return False
        return True

    # ------------------------------------------------------------------
    # filter clauses
    # ------------------------------------------------------------------
    @staticmethod
    def _scope_clause(scope):
        """Whitelisted, never interpolated. An unknown value falls back to the
        default rather than widening the scope by accident."""
        return SCOPES.get(scope if scope in SCOPES else DEFAULT_SCOPE)

    def _drill_clauses(self, drill_path, budget=False):
        """WHERE fragments for every level already drilled into.

        One set of columns for both measures now: actuals and target sit on
        the same rows, so a filter can no longer be expressed one way against
        the facts and another against the budget, and the two halves of a
        chart can no longer disagree about what was filtered.

        The Unassigned bucket is a real selection: drilling into it means "the
        rows with no value at this level", which is IS NULL, not = '__none__'.

        `budget` narrows the TARGET rather than the actuals, and at a level in
        BUDGET_LEVEL_COLUMNS that is a different column: drilling into
        "Projects" must select the budget captured as Projects, not the budget
        that happened to sell as Projects.
        """
        clauses, params = [], []
        for entry in (drill_path or []):
            if not isinstance(entry, dict):
                continue
            level, code = entry.get('level'), entry.get('code')
            if level not in LEVELS or code is None:
                continue
            col = 'f.%s' % ((self._budget_columns(level)[0]) if budget
                            else LEVEL_COLUMNS[level][0])
            if str(code) == UNASSIGNED:
                clauses.append("%s IS NULL" % col)
            else:
                clauses.append("%s = %%s" % col)
                params.append(str(code))
        return clauses, params

    def _normalise_level_filters(self, level_filters):
        """{level: code} with the unset dropdowns and unknown levels dropped."""
        out = {}
        for level, code in (level_filters or {}).items():
            if level not in LEVELS or code in (None, "", "all"):
                continue
            out[level] = str(code)
        return out

    def _level_filter_entries(self, level_filters):
        """The active dropdowns expressed as drill entries.

        Every level has its own dropdown, and a chosen value narrows the data
        exactly the way clicking that category's bar would -- so the filters
        reuse _drill_clauses rather than growing a second, parallel set of
        WHERE builders that could drift from it.
        """
        norm = self._normalise_level_filters(level_filters)
        return [{"level": level, "code": norm[level]}
                for level in LEVELS if level in norm]

    def _period_clauses(self, year, month=None, month_lte=None, table='f',
                        yr_col='yr', mth_col='mth'):
        clauses, params = ["%s.%s = %%s" % (table, yr_col)], [year]
        if month is not None:
            clauses.append("%s.%s = %%s" % (table, mth_col))
            params.append(month)
        if month_lte is not None:
            clauses.append("%s.%s <= %%s" % (table, mth_col))
            params.append(month_lte)
        return clauses, params

    # ------------------------------------------------------------------
    # actuals
    # ------------------------------------------------------------------
    def _build_fact(self, sub_mode, year, scope=DEFAULT_SCOPE):
        """Copy this request's slice of the snapshot into a temp table, once.

        Three consumers need the same rows -- the tiles, the bars and the ten
        filter dropdowns. Reading them straight from the materialised view each
        time would re-scan the whole snapshot three times and re-plan the
        Regular/Manager column choice with them; copying the two years this
        request cares about, then ANALYZE-ing, gives all three a table Postgres
        has actually measured. ON COMMIT DROP ties its life to the request's
        transaction.

        No franchise clause: the snapshot is MDA-only (see FRANCHISE).

        This is also where the Regular/Manager switch happens. The snapshot
        carries both readings side by side (l7/l8 and l7m/l8m); the temp table
        aliases the chosen pair to l7_*/l8_*, so every query downstream --
        and LEVEL_COLUMNS itself -- stays mode-agnostic.
        """
        cr = request.env.cr
        m = self._sub_field(sub_mode)          # '' or 'm', whitelisted
        # Only what something downstream actually reads. `id`,
        # `franchise_code`, `franchise_label` and `part_label` used to ride
        # along and were never selected once -- the snapshot is MDA-only, so
        # the franchise pair is a constant, and nothing joins back on the id.
        # Four columns off a 69k-row copy is 3MB less to write and, more to the
        # point, four fewer columns for ANALYZE to sample.
        cols = (
            "yr, mth, part_no, "
            "l1_code, l1_label, l2_code, l2_label, l3_code, l3_label, "
            "l4_code, l4_label, l5_code, l5_label, l6_code, l6_label, "
            "l7{m}_code AS l7_code, l7{m}_label AS l7_label, "
            "l8{m}_code AS l8_code, l8{m}_label AS l8_label, "
            "l9_code, l9_label, lfam_code, lfam_label, "
            "budget_l1_code, budget_l1_label, "
            "qty, amount, budget_key, budget_qty, budget_value"
        ).format(m=m)
        clauses, params = ["f.yr IN (%s, %s)"], [year, year - 1]
        sc = self._scope_clause(scope)
        if sc:
            clauses.append(sc)
        cr.execute("DROP TABLE IF EXISTS pbi_sman_fact")
        cr.execute(
            "CREATE TEMP TABLE pbi_sman_fact ON COMMIT DROP AS "
            "SELECT " + cols + " FROM " + FACT_VIEW + " f WHERE " +
            " AND ".join(clauses), params)
        # Every budget query groups by this first; without the index each one
        # re-sorts the whole slice.
        cr.execute("CREATE INDEX ON pbi_sman_fact (budget_key)")
        # A bare ANALYZE of this table cost 1.1s of every request -- more than
        # the copy and the index together, and paid again on every drill-down.
        # It was sampling 30,000 rows for each of thirty-odd columns, half of
        # them labels.
        #
        # Two things fix it, and neither costs a plan. The column list drops
        # the labels: a label is only ever selected and grouped BESIDE its own
        # code, so the row estimate comes off the code's n_distinct and the
        # label's own histogram is never consulted. The lower target samples
        # 7,500 rows instead of 30,000, which on 69k rows and a dozen
        # low-cardinality dimensions is still the whole story -- these columns
        # hold tens of distinct values, not tens of thousands.
        #
        # 1118ms -> 116ms, with every plan in the request unchanged.
        cr.execute("SET LOCAL default_statistics_target = 25")
        cr.execute("ANALYZE pbi_sman_fact (" + ANALYZE_COLUMNS + ")")
        build_budget_temp(cr, year, m)

    def _drill_where(self, drill_path):
        """WHERE for the temp fact table. Year and scope are already baked
        into it by _build_fact, so only the drill/filter levels remain."""
        clauses, params = self._drill_clauses(drill_path)
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params

    def _sums_both_years(self, drill_path, year, month):
        """MTD, YTD, and both prior-year equivalents from ONE scan.

        These were four separate _sums() calls over the same rows, and the fact
        CTE is expensive enough that the repetition dominated the page load --
        10 scans, 5.0s of a 5.2s request. Widening the year predicate to cover
        both years and splitting the measures with FILTER gets the same four
        answers for one scan.
        """
        sel_params = []
        for yr in (year, year - 1):
            for op in ('=', '<='):
                sel_params += [yr, month, yr, month]
        cols = []
        for tag, op in (("mtd", "="), ("ytd", "<="), ("pmtd", "="), ("pytd", "<=")):
            cols.append("COALESCE(sum(f.qty) FILTER (WHERE f.yr = %%s AND f.mth %s %%s), 0) AS %s_qty" % (op, tag))
            cols.append("COALESCE(sum(f.amount) FILTER (WHERE f.yr = %%s AND f.mth %s %%s), 0) AS %s_amount" % (op, tag))
        where, wp = self._drill_where(drill_path)
        row = self._query(
            "SELECT " + ", ".join(cols) + " FROM pbi_sman_fact f" + where,
            sel_params + wp)[0]
        return {tag: {"qty": float(row[tag + "_qty"] or 0),
                      "amount": float(row[tag + "_amount"] or 0)}
                for tag in ("mtd", "ytd", "pmtd", "pytd")}

    def _breakdown_both_years(self, level, drill_path, year, month):
        """The same four periods, broken down by category, from ONE scan.

        Returns (mtd_rows, ytd_rows, prev_mtd_by_code, prev_ytd_by_code) so the
        callers read exactly as they did when this was four _breakdown() calls.
        A category is emitted when ANY of the four periods is non-zero, which is
        what keeps prior-year-only categories available to _merge.
        """
        code_col, label_col = LEVEL_COLUMNS[level]
        sel_params = [UNASSIGNED, UNASSIGNED_LABEL]
        for yr in (year, year - 1):
            for _ in range(2):
                sel_params += [yr, month, yr, month]
        where, wp = self._drill_where(drill_path)
        cols = []
        for tag, op in (("mtd", "="), ("ytd", "<="), ("pmtd", "="), ("pytd", "<=")):
            cols.append("COALESCE(sum(f.qty) FILTER (WHERE f.yr = %%s AND f.mth %s %%s), 0) AS %s_qty" % (op, tag))
            cols.append("COALESCE(sum(f.amount) FILTER (WHERE f.yr = %%s AND f.mth %s %%s), 0) AS %s_amount" % (op, tag))
        rows = self._query(
            "SELECT COALESCE(f.{code}, %s) AS code, COALESCE(max(f.{label}), %s) AS label, "
            .format(code=code_col, label=label_col) + ", ".join(cols) +
            " FROM pbi_sman_fact f{where} GROUP BY f.{code}".format(where=where, code=code_col),
            sel_params + wp)

        def pick(tag):
            out = []
            for r in rows:
                qty, amount = float(r[tag + "_qty"] or 0), float(r[tag + "_amount"] or 0)
                if not qty and not amount:
                    continue
                lbl = r["label"] or UNASSIGNED_LABEL
                if level == "productGroup" and (lbl.upper() in ("ACWTSPLIT", "ACWTS") or "ACWTSPLIT" in lbl.upper()):
                    lbl = "Split"
                out.append({"code": str(r["code"]), "label": lbl,
                            "qty": qty, "amount": amount})
            out.sort(key=_order_key)
            return out
        return (pick("mtd"), pick("ytd"),
                {r["code"]: r for r in pick("pmtd")},
                {r["code"]: r for r in pick("pytd")})

    # ------------------------------------------------------------------
    # budget
    # ------------------------------------------------------------------
    def _budget_two_stage(self, inner_select, inner_group, outer_select,
                          outer_group, where, params):
        """The only shape a budget query may take on this board.

        The snapshot repeats one budget figure across every part row of its
        (month x classification x region x city x customer x product group)
        tuple, so the figure has to be collapsed per budget_key BEFORE it is
        summed. Doing it in one pass instead -- SUM(budget_value) GROUP BY
        level -- does not error; it silently returns several times the real
        target. Measured: 2.8x at product sub-group, 7.5x at part.

        budget_key IS NULL is excluded rather than coalesced: those are rows
        with sales and no target, and letting them form a key of their own
        would add a phantom zero-budget group to the outer sum.
        """
        return self._query(
            "SELECT " + outer_select + " FROM ("
            "SELECT " + inner_select + " FROM " + BUDGET_TEMP + " f"
            " WHERE f.budget_key IS NOT NULL" +
            ("".join(" AND " + c for c in where)) +
            " GROUP BY " + inner_group + ") t" +
            (" GROUP BY " + outer_group if outer_group else ""), params)

    def _budget_sums(self, year, entries, month=None, month_lte=None):
        """Target for the KPI tiles under the current filters."""
        if not (self._budget_available() and self._budget_reliable(entries)):
            return {"qty": 0.0, "amount": 0.0}
        clauses, params = self._period_clauses(year, month, month_lte)
        kc, kp = self._drill_clauses(entries, budget=True)
        rows = self._budget_two_stage(
            inner_select="f.budget_key, max(f.budget_qty) AS bq, max(f.budget_value) AS bv",
            inner_group="f.budget_key",
            outer_select="COALESCE(sum(t.bq),0) AS qty, COALESCE(sum(t.bv),0) AS amount",
            outer_group="",
            where=clauses + kc, params=params + kp)
        row = rows[0] if rows else {"qty": 0, "amount": 0}
        return {"qty": float(row["qty"] or 0), "amount": float(row["amount"] or 0)}

    def _actual_mix(self, level, entries, year, month=None, month_lte=None):
        """Sales per (basis group, category), this year and last -- the weights
        an allocated target is shared out by.

        greatest(x, 0) because credit notes make a category's sales negative,
        and a negative weight would hand it a negative target. Clamping costs
        nothing real: a category whose net sales are a refund has no claim on a
        share of the target anyway.
        """
        code_col, label_col = LEVEL_COLUMNS[level]
        basis_col = LEVEL_COLUMNS[budget_basis_for(level)][0]
        op = "=" if month is not None else "<="
        mth = month if month is not None else month_lte
        cols, cp = [], []
        for tag, yr in (("cur", year), ("prev", year - 1)):
            for meas in ("qty", "amount"):
                cols.append("COALESCE(sum(greatest(f.{m}, 0)) FILTER "
                            "(WHERE f.yr = %s AND f.mth {op} %s), 0) AS {t}_{m}"
                            .format(m=meas, op=op, t=tag))
                cp += [yr, mth]
        where, wp = self._drill_where(entries)
        rows = self._query(
            "SELECT COALESCE(f.{basis}::text, %s) AS grp, "
            "COALESCE(f.{code}, %s) AS code, "
            "COALESCE(max(f.{label}), %s) AS label, ".format(
                basis=basis_col, code=code_col, label=label_col)
            + ", ".join(cols) +
            " FROM pbi_sman_fact f{where} GROUP BY 1, 2".format(where=where),
            [UNASSIGNED, UNASSIGNED, UNASSIGNED_LABEL] + cp + wp)
        return [{"grp": str(r["grp"]), "code": str(r["code"]),
                 "label": r["label"] or UNASSIGNED_LABEL,
                 "cur_qty": float(r["cur_qty"] or 0),
                 "cur_amount": float(r["cur_amount"] or 0),
                 "prev_qty": float(r["prev_qty"] or 0),
                 "prev_amount": float(r["prev_amount"] or 0)} for r in rows]

    def _budget_allocated_breakdown(self, level, year, entries,
                                    month=None, month_lte=None):
        """A target for a level the budget was never captured at, shared down
        from BUDGET_BASIS_LEVEL by each category's actual mix.

        This is a DERIVED number and the board says so -- see budgetAllocated in
        the payload and the "(allocated)" the series labels carry. It is not a
        target anyone set for a salesman; it is that salesman's share of a
        target set for his sale type. The distinction is the whole reason the
        label exists, because the arithmetic cannot make it for the reader.

        THE WEIGHT IS LAST YEAR, not this year, and that choice is what makes
        the result worth drawing. Weighting by this year's sales makes the
        allocation circular: a category's target becomes proportional to its own
        performance, so every bar in a group reports the SAME achievement
        percentage as the group, and the comparison the target exists for
        disappears. Last year's mix is independent of this year's result, so a
        salesman who grew faster than his sale type beats his share and one who
        did not, misses.

        The fallback is per category, not per group: 29 of the 78
        salesman-by-sale-type pairs selling in 2026 have no 2025 sales at all
        (14 in one group, 15 in the other -- the teams move). Falling back only
        when a WHOLE group had no prior year would hand every one of those a
        zero target beside real sales, which reads as a total miss rather than
        as a new arrival. Such a category is weighted on this year instead, and
        carries the circularity for itself alone.

        Allocation preserves the total: the shares of a group sum to that
        group's target, so the bars still add up to the Target tile. A group
        with a target and no sales either year has nothing to weight, and its
        target lands on Unassigned rather than being quietly dropped.
        """
        basis = self._budget_breakdown(budget_basis_for(level), year, entries,
                                       month, month_lte)
        if not basis:
            return {}
        mix = self._actual_mix(level, entries, year, month, month_lte)
        by_grp = {}
        labels = {}
        for r in mix:
            by_grp.setdefault(r["grp"], []).append(r)
            labels[r["code"]] = r["label"]

        out = {}
        def add(code, meas, value):
            slot = out.setdefault(code, {"qty": 0.0, "amount": 0.0,
                                         "label": labels.get(code, code)})
            slot[meas] += value

        for grp, target in basis.items():
            rows = by_grp.get(grp, [])
            for meas in ("qty", "amount"):
                pot = float(target.get(meas) or 0)
                if not pot:
                    continue
                weights = {}
                for r in rows:
                    w = r["prev_" + meas] or r["cur_" + meas]
                    if w > 0:
                        weights[r["code"]] = w
                total = sum(weights.values())
                if not total:
                    add(UNASSIGNED, meas, pot)
                    continue
                for code, w in weights.items():
                    add(code, meas, pot * w / total)
        out.setdefault(UNASSIGNED, None)
        if out.get(UNASSIGNED) is None:
            out.pop(UNASSIGNED, None)
        else:
            out[UNASSIGNED]["label"] = UNASSIGNED_LABEL
        return out

    def _budget_breakdown(self, level, year, entries, month=None, month_lte=None):
        """Target per category, plus the caption -- so a category with a target
        and no sales still draws a bar AND still has a name. That caption used
        to need a second lookup against each dimension table (_budget_labels);
        the snapshot already carries it beside the code."""
        if not (self._budget_available() and self._budget_reliable(entries, level)):
            return {}
        code_col, label_col = self._budget_columns(level)
        clauses, params = self._period_clauses(year, month, month_lte)
        kc, kp = self._drill_clauses(entries, budget=True)
        rows = self._budget_two_stage(
            inner_select=(
                "COALESCE(f.{code}::text, %s) AS code, max(f.{label}) AS label, "
                "f.budget_key, max(f.budget_qty) AS bq, max(f.budget_value) AS bv"
            ).format(code=code_col, label=label_col),
            inner_group="1, f.budget_key",
            outer_select=("t.code, max(t.label) AS label, "
                          "COALESCE(sum(t.bq),0) AS qty, COALESCE(sum(t.bv),0) AS amount"),
            outer_group="t.code",
            where=clauses + kc, params=[UNASSIGNED] + params + kp)
        return {str(r["code"]): {"qty": float(r["qty"] or 0),
                                 "amount": float(r["amount"] or 0),
                                 "label": r["label"]} for r in rows}

    # ------------------------------------------------------------------
    # merging
    # ------------------------------------------------------------------
    def _merge(self, current, prev_by_code, budget_by_code, level_label_hint=None):
        """Attach prior-year and budget figures to the actuals breakdown.

        A FULL OUTER merge on BOTH sides, not a left join. A category with a
        budget but no actuals must still appear as a bar — that is the entire
        point of a target — and so must one that sold last year but not this
        year, or the Last Year tile stops matching the bars beneath it. The
        prior-year half of that used to be missing: 249 customers and 13.6M of
        2024 sales simply vanished from the 2025 YTD chart. It read as a
        shortfall, but at Product Sub-group the dropped categories were net
        NEGATIVE (credit notes), so the bars there OVERSHOT the tile instead —
        same bug, opposite sign.
        """
        by_code = {r["code"]: r for r in current}
        for row in current:
            p = prev_by_code.get(row["code"])
            row["prevYearQty"] = p["qty"] if p else 0.0
            row["prevYearAmount"] = p["amount"] if p else 0.0
            b = budget_by_code.get(row["code"])
            row["budgetQty"] = b["qty"] if b else 0.0
            row["budgetAmount"] = b["amount"] if b else 0.0
        for code, b in (budget_by_code or {}).items():
            if code in by_code:
                continue
            if not b["qty"] and not b["amount"]:
                continue
            row = {
                "code": code,
                "label": (level_label_hint or {}).get(code) or UNASSIGNED_LABEL
                         if code == UNASSIGNED else (level_label_hint or {}).get(code, code),
                "qty": 0.0, "amount": 0.0,
                "prevYearQty": 0.0, "prevYearAmount": 0.0,
                "budgetQty": b["qty"], "budgetAmount": b["amount"],
            }
            current.append(row)
            by_code[code] = row       # so the prior-year pass below finds it
        for code, p in (prev_by_code or {}).items():
            if not p["qty"] and not p["amount"]:
                continue
            existing = by_code.get(code)
            if existing is not None:
                # Already a bar — either it has current-year sales (the first
                # loop set these) or it is budget-only, which the loop above
                # left at zero. Either way this is the correct prior year.
                existing["prevYearQty"] = p["qty"]
                existing["prevYearAmount"] = p["amount"]
                continue
            row = {
                "code": code,
                "label": p.get("label") or (level_label_hint or {}).get(code, code),
                "qty": 0.0, "amount": 0.0,
                "prevYearQty": p["qty"], "prevYearAmount": p["amount"],
                "budgetQty": 0.0, "budgetAmount": 0.0,
            }
            current.append(row)
            by_code[code] = row
        current.sort(key=_order_key)
        return current

    def _collapse_others(self, rows, limit=CHART_BARS, top_by_current=False,
                         keep_others=True, rank_key="amount"):
        """The `limit` biggest categories, plus one row carrying the rest.

        Called LAST, after _merge, so the roll-up picks up budget-only
        categories too -- collapsing before the merge would leave their targets
        outside the chart and the Target tile would stop tallying. Every measure
        is summed, not just This Year, so the bars add up to each of the four
        tiles rather than only the one.

        "Biggest" weighs This Year, Target and Last Year together rather than
        This Year alone. Ranking on This Year alone meant a category could be
        cut for having no sales this year while carrying a large target, and at
        Product Sub-group that put 73.3M of a 74.9M target into Others -- the
        bars still added up, but there was nothing left to compare a target
        against. Selection uses the three amounts; the surviving rows are then
        ordered by This Year, which is how the chart reads left to right.

        `keep_others` drops that last row entirely, which is what a board asking
        for a top ten means by one: a ranking of ten is ten, and an eleventh bar
        taller than all of them for "everyone else" is not part of the ranking.
        It costs the invariant in the paragraph above -- the bars no longer add
        up to the tiles, because they are no longer meant to. The tiles keep
        showing the true totals, so what is missing stays visible; and the
        Share column is taken against the tile rather than against the rows, so
        ten shares that come to 43.6 per cent SAY they are ten of a larger
        whole. Only offered with a cap: dropping Others from an uncapped chart
        would drop nothing.

        `rank_key` is which This Year measure the ranking is on -- "amount" for
        the top ten by value, "qty" for the top ten by units. It only applies
        with `top_by_current`, and it is not cosmetic: at Product Sub-Group the
        two lists overlap by three of ten, because cheap high-volume categories
        rank high on units and low on money. Ranking by value and then merely
        re-sorting by quantity would show ten sub-groups holding 41.3 pct of the
        quantity the real top ten hold, under a heading that says top ten.

        `top_by_current` asks for the other reading: a plain This Year ranking,
        the "top N" a reader means when they say top ten. It is a per-board,
        per-level choice (see BAR_CAPS in sales_vq_main.py), not a new default,
        because it reintroduces exactly the trade-off the paragraph above
        describes -- a category with a large target and no sales this year now
        falls into Others. That is the point at the levels it is asked for:
        salesman and Product Sub-group carry no target at all
        (BUDGET_UNSAFE_LEVELS), so there is nothing to lose there, and at
        Customer and Product Group the ranking the reader asked for wins over
        the target that would otherwise drag a category in. Others still carries
        every measure, so the tiles keep tallying either way.
        """
        if len(rows) <= limit:
            return rows
        key = rank_key if top_by_current else "amount"
        def biggest(r):
            if top_by_current:
                return r.get(key) or 0.0
            return max(r.get("amount") or 0.0,
                       r.get("budgetAmount") or 0.0,
                       r.get("prevYearAmount") or 0.0)
        # The code breaks the tie here too, and it matters more: at this
        # sort a tie decides which categories get a bar at all and which are
        # rolled into Others, not merely what order they stand in.
        ranked = sorted(rows, key=lambda r: (-biggest(r), str(r.get("code") or "")))
        head, tail = ranked[:limit], ranked[limit:]
        head.sort(key=lambda r: _order_key(r, key))
        if not keep_others:
            return head
        agg = {"code": OTHERS, "label": OTHERS_LABEL, "isOthers": True}
        for key in ("qty", "amount", "prevYearQty", "prevYearAmount",
                    "budgetQty", "budgetAmount"):
            agg[key] = sum(r.get(key) or 0.0 for r in tail)
        head.append(agg)
        return head

    # ------------------------------------------------------------------
    # options
    # ------------------------------------------------------------------
    def _year_options(self, sub_mode):
        """Off the snapshot, which is already scoped to what the board can show.

        The current year is always in the list even when nothing has been
        invoiced in it yet, because that is the year the dashboard opens on: a
        default the dropdown cannot display would leave the control showing one
        year while the charts drew another.
        """
        if not self._fact_available():
            return [{"v": self._default_period()[0], "l": str(self._default_period()[0])}]
        rows = self._query(
            "SELECT DISTINCT yr FROM " + FACT_VIEW +
            " WHERE yr IS NOT NULL ORDER BY 1 DESC LIMIT 10")
        years = [r["yr"] for r in rows]
        this_year = self._default_period()[0]
        if this_year not in years:
            years.append(this_year)
            years.sort(reverse=True)
        return [{"v": y, "l": str(y)} for y in years]

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

    # "Sales Dashboard - VQ" reaches this through _data (see sales_vq_main),
    # so it opens on the same month without carrying its own copy.

    def _level_filter_options(self, selection, month):
        """Options for all TEN level dropdowns, from ONE pass over the facts.

        Leave-one-out: a level's own list is what the OTHER nine selections
        allow, so a chosen value can always be swapped for a sibling without
        first going back to All. Answering that one level at a time would mean
        ten grouped passes with ten different WHERE clauses, so instead every
        row carries a match flag per level plus a count of how many flags it
        fails, and a level takes the rows that fail none of them or fail only
        its own.

        ``selection`` is the merged view of the drill path and the ten
        dropdowns -- a drilled level is just a level whose value was chosen by
        clicking a bar, and it belongs in the leave-one-out set like any other,
        or its dropdown would list the one value it is already on.

        Scope is the union of every series the charts draw -- this year and
        last (both already in the temp table), up to the selected month -- so a
        category that only sold last year is still reachable from the dropdown.
        """
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

        # part_no IS NOT NULL drops the budget-only rows. They carry no
        # salesman and no sub-group, so leaving them in added an "Unassigned"
        # option to those two dropdowns that had never been there and that
        # selects nothing but zero-sales rows. Budget-only categories are not
        # lost by this: _merge still gives them a bar, and a bar is clickable,
        # so they remain reachable the way every other category is.
        sql = ("WITH matched AS (SELECT {carried}, {picks} "
               "FROM pbi_sman_fact f WHERE f.mth <= %s AND f.part_no IS NOT NULL), "
               "scoped AS (SELECT matched.*, ({misses}) AS misses FROM matched) ".format(
                   carried=carried, picks=picks, misses=misses) +
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

    def _natural_level(self, drill_path):
        """Which level the charts group at, given how far the user has drilled.

        With nothing drilled that is OPENING_LEVEL -- today the head of the
        chain, though the two are deliberately separate names: where a board
        opens is a display choice, and it has already moved once. It was Partner
        Classification while Sales Type Group could show no target; see
        OPENING_LEVEL for why that no longer applies.
        """
        drilled = [LEVELS.index(e["level"]) for e in (drill_path or [])
                   if isinstance(e, dict) and e.get("level") in LEVELS]
        depth = min((max(drilled) + 1) if drilled else LEVELS.index(OPENING_LEVEL),
                    len(LEVELS) - 1)
        return LEVELS[depth]

    # ------------------------------------------------------------------
    # bundle
    # ------------------------------------------------------------------
    def _fetch_bundle(self, year, month, sub_mode, drill_path,
                      level_filters=None, view_level=None, scope=DEFAULT_SCOPE,
                      bar_caps=None, measure=DEFAULT_MEASURE):
        # Same JIT fix as sales_kpi_main.py: Postgres JIT-compiles these
        # multi-CASE aggregates and spends more time generating code than
        # scanning. SET LOCAL reverts at commit.
        request.env.cr.execute("SET LOCAL jit = off")
        self._build_fact(sub_mode, year, scope)

        # Before anything asks whether the budget is reliable. The levels the
        # budget is never captured at, plus the ones THIS year's file was
        # captured at a different grain from -- measured, not assumed.
        self._unsafe_levels = BUDGET_UNSAFE_LEVELS | self._budget_grain_unsafe(year)

        level = view_level if view_level in LEVELS else self._natural_level(drill_path)
        can_drill_further = LEVELS.index(level) < len(LEVELS) - 1
        has_prev_year = True

        # A filter narrows the data exactly as clicking that category's bar
        # would, so filters and drill steps go into one list. A level that is
        # already drilled ignores its own dropdown: the drill is the narrower
        # of the two, and a contradicting pair would empty every chart with no
        # visible cause.
        drilled = {e["level"]: str(e["code"]) for e in (drill_path or [])
                   if isinstance(e, dict) and e.get("level") in LEVELS
                   and e.get("code") is not None}
        effective = list(drill_path or [])
        effective += [e for e in self._level_filter_entries(level_filters)
                      if e["level"] not in drilled]

        # What the ten dropdowns should read: whichever of the two chose the
        # value. Clicking a bar and picking from a dropdown are the same act
        # against the same level, so they share one display.
        selection = dict(self._normalise_level_filters(level_filters))
        selection.update(drilled)

        # Two fact scans, not eight: _sums_both_years and _breakdown_both_years
        # each answer all four period/year combinations in one pass. The tiles
        # are still computed independently of the bars rather than derived from
        # them -- that redundancy is what exposed the prior-year merge bug, so
        # it is worth one extra scan to keep.
        sums = self._sums_both_years(effective, year, month)
        mtd, ytd, mtd_prev, ytd_prev = sums["mtd"], sums["ytd"], sums["pmtd"], sums["pytd"]
        # Year and scope are already baked into the temp table by
        # _build_fact, so the budget queries carry only period and drill.
        mtd_bud = self._budget_sums(year, effective, month=month)
        ytd_bud = self._budget_sums(year, effective, month_lte=month)

        mtd_rows, ytd_rows, mtd_prev_rows, ytd_prev_rows = self._breakdown_both_years(
            level, effective, year, month)
        # A level the budget was never captured at gets its target ALLOCATED
        # from the sale type down, rather than nothing at all -- but only while
        # nothing unsafe is filtering the rows. Drilled into one salesman, the
        # basis target itself is unattributable, and allocating from a number
        # that does not exist would be inventing rather than sharing out.
        unsafe_filter = any(isinstance(e, dict) and e.get("level") in self._unsafe_levels
                            for e in effective)
        allocated = level in self._unsafe_levels and not unsafe_filter
        if allocated:
            mtd_bud_rows = self._budget_allocated_breakdown(level, year, effective, month=month)
            ytd_bud_rows = self._budget_allocated_breakdown(level, year, effective, month_lte=month)
        else:
            mtd_bud_rows = self._budget_breakdown(level, year, effective, month=month)
            ytd_bud_rows = self._budget_breakdown(level, year, effective, month_lte=month)

        # Captions for budget-only categories used to need a second lookup per
        # dimension table; _budget_breakdown now returns the label beside the
        # figure, straight off the snapshot, so a bar with a target and no sales
        # is never rendered as a bare row id.
        labels = {code: b["label"] for code, b in
                  list(mtd_bud_rows.items()) + list(ytd_bud_rows.items())
                  if b.get("label")}
        self._merge(mtd_rows, mtd_prev_rows, mtd_bud_rows, labels)
        self._merge(ytd_rows, ytd_prev_rows, ytd_bud_rows, labels)

        # Never built from the chart rows: those are capped at CHART_BARS and
        # rolled into Others, and the dropdown is precisely how you reach a
        # category too small to earn its own bar.
        level_options = self._level_filter_options(selection, month)

        # How many bars this board wants at THIS level, and how it wants them
        # picked. A board that names a cap for a level is asking for a RANKING:
        # the top N by This Year sales, drawn biggest first, with no Others row
        # -- ten means ten. Every other level keeps the shared CHART_BARS, the
        # target-aware selection and the Others roll-up that makes the bars add
        # up to the tiles. Both charts on a VQ card read the same rows, so
        # capping here caps value and quantity together -- which is what keeps
        # the nth bar the same category on both.
        cap = (bar_caps or {}).get(level)
        limit = cap or CHART_BARS
        # Only a ranked level reads the measure. Everywhere else the rows carry
        # every category anyway, so which measure orders them is the client's
        # business and the payload stays measure-agnostic -- which is what lets
        # the boards switch Amount/Quantity without a round trip at nine levels
        # out of ten.
        rank_key = measure if cap else "amount"
        mtd_rows = self._collapse_others(mtd_rows, limit, top_by_current=bool(cap),
                                         keep_others=not cap, rank_key=rank_key)
        ytd_rows = self._collapse_others(ytd_rows, limit, top_by_current=bool(cap),
                                         keep_others=not cap, rank_key=rank_key)

        # One answer for the whole payload: the tiles and the bars must agree
        # about whether there IS a target, or a dark tile above a drawn bar
        # reads as a bug rather than as a deliberate blank.
        budget_ok = self._budget_available() and (
            allocated or self._budget_reliable(effective, level))
        unsafe = sorted({e["level"] for e in effective
                         if isinstance(e, dict) and e.get("level") in self._unsafe_levels}
                        | ({level} if level in self._unsafe_levels else set()))

        return {
            "period": {"year": year, "month": month,
                       "monthName": MONTH_NAMES[month - 1],
                       "label": "%s %s" % (MONTH_NAMES[month - 1], year)},
            "hasPrevYear": has_prev_year,
            "hasBudget": budget_ok,
            # Why it is dark, so the client can say so instead of showing a
            # blank the user has to guess at.
            "budgetReliable": budget_ok,
            "budgetUnsafeLevels": [LEVEL_LABELS[lv] for lv in unsafe],
            # Why, in a sentence the chart subtitle can print. A board that says
            # only "no target at this level" makes the reader guess between a
            # broken dashboard and a budget that was never captured that way.
            # A derived target, not a captured one. The client labels the
            # series and the tile with it; nothing downstream may treat an
            # allocated figure as a budget somebody actually set.
            "budgetAllocated": allocated,
            "budgetBasisLabel": LEVEL_LABELS[budget_basis_for(level)],
            "budgetReason": None if budget_ok else "; ".join(
                r for r in (self._budget_reason(lv, year) for lv in unsafe) if r),
            # Null unless this level is a ranking, and then the measure the
            # rows were CHOSEN on. Two readers:
            #
            #   * the measure toggle re-fetches when this is set, because the
            #     rows themselves depended on it -- see selectMeasure;
            #   * it is also how a client knows the bars are PART of the whole
            #     (no Others row), so a Share column or a donut ring must take
            #     its denominator from the KPI tile rather than from the rows.
            "rankedBy": measure if cap else None,
            "kpis": {
                "mtdThisYear": mtd["amount"], "mtdTarget": mtd_bud["amount"], "mtdLastYear": mtd_prev["amount"],
                "mtdQtyThisYear": mtd["qty"], "mtdQtyTarget": mtd_bud["qty"], "mtdQtyLastYear": mtd_prev["qty"],
                "ytdThisYear": ytd["amount"], "ytdTarget": ytd_bud["amount"], "ytdLastYear": ytd_prev["amount"],
                "ytdQtyThisYear": ytd["qty"], "ytdQtyTarget": ytd_bud["qty"], "ytdQtyLastYear": ytd_prev["qty"],
            },
            "breakdown": {"mtd": mtd_rows, "ytd": ytd_rows},
            "level": level,
            "levelLabel": LEVEL_LABELS[level],
            "canDrillFurther": can_drill_further,
            "levelFilterOptions": level_options,
            "levelFilters": selection,
            "franchise": FRANCHISE,
            "subCategoryMode": sub_mode,
            "scope": scope if scope in SCOPES else DEFAULT_SCOPE,
        }

    # ------------------------------------------------------------------
    # payload + route
    # ------------------------------------------------------------------
    def _data(self, menu_xmlid, period=None, subCategoryMode='regular',
              drillPath=None, levelFilters=None, viewLevel=None,
              scope=DEFAULT_SCOPE, bar_caps=None, measure=DEFAULT_MEASURE):
        """The whole payload, for whichever board is asking.

        `menu_xmlid` is the gate, and it is a ROUTE-side argument, never a
        request one: each route passes its own board's menu, so a client
        cannot name the menu it happens to be granted and read a board it is
        not. Everything below this line is identical for every board reading
        this engine -- "Sales Dashboard With Salesman" and
        "Sales Dashboard - VQ" differ in what they DRAW, not in what they ask
        for (see controllers/sales_vq_main.py).

        `bar_caps` is the one exception, and it is route-side for the same
        reason `menu_xmlid` is: how many bars a board shows is that board's
        decision, not the caller's. {level: n} caps those levels at n bars
        ranked by This Year sales; levels it does not name are untouched, so a
        board that passes nothing behaves exactly as before.
        """
        if not self._has_access(menu_xmlid):
            return {'error': 'You do not have access to this dashboard.'}
        try:
            sub_mode = 'manager' if subCategoryMode == 'manager' else 'regular'
            year = month = None
            if period:
                try:
                    y, m = period.split('-')
                    year, month = int(y), int(m)
                except (ValueError, AttributeError):
                    year = month = None
            if year is None or month is None:
                year, month = self._default_period()

            # The snapshot is created on module install/upgrade. Say so plainly
            # rather than raising "relation does not exist" at the user.
            if not self._fact_available():
                return {'error': 'The sales snapshot has not been built yet. '
                                 'Upgrade the pbi_dashboards module, then refresh.'}

            drill_path = drillPath if isinstance(drillPath, list) else []
            level_filters = levelFilters if isinstance(levelFilters, dict) else {}
            bundle = self._fetch_bundle(year, month, sub_mode, drill_path,
                                        level_filters, viewLevel, scope,
                                        bar_caps,
                                        measure if measure in MEASURES
                                        else DEFAULT_MEASURE)
            bundle["yearOptions"] = self._year_options(sub_mode)
            return bundle
        except Exception as e:
            return {'error': str(e)}

    @http.route('/pbi_dashboards/sales_sman/data', type='json', auth='user')
    def sales_sman_data(self, period=None, subCategoryMode='regular',
                        drillPath=None, levelFilters=None, viewLevel=None,
                        scope=DEFAULT_SCOPE, measure=DEFAULT_MEASURE, **kw):
        # **kw swallows `franchise`, which the board no longer sends, and stops
        # anything else the client sends -- `menu_xmlid` above all -- from
        # reaching _data. Odoo serves a cached JS bundle that a container
        # restart does not invalidate, so a browser can still be posting the
        # old argument for a while after this deploys; accepting and ignoring
        # it beats a TypeError in the one window where that matters.
        # `measure` is the ONE request argument that reaches a chart's shape,
        # and it reaches only the ranked levels: this board's Amount/Quantity
        # control decides whether its top ten is ten by value or ten by units.
        # Whitelisted in _data, so an unknown value falls back rather than
        # reaching a sort key.
        return self._data(MENU_SMAN, period, subCategoryMode, drillPath,
                          levelFilters, viewLevel, scope, BAR_CAPS, measure)

    # ---------------------------------------------------------------- refresh
    #
    # Both routes are deliberately thin: they gate on the same menu this board
    # gates on and hand straight to the model. Nothing here rebuilds anything.
    # See pbi.sales.sman.fact.queue_refresh for why a button must never call
    # refresh_fact() inside a request -- it is ~16s of database CPU, and
    # holding a worker and a transaction for that long is what took staging
    # down when the REFRESH was run by hand.

    @http.route('/pbi_dashboards/sales_sman/refresh_status', type='json',
                auth='user')
    def sales_sman_refresh_status(self, **kw):
        if not self._has_access():
            return {'error': 'forbidden'}
        return request.env['pbi.sales.sman.fact'].refresh_status()

    @http.route('/pbi_dashboards/sales_sman/queue_refresh', type='json',
                auth='user')
    def sales_sman_queue_refresh(self, **kw):
        # Same menu check as the data route: anyone who may read this board may
        # ask for its numbers to be current. The model's debounce, not this
        # check, is what keeps the request cheap.
        if not self._has_access():
            return {'error': 'forbidden'}
        return request.env['pbi.sales.sman.fact'].queue_refresh()
