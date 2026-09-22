# -*- coding: utf-8 -*-
"""Check the feed against the dashboards, and repair what is repairable.

TWO ROUTES, DELIBERATELY SEPARATE. `check_gaps` reads and reports; `fix_gaps`
acts. Nothing repairs anything as a side effect of being asked a question --
someone has to press the second button, having read the first answer.

WHAT A "GAP" IS. A cell where the ERP feed (v_bidata_live) and the board's own
KPI tile disagree, over the periods both report. The comparison is the one
written up in docs/feed_vs_dashboard_review.html and built by study.py, which
this reuses rather than re-implementing -- one definition of the comparison, so
the check cannot drift from the document.

WHAT `fix_gaps` CAN AND CANNOT DO, because the difference matters more than the
button does. It runs three repairs that are already written, reviewed and
idempotent -- it invents no repair logic of its own:

  1. REBUILD THE SNAPSHOT. The boards read a materialised view. A correction
     made anywhere upstream is not on a chart until it is rebuilt, and a stale
     snapshot is the single most common reason for a gap that has no other
     cause.
  2. BACKFILL THE CATALOGUE. A part that sells with no catalogue row cannot be
     classified; where it also has no product group on the line it falls out of
     scope entirely and its value goes missing.
  3. NORMALISE PART-NUMBER CASE. Housekeeping. It has never moved a board
     figure and is not expected to -- it is run because it costs nothing and
     removes a latent trap.

WHAT IT CANNOT FIX, and will say so rather than appearing to try: a gap caused
by the FEED not having the data. If bidata was extracted before a document
posted, no button here can invent that row -- the extract has to run again.
Equally, a gap where the FEED is ahead of the ERP (rows loaded from an export
newer than the ERP tables) closes when the ERP catches up, not from here. Both
show up as periods where one side reports and the other does not, and both are
reported as unfixable rather than attempted.

So a `fix_gaps` that closes nothing is a normal, useful answer: it means the
gap is in the data, not in anything this server can rebuild.
"""

import logging

from odoo import http
from odoo.http import request

from .scripts import SCRIPTS
from .sql_runner import split_statements, strip_meta

_logger = logging.getLogger(__name__)

# The repairs fix_gaps runs, in order, and why each is worth running before the
# next. Keys are entries in scripts.SCRIPTS; the snapshot rebuild is a model
# call and is handled separately, first, because the other two change data the
# snapshot is built FROM.
REPAIR_SCRIPTS = ('catalog_backfill_missing_parts', 'normalise_part_number_case')

_MEASURE_LABEL = {
    'sales_val_ytd': 'Sales value YTD',   'sales_val_mtd': 'Sales value MTD',
    'sales_qty_ytd': 'Sales qty YTD',     'sales_qty_mtd': 'Sales qty MTD',
    'tgt_val_ytd': 'Target value YTD',    'tgt_val_mtd': 'Target value MTD',
    'tgt_qty_ytd': 'Target qty YTD',      'tgt_qty_mtd': 'Target qty MTD',
    'ly_val_ytd': 'Prior-yr value YTD',   'ly_val_mtd': 'Prior-yr value MTD',
    'ly_qty_ytd': 'Prior-yr qty YTD',     'ly_qty_mtd': 'Prior-yr qty MTD',
}

MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def _block(idx, label, columns=(), rows=(), notices=()):
    """One result block in the shape the Configurations page already renders."""
    return {'index': idx, 'sql': label, 'notices': list(notices),
            'columns': list(columns), 'rows': [list(r) for r in rows],
            'rowcount': len(rows), 'truncated': False}


