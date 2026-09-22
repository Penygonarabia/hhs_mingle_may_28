# -*- coding: utf-8 -*-
"""Move `bidata` between servers: export a year here, import it there.

WHY A FILE. A button on one server cannot read another's database, so the data
travels as a CSV that someone downloads and uploads. That is the same route the
2026 load took by hand; this makes it repeatable and guards the parts that were
checked by eye that day.

`bidata` IS AN OUTSIDER. No Odoo module creates it -- it is loaded from outside
by the ERP extract -- so nothing here treats it as a model. It is read and
written as a table, by column name, and the import refuses anything whose header
does not match this server's own columns exactly.

THE KEY IS `id`, NOT `bi_sqlrecid`. The table carries no primary key and no
unique constraint, but `id` IS unique across every row, while `bi_sqlrecid` is
NULL on every budget row -- keying on it would collapse the budget into one row
or duplicate it, depending on which way the upsert fell. Verified before this
was written; the import re-verifies on the file it is given rather than trusting
that it still holds.

INSERT AND UPDATE, NEVER DELETE. A row present here and absent from the file is
LEFT ALONE. The file is a delivery, not a mirror: an export taken before a late
correction would otherwise silently revoke it. If a year genuinely needs
replacing, that is a decision someone makes deliberately, not a side effect of
uploading a smaller file.

IT DIAGNOSES BEFORE IT WRITES, and the diagnosis is the point. It reports how
many rows the file holds, how many already exist, how many are new, and how many
OVERLAP BUT DIFFER -- that last number is the one to read before pressing
anything, because it is the only one that changes data already here.
"""

import csv
import io
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Audit columns are Odoo's, not the feed's, and an export carrying them would
# invite an import that overwrites this server's with another's.
SKIP_COLUMNS = ('create_uid', 'create_date', 'write_uid', 'write_date')

STAGE = 'bidata_import_stage'


def _columns(cr):
    cr.execute("""
        SELECT a.attname
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'bidata' AND n.nspname = 'public'
          AND a.attnum > 0 AND NOT a.attisdropped
        ORDER BY a.attnum
    """)
    return [r[0] for r in cr.fetchall()]


