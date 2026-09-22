# -*- coding: utf-8 -*-
"""Backs "PBI Dashboards > Sales Dashboards > Sales Data Study".

The same matrix as sales_study_main.py — twelve months across the top, Qty and
Value under each, rows expanding in place, one slicer per level — over the TEN
level chain of "Sales Dashboard With Salesman" instead of the six of the bidata
boards: Sales Type Group, Partner Classification, Region, City, Salesman,
Customer, Main Category, Sub Category, Product Group, Product Sub-Group, plus
the Regular/Manager switch that decides which product-category reading feeds
levels 7 and 8.

The two boards deliberately share a menu name; they sit in different
containers ("Sales Dashboards" here, "Sales Dashboards - Temp" for the bidata
one) and their subtitles name the level count. They share the whole client too
— one OWL component, configured by route and by the levels the server
declares — so the two cannot drift apart in look or behaviour.

Reads v_pbi_sales_sman_fact (models/sales_sman_fact_view.py), the same snapshot
the salesman chart boards read, through the same per-request temp-table copy
they use. The level constants come from sales_sman_main.py so the two boards
cannot disagree about which column is which level.

THE TARGET
----------
The matrix also draws the BUDGET, on the "Data" control: Sales, Budget, or the
two side by side. It is read from BUDGET_TEMP — the shared once-per-request copy
of v_pbi_sales_budget_live that sales_sman_main.build_budget_temp() puts there,
and the same table the three salesman chart boards read — so this board and they
cannot answer "what is the target" differently.

Built ONLY when the client asks (withBudget), so a board on Sales alone costs
exactly what it cost before the target existed.

Two levels can never carry one: the budget was not captured per salesman or per
product sub-group, and the view has no column to read one from. A third can go
blank for one YEAR when that year's file was captured at another grain — 2026's
Customer codes are channels, and the grain test catches it. Those cells draw a
dash and the reason rather than a figure allocated down from somewhere else:
this board is exported to Excel, where a derived number and a captured one would
become indistinguishable. The chart boards make the other choice, and label it.

WHY NOT REUSE PbiSalesSmanController'S HELPERS
----------------------------------------------
Its equivalents are built around a fact table that carries the budget columns
inline, indexes budget_key on them and ANALYZEs for the two-stage max()
de-duplication, and it copies TWO years because every chart there draws a
prior-year series. This matrix needs one year of actuals with no budget columns
on them at all — the target arrives as its own table beside them — which keeps
the per-request setup at about a third of a second for the Sales-only case that
is most of the traffic. What IS shared is the part that must never disagree: the
level/column constants, the scope whitelist, the Regular/Manager column
aliasing, and now the budget temp and its unsafe-level rules, all imported or
mirrored line for line below.
And it is a live http.Controller, so it could not have been subclassed anyway
(see PbiSalesKpiEngineMixin's docstring for what that does to the parent's
routes).
"""

from odoo import fields, http
from odoo.http import request

from .access import menu_allowed
from .sales_sman_main import (
    BUDGET_GRAIN_LEVELS,
    BUDGET_RESOLVE_MIN,
    BUDGET_TEMP,
    BUDGET_UNSAFE_LEVELS,
    BUDGET_UNSAFE_REASON,
    DEFAULT_SCOPE,
    FACT_VIEW,
    LEVEL_COLUMNS,
    LEVEL_LABELS,
    LEVELS,
    MONTH_NAMES,
    SCOPES,
    UNASSIGNED,
    UNASSIGNED_LABEL,
    build_budget_temp,
)

# Same caps as the six-level board — see sales_study_main.py for what each one
# protects against.
ROW_LIMIT = 250
MAX_NODES_PER_REQUEST = 150
FILTER_OPTION_LIMIT = 500

STUDY_SCOPES = ("mtd", "ytd", "year")

# The request's slice of the snapshot. Named differently from the chart board's
# pbi_sman_fact so the two can never be confused in a log or an EXPLAIN, even
# though they can only ever exist in separate transactions.
FACT_TMP = "pbi_sman_study_fact"

# Every column this board reads, with the Regular/Manager pair aliased down to
# l7_*/l8_* so LEVEL_COLUMNS applies unchanged downstream. Mirrors the same
# aliasing in PbiSalesSmanController._build_fact; the {m} is whitelisted to ''
# or 'm' by _sub_field and never comes from the request as text.
#
# part_no/part_label ride along for the Part No control -- the same two columns
# PbiSalesSmanController._build_fact copies for the chart boards, off the same
# view. They are never grouped on: part is not an eleventh level, it is a
# FILTER, and _build_fact applies it while copying so the whole request -- grand
# total, every node, all ten slicer lists -- narrows to that one part with no
# further clause anywhere. part_label is carried only to caption the resolution
# line; nothing groups by it.
#
# in_scope rides along for the same control and nothing else. The part filter
# BYPASSES the product scope (see _build_fact), so the copy can now hold rows
# the scope would have dropped -- and the board has to be able to SAY that
# rather than quietly showing figures a scoped board would not. It is a
# boolean; carrying it costs nothing.
_FACT_COLUMNS = (
    "yr, mth, part_no, part_label, in_scope, "
    "l1_code, l1_label, l2_code, l2_label, l3_code, l3_label, "
    "l4_code, l4_label, l5_code, l5_label, l6_code, l6_label, "
    "l7{m}_code AS l7_code, l7{m}_label AS l7_label, "
    "l8{m}_code AS l8_code, l8{m}_label AS l8_label, "
    "l9_code, l9_label, lfam_code, lfam_label, "
    "qty, amount"
)


