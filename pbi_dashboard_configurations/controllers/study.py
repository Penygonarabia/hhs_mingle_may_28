# -*- coding: utf-8 -*-
"""Build the feed-vs-dashboard reconciliation as a standalone HTML file.

WHAT THIS IS FOR. The reconciliation was first done by hand against dbprod --
drive every board over every period, aggregate `v_bidata_live` beside it, and
compare. That answered the question for one server on one day. This route does
the same work on whichever server it runs on, so the next server does not need
the shell session, only the button.

It reports; it never writes. Nothing here changes a row.

TWO SIDES, AND WHY THEY ARE READ DIFFERENTLY
--------------------------------------------
The whole point is that the two columns come from independent paths, so the
comparison is not circular:

  * ACTUAL comes from `v_bidata_live`, the ERP's own extract. Aggregated
    directly here. Value is read from `bi_amount` as the view computes it and
    is never re-derived from quantity -- the view's output quantity is
    catalog-gated while its amount is not, so rebuilding value from units
    roughly halves it. Sales and budget are SEPARATE ROWS keyed by `bi_type`
    ('S' carries bi_qty/bi_amount, 'B' carries bi_budgetqty/bi_budgetamount).
  * DASHBOARD comes from the board's OWN route, `PbiSalesSmanController._data`
    -- not from its SQL re-implemented here. Whatever a reader sees on the KPI
    tile is what this tabulates, which is the only reading that can be checked
    against what they were shown.

PRIOR YEAR is the previous year's own actuals recomputed the same way on both
sides, never the feed's stored `bi_pyamount` column, because that is how the
boards derive it.

PORTABILITY. Nothing about dbprod is assumed:

  * the years come from the data, not a constant;
  * the cutoff month comes from the data too. A part-finished year is reported
    only as far as the boards carry figures, and the months after it are zeroed
    on both sides rather than left half-populated -- on dbprod that fell on
    August 2026, but the rule is "the last month the boards report", not a date.
  * `v_bidata_live` and the sales boards are both PROBED. A server missing
    either gets a document that says so instead of a traceback.

ACCESS. The route gates on this page's own menu, and the sales figures gate a
second time on the sales board's menu through `_data` -- so a reader who may
open Configurations but not the sales boards gets the explanation, not the
numbers.
"""

import json
import logging
import os

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Beside the .sql files, NOT under static/ -- everything under static/ is
# served publicly by Odoo, and a page template is module internals, not a web
# asset. It is read from disk at request time and never enters an asset bundle.
_TEMPLATE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'study', 'study_template.html')

MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')

# How many years the document reports, counting back from the latest the feed
# carries. TWO, because the third adds rows nobody reads: every year already
# shows its predecessor in the prior-year columns, so a third tab only repeats
# what the second tab's comparator already said. An older year that IS still
# needed as a comparator is unaffected -- the prior-year figures are computed
# per period on both sides (the feed's self-join, the board's own ytdLastYear),
# never by reading an earlier row out of this payload -- so dropping a year's
# TAB never blanks another year's comparison.
#
# It also decides how many periods the boards are driven for, which is most of
# the build time.
REPORT_YEARS = 2

# The order the template's columns are declared in. The page reads a flat row
# of (actual, dashboard) pairs in exactly this sequence, so the two must not
# drift apart.
MEASURES = ('sales_val_ytd', 'sales_val_mtd', 'sales_qty_ytd', 'sales_qty_mtd',
            'tgt_val_ytd', 'tgt_val_mtd', 'tgt_qty_ytd', 'tgt_qty_mtd',
            'ly_val_ytd', 'ly_val_mtd', 'ly_qty_ytd', 'ly_qty_mtd')

# Which KPI the board returns for each of those.
_KPI_OF = {
    'sales_val_ytd': 'ytdThisYear',   'sales_val_mtd': 'mtdThisYear',
    'sales_qty_ytd': 'ytdQtyThisYear', 'sales_qty_mtd': 'mtdQtyThisYear',
    'tgt_val_ytd': 'ytdTarget',       'tgt_val_mtd': 'mtdTarget',
    'tgt_qty_ytd': 'ytdQtyTarget',    'tgt_qty_mtd': 'mtdQtyTarget',
    'ly_val_ytd': 'ytdLastYear',      'ly_val_mtd': 'mtdLastYear',
    'ly_qty_ytd': 'ytdQtyLastYear',   'ly_qty_mtd': 'mtdQtyLastYear',
}

