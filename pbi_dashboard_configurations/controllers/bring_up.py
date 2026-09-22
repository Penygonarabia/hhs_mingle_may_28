# Bringing a from-scratch server up to the schema the boards expect.
#
# WHAT THIS IS FOR. dbprod accumulated things by hand that no module carries:
# a product_family table whose owning model was later removed, a fact view
# compiled when columns existed that a new database has never had. Install the
# pbi stack on a fresh server and none of it errors -- it degrades, which is
# worse, because a board of confident zeroes looks like an answer. This runs
# the steps that close that gap, in the order they have to happen, and reports
# the ones it cannot close rather than leaving them to be discovered later.
#
# WHY init() AND NOT A MODULE UPGRADE. The fact view's SQL is compiled from
# pbi_sales_dashboards' own Python against the schema as it stands at build
# time. Restoring a column it was compiled without does not change the view;
# its text still carries NULL::integer where the column should be, and every
# REFRESH re-runs that same stale text. Odoo rebuilds it by calling the model's
# init(), which is all `-u pbi_sales_dashboards` does that matters here. So
# this calls init() directly: same rebuild, no upgrade machinery, nothing
# staged to disk, and it works on a server where upgrading from a web request
# is not wanted. init() DROPs and re-CREATEs the materialized view WITH DATA
# and rebuilds its indexes and master-data triggers, so it repopulates too --
# which is why step 2 deliberately skips the repair script's own REFRESH.
#
# THIS ONE REBUILDS INSIDE THE REQUEST, AND THAT IS A DELIBERATE EXCEPTION.
# Every other control on this page queues the cron rather than working in the
# request, so one impatient click cannot hold a worker and lock a view. This
# cannot: the cron REFRESHes the view, and a refresh re-runs the definition it
# already has -- the whole problem here is that the definition itself is wrong.
# Only init() rewrites it. So this is a bring-up action, run once against a new
# server, not a routine control, and the button says so. On a database with a
# full ERP feed the rebuild can outlast the HTTP timeout; the work commits or
# rolls back on its own either way, and re-running is safe.
#
# WHAT IT WILL NOT DO. Module load order comes from manifest FILES on disk
# (graph.py Graph.add_modules reads get_manifest(module)['depends']), so no
# request can repair a missing dependency -- see the Upgrade Blockers section.
# The last step detects that case and names it instead of pretending.

import logging

from odoo import http
from odoo.http import request

from . import scripts as scripts_ctl
from .sql_runner import bare_sql

_logger = logging.getLogger(__name__)

# The repair whose schema half this pipeline needs. Its trailing REFRESH is
# dropped here: init() repopulates a moment later, and refreshing the stale
# definition first costs a full populate for nothing.
_SCHEMA_SCRIPT = 'restore_product_category_family_link'
_SKIP_SQL = ('REFRESH MATERIALIZED VIEW', 'ANALYZE V_PBI_SALES_SMAN_FACT')

_FACT_MODEL = 'pbi.sales.sman.fact'

# How long step 3 is allowed to take. NOT the 300s the ad-hoc scripts get:
# that ceiling exists so one careless script cannot sit on the server, while
# this rebuild is a DROP and a CREATE MATERIALIZED VIEW WITH DATA over the
# whole ERP feed and is legitimately the longest thing this page does. Under
# the 300s ceiling -- which step 2 leaves behind, because SET LOCAL outlives
# the savepoint that set it -- the action could not finish on the databases it
# exists for: staging-hhsv3 timed out here on 2026-09-11 with the view already
# dropped and put back. Bounded rather than 0 so a pathological plan still
# ends, and the server sets no timeout of its own (statement_timeout = 0).
_REBUILD_TIMEOUT = '1800s'

# THE REBUILD LOCK. Must equal pbi.sales.sman.fact._REBUILD_LOCK_KEY, which is
# where it is documented. Repeated as a literal because this module depends on
# pbi_dashboards, not pbi_sales_dashboards, so the class is not importable here
# -- and the pipeline has to be able to take the lock on a server where the
# fact model is not loaded at all.
_REBUILD_LOCK_KEY = 7420110

# How long to wait for whatever is already rebuilding. A refresh is ~16s on
# dbprod; a full init() is minutes. Bounded so a stuck holder reports itself
# instead of sitting on the request until the HTTP timeout.
_REBUILD_LOCK_WAIT = '300s'