# ---------------------------------------------------------------------------
# THE TARGET
#
# Read from BUDGET_TEMP -- the shared, once-per-request copy of
# v_pbi_sales_budget_live that sales_sman_main.build_budget_temp() puts there,
# and the same table "Sales Dashboard With Salesman", "Sales Dashboard - VQ"
# and "Sales Analysis with Salesman" read. One source, so this board and the
# chart boards cannot answer "what is the target" differently.
#
# It is built ONLY when the client asks for budget (withBudget), because a
# board showing Sales alone should keep costing what it costs today: the copy
# is ~0.4s and every study request would otherwise pay it to show nothing.
# ---------------------------------------------------------------------------

# The (code, label) columns the target is read through, per level.
#
# ONE LEVEL IS ABSENT AND CANNOT BE ADDED: the budget was never captured per
# salesman, and v_pbi_sales_budget_live has no l5 column at all to read one
# from. That is not an oversight to be filled in later; it is the shape of the
# capture. See BUDGET_UNSAFE_LEVELS.
#
# salesTypeGroup reads the budget's OWN sale type (budget_l1_code) rather than
# the sale's, for the reason spelled out at BUDGET_LEVEL_COLUMNS in
# sales_sman_main: l1 is not part of budget_key, so grouping on the sale's sale
# type would count a tuple once per sale type its parts sold under.
#
# NO {m} HERE, and none is needed: build_budget_temp already aliased the
# chosen Regular/Manager pair down to l7_code/l8_code when it filled
# BUDGET_TEMP, exactly as _build_fact does on the actuals. Both halves of the
# board therefore arrive in one taxonomy and every query here stays
# mode-agnostic. Reading l7m/l8m at this point would read the wrong thing --
# the temp table no longer carries them.
_BUDGET_COLUMNS = {
    "salesTypeGroup": ("budget_l1_code", "budget_l1_label"),
    "partnerClassification": ("l2_code", "l2_label"),
    "reportRegion": ("l3_code", "l3_label"),
    "city": ("l4_code", "l4_label"),
    "salesman": ("l5_code", "l5_label"),
    "customer": ("l6_code", "l6_label"),
    "mainCategory": ("l7_code", "l7_label"),
    "subCategory": ("l8_code", "l8_label"),
    "productGroup": ("l9_code", "l9_label"),
    "productSubGroup": ("lfam_code", "lfam_label"),
}