_BIDATA_SQL = """
WITH m AS (
  SELECT bi_year AS yr, bi_month AS mth,
         COALESCE(sum(bi_amount)       FILTER (WHERE bi_type='S'), 0)::numeric AS amt,
         COALESCE(sum(bi_qty)          FILTER (WHERE bi_type='S'), 0)::numeric AS qty,
         COALESCE(sum(bi_budgetamount) FILTER (WHERE bi_type='B'), 0)::numeric AS bamt,
         COALESCE(sum(bi_budgetqty)    FILTER (WHERE bi_type='B'), 0)::numeric AS bqty
  FROM v_bidata_live
  WHERE bi_month BETWEEN 1 AND 12
  GROUP BY 1, 2
),
g AS (
  SELECT y.yr, s.mth
  FROM (SELECT DISTINCT yr FROM m) y
  CROSS JOIN (SELECT generate_series(1, 12) AS mth) s
),
f AS (
  SELECT g.yr, g.mth,
         COALESCE(m.amt, 0) AS amt, COALESCE(m.qty, 0) AS qty,
         COALESCE(m.bamt, 0) AS bamt, COALESCE(m.bqty, 0) AS bqty
  FROM g LEFT JOIN m ON m.yr = g.yr AND m.mth = g.mth
),
c AS (
  SELECT yr, mth, amt, qty, bamt, bqty,
         sum(amt)  OVER w AS amt_ytd,  sum(qty)  OVER w AS qty_ytd,
         sum(bamt) OVER w AS bamt_ytd, sum(bqty) OVER w AS bqty_ytd
  FROM f WINDOW w AS (PARTITION BY yr ORDER BY mth ROWS UNBOUNDED PRECEDING)
)
SELECT c.yr, c.mth,
       c.amt, c.amt_ytd, c.qty, c.qty_ytd,
       c.bamt, c.bamt_ytd, c.bqty, c.bqty_ytd,
       COALESCE(p.amt, 0) AS py_amt, COALESCE(p.amt_ytd, 0) AS py_amt_ytd,
       COALESCE(p.qty, 0) AS py_qty, COALESCE(p.qty_ytd, 0) AS py_qty_ytd
FROM c LEFT JOIN c p ON p.yr = c.yr - 1 AND p.mth = c.mth
ORDER BY c.yr, c.mth
"""

_BIDATA_KEY = {
    'sales_val_ytd': 'amt_ytd',  'sales_val_mtd': 'amt',
    'sales_qty_ytd': 'qty_ytd',  'sales_qty_mtd': 'qty',
    'tgt_val_ytd': 'bamt_ytd',   'tgt_val_mtd': 'bamt',
    'tgt_qty_ytd': 'bqty_ytd',   'tgt_qty_mtd': 'bqty',
    'ly_val_ytd': 'py_amt_ytd',  'ly_val_mtd': 'py_amt',
    'ly_qty_ytd': 'py_qty_ytd',  'ly_qty_mtd': 'py_qty',
}


def _f(v):
    return float(v or 0)