def _take_rebuild_lock(cr):
    """Wait for any in-flight refresh or rebuild to finish. True if taken.

    STEP 2 CANNOT SAFELY SKIP THIS. It does DDL on the master tables -- ALTER
    TABLE product_category ADD COLUMN product_family, ALTER TABLE res_partner,
    CREATE TABLE product_family -- and then reads the snapshot, while a refresh
    holds the snapshot and then reads the master tables. Opposite orders, both
    ACCESS EXCLUSIVE, and Postgres resolves it by killing one:

        deadlock detected: process A waits for AccessShareLock on relation ...
        blocked by process B; process B waits for AccessShareLock on ...

    And step 2 summons its own opponent. product_category and product_family
    are both in pbi.sales.sman.fact._MASTER_DATA_TABLES, so its own writes fire
    the stale triggers, queue the refresh cron, and the cron thread wakes 60
    seconds later -- inside step 2's still-open transaction. A dev box started
    with --max-cron-threads=0 has no thread to wake, which is why this step
    runs clean locally and deadlocks on a server.

    Taken BEFORE the first relation lock, so there is one global order and no
    cycle. Transaction-scoped: released by the commit or rollback that ends
    this request, never leaked by a worker that dies holding it, and taken
    outside the savepoint in _restore_schema because a savepoint abort would
    drop it while the pipeline ran on.
    """
    # Inside a savepoint: a lock_timeout expiry raises, and an aborted
    # transaction cannot run the reset below -- or anything else the caller
    # wants to report with. A subtransaction that COMMITS hands its locks up to
    # the parent, so the lock outlives the savepoint; one that aborts never
    # held it. Either way the pipeline is left able to talk to the database.
    try:
        with cr.savepoint():
            cr.execute("SET LOCAL lock_timeout = %s", (_REBUILD_LOCK_WAIT,))
            cr.execute("SELECT pg_advisory_xact_lock(%s)", (_REBUILD_LOCK_KEY,))
    except Exception:                               # noqa: BLE001 - reported
        return False
    # Relation locks past this point are the pipeline's own business and some
    # of them are legitimately slow; only the wait above is bounded. SET LOCAL
    # is rolled back with its savepoint, so this is re-stated, not reset.
    cr.execute("SET LOCAL lock_timeout = 0")
    return True


def _leaves_to_step_3(stmt):
    """Is this one of the repair script's refresh statements?

    Read from the statement's SQL, not its first line. The repair script's
    REFRESH is wrapped in a DO block that falls back to a blocking refresh
    where CONCURRENTLY cannot run, so its first line reads `DO $refresh$` and
    a first-line prefix test stopped recognising it -- silently, by running a
    full populate that init() then threw away a moment later. Comments are
    stripped first: half this file's statements DISCUSS the refresh.
    """
    bare = bare_sql(stmt).upper()
    return any(marker in bare for marker in _SKIP_SQL)


def _step(key, name, state, detail, **extra):
    out = {'key': key, 'name': name, 'state': state, 'detail': detail}
    out.update(extra)
    return out