class PbiDashboardConfigBidata(http.Controller):

    def _has_access(self):
        from .main import PbiDashboardConfigurations
        return PbiDashboardConfigurations()._has_access()

    # ---------------------------------------------------------------- years
    @http.route('/pbi_dashboards/config/bidata_years', type='json', auth='user')
    def bidata_years(self, **kw):
        """What this server has, so the page can offer it rather than guess."""
        if not self._has_access():
            return {'error': 'forbidden'}
        cr = request.env.cr
        cr.execute("SELECT to_regclass('bidata')")
        if not cr.fetchone()[0]:
            return {'years': [], 'message': 'This database has no bidata table.'}
        cr.execute("SELECT bi_year, count(*) FROM bidata GROUP BY 1 ORDER BY 1")
        return {'years': [{'year': y, 'rows': n} for y, n in cr.fetchall()]}

    # --------------------------------------------------------------- export
    @http.route('/pbi_dashboards/config/export_bidata', type='http', auth='user')
    def export_bidata(self, years=None, **kw):
        if not self._has_access():
            return request.make_response('Forbidden', status=403,
                                         headers=[('Content-Type', 'text/plain')])
        cr = request.env.cr
        try:
            wanted = sorted({int(y) for y in (years or '').split(',') if y.strip()})
        except ValueError:
            return request.make_response('Bad years', status=400,
                                         headers=[('Content-Type', 'text/plain')])
        if not wanted:
            return request.make_response('No years given', status=400,
                                         headers=[('Content-Type', 'text/plain')])

        cols = [c for c in _columns(cr) if c not in SKIP_COLUMNS]
        buf = io.StringIO()
        # COPY, not a fetchall: a year of bidata is ~60k rows and streaming it
        # through the server's own CSV writer keeps it out of Python memory.
        cr.copy_expert(
            "COPY (SELECT %s FROM bidata WHERE bi_year IN (%s) ORDER BY id) "
            "TO STDOUT WITH (FORMAT csv, HEADER true, NULL 'NULL')"
            % (', '.join('"%s"' % c for c in cols),
               ', '.join(str(y) for y in wanted)), buf)
        data = buf.getvalue()
        name = 'bidata_%s.csv' % '_'.join(str(y) for y in wanted)
        _logger.info("config page: %s exported bidata %s (%d bytes)",
                     request.env.user.login, wanted, len(data))
        return request.make_response(data, headers=[
            ('Content-Type', 'text/csv; charset=utf-8'),
            ('Content-Disposition', 'attachment; filename="%s"' % name),
        ])

    # --------------------------------------------------------------- import
    @http.route('/pbi_dashboards/config/import_bidata', type='http',
                auth='user', methods=['POST'], csrf=False)
    def import_bidata(self, csv_file=None, apply=None, **kw):
        """Diagnose the uploaded file, and write only when `apply` says to.

        Two passes over one upload: the first reports what the file would do,
        the second does it. The page calls this twice with the same file so the
        reader sees the numbers before anything changes.
        """
        if not self._has_access():
            return request.make_response('{"error":"forbidden"}', status=403,
                                         headers=[('Content-Type', 'application/json')])
        import json as _json

        def reply(payload, status=200):
            return request.make_response(_json.dumps(payload), status=status,
                                         headers=[('Content-Type', 'application/json')])

        cr = request.env.cr
        cr.execute("SELECT to_regclass('bidata')")
        if not cr.fetchone()[0]:
            return reply({'error': 'This database has no bidata table.'})
        if csv_file is None:
            return reply({'error': 'No file was uploaded.'})

        raw = csv_file.read()
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8-sig')
        header = next(csv.reader(io.StringIO(raw)), None)
        if not header:
            return reply({'error': 'The file is empty.'})

        table_cols = _columns(cr)
        unknown = [c for c in header if c not in table_cols]
        if unknown:
            return reply({'error': 'The file has columns this server’s bidata does not: %s'
                                   % ', '.join(unknown[:8])})
        if 'id' not in header or 'bi_year' not in header:
            return reply({'error': 'The file must carry at least id and bi_year.'})

        quoted = ', '.join('"%s"' % c for c in header)
        try:
            with cr.savepoint():
                cr.execute('DROP TABLE IF EXISTS %s' % STAGE)
                cr.execute('CREATE TEMP TABLE %s (LIKE bidata INCLUDING DEFAULTS) '
                           'ON COMMIT DROP' % STAGE)
                cr.copy_expert(
                    "COPY %s (%s) FROM STDIN WITH (FORMAT csv, HEADER true, NULL 'NULL')"
                    % (STAGE, quoted), io.StringIO(raw))

                cr.execute('SELECT count(*), count(DISTINCT id) FROM %s' % STAGE)
                n_rows, n_ids = cr.fetchone()
                if n_rows != n_ids:
                    return reply({'error': 'The file repeats %d id(s); it cannot be keyed on id.'
                                           % (n_rows - n_ids)})

                cr.execute('SELECT DISTINCT bi_year FROM %s ORDER BY 1' % STAGE)
                file_years = [r[0] for r in cr.fetchall()]
                cr.execute('SELECT count(*) FROM %s s JOIN bidata b ON b.id = s.id' % STAGE)
                overlap = cr.fetchone()[0]
                cr.execute('SELECT count(*) FROM %s s WHERE NOT EXISTS '
                           '(SELECT 1 FROM bidata b WHERE b.id = s.id)' % STAGE)
                new = cr.fetchone()[0]
                # An id here under a DIFFERENT year is the dangerous case: the
                # two servers' id spaces have collided and an upsert would
                # rewrite an unrelated row.
                cr.execute('SELECT count(*) FROM %s s JOIN bidata b ON b.id = s.id '
                           'WHERE b.bi_year IS DISTINCT FROM s.bi_year' % STAGE)
                collisions = cr.fetchone()[0]
                diff_cols = [c for c in header if c not in ('id',) + SKIP_COLUMNS]
                cr.execute('SELECT count(*) FROM %s s JOIN bidata b ON b.id = s.id WHERE (%s) '
                           'IS DISTINCT FROM (%s)'
                           % (STAGE,
                              ', '.join('s."%s"' % c for c in diff_cols),
                              ', '.join('b."%s"' % c for c in diff_cols)))
                differing = cr.fetchone()[0]

                diagnosis = {
                    'rows_in_file': n_rows, 'years_in_file': file_years,
                    'already_present': overlap, 'new_rows': new,
                    'overlapping_but_different': differing,
                    'year_collisions': collisions,
                }

                if collisions:
                    return reply({'error': 'Refused: %d row(s) in the file share an id with a row '
                                           'here belonging to a DIFFERENT year. The two databases’ '
                                           'id spaces have diverged and an upsert would rewrite '
                                           'unrelated rows.' % collisions,
                                  'diagnosis': diagnosis})

                if not apply:
                    return reply({'diagnosis': diagnosis, 'applied': False})

                sets = ', '.join('"%s" = s."%s"' % (c, c) for c in diff_cols)
                cr.execute('UPDATE bidata b SET %s FROM %s s WHERE s.id = b.id AND (%s) '
                           'IS DISTINCT FROM (%s)'
                           % (sets, STAGE,
                              ', '.join('s."%s"' % c for c in diff_cols),
                              ', '.join('b."%s"' % c for c in diff_cols)))
                updated = cr.rowcount
                cr.execute('INSERT INTO bidata (%s) SELECT %s FROM %s s '
                           'WHERE NOT EXISTS (SELECT 1 FROM bidata b WHERE b.id = s.id)'
                           % (quoted, quoted, STAGE))
                inserted = cr.rowcount
                cr.execute('ANALYZE bidata')
                diagnosis.update({'updated': updated, 'inserted': inserted})
        except Exception as exc:                     # noqa: BLE001 - reported, not swallowed
            _logger.exception("config page: bidata import failed")
            return reply({'error': 'The import failed: %s' % exc})

        _logger.info("config page: %s imported bidata (%d updated, %d inserted, years %s)",
                     request.env.user.login, diagnosis['updated'], diagnosis['inserted'],
                     diagnosis['years_in_file'])
        return reply({'diagnosis': diagnosis, 'applied': True})