class PbiSalesStudySmanController(http.Controller):
    """The route for the ten-level "Sales Data Study"."""

    # ------------------------------------------------------------------
    # plumbing
    # ------------------------------------------------------------------
    def _query(self, sql, params=()):
        request.env.cr.execute(sql, params)
        cols = [d[0] for d in request.env.cr.description]
        return [dict(zip(cols, row)) for row in request.env.cr.fetchall()]

    def _has_access(self):
        return menu_allowed("pbi_sales_dashboards.menu_pbi_sales_data_study_sman")

    def _fact_available(self):
        request.env.cr.execute("SELECT to_regclass('public.%s')" % FACT_VIEW)
        return bool(request.env.cr.fetchone()[0])

    @staticmethod
    def _sub_field(sub_mode):
        """Regular -> the l7/l8 columns, Manager -> l7m/l8m. Whitelisted, never
        interpolated from the request."""
        return 'm' if sub_mode == 'manager' else ''

    @staticmethod
    def _scope_clause(scope):
        """Whitelisted against SCOPES, so an unknown value narrows to the
        default rather than widening the board by accident."""
        return SCOPES.get(scope if scope in SCOPES else DEFAULT_SCOPE)

    def _default_period(self):
        """The month the board opens on: the one BEFORE the current one --
        the most recent COMPLETE month. Same answer, and the same reasoning, as
        PbiSalesSmanController._default_period, including context_today because
        the server may sit well away from the user's timezone."""
        today = fields.Date.context_today(request.env.user)
        return (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)

    def _year_options(self):
        rows = self._query(
            "SELECT DISTINCT yr FROM " + FACT_VIEW +
            " WHERE yr IS NOT NULL ORDER BY 1 DESC LIMIT 10")
        years = [r["yr"] for r in rows]
        this_year = self._default_period()[0]
        if this_year not in years:
            years.append(this_year)
            years.sort(reverse=True)
        return [{"v": y, "l": str(y)} for y in years]

    # ------------------------------------------------------------------
    # the request's slice
    # ------------------------------------------------------------------
    def _build_fact(self, sub_mode, year, scope, part_no=None):
        """Copy one year of the snapshot into a temp table, once per request.

        Twelve to twenty-two queries then run against it — the grand total, the
        rows of every node asked for, and ten slicer lists — and each is a
        single-table GROUP BY of a few tens of thousands of rows, which is why
        no index and no ANALYZE: measured on dbprod the copy is ~0.3s and every
        query after it 15-45ms, while ANALYZE alone would add 0.6s to every
        expand click for a plan it cannot improve.

        ON COMMIT DROP ties its life to the request's transaction.

        THE PART FILTER IS APPLIED HERE, not downstream, and that is the whole
        design of the control: one clause on the copy narrows the grand total,
        every node and all ten slicer lists at once, and it makes the request
        CHEAPER rather than dearer -- a single part is a few hundred rows out of
        seventy thousand. The snapshot already stores part_no upper-cased and
        trimmed (see sales_sman_fact_view.py), so the request's value is folded
        the same way and compared as equals.

        AND IT REPLACES THE PRODUCT SCOPE RATHER THAN STACKING WITH IT. The
        default scope is the twelve AC product groups, which is the right
        default for a board read as "the business" -- but a part number is not
        a browse, it is a lookup of one known thing, and answering it with an
        empty matrix because the part is a spare or a non-AC MDA line is a
        wrong answer wearing the clothes of an empty one. The scope exists to
        keep the DEFAULT VIEW comparable, and a single-part view is not being
        compared with anything.

        What it must not do is hide the swap. The copy carries in_scope, and
        _resolve_part reports whether the part is inside the scope the control
        still shows, so the board says which of the two it is looking at.
        """
        cr = request.env.cr
        cols = _FACT_COLUMNS.format(m=self._sub_field(sub_mode))
        clauses, params = ["f.yr = %s"], [year]
        if part_no:
            clauses.append("f.part_no = %s")
            params.append(part_no)
        else:
            sc = self._scope_clause(scope)
            if sc:
                clauses.append(sc)
        cr.execute("DROP TABLE IF EXISTS " + FACT_TMP)
        cr.execute(
            "CREATE TEMP TABLE " + FACT_TMP + " ON COMMIT DROP AS SELECT " + cols +
            " FROM " + FACT_VIEW + " f WHERE " + " AND ".join(clauses), params)

    # ------------------------------------------------------------------
    # dimensions
    # ------------------------------------------------------------------
    def _code_expr(self, level):
        """The code a row groups under, with NULL folded onto the Unassigned
        sentinel so a level's missing values stay one addressable row rather
        than disappearing from the matrix."""
        code_col, _ = LEVEL_COLUMNS[level]
        return "COALESCE(%s, '%s')" % (code_col, UNASSIGNED)

    def _group_label_expr(self, level):
        """The caption for a group keyed on the CODE ALONE.

        Falls back to the code before the Unassigned wording: a row with a real
        code and no caption is a naming gap, not an unassigned row, and calling
        it 'Unassigned' would merge it with the genuinely empty ones.

        Every grouping here groups by code and AGGREGATES the caption rather
        than grouping by the pair, for the reason spelled out in
        sales_study_main.py's _group_label_expr: one code carrying two captions
        splits into two matrix rows with its figures divided between them, and
        offers the slicer the same code twice, which OWL refuses to render. The
        snapshot has no such code today — checked across 2026 — but it is built
        from the same legacy masters that produced the case on the bidata side,
        so this board does not rely on that staying true.
        """
        code_col, label_col = LEVEL_COLUMNS[level]
        return "COALESCE(max(%s), max(%s), '%s')" % (label_col, code_col, UNASSIGNED_LABEL)

    def _entry_clauses(self, entries):
        """WHERE fragments for a list of {level, code}.

        Serves both the expanded path and the ten slicers — a slicer value
        narrows the data exactly the way opening that row would, so both go
        through one builder rather than two that could drift. Drilling into
        Unassigned means "the rows with no value here", which is IS NULL, not
        an equality against the sentinel string.
        """
        clauses, params = [], []
        for entry in (entries or []):
            if not isinstance(entry, dict):
                continue
            level, code = entry.get("level"), entry.get("code")
            if level not in LEVEL_COLUMNS or code is None:
                continue
            col = LEVEL_COLUMNS[level][0]
            if str(code) == UNASSIGNED:
                clauses.append("%s IS NULL" % col)
            else:
                clauses.append("%s = %%s" % col)
                params.append(str(code))
        return clauses, params

    def _scope_period_clauses(self, month, scope):
        """The year is already baked into the temp table, so only the month
        survives: the whole year, one month, or everything up to it."""
        if scope == "year":
            return [], []
        if scope == "mtd":
            return ["mth = %s"], [month]
        return ["mth <= %s"], [month]

    def _base_where(self, path, month, scope, level_filters):
        clauses, params = self._scope_period_clauses(month, scope)
        path_clauses, path_params = self._entry_clauses(path)
        filter_clauses, filter_params = self._entry_clauses(
            [{"level": lv, "code": code} for lv, code in (level_filters or {}).items()])
        clauses = clauses + path_clauses + filter_clauses
        params = params + path_params + filter_params
        return clauses, params

    @staticmethod
    def _where(clauses):
        return (" WHERE " + " AND ".join(clauses)) if clauses else ""

    # ------------------------------------------------------------------
    # measures
    # ------------------------------------------------------------------
    @staticmethod
    def _month_measure_sql():
        """Twelve Qty/Value pairs, one per calendar month — see the same method
        in sales_study_main.py for why conditional sums rather than a second
        GROUP BY on the month. The month numbers are loop constants, never
        client input."""
        return ", ".join(
            f"sum(CASE WHEN mth = {m} THEN qty ELSE 0 END) AS qty_{m}, "
            f"sum(CASE WHEN mth = {m} THEN amount ELSE 0 END) AS val_{m}"
            for m in range(1, 13)
        )

    @staticmethod
    def _months_of(row):
        return [[float(row[f"qty_{m}"] or 0), float(row[f"val_{m}"] or 0)]
                for m in range(1, 13)]

    # ------------------------------------------------------------------
    # matrix rows
    # ------------------------------------------------------------------
    def _total(self, month, scope, level_filters, budget_ctx=None):
        clauses, params = self._base_where([], month, scope, level_filters)
        r = self._query(
            "SELECT sum(qty) AS qty, sum(amount) AS value, " + self._month_measure_sql() +
            " FROM " + FACT_TMP + self._where(clauses), params)[0]
        out = {"qty": float(r["qty"] or 0), "value": float(r["value"] or 0),
               "m": self._months_of(r)}
        if budget_ctx:
            # The grand total is above every level, so it is budgetable
            # whenever the SELECTION is -- an unsafe level in a slicer takes it
            # out, an unsafe level merely present in the chain does not.
            out["b"] = self._budget_total(
                [], budget_ctx["year"], month, scope, level_filters,
                budget_ctx["m"])
        return out

    def _levels(self, group_by=None):
        """The drill chain with the chosen group_by level at the top (root)."""
        if group_by and group_by in LEVELS:
            return [group_by] + [lv for lv in LEVELS if lv != group_by]
        return list(LEVELS)

    def _children(self, path, month, scope, level_filters, sort, budget_ctx=None, levels_order=None):
        """One level of the matrix: the rows directly under ``path``.

        ``path``'s LENGTH is the level being grouped in ``levels_order``, so
        children of the root are levels_order[0] (the chosen Group By level).
        A path at the deepest level has no children at all.
        """
        levels_order = levels_order or list(LEVELS)
        depth = len(path)
        if depth >= len(levels_order):
            return {"level": None, "levelLabel": "", "rows": [], "more": 0}
        level = levels_order[depth]
        code_expr, label_expr = self._code_expr(level), self._group_label_expr(level)

        clauses, params = self._base_where(path, month, scope, level_filters)
        order = {
            "qty": "qty DESC NULLS LAST",
            "label": "label ASC",
        }.get(sort, "value DESC NULLS LAST")

        rows = self._query(
            "SELECT " + code_expr + " AS code, " + label_expr + " AS label, "
            "sum(qty) AS qty, sum(amount) AS value, " + self._month_measure_sql() +
            " FROM " + FACT_TMP + self._where(clauses) +
            " GROUP BY 1 HAVING sum(qty) <> 0 OR sum(amount) <> 0"
            " ORDER BY " + order + " LIMIT " + str(ROW_LIMIT + 1), params)

        more = 0
        if len(rows) > ROW_LIMIT:
            more = len(rows) - ROW_LIMIT
            rows = rows[:ROW_LIMIT]
        out_rows = [{
            "code": r["code"], "label": r["label"],
            "qty": float(r["qty"] or 0), "value": float(r["value"] or 0),
            "m": self._months_of(r),
        } for r in rows]

        out = {
            "level": level,
            "levelLabel": LEVEL_LABELS[level],
            "hasChildren": depth + 1 < len(levels_order),
            "more": more,
            "rows": out_rows,
        }

        if budget_ctx:
            # None means "no target at this level or under this selection", and
            # it travels to the client as budget:false plus a reason. An empty
            # dict would mean "a target exists and every row's share of it is
            # zero", which is a different and much more misleading statement.
            reason = self._budget_reason(level, budget_ctx["year"],
                                         budget_ctx["unsafe"])
            by_code = None if reason else self._budget_children(
                level, path, budget_ctx["year"], month, scope, level_filters,
                budget_ctx["m"])
            out["budget"] = by_code is not None
            out["budgetReason"] = reason or (
                None if by_code is not None else
                "this selection narrows the rows by a level the budget "
                "does not carry")
            if by_code is not None:
                for row in out_rows:
                    b = by_code.get(str(row["code"]))
                    if b:
                        row["bqty"], row["bvalue"] = b["qty"], b["value"]
                        row["bm"] = b["m"]
                # A category with a TARGET and no sales this year is a real
                # miss, and dropping it would hide the one row a target-vs-
                # actual reading exists to find. The month cells are the
                # actuals' own zeros; only the target half is populated.
                seen = {str(r["code"]) for r in out_rows}
                extra = [c for c in by_code
                         if c not in seen and (by_code[c]["qty"] or by_code[c]["value"])]
                for code in extra[:max(0, ROW_LIMIT - len(out_rows))]:
                    b = by_code[code]
                    out_rows.append({
                        "code": code,
                        "label": b["label"] or (
                            UNASSIGNED_LABEL if code == UNASSIGNED else code),
                        "qty": 0.0, "value": 0.0,
                        "m": [[0.0, 0.0] for _ in range(12)],
                        "bqty": b["qty"], "bvalue": b["value"], "bm": b["m"],
                    })
        return out

    # ------------------------------------------------------------------
    # the target
    # ------------------------------------------------------------------
    def _budget_columns(self, level, m):
        """The (code, label) pair a level's target is read through, or None.

        None means the budget carries no such column -- salesman and product
        sub-group -- and every caller treats that as "no target here" rather
        than falling back to the actuals' column, which would read a column
        that does not exist.

        ``m`` is accepted and deliberately unused: build_budget_temp has
        already applied the sub-mode by aliasing the chosen pair into
        BUDGET_TEMP, so the column names here are the same in both modes. Kept
        in the signature so the call sites read the same as the actuals' ones.
        """
        return _BUDGET_COLUMNS.get(level)

    def _budget_available(self):
        """Whether there is a target for the years on screen.

        BUDGET_TEMP is year-scoped by build_budget_temp, so this is "a target
        for this year", not "a budget somewhere in this database" -- the same
        answer the chart boards give, and the one the question is really
        asking.
        """
        request.env.cr.execute("SELECT EXISTS (SELECT 1 FROM %s)" % BUDGET_TEMP)
        return bool(request.env.cr.fetchone()[0])

    def _budget_grain_unsafe(self, year, m):
        """Levels where THIS year's budget was captured at a different grain.

        A port of PbiSalesSmanController._budget_grain_unsafe onto this board's
        two temp tables: the "does this code actually sell" sets come from
        FACT_TMP (already scoped to the year and the product scope) and the
        money from BUDGET_TEMP, rather than from the one snapshot table that
        carries both there.

        For each level, the share of the de-duplicated target whose code also
        appears on a row that actually sold. Below BUDGET_RESOLVE_MIN the
        budget is keyed on something that is not this level, and putting it
        beside this level's sales is putting it beside the wrong dimension.
        2026's Customer capture is the case that forced this -- ten channel
        codes, none of which is a customer that sells. See the constant.

        One pass, not one per level: the scan is what costs, so scan once and
        split the answers with FILTER.
        """
        unsafe = set()
        levels, cols = [], []
        for lv in BUDGET_GRAIN_LEVELS:
            pair = self._budget_columns(lv, m)
            if pair:
                levels.append(lv)
                cols.append((LEVEL_COLUMNS[lv][0], pair[0]))
        if not levels:
            return unsafe

        selling = ", ".join(
            "s{n} AS (SELECT DISTINCT {fc} AS code FROM {tmp}"
            "         WHERE amount <> 0 AND {fc} IS NOT NULL)".format(
                n=i, fc=fc, tmp=FACT_TMP)
            for i, (fc, _bc) in enumerate(cols))
        joins = " ".join(
            "LEFT JOIN s{n} ON s{n}.code = f.{bc}".format(n=i, bc=bc)
            for i, (_fc, bc) in enumerate(cols))
        flags = ", ".join(
            "bool_or(s{n}.code IS NOT NULL) AS r{n}".format(n=i)
            for i in range(len(cols)))
        oks = ", ".join(
            "COALESCE(sum(bv) FILTER (WHERE r{n}), 0) AS ok{n}".format(n=i)
            for i in range(len(cols)))
        rows = self._query(
            "WITH " + selling + ", k AS ("
            "  SELECT f.budget_key, max(f.budget_value) AS bv, " + flags +
            "  FROM " + BUDGET_TEMP + " f " + joins +
            "  WHERE f.yr = %s AND f.budget_key IS NOT NULL"
            "  GROUP BY f.budget_key) "
            "SELECT COALESCE(sum(bv), 0) AS total, " + oks + " FROM k", [year])
        row = rows[0] if rows else None
        total = float(row["total"] or 0) if row else 0.0
        # No target for the year at all is not a grain failure -- there is
        # simply nothing to draw, and _budget_available already says so.
        if not total:
            return unsafe
        for i, level in enumerate(levels):
            if float(row["ok%d" % i] or 0) / total < BUDGET_RESOLVE_MIN:
                unsafe.add(level)
        return unsafe

    @staticmethod
    def _budget_reason(level, year, unsafe):
        """Why a level's target cells are blank, in the board's own words.

        Phrased as what the CAPTURE does not carry rather than what the board
        will not draw: the reader's next question is always "why", and "not
        available" does not answer it.
        """
        if level not in unsafe:
            return None
        if level in BUDGET_UNSAFE_REASON:
            return BUDGET_UNSAFE_REASON[level]
        return "the %s budget is not captured per %s" % (
            year, LEVEL_LABELS[level].lower())

    def _budget_entry_clauses(self, entries, m):
        """WHERE fragments for a list of {level, code} against BUDGET_TEMP.

        Returns (clauses, params, ok). ``ok`` is False as soon as an entry sits
        at a level the budget does not carry -- drilling into one salesman
        leaves only the tuples he happened to sell into, and summing their
        target is not "his target"; there is no such number. The caller draws
        nothing rather than a figure that is both inflated and patchy, which is
        the same rule _budget_reliable applies on the chart boards.
        """
        clauses, params = [], []
        for entry in (entries or []):
            if not isinstance(entry, dict):
                continue
            level, code = entry.get("level"), entry.get("code")
            if level not in LEVEL_COLUMNS or code is None:
                continue
            pair = self._budget_columns(level, m)
            if not pair:
                return [], [], False
            col = pair[0]
            if str(code) == UNASSIGNED:
                clauses.append("f.%s IS NULL" % col)
            else:
                clauses.append("f.%s = %%s" % col)
                params.append(str(code))
        return clauses, params, True

    def _budget_where(self, path, year, month, scope, level_filters, m):
        """Period + path + slicers for a budget query. (clauses, params, ok).

        The year is explicit here where the actuals get it from the temp
        table's own build: BUDGET_TEMP carries two years, because the chart
        boards draw a prior-year series and share this build. This board draws
        one.
        """
        clauses = ["f.yr = %s", "f.budget_key IS NOT NULL"]
        params = [year]
        if scope == "mtd":
            clauses.append("f.mth = %s")
            params.append(month)
        elif scope != "year":
            clauses.append("f.mth <= %s")
            params.append(month)
        pc, pp, ok = self._budget_entry_clauses(path, m)
        if not ok:
            return [], [], False
        fc, fp, ok = self._budget_entry_clauses(
            [{"level": lv, "code": code} for lv, code in (level_filters or {}).items()], m)
        if not ok:
            return [], [], False
        return clauses + pc + fc, params + pp + fp, True

    @staticmethod
    def _budget_month_sql():
        """Twelve target Qty/Value pairs, one per calendar month.

        FILTER rather than CASE because these run over the OUTER half of the
        two-stage query, where the figure has already been collapsed per
        budget_key. The month numbers are loop constants, never client input.
        """
        return ", ".join(
            f"COALESCE(sum(t.bq) FILTER (WHERE t.mth = {mo}), 0) AS bqty_{mo}, "
            f"COALESCE(sum(t.bv) FILTER (WHERE t.mth = {mo}), 0) AS bval_{mo}"
            for mo in range(1, 13)
        )

    @staticmethod
    def _budget_months_of(row):
        return [[float(row[f"bqty_{mo}"] or 0), float(row[f"bval_{mo}"] or 0)]
                for mo in range(1, 13)]

    _EMPTY_BUDGET = {"qty": 0.0, "value": 0.0,
                     "m": [[0.0, 0.0] for _ in range(12)]}

    def _budget_two_stage(self, inner_extra, inner_group, outer_extra,
                          outer_group, clauses, params):
        """The only shape a budget query may take on this board.

        max(budget_qty)/max(budget_value) per budget_key FIRST, then sum. The
        figure repeats across the part rows of its tuple wherever this view is
        joined to parts, and collapsing it afterwards instead does not error --
        it silently returns a multiple of the real target (measured elsewhere
        at 2.8x by product sub-group, 7.5x by part). budget_key embeds the
        month, so carrying mth through the inner group keeps every month's
        figure its own rather than a repeat of one.
        """
        return self._query(
            "SELECT " + outer_extra +
            "COALESCE(sum(t.bq), 0) AS qty, COALESCE(sum(t.bv), 0) AS value, " +
            self._budget_month_sql() + " FROM ("
            "SELECT " + inner_extra + "f.mth, f.budget_key,"
            " max(f.budget_qty) AS bq, max(f.budget_value) AS bv"
            " FROM " + BUDGET_TEMP + " f WHERE " + " AND ".join(clauses) +
            " GROUP BY " + ", ".join(
                ([inner_group] if inner_group else []) + ["f.mth", "f.budget_key"]) +
            ") t" +
            (" GROUP BY " + outer_group if outer_group else ""), params)

    def _budget_total(self, path, year, month, scope, level_filters, m):
        """The target behind the grand-total row, under the current selection."""
        clauses, params, ok = self._budget_where(
            path, year, month, scope, level_filters, m)
        if not ok:
            return None
        rows = self._budget_two_stage(
            inner_extra="", inner_group="", outer_extra="",
            outer_group="", clauses=clauses, params=params)
        if not rows:
            return dict(self._EMPTY_BUDGET)
        r = rows[0]
        return {"qty": float(r["qty"] or 0), "value": float(r["value"] or 0),
                "m": self._budget_months_of(r)}

    def _budget_children(self, level, path, year, month, scope, level_filters, m):
        """The target for each row under ``path``, keyed by the row's code.

        None -- not an empty dict -- when this level or this selection carries
        no target: the client draws blank cells and the reason, where an empty
        dict would draw a confident zero.
        """
        pair = self._budget_columns(level, m)
        if not pair:
            return None
        clauses, params, ok = self._budget_where(
            path, year, month, scope, level_filters, m)
        if not ok:
            return None
        code_col, label_col = pair
        rows = self._budget_two_stage(
            inner_extra="COALESCE(f.%s, %%s) AS code, max(f.%s) AS label, " % (
                code_col, label_col),
            inner_group="1",
            outer_extra="t.code, max(t.label) AS label, ",
            outer_group="t.code",
            clauses=clauses, params=[UNASSIGNED] + params)
        return {str(r["code"]): {
            "qty": float(r["qty"] or 0), "value": float(r["value"] or 0),
            "label": r["label"], "m": self._budget_months_of(r),
        } for r in rows}

    def _level_filter_options(self, month, scope, level_filters, levels_order=None):
        """The values each of the ten slicers offers, one query per level.

        Narrowed by the levels ABOVE each one in the chain, matching the
        six-level board. Note this is NOT the leave-one-out rule the salesman
        CHART board uses (_level_filter_options there): on a matrix the chain
        is on screen as the row hierarchy, so a slicer reading "the values that
        exist under what you already picked above" is the same promise the rows
        make. Filtering a level's own list by its own value is what would trap
        the dropdown on one option, and that is excluded here.
        """
        options = {}
        active_levels = levels_order or list(LEVELS)
        for idx, level in enumerate(active_levels):
            ancestors = {lv: level_filters[lv] for lv in active_levels[:idx] if lv in level_filters}
            clauses, params = self._base_where([], month, scope, ancestors)
            rows = self._query(
                "SELECT " + self._code_expr(level) + " AS code, " +
                self._group_label_expr(level) + " AS label, sum(amount) AS value"
                " FROM " + FACT_TMP + self._where(clauses) +
                " GROUP BY 1 ORDER BY 3 DESC NULLS LAST LIMIT " + str(FILTER_OPTION_LIMIT),
                params)
            options[level] = [{"v": r["code"], "l": r["label"]} for r in rows]
        return options

    # ------------------------------------------------------------------
    # THE PART NUMBER
    #
    # Part is a FILTER, never a level. The chain the matrix draws stops at
    # Product Sub-Group (the model family) and stops there on purpose -- see
    # LEVEL_COLUMNS in sales_sman_main.py for why the family and not the parts
    # it ships as. What the control adds is the other direction: given a part,
    # narrow the whole board to it and say where it sits.
    #
    # WHAT "WHERE IT SITS" HONESTLY MEANS. Four of the ten levels are
    # product-side -- Main Category, Sub Category, Product Group, Product
    # Sub-Group -- and a part resolves to exactly one of each, so those four
    # ARE the part's chain. The other six are sale-side: one part sells to many
    # customers, in many cities, through many salesmen. There is no single
    # value to report there and inventing one would be a lie, so _resolve_part
    # reports a level's value only when the slice genuinely holds one, and
    # reports the COUNT otherwise. The client prints both the same way.
    # ------------------------------------------------------------------
    def _resolve_part(self, part_no):
        """Where the part in FACT_TMP sits, level by level.

        Runs AFTER _build_fact has already narrowed the copy to the part, so it
        is one aggregate over a few hundred rows and needs no clause of its own.

        Per level: the single (code, label) when the slice holds exactly one,
        otherwise how many it holds. A level whose rows are all NULL holds one
        value -- the Unassigned sentinel -- and is reported as such, the same
        way the matrix itself folds NULL onto that row.
        """
        sel = ["count(*) AS n", "max(part_label) AS part_label",
               # Whether the part would have survived the AC-groups scope the
               # filter bypassed. bool_or, not bool_and: a part is in scope if
               # any of its rows are, which is how in_scope is set -- per
               # product group, not per line.
               "bool_or(in_scope) AS in_scope"]
        for i, level in enumerate(LEVELS):
            code_col, label_col = LEVEL_COLUMNS[level]
            sel.append("count(DISTINCT %s) AS n%d" % (code_col, i))
            sel.append("min(%s) AS c%d" % (code_col, i))
            sel.append("min(%s) AS b%d" % (label_col, i))
        row = self._query("SELECT " + ", ".join(sel) + " FROM " + FACT_TMP)[0]

        if not row["n"]:
            return {"partNo": part_no, "found": False, "chain": []}

        chain = []
        for i, level in enumerate(LEVELS):
            distinct = row["n%d" % i] or 0
            entry = {"level": level, "label": LEVEL_LABELS[level], "n": distinct}
            if distinct == 0:
                # count(DISTINCT) skips NULLs, so nought means every row is NULL
                # here -- which is the matrix's Unassigned row: one value, not
                # none. _code_expr folds it the same way.
                entry["code"] = UNASSIGNED
                entry["value"] = UNASSIGNED_LABEL
            elif distinct == 1:
                # Falls back to the code before the Unassigned wording, for the
                # reason _group_label_expr gives: a real code with no caption is
                # a naming gap, not an unassigned row.
                entry["code"] = row["c%d" % i]
                entry["value"] = (row["b%d" % i] or row["c%d" % i]
                                  or UNASSIGNED_LABEL)
            chain.append(entry)
        return {"partNo": part_no, "found": True,
                "partLabel": row["part_label"] or "",
                "inScope": bool(row["in_scope"]), "chain": chain}

    # ------------------------------------------------------------------
    # request scrubbing
    # ------------------------------------------------------------------
    @staticmethod
    def _clean_path(path):
        out = []
        for entry in (path or []):
            if not isinstance(entry, dict):
                continue
            level, code = entry.get("level"), entry.get("code")
            if level in LEVEL_COLUMNS and code is not None:
                out.append({"level": level, "code": code})
        return out

    @staticmethod
    def _clean_part(part_no):
        """Fold the request's part number the way the snapshot stores it.

        Upper-cased and trimmed because sales_sman_fact_view.py stores it that
        way -- without it MSTS12CRNAG15-NP-F and ...-np-f are two parts and one
        of them has no sales. Length-capped so the clause can never carry an
        essay; it goes through as a bound parameter either way.
        """
        if not isinstance(part_no, str):
            return None
        return part_no.strip().upper()[:64] or None

    @staticmethod
    def _clean_level_filters(level_filters):
        if not isinstance(level_filters, dict):
            return {}
        return {lv: str(code) for lv, code in level_filters.items()
                if lv in LEVEL_COLUMNS and code not in (None, "", "all")}

    # ------------------------------------------------------------------
    # route
    # ------------------------------------------------------------------
    @http.route('/pbi_dashboards/sales_study_sman/data', type='json', auth='user')
    def sales_study_sman_data(self, period=None, subCategoryMode='regular', scope='year',
                              periodScope='year', sort='value', groupBy='salesTypeGroup',
                              levelFilters=None, nodes=None, meta=True, withBudget=False,
                              partNo=None):
        """Children of every requested node in one round trip.

        Two different "scopes" are in play and they are not related:
        ``scope`` is the PRODUCT scope whitelisted in SCOPES (which lines the
        board may show at all, developer-mode only), ``periodScope`` is
        year/ytd/mtd. The client sends both; the names are kept apart here
        rather than overloaded, because silently applying one as the other
        would change every figure on the board without any visible cause.
        """
        if not self._has_access():
            return {'error': 'You do not have access to this dashboard.'}
        try:
            if not self._fact_available():
                return {'error': 'The salesman sales snapshot has not been built yet. '
                                 'Upgrade the module to create it.'}
            year = month = None
            if period:
                try:
                    y, m = period.split('-')
                    year, month = int(y), int(m)
                except (ValueError, AttributeError):
                    year = month = None
            if year is None or month is None:
                year, month = self._default_period()

            period_scope = periodScope if periodScope in STUDY_SCOPES else 'year'
            level_filters = self._clean_level_filters(levelFilters)
            part_no = self._clean_part(partNo)
            requested = nodes if isinstance(nodes, list) else [{"key": "", "path": []}]
            if len(requested) > MAX_NODES_PER_REQUEST:
                return {'error': f'Too many rows to expand at once ({len(requested)}). '
                                 f'Expand rows individually, or expand a narrower branch.'}

            self._build_fact(subCategoryMode, year, scope, part_no)

            # THE TARGET IS OFF WHILE A PART IS SELECTED, and cannot be
            # otherwise: BUDGET_TEMP has no part_no column, because the budget
            # was never captured per part -- it is captured per budget_key
            # tuple and the snapshot repeats one figure across every part row of
            # that tuple (see the header of sales_sman_main.py). Leaving the
            # target on would therefore draw the WHOLE TUPLE'S target beside one
            # part's sales and call the pair an achievement percentage. This
            # board is exported to Excel; that number would outlive any caveat
            # printed next to it. So it is not drawn, and the reason is sent
            # back for the client to say out loud.
            budget_blocked = ''
            if part_no and withBudget:
                budget_blocked = 'the budget is not captured per part'
                withBudget = False

            # The target is built only when the client is showing it. A board
            # on Sales alone keeps costing exactly what it costs today.
            budget_ctx = None
            if withBudget:
                sub_m = self._sub_field(subCategoryMode)
                build_budget_temp(request.env.cr, year, sub_m)
                if self._budget_available():
                    budget_ctx = {
                        "year": year, "m": sub_m,
                        "unsafe": set(BUDGET_UNSAFE_LEVELS) |
                                  self._budget_grain_unsafe(year, sub_m),
                    }

            levels_order = self._levels(groupBy)

            out_nodes = {}
            for node in requested:
                if not isinstance(node, dict):
                    continue
                key = node.get("key") or ""
                path = self._clean_path(node.get("path"))
                out_nodes[key] = self._children(path, month, period_scope,
                                                level_filters, sort, budget_ctx,
                                                levels_order=levels_order)

            res = {
                "period": {"year": year, "month": month,
                           "monthName": MONTH_NAMES[month - 1],
                           "label": f"{MONTH_NAMES[month - 1]} {year}"},
                "scope": period_scope,
                "groupBy": groupBy if groupBy in LEVELS else LEVELS[0],
                "nodes": out_nodes,
            }
            if meta:
                res["levels"] = [{"v": lvl, "l": LEVEL_LABELS[lvl]} for lvl in levels_order]
                res["allLevels"] = [{"v": lvl, "l": LEVEL_LABELS[lvl]} for lvl in LEVELS]
                res["yearOptions"] = self._year_options()
                res["levelFilterOptions"] = self._level_filter_options(
                    month, period_scope, level_filters, levels_order=levels_order)
                res["total"] = self._total(month, period_scope, level_filters,
                                           budget_ctx)
                res["rowLimit"] = ROW_LIMIT
                # Whether the Budget control has anything to offer at all, and
                # which levels will draw blank cells if it is switched on. The
                # client greys those rather than letting a user pick a view
                # that silently shows nothing.
                res["hasBudget"] = bool(budget_ctx)
                res["budgetBlocked"] = budget_blocked
                # Where this part sits, level by level -- one value per level
                # where the slice holds one, a count where it holds many. Only
                # on a meta reply: it cannot change while the tree is expanded,
                # because the part is baked into the temp table.
                if part_no:
                    res["part"] = self._resolve_part(part_no)
                if budget_ctx:
                    res["budgetUnsafe"] = {
                        lv: self._budget_reason(lv, year, budget_ctx["unsafe"])
                        for lv in sorted(budget_ctx["unsafe"])}
            return res
        except Exception as e:
            return {'error': str(e)}