class PbiDashboardConfigBringUp(http.Controller):

    def _has_access(self):
        from .main import PbiDashboardConfigurations
        return PbiDashboardConfigurations()._has_access()

    # ------------------------------------------------------------------ probe
    def _preflight(self):
        """What this database actually has. Read-only, and it decides which of
        the later steps can run at all."""
        cr = request.env.cr
        facts = []

        def regclass(rel):
            cr.execute("SELECT to_regclass(%s)", (rel,))
            return cr.fetchone()[0] is not None

        feed = ['transaction_header', 'transaction_details', 'catalog',
                'customer']
        missing_feed = [t for t in feed if not regclass(t)]
        facts.append('ERP feed: %s of %s tables present'
                     % (len(feed) - len(missing_feed), len(feed)))
        if missing_feed:
            facts.append('MISSING feed tables: %s' % ', '.join(missing_feed))

        cr.execute("""SELECT count(*) FROM information_schema.columns
                       WHERE table_name = 'product_category'
                         AND column_name = 'code'""")
        has_code = cr.fetchone()[0] > 0
        facts.append('product_category.code: %s'
                     % ('present' if has_code else
                        'ABSENT -- the fact view cannot be built without it'))

        unit_parts = 0
        if regclass('catalogflags'):
            cr.execute("SELECT count(DISTINCT cat_part) FROM catalogflags WHERE trim(cat_flag) = '02'")
            unit_parts = cr.fetchone()[0]
        elif regclass('product_tag_product_template_rel') and regclass('product_tag'):
            cr.execute("""SELECT count(DISTINCT pt.default_code)
                          FROM product_template pt
                          JOIN product_tag_product_template_rel r ON r.product_template_id = pt.id
                          JOIN product_tag g ON g.id = r.product_tag_id
                          WHERE TRIM(COALESCE(to_jsonb(g.name)->>'en_US', g.name::text)) IN ('02', '2')""")
            unit_parts = cr.fetchone()[0]
        facts.append("Unit gating ('02' flag/tag): %s part(s)%s"
                     % (unit_parts, '' if unit_parts else
                        ' -- every board QUANTITY will read zero while value is fine'))

        has_budget = regclass('sales_budget_line')
        facts.append('sales_budget_line: %s'
                     % ('present' if has_budget else 'absent'))

        facts.append('product_family: %s'
                     % ('present' if regclass('product_family') else
                        'absent -- step 2 creates it'))

        blocked = bool(missing_feed) or not has_code
        return _step('preflight', '1. Probe this server',
                     'warn' if blocked else 'ok', ' | '.join(facts),
                     blocked=blocked)

    # ------------------------------------------------- schema and master data
    def _restore_schema(self):
        spec = scripts_ctl.SCRIPTS.get(_SCHEMA_SCRIPT)
        statements, _narration, err = scripts_ctl.load_statements(spec)
        if err:
            return _step('product_family', '2. Restore Master Taxonomy & Product Tags',
                         'error', err)
        kept = [s for s in statements if not _leaves_to_step_3(s)]
        skipped = len(statements) - len(kept)
        cr = request.env.cr
        try:
            with cr.savepoint():
                cr.execute("SET LOCAL statement_timeout = '300s'")
                cr.execute("SET LOCAL jit = off")
                cr.execute("SET LOCAL enable_nestloop = off")
                for stmt in kept:
                    cr.execute(stmt)

                # Also run sync_product_tags.sql if available
                tag_spec = scripts_ctl.SCRIPTS.get('sync_product_tags')
                if tag_spec:
                    tag_stmts, _t_narr, _t_err = scripts_ctl.load_statements(tag_spec)
                    if tag_stmts:
                        for t_stmt in tag_stmts:
                            cr.execute(t_stmt)

                # Backfill missing customers and partner classifications
                cr.execute("""SELECT to_regclass('customer'),
                                     to_regclass('transaction_header'),
                                     to_regclass('res_city'),
                                     to_regclass('bidata'),
                                     to_regclass('res_partner'),
                                     to_regclass('partner_classification')""")
                if all(cr.fetchone()):
                    # The INSERT below takes its id from the table default, so
                    # a database whose customer rows arrived with explicit ids
                    # (dump restore, table copy, migrate_amc_to_dbcloud.py --
                    # which resets only three sequences) fails it with
                    # `duplicate key value violates unique constraint
                    # "customer_pkey"`. Same repair, and the same reason, as
                    # Step 0 of sync_and_repair_all_masters.sql. Raises the
                    # sequence to max(id), never lowers it.
                    cr.execute("""
                        SELECT setval(s.seq, v.max_id)
                          FROM (SELECT pg_get_serial_sequence('customer', 'id') AS seq) s,
                               (SELECT COALESCE(max(id), 0) AS max_id FROM customer) v
                         WHERE s.seq IS NOT NULL
                           AND v.max_id > COALESCE(
                                 (SELECT last_value FROM pg_sequences
                                   WHERE (quote_ident(schemaname) || '.' || quote_ident(sequencename))::regclass
                                         = s.seq::regclass), 0)
                    """)
                    cr.execute("""
                        WITH missing_cust AS (
                            SELECT DISTINCT trim(h.trnh_cstno) AS cst_no, max(trim(h.trnh_cstname)) AS cst_name
                              FROM transaction_header h
                              LEFT JOIN customer c ON c.cst_no = trim(h.trnh_cstno)
                             WHERE c.cst_no IS NULL AND NULLIF(trim(h.trnh_cstno), '') IS NOT NULL
                             GROUP BY 1
                        ),
                        stamped AS (
                            SELECT trim(h.trnh_cstno) AS cst_no, trim(h.trnh_sman) AS sman,
                                   ct.code AS city_code, count(*) AS n
                              FROM transaction_header h JOIN res_city ct ON ct.id = h.trnh_cityid
                             GROUP BY 1, 2, 3
                        ),
                        own_city AS (
                            SELECT DISTINCT ON (cst_no) cst_no, city_code
                              FROM (SELECT cst_no, city_code, sum(n) AS n FROM stamped GROUP BY 1, 2) x
                             ORDER BY cst_no, n DESC, city_code
                        ),
                        cust_sman AS (
                            SELECT DISTINCT trim(h.trnh_cstno) AS cst_no, trim(h.trnh_sman) AS sman
                              FROM transaction_header h
                             WHERE COALESCE(trim(h.trnh_sman), '') <> ''
                        ),
                        sman_city AS (
                            SELECT DISTINCT ON (cs.cst_no) cs.cst_no, t.city_code
                              FROM cust_sman cs
                              JOIN (SELECT sman, city_code, sum(n) AS n FROM stamped GROUP BY 1, 2) t
                                ON t.sman = cs.sman
                             ORDER BY cs.cst_no, t.n DESC, t.city_code
                        ),
                        b_class AS (
                            SELECT DISTINCT ON (upper(btrim(bi_cstno)))
                                   upper(btrim(bi_cstno)) AS cst_no,
                                   btrim(bi_cstsubtypecode) AS cst_classification
                              FROM bidata
                             WHERE COALESCE(btrim(bi_cstsubtypecode), '') NOT IN ('', '*')
                             ORDER BY upper(btrim(bi_cstno)), id DESC
                        ),
                        rp_class AS (
                            SELECT DISTINCT ON (upper(btrim(rp.ref)))
                                   upper(btrim(rp.ref)) AS cst_no,
                                   pcl.pc_code AS cst_classification
                              FROM res_partner rp
                              JOIN partner_classification pcl ON pcl.id = rp.partner_classification_id
                             WHERE NULLIF(btrim(rp.ref), '') IS NOT NULL
                             ORDER BY upper(btrim(rp.ref)), rp.id DESC
                        )
                        INSERT INTO customer (cst_no, cst_name, cst_subregion, cst_cstclassification,
                                              create_uid, create_date, write_uid, write_date)
                        SELECT m.cst_no, m.cst_name,
                               COALESCE(o.city_code, s.city_code, 'JED'),
                               COALESCE(bc.cst_classification, rc.cst_classification, '001'),
                               1, now(), 1, now()
                          FROM missing_cust m
                          LEFT JOIN own_city  o ON o.cst_no = m.cst_no
                          LEFT JOIN sman_city s ON s.cst_no = m.cst_no
                          LEFT JOIN b_class  bc ON bc.cst_no = upper(m.cst_no)
                          LEFT JOIN rp_class rc ON rc.cst_no = upper(m.cst_no)
                         WHERE NOT EXISTS (SELECT 1 FROM customer c_ex WHERE c_ex.cst_no = m.cst_no);

                        WITH b_class AS (
                            SELECT DISTINCT ON (upper(btrim(bi_cstno)))
                                   upper(btrim(bi_cstno)) AS cst_no,
                                   btrim(bi_cstsubtypecode) AS cst_classification
                              FROM bidata
                             WHERE COALESCE(btrim(bi_cstsubtypecode), '') NOT IN ('', '*')
                             ORDER BY upper(btrim(bi_cstno)), id DESC
                        ),
                        rp_class AS (
                            SELECT DISTINCT ON (upper(btrim(rp.ref)))
                                   upper(btrim(rp.ref)) AS cst_no,
                                   pcl.pc_code AS cst_classification
                              FROM res_partner rp
                              JOIN partner_classification pcl ON pcl.id = rp.partner_classification_id
                             WHERE NULLIF(btrim(rp.ref), '') IS NOT NULL
                             ORDER BY upper(btrim(rp.ref)), rp.id DESC
                        )
                        UPDATE customer c
                           SET cst_cstclassification = COALESCE(bc.cst_classification, rc.cst_classification, '001'),
                               write_date = now()
                          FROM customer c2
                          LEFT JOIN b_class  bc ON bc.cst_no = upper(btrim(c2.cst_no))
                          LEFT JOIN rp_class rc ON rc.cst_no = upper(btrim(c2.cst_no))
                         WHERE c.id = c2.id
                           AND (c.cst_cstclassification IS NULL OR btrim(c.cst_cstclassification) IN ('', '*'));

                        UPDATE res_partner rp
                           SET partner_classification_id = pcl.id,
                               write_date = now()
                          FROM customer c
                          JOIN partner_classification pcl ON pcl.pc_code = trim(c.cst_cstclassification)
                         WHERE rp.ref = c.cst_no
                           AND (rp.partner_classification_id IS NULL OR rp.partner_classification_id != pcl.id);
                    """)
        except Exception as exc:                    # noqa: BLE001 - reported
            detail = str(exc).strip()
            # The pipeline holds the rebuild lock, so the refresh cron can no
            # longer be the other side of this. Anything still deadlocking here
            # is a party that does not take that lock -- a psql session running
            # the repair by hand, or a module upgrade doing its own DDL -- and
            # saying so beats leaving the oids to be looked up.
            if 'deadlock detected' in detail.lower():
                detail += (' || Something outside this page holds an ACCESS '
                           'EXCLUSIVE lock on the master tables or the '
                           'snapshot. Nothing was changed. Identify it with '
                           "SELECT pid, query FROM pg_stat_activity WHERE "
                           "state <> 'idle', let it finish, and run this "
                           'again.')
            return _step('product_family', '2. Restore Master Taxonomy & Product Tags',
                         'error', detail)
        cr.execute("SELECT count(*) FROM product_family")
        families = cr.fetchone()[0]
        cr.execute("""SELECT count(*) FROM product_category
                       WHERE product_family IS NOT NULL""")
        linked = cr.fetchone()[0]
        return _step('product_family', '2. Restore Master Taxonomy & Product Tags', 'ok',
                     '%s statement(s) run (%s refresh statement(s) left to step 4): '
                     '%s families, %s categories linked, unit tags synchronized'
                     % (len(kept), skipped, families, linked))

    # ------------------------------------------------- budget and salesman attribution
    def _attribute_budget(self):
        cr = request.env.cr
        cr.execute("SELECT to_regclass('sales_budget_line')")
        if not cr.fetchone()[0]:
            return _step('budget_attribution', '3. Seed Budget & Salesman Targets', 'skipped',
                         'sales_budget_line is absent on this server, skipping budget attribution.')

        attr_spec = scripts_ctl.SCRIPTS.get('attribute_salesman_budget')
        if not attr_spec:
            return _step('budget_attribution', '3. Seed Budget & Salesman Targets', 'ok',
                         'Budget table verified.')

        statements, _narr, err = scripts_ctl.load_statements(attr_spec)
        if err:
            return _step('budget_attribution', '3. Seed Budget & Salesman Targets', 'warn',
                         'Attribution script notice: %s' % err)

        try:
            with cr.savepoint():
                cr.execute("SET LOCAL statement_timeout = '300s'")
                cr.execute("SET LOCAL jit = off")
                for stmt in statements:
                    cr.execute(stmt)
        except Exception as exc:
            return _step('budget_attribution', '3. Seed Budget & Salesman Targets', 'warn',
                         'Attribution finished with notice: %s' % str(exc).strip())

        cr.execute("""SELECT count(*), count(salesman_id) FROM sales_budget_line""")
        tot, attr = cr.fetchone()
        return _step('budget_attribution', '3. Seed Budget & Salesman Targets', 'ok',
                     '%s budget lines verified, %s attributed to salesmen' % (tot, attr))

    # ----------------------------------------------------- rebuild the views
    def _rebuild_views(self):
        model = request.env.get(_FACT_MODEL)
        if model is None:
            return _step('rebuild_views', '4. Rebuild the fact and budget views',
                         'skipped',
                         'The Sales Dashboards module is not installed on this '
                         'server, so there is no view to rebuild.')
        cr = request.env.cr
        try:
            with cr.savepoint():
                cr.execute("SET LOCAL statement_timeout = %s", (_REBUILD_TIMEOUT,))
                model.sudo().init()
        except Exception as exc:                    # noqa: BLE001 - reported
            detail = str(exc).strip()
            if getattr(exc, 'pgcode', None) == '57014' or 'statement timeout' in detail:
                detail = (
                    '%s -- this page\'s %s ceiling, not a fault in the view. '
                    'Re-running is safe. If it keeps hitting the ceiling, run '
                    '"9. Create legacy master-table indexes" first (the rebuild '
                    'reads the legacy transaction tables, which carry no planner '
                    'stats until that runs), or rebuild off the request with '
                    '`odoo -d <database> -u pbi_sales_dashboards --stop-after-init`.'
                    % (detail, _REBUILD_TIMEOUT))
            return _step('rebuild_views', '4. Rebuild the fact and budget views',
                         'error',
                         '%s -- the previous view definition was left in place.'
                         % detail)
        cr.execute("SELECT to_regclass('v_pbi_sales_sman_fact')")
        if not cr.fetchone()[0]:
            return _step(
                'rebuild_views', '4. Rebuild the fact and budget views', 'warn',
                'init() ran but left the view unbuilt, which is what it does '
                'when the ERP feed or product_category.code is absent -- see step 1.')
        cr.execute("SELECT count(*) FROM v_pbi_sales_sman_fact")
        rows = cr.fetchone()[0]
        cr.execute("""SELECT pg_get_viewdef('v_pbi_sales_sman_fact'::regclass)
                          ILIKE '%product_family%'""")
        linked = cr.fetchone()[0]
        return _step('rebuild_views', '4. Rebuild the fact and budget views', 'ok',
                     'Rebuilt and repopulated: %s rows. Product Sub-Group is %s '
                     'in the view definition.'
                     % (rows, 'wired' if linked else 'STILL ABSENT'))

    # --------------------------------------- what a button cannot do, by name
    def _remaining(self):
        cr = request.env.cr
        notes = []
        try:
            cr.execute(scripts_ctl.load_order_query())
            for row in cr.fetchall():
                notes.append('MANIFEST, not fixable from here: %s' % row[-1])
        except Exception as exc:                    # noqa: BLE001 - reported
            notes.append('load-order check failed: %s' % str(exc).strip())
        if not notes:
            return _step('remaining', '5. What is left to do by hand', 'ok',
                         'Nothing. All module schemas, dependencies and relations are fully aligned.')
        return _step('remaining', '5. What is left to do by hand', 'warn',
                     ' || '.join(notes))

    # ------------------------------------------------------------- the button
    @http.route('/pbi_dashboards/config/bring_up', type='json', auth='user')
    def bring_up(self, dry_run=False, **kw):
        if not self._has_access():
            return {'error': 'forbidden'}

        steps = [self._preflight()]
        if dry_run:
            steps.append(_step('dry_run', 'Stopped after the probe', 'ok',
                               'Nothing was changed. Run it for real to apply steps 2 to 5.'))
            return {'steps': steps, 'dry_run': True}

        if steps[0].get('blocked'):
            steps.append(_step(
                'aborted', 'Stopped before changing anything', 'error',
                'The ERP feed or product_category.code is missing, so the view '
                'cannot be built and the repair would have nothing to key on. '
                'Load the feed first.'))
            return {'steps': steps}

        _logger.info("pbi config page: %s started the from-scratch bring-up",
                     request.env.user.login)
        # Before step 2 touches anything, and for the whole request: see
        # _take_rebuild_lock. Held until this request commits or rolls back.
        if not _take_rebuild_lock(request.env.cr):
            steps.append(_step(
                'rebuild_lock', 'Stopped before changing anything', 'error',
                'Another rebuild or refresh of v_pbi_sales_sman_fact has held '
                'the snapshot for more than %s. Nothing was changed. Wait for '
                'it to finish -- the nightly cron refresh takes seconds -- and '
                'run this again. If nothing is running, a session is holding '
                'the lock open: SELECT * FROM pg_locks WHERE locktype = '
                "'advisory'." % _REBUILD_LOCK_WAIT))
            return {'steps': steps}
        steps.append(self._restore_schema())
        if steps[-1]['state'] == 'error':
            steps.append(_step('aborted', 'Stopped after the failure above', 'error',
                               'Step 3 was not run: rebuilding the view over a '
                               'half-applied schema would bake the wrong thing in.'))
            return {'steps': steps}
        steps.append(self._attribute_budget())
        steps.append(self._rebuild_views())
        steps.append(self._remaining())
        _logger.info("pbi config page: bring-up finished -> %s",
                     [(s['key'], s['state']) for s in steps])
        return {'steps': steps}