class PbiDashboardConfigStudy(http.Controller):

    def _has_access(self):
        from .main import PbiDashboardConfigurations
        return PbiDashboardConfigurations()._has_access()

    # ------------------------------------------------------------------
    @staticmethod
    def _sales_controller():
        """The sales board's own controller, or None where it is not installed.

        Imported here rather than at module scope for the reason this module
        declares no dependency on it: the Configurations page installs on a
        server carrying a different subset of the boards, and an import at the
        top would make that a load-time failure instead of a missing card.
        """
        try:
            from odoo.addons.pbi_sales_dashboards.controllers.sales_sman_main import (
                PbiSalesSmanController, MENU_SMAN,
            )
        except ImportError:
            return None, None
        return PbiSalesSmanController, MENU_SMAN

    def _feed_rows(self):
        """{(yr, mth): {measure: value}} from v_bidata_live, or None if absent."""
        cr = request.env.cr
        cr.execute("SELECT to_regclass('v_bidata_live')")
        if not cr.fetchone()[0]:
            return None
        # The view LEFT JOINs ten stats-less legacy master tables; without this
        # the planner nested-loops every one of them and the query runs for
        # minutes. Set before the first read, and only for this transaction.
        cr.execute("SET LOCAL enable_nestloop = off")
        cr.execute(_BIDATA_SQL)
        cols = [d[0] for d in cr.description]
        out = {}
        for row in cr.fetchall():
            r = dict(zip(cols, row))
            out[(int(r['yr']), int(r['mth']))] = {
                m: _f(r[_BIDATA_KEY[m]]) for m in MEASURES
            }
        return out

    def _board_rows(self, years):
        """{(yr, mth): {measure: value}} from the board's own KPI route."""
        Controller, menu = self._sales_controller()
        if Controller is None:
            return None, 'not_installed'
        ctl = Controller()
        out = {}
        for year in years:
            for month in range(1, 13):
                bundle = ctl._data(menu, period="%d-%02d" % (year, month))
                if isinstance(bundle, dict) and bundle.get('error'):
                    return None, bundle['error']
                kpis = (bundle or {}).get('kpis') or {}
                out[(year, month)] = {m: _f(kpis.get(_KPI_OF[m])) for m in MEASURES}
        return out, None

    # ------------------------------------------------------------------
    def _build(self):
        """(rows, meta) -- the table's data and what to say about it."""
        feed = self._feed_rows()
        meta = {
            'database': request.env.cr.dbname,
            'hasFeed': feed is not None,
            'boardError': None,
        }
        # The years to report: the most recent REPORT_YEARS the feed carries.
        # Trimmed BEFORE the boards are driven, so the periods that would not
        # be shown are not fetched either.
        available = sorted({yr for (yr, _m) in (feed or {})})
        years = available[-REPORT_YEARS:] if available else []
        board, err = self._board_rows(years)
        if err:
            meta['boardError'] = err
        if not years and board:
            years = sorted({yr for (yr, _m) in board})[-REPORT_YEARS:]
        meta['yearsAvailable'] = available

        rows = []
        for year in years:
            for month in range(1, 13):
                a = (feed or {}).get((year, month), {})
                d = (board or {}).get((year, month), {})
                rows.append({
                    'year': year, 'month': month, 'monthName': MONTHS[month - 1],
                    'a': {m: a.get(m, 0.0) for m in MEASURES},
                    'd': {m: d.get(m, 0.0) for m in MEASURES},
                })

        # A part-finished year is reported only as far as the boards carry
        # figures; the months after that are zeroed on BOTH sides rather than
        # left half-populated, which would read as a shortfall rather than as a
        # month that has not happened. Derived, never a hardcoded cutoff.
        cutoff = {}
        for year in years:
            last = 0
            for month in range(1, 13):
                d = (board or {}).get((year, month), {})
                if d.get('sales_val_mtd') or d.get('sales_qty_mtd'):
                    last = month
            cutoff[year] = last or 12
        for r in rows:
            if r['month'] > cutoff[r['year']]:
                for m in MEASURES:
                    r['a'][m] = 0.0
                    r['d'][m] = 0.0
        meta['cutoff'] = cutoff

        payload = [[r['year'], r['monthName']] +
                   [round(r[side][m], 2) for m in MEASURES for side in ('a', 'd')]
                   for r in rows]

        populated = [r for r in rows if r['month'] <= cutoff[r['year']]]
        mismatches = 0
        for r in populated:
            for m in MEASURES:
                tol = 0.005 if '_val_' in m else 0.0
                if abs(r['d'][m] - r['a'][m]) > tol:
                    mismatches += 1
        meta['cells'] = len(populated) * len(MEASURES)
        meta['mismatches'] = mismatches
        meta['years'] = years
        return payload, meta

    # ------------------------------------------------------------------
    @http.route('/pbi_dashboards/config/build_study', type='http', auth='user')
    def build_study(self, **kw):
        if not self._has_access():
            return request.make_response(
                'Forbidden', headers=[('Content-Type', 'text/plain')], status=403)
        try:
            payload, meta = self._build()
            with open(_TEMPLATE, 'r') as fh:
                html = fh.read()
            html = html.replace('"__STUDY_DATA__"', json.dumps(payload, separators=(',', ':')))
            html = html.replace('"__STUDY_META__"', json.dumps(meta, separators=(',', ':')))
        except Exception as exc:                     # noqa: BLE001 - reported, not swallowed
            _logger.exception("config page: building the study document failed")
            return request.make_response(
                'Could not build the study: %s' % exc,
                headers=[('Content-Type', 'text/plain')], status=500)

        _logger.info("config page: %s built the study document (%d rows, %d cells, %d mismatches)",
                     request.env.user.login, len(payload), meta['cells'], meta['mismatches'])
        return request.make_response(html, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Content-Disposition', 'attachment; filename="study_preview.html"'),
        ])