class PbiDashboardConfigGaps(http.Controller):

    def _has_access(self):
        from .main import PbiDashboardConfigurations
        return PbiDashboardConfigurations()._has_access()

    # ------------------------------------------------------------------
    @staticmethod
    def _compare():
        """(gaps, meta) -- every disagreeing cell, from study.py's own build.

        Reusing the document's builder rather than writing a second comparison
        is the point: a check that could disagree with the document it is
        checking would be worse than no check.
        """
        from .study import PbiDashboardConfigStudy, MEASURES
        payload, meta = PbiDashboardConfigStudy()._build()
        gaps = []
        for row in payload:
            year, month_name = row[0], row[1]
            if meta.get('cutoff', {}).get(year, 12) < MONTHS.index(month_name) + 1:
                continue                      # not reported yet on either side
            for i, m in enumerate(MEASURES):
                a, d = row[2 + i * 2], row[3 + i * 2]
                tol = 0.005 if '_val_' in m else 0.0
                if abs(d - a) > tol:
                    gaps.append({'year': year, 'month': month_name, 'measure': m,
                                 'feed': a, 'dashboard': d, 'delta': d - a})
        return gaps, meta

    def _gap_blocks(self, gaps, meta, start=0):
        blocks = [_block(start, 'Comparison summary',
                         ['database', 'years', 'cells compared', 'matching', 'differing'],
                         [[meta.get('database'),
                           ', '.join(str(y) for y in meta.get('years', [])),
                           meta.get('cells', 0),
                           meta.get('cells', 0) - len(gaps),
                           len(gaps)]],
                         notices=['Every populated cell agrees.'] if not gaps else
                                 ['%d cell%s disagree%s.' % (len(gaps),
                                  '' if len(gaps) == 1 else 's',
                                  's' if len(gaps) == 1 else '')])]
        if gaps:
            shown = gaps[:200]
            b = _block(
                start + 1, 'The cells that disagree',
                ['year', 'month', 'measure', 'feed', 'dashboard', 'dashboard − feed'],
                [[g['year'], g['month'], _MEASURE_LABEL.get(g['measure'], g['measure']),
                  '%.2f' % g['feed'], '%.2f' % g['dashboard'], '%+.2f' % g['delta']]
                 for g in shown])
            b['truncated'] = len(gaps) > len(shown)
            blocks.append(b)
        return blocks

    # ------------------------------------------------------------------
    @http.route('/pbi_dashboards/config/check_gaps', type='json', auth='user')
    def check_gaps(self, **kw):
        if not self._has_access():
            return {'error': 'forbidden'}
        try:
            gaps, meta = self._compare()
        except Exception as exc:                     # noqa: BLE001 - reported, not swallowed
            _logger.exception("config page: gap check failed")
            return {'name': 'Feed vs dashboard check', 'blocks': [],
                    'failed': {'index': 0, 'message': str(exc)}, 'statements': 0}
        blocks = self._gap_blocks(gaps, meta)
        if meta.get('boardError'):
            blocks.append(_block(len(blocks), 'Dashboard side unavailable',
                                 notices=[meta['boardError']]))
        if not meta.get('hasFeed'):
            blocks.append(_block(len(blocks), 'Feed unavailable',
                                 notices=['This database has no v_bidata_live, so there is '
                                          'nothing to compare the boards against.']))
        _logger.info("config page: %s ran the gap check (%d gaps over %d cells)",
                     request.env.user.login, len(gaps), meta.get('cells', 0))
        return {'name': 'Feed vs dashboard check', 'writes': False,
                'narration': [], 'blocks': blocks, 'failed': None,
                'statements': len(blocks)}

    # ------------------------------------------------------------------
    def _run_script(self, key):
        """One committed .sql repair, returning its notices. Mirrors scripts.py's
        runner: a savepoint per script, so one failure does not poison the
        cursor and cost us the reply."""
        import os
        from .scripts import _SQL_DIR
        spec = SCRIPTS.get(key)
        if not spec:
            return ['%s: not available on this server.' % key]
        path = os.path.join(_SQL_DIR, spec['file'])
        if not os.path.isfile(path):
            alt = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'scripts', spec['file'])
            if os.path.isfile(alt):
                path = alt
        try:
            with open(path, 'r') as fh:
                raw = fh.read()
        except OSError as exc:
            return ['%s: could not read %s (%s).' % (spec['name'], spec['file'], exc)]
        cr = request.env.cr
        cnx = getattr(cr, '_cnx', None)
        notices = []
        try:
            with cr.savepoint():
                cr.execute("SET LOCAL statement_timeout = '300s'")
                for stmt in split_statements(strip_meta(raw)[0]):
                    if cnx is not None:
                        del cnx.notices[:]
                    cr.execute(stmt)
                    notices += [n.strip() for n in (cnx.notices if cnx else [])]
        except Exception as exc:                     # noqa: BLE001 - reported, not swallowed
            _logger.exception("config page: repair %s failed", key)
            notices.append('FAILED: %s' % exc)
        return notices or ['%s: nothing to report.' % spec['name']]

    @http.route('/pbi_dashboards/config/fix_gaps', type='json', auth='user')
    def fix_gaps(self, **kw):
        if not self._has_access():
            return {'error': 'forbidden'}
        blocks = []
        try:
            before, meta = self._compare()
        except Exception as exc:                     # noqa: BLE001
            _logger.exception("config page: gap fix could not measure first")
            return {'name': 'Repair gaps', 'blocks': [],
                    'failed': {'index': 0, 'message': str(exc)}, 'statements': 0}

        blocks.append(_block(0, 'Before', ['cells compared', 'differing'],
                             [[meta.get('cells', 0), len(before)]]))

        # 1. The snapshot first: the repairs below change data it is built FROM,
        #    so rebuilding before them would throw the work away.
        notices = []
        model = 'pbi.sales.sman.fact'
        if model in request.env:
            try:
                request.env[model].sudo().refresh_fact()
                notices.append('Salesman snapshot rebuilt.')
            except Exception as exc:                 # noqa: BLE001
                _logger.exception("config page: snapshot rebuild failed")
                notices.append('Snapshot rebuild FAILED: %s' % exc)
        else:
            notices.append('No salesman snapshot on this server; nothing to rebuild.')

        # 2 and 3. The committed repairs, then the snapshot again so the boards
        #    read what they changed.
        for key in REPAIR_SCRIPTS:
            notices += self._run_script(key)
        if model in request.env:
            try:
                request.env[model].sudo().refresh_fact()
                notices.append('Snapshot rebuilt again, so the boards read the repairs above.')
            except Exception as exc:                 # noqa: BLE001
                notices.append('Second snapshot rebuild FAILED: %s' % exc)
        blocks.append(_block(1, 'Repairs run', notices=notices))

        after, meta2 = self._compare()
        blocks.append(_block(2, 'After', ['cells compared', 'differing', 'closed'],
                             [[meta2.get('cells', 0), len(after),
                               max(len(before) - len(after), 0)]]))
        blocks += self._gap_blocks(after, meta2, start=3)[1:]

        if after:
            blocks.append(_block(len(blocks), 'Why these remain', notices=[
                'These are gaps in the DATA, not in anything this server rebuilds. '
                'A cell where the feed reports and the boards do not means the ERP '
                'tables have not received it; a cell where the boards report and the '
                'feed does not means the extract ran before the document posted. '
                'Neither can be repaired from here — the extract has to run again, or '
                'the ERP has to catch up.']))
        _logger.info("config page: %s ran the gap repair (%d -> %d gaps)",
                     request.env.user.login, len(before), len(after))
        return {'name': 'Repair gaps', 'writes': True, 'narration': [],
                'blocks': blocks, 'failed': None, 'statements': len(blocks)}
