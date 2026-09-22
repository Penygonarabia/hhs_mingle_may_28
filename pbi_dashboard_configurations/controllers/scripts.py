# The maintenance-script actions on the Configurations page.
#
# NOTHING HERE TAKES SQL FROM A REQUEST. The page offers a fixed list of named
# actions; each runs a .sql file committed inside this module, and the request
# carries only a key that is looked up in SCRIPTS below. A key that is not in
# that dict is refused, so an unexpected value can never reach the filesystem
# or the cursor.
#
# That is the whole point of the design. These files went through review like
# any other code, they diagnose before they change anything, they guard every
# write and they are safe to run twice. A textarea would have none of that, and
# the log would only ever say "someone ran something".

import logging
import os

from odoo import http
from odoo.http import request

from .sql_runner import split_statements, strip_meta

_logger = logging.getLogger(__name__)

_SQL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sql')

# Rows returned per statement. Enough to read a diagnosis, small enough that a
# careless SELECT cannot push megabytes into a browser.
_MAX_ROWS = 200

# Per-statement ceiling. The reason this page exists is that a REFRESH run by
# hand in a SQL client ran for minutes and took a server with it; nothing
# started from here is allowed to do that.
_STATEMENT_TIMEOUT = '300s'

SCRIPTS = {
    'sync_product_tags': {
        'file': 'sync_product_tags.sql',
        'name': '★ Sync Product Unit Tags (02 & 10)',
        'step': 1,
        'date': '2026-09-12',
        'group_key': 'tags_2026-09-12',
        'group_title': '2026-09-12 — Product Unit Tag & Scope Synchronization',
        'group_note': 'Idempotently ensures tags 02 (Machine Unit Gated) and 10 (AC Scope) exist in product_tag and populates product_tag_product_template_rel from catalogflags.',
        'writes': True,
        'note': 'Establishes Odoo-native unit gating to eliminate split-system double-counting.',
    },
    'check_sman_fact_budget_integrity': {
        'file': 'check_sman_fact_budget_integrity.sql',
        'name': '2. Check 10-Level Target & Deduplication Integrity',
        'step': 3,
        'date': '2026-09-12',
        'group_key': 'budget_2026-09-12',
        'group_title': '2026-09-12 — Multi-Year Budget & Salesman Attribution',
        'group_note': 'Validates that SUM(budget_value) across 10 levels matches v_sales_budget_month control totals exactly.',
        'writes': False,
        'note': 'Audits two-stage MAX(budget_value) deduplication across all 10 hierarchy levels.',
    },
    'create_bidata_table_and_live_view': {
        'file': 'create_bidata_table_and_live_view.sql',
        'name': '★ Create the bidata table and v_bidata_live',
        'step': 1,
        'date': '2026-09-11',
        'group_key': 'bidata_2026-09-11',
        'group_title': '2026-09-11 — Bidata Feed',
        'group_note': 'The ERP feed arrives outside Odoo, so no module creates bidata and none creates v_bidata_live over it. This builds both; the rows come across with Move Bidata.',
        'writes': True,
        'note': 'Creates bidata with dbprod\'s full 52-column shape and both indexes, and '
                'builds v_bidata_live over it. Where the table is already present but '
                'NARROWER -- staging-hhsv3\'s feed arrived without bi_invprice -- every '
                'missing column is added, because a half-right table passes the '
                'to_regclass guards and pushes the failure somewhere else. Ships the '
                'SHAPE only: 292,682 rows and ~86MB of data would live in this repo\'s '
                'history forever, so the rows move through the Move Bidata card instead. '
                'The view is skipped with a notice, not an error, on a database missing '
                'the legacy ERP masters it reads. Drops and recreates the view rather '
                'than CREATE OR REPLACE, which refuses whenever the column list differs '
                '-- exactly the case this repairs. Safe to run twice.',
    },
    'diagnose_module_load_order': {
        'file': 'diagnose_module_load_order.sql',
        'name': '★ Diagnose Module Load Order & Related Fields',
        'step': 1,
        'date': '2026-09-11',
        'group_key': 'load_order_2026-09-11',
        'group_title': '2026-09-11 — Module Load Order & Related Fields',
        'group_note': 'Finds the missing manifest dependency behind "KeyError: Field '
                      '<name> referenced in related field definition <model>.<name> does '
                      'not exist." -- the error that aborts EVERY module upgrade and '
                      'presents itself as a pbi failure when it is nothing of the kind.',
        'writes': False,
        'note': 'Read-only, and it deliberately has no repair half. Odoo builds the '
                'module graph from the manifest FILES on disk, not from '
                'ir_module_module_dependency, so no SQL can change load order -- '
                'writing that table would only change what the Apps list draws, and '
                '_update_dependencies erases it on the next module update. What this '
                'does instead is name the module, the field, the module owning the '
                'related target, and the exact line to add to depends. Filters out '
                'transient models and Odoo-authored modules, without which it returns '
                'about fifty structural rows and is useless; block 3 counts everything '
                'it skipped. Found the salesman_new_partner / salesman_type break on '
                'staging-hhsv3 on 2026-09-11.',
    },
    'merge_duplicate_partner_classifications': {
        'file': 'merge_duplicate_partner_classifications.sql',
        'name': '★ De-duplicate Partner Classification',
        'step': 1,
        'date': '2026-09-11',
        'group_key': 'pclass_2026-09-11',
        'group_title': '2026-09-11 — Duplicate Master Repair',
        'group_note': 'A master imported twice doubles every figure that resolves it by code. '
                      'This restores one row per code and constrains it.',
        'writes': True,
        'note': 'Run before the rebuild, not after. v_pbi_sales_sman_fact resolves '
                'partner_classification BY CODE on both the actuals and the budget side, '
                'and has always assumed one row per code -- the view says so in its own '
                'comments ("verified: 6/3/6/10/6 rows, no duplicates"). Nothing enforced '
                'it, and staging-hhsv3 held two complete copies, ids 11-20 and 21-30: '
                'every invoice line matched two rows and was summed twice, so value and '
                'quantity both read double and the target doubled with them. August 2026 '
                'drew 132,903,672 against the 50,330,445 the ERP holds. Merges each '
                'duplicated code onto its lowest id, repoints every foreign key found in '
                'pg_constraint rather than a list written here, drops the stale external '
                'ids, and adds the UNIQUE index that stops it recurring. Declines a code '
                'whose copies are not identical rather than deciding which one the sales '
                'belong to. The snapshot still holds the doubled rows until it is rebuilt. '
                'Safe to run twice.',
    },
    'restore_product_category_family_link': {
        'file': 'restore_product_category_family_link.sql',
        'name': '★ Restore Product Sub-Group link (product_family)',
        'step': 1,
        'date': '2026-09-11',
        'group_key': '2026-09-11',
        'group_title': '2026-09-11 — Product Sub-Group Link Repair',
        'group_note': 'Restores product_category.product_family (dropped when dashboard_groups\' product.family model was removed) and rebuilds the fact snapshot so Product Sub-Group shows This Year/Last Year again, not just Target.',
        'writes': True,
        'note': 'Creates the product_family table where the database has none (nothing '
                'else does any more -- the owning model was removed and pbi_sales_dashboards '
                'only probes for the table), re-adds product_category.product_family and the '
                'product_family.pfam_ref unique constraint, repopulates the link from '
                'catalog/bidata (same logic as Complete Master Sync\'s Step 5b), refreshes '
                'v_pbi_sales_sman_fact with the correct planner hints -- falling back to a '
                'blocking refresh where the concurrent one cannot run, rather than losing '
                'the repair to a refresh the cron started meanwhile -- and reports what the '
                'database holds afterwards. Safe to run twice. If it had to create the table '
                'or the column, the view definition is stale by construction and needs '
                '`-u pbi_sales_dashboards`, not another run of this script -- the last block '
                'says so outright in view_state. Step 0 was added 2026-09-11 after the script '
                'died on staging-hhsv3 with `relation "product_family" does not exist`.',
    },
    'sync_and_repair_all_masters': {
        'file': 'sync_and_repair_all_masters.sql',
        'name': '★ Complete Master Sync & Gap Repair',
        'step': 1,
        'date': '2026-09-07',
        'group_key': '2026-09-07',
        'group_title': '2026-09-07 — Target Alignment & Dashboard Verification',
        'group_note': 'Complete 1-click pipeline: repairs master taxonomy, normalises part numbers, builds indexes, rebuilds fact/budget snapshots, and verifies 0 gaps across Target, Sales & Last Year.',
        'writes': True,
        'note': 'All-in-one execution: case normalisation + catalog backfill + AC scope fix + master indexes + '
                'materialized view rebuilds + 10-level audit for Target, TY Sales & LY Sales in a single transaction. '
                'Step 0 was added 2026-09-15 after the script died on the server with `duplicate key value violates '
                'unique constraint "customer_pkey"` while running clean locally: the inserts take their id from the '
                'table default, and on a database whose rows arrived with explicit ids (dump restore, table copy, '
                'scripts/migrate_amc_to_dbcloud.py -- which resets only three sequences) the sequence still sits '
                'below max(id). Step 0 raises the sequence on every table this script inserts into -- customer, '
                'catalog, product_tag, product_family, product_category -- to max(id), never lowers one, and skips '
                'tables the database does not have.',
    },
    'verify_links_gaps_and_alignment': {
        'file': 'verify_links_gaps_and_alignment.sql',
        'name': '1. Verify Links, Gaps and Data Alignments',
        'step': 2,
        'date': '2026-09-07',
        'group_key': '2026-09-07',
        'group_title': '2026-09-07 — Target Alignment & Dashboard Verification',
        'group_note': 'Complete 1-click pipeline: repairs master taxonomy, normalises part numbers, builds indexes, rebuilds fact/budget snapshots, and verifies 0 gaps across Target, Sales & Last Year.',
        'writes': False,
        'note': 'Read-only. One check covering all three: master link gaps across the ten levels for This Year, Last Year '
                'and Target; target-vs-actuals alignment by Year, Sales Type Group, Region, Main and Sub-Category; and '
                'snapshot coverage with the unassigned breakdown. Replaces the separate diagnose, verify and '
                'rebuild-verify actions -- the rebuild half of that last one is what the Complete Master Sync does.',
    },
    'diagnose_and_clean_salesman_type_id': {
        'file': 'diagnose_and_clean_salesman_type_id.sql',
        'name': '4. Diagnose & Clean salesman_type_id (Studio fields only)',
        'step': 5,
        'date': '2026-09-07',
        'group_key': '2026-09-07',
        'group_title': '2026-09-07 — Target Alignment & Dashboard Verification',
        'group_note': 'Complete 1-click pipeline: repairs master taxonomy, normalises part numbers, builds indexes, rebuilds fact/budget snapshots, and verifies 0 gaps across Target, Sales & Last Year.',
        'writes': True,
        'note': 'Diagnoses and cleans up orphaned manual/studio salesman_type_id field definitions on res.users in ir_model_fields. '
                'Only touches state=manual rows, which is all a delete can fix. If the '
                'diagnosis comes back state=base the field is declared in live Python and '
                'the delete changes nothing -- that is a missing manifest dependency, and '
                'the Upgrade Blockers section diagnoses it. That is what it turned out to '
                'be on staging-hhsv3 on 2026-09-11. '
                'To search server Python modules, run: grep -rn "salesman_type_id" /var/odoo/staging-hhsv3.cieloapps.com/',
    },
    'ac_scope_data_fixes': {
        'file': 'ac_scope_data_fixes_portable.sql',
        'name': '3. Repair AC scope master data',
        'step': 3,
        'date': '2026-09-04',
        'group_key': '2026-09-04',
        'group_title': '2026-09-04 — Master Data & Scope Repairs',
        'group_note': 'Repairs missing/deleted product groups, restores ATOM taxonomy, and links dangling invoice lines.',
        'writes': True,
        'note': 'Diagnoses first, then restores the ATOM product group if this '
                'database has the dangling reference, and fills in the missing '
                'product group on IN10133375. Declines rather than guesses when '
                'a lookup is ambiguous. Safe to run twice.',
    },
    'catalog_backfill_missing_parts': {
        'file': 'catalog_backfill_missing_parts.sql',
        'name': '4. Backfill uncatalogued selling parts',
        'step': 4,
        'date': '2026-09-04',
        'group_key': '2026-09-04',
        'group_title': '2026-09-04 — Master Data & Scope Repairs',
        'group_note': 'Repairs missing/deleted product groups, restores ATOM taxonomy, and links dangling invoice lines.',
        'writes': True,
        'note': 'The catalog feed is external, and where it stops delivering, '
                'every part introduced afterwards has no Product Group -- the '
                'boards show it under "Unassigned" while every total stays '
                'correct, so it hides. Diagnoses first: reports when the feed '
                'last delivered and which parts are missing. Then gives each '
                'one the group its own invoice lines carry, and the sub-group '
                'only where that is genuinely a child of the group. Safe to run twice.',
    },
    'normalise_part_number_case': {
        'file': 'normalise_part_number_case.sql',
        'name': '5. Normalise part number casing',
        'step': 5,
        'date': '2026-09-04',
        'group_key': '2026-09-04',
        'group_title': '2026-09-04 — Master Data & Scope Repairs',
        'group_note': 'Repairs missing/deleted product groups, restores ATOM taxonomy, and links dangling invoice lines.',
        'writes': True,
        'note': 'Moves invoice lines whose part number was typed in the wrong '
                'letter case onto the form the catalogue holds. Diagnoses first, '
                'and declines rather than guesses if the catalogue itself holds a '
                'part under two casings. Housekeeping that removes a latent trap '
                'for anything joining on the part number without upper-casing. Safe to run twice.',
    },
    'check_bidata_feed_gaps': {
        'file': 'check_bidata_feed_gaps.sql',
        'name': '6. Check bidata feed gaps',
        'step': 6,
        'date': '2026-09-03',
        'group_key': '2026-09-03',
        'group_title': '2026-09-03 — Feed Diagnostics & Alignment',
        'group_note': 'Identifies ERP feed timing differences and aligns split unit views.',
        'writes': False,
        'note': 'Read-only. Lists documents the ERP has posted that the bidata '
                'extract never received, and compares the live figures against '
                'the fed ones month by month.',
    },
    'v_bidata_live_case_insensitive_unit_gate': {
        'file': 'v_bidata_live_case_insensitive_unit_gate.sql',
        'name': '7. Case-insensitive unit gate for v_bidata_live',
        'step': 7,
        'date': '2026-09-03',
        'group_key': '2026-09-03',
        'group_title': '2026-09-03 — Feed Diagnostics & Alignment',
        'group_note': 'Identifies ERP feed timing differences and aligns split unit views.',
        'writes': True,
        'note': 'Updates view v_bidata_live so split AC units with lower-cased part '
                'numbers match catalogflags "02" unit gate instead of miscounting as '
                'zero quantity. Reports which of the twelve legacy masters this '
                'database has, and where t_rptregionsdesc is not one of them -- the '
                'report-region master, absent on staging-hhsv3, which used to abort '
                'this script -- creates it and seeds it from the codes bidata and '
                'res_region already carry. t_regionsdesc is a different table and is '
                'not used as a stand-in. An existing master is left untouched. '
                'Re-runnable and idempotent.',
    },
    'delete_CR20112352_bidata_align': {
        'file': 'delete_CR20112352_bidata_align.sql',
        'name': '8. Align June 2026 Credit Note (Optional)',
        'step': 8,
        'date': '2026-09-03',
        'group_key': '2026-09-03',
        'group_title': '2026-09-03 — Feed Diagnostics & Alignment',
        'group_note': 'Identifies ERP feed timing differences and aligns split unit views.',
        'writes': True,
        'note': 'Deletes posted return credit note CR20112352 to strictly align '
                'June 2026 actuals with a lagging bidata snapshot missing this '
                'document. Run only if feed alignment is strictly required.',
    },
    'legacy_master_join_key_indexes': {
        'file': 'legacy_master_join_key_indexes.sql',
        'name': '9. Create legacy master-table indexes',
        'step': 9,
        'date': '2026-08-27',
        'group_key': '2026-08-27',
        'group_title': '2026-08-27 — Database Performance & Indexes',
        'group_note': 'Optimizes query execution plans and eliminates sequential scans on master lookups.',
        'writes': True,
        'note': 'Unique indexes on the join keys of the ten legacy master '
                'tables the dashboards read, plus fresh statistics. Uses IF NOT '
                'EXISTS throughout, so it is a no-op once applied.',
    },
}


def first_line(stmt):
    """The first line that is not a comment, for labelling a result block."""
    for line in stmt.splitlines():
        text = line.strip()
        if text and not text.startswith('--'):
            return text[:120]
    return stmt.strip()[:120]


def resolve_path(spec):
    """Where this script's .sql actually is on THIS server.

    sql/ holds the real files, so a deploy of this module folder alone carries
    them. The fallback to <addons root>/scripts/ is for the reverse: a checkout
    still on the old layout, where sql/ was symlinks into the repository's
    scripts/ directory and a module-only deploy left all of them dangling --
    which is exactly how staging-hhsv3 failed on 2026-09-11. os.path.isfile
    follows links, so a live symlink is found by the first branch and a dead
    one falls through to the fallback.
    """
    path = os.path.join(_SQL_DIR, spec['file'])
    if os.path.isfile(path):
        return path
    alt = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'scripts', spec['file'])
    return alt if os.path.isfile(alt) else path


def load_statements(spec):
    """(statements, narration, error). One implementation, so the bring-up
    pipeline and the per-script buttons can never disagree about what a file
    contains or how it is split."""
    if not spec:
        return [], [], 'unknown_script'
    path = resolve_path(spec)
    try:
        with open(path, 'r') as fh:
            raw = fh.read()
    except OSError as exc:
        _logger.error("pbi config page: cannot read %s: %s", path, exc)
        return [], [], ('The script file %s could not be read on this server: %s'
                        % (spec['file'], exc))
    cleaned, narration = strip_meta(raw)
    return split_statements(cleaned), narration, None


def load_order_query():
    """The load-order detector's first block, on its own.

    Read from the committed .sql rather than restated here, so the query the
    bring-up reports on is by construction the same one the Upgrade Blockers
    card runs.
    """
    statements, _narration, err = load_statements(SCRIPTS['diagnose_module_load_order'])
    if err or not statements:
        raise RuntimeError(err or 'diagnose_module_load_order.sql is empty')
    return statements[0]


class PbiDashboardConfigScripts(http.Controller):

    def _has_access(self):
        from .main import PbiDashboardConfigurations
        return PbiDashboardConfigurations()._has_access()

    @http.route('/pbi_dashboards/config/scripts', type='json', auth='user')
    def scripts(self, **kw):
        """The catalogue the page renders. Grouped by date with step order."""
        if not self._has_access():
            return {'error': 'forbidden'}

        script_list = []
        groups_dict = {}

        for key, spec in SCRIPTS.items():
            is_write = bool(spec.get('writes'))
            item = {
                'key': key,
                'name': spec['name'],
                'step': spec.get('step', 99),
                'date': spec.get('date', ''),
                'group_key': spec.get('group_key', 'other'),
                'group_title': spec.get('group_title', 'Maintenance Scripts'),
                'group_note': spec.get('group_note', ''),
                'writes': is_write,
                'disabled': False,
                'note': spec['note'],
                'file': spec['file'],
            }
            script_list.append(item)

            g_key = item['group_key']
            if g_key not in groups_dict:
                groups_dict[g_key] = {
                    'key': g_key,
                    'date': item['date'],
                    'title': item['group_title'],
                    'note': item['group_note'],
                    'scripts': [],
                }
            groups_dict[g_key]['scripts'].append(item)

        # Sort groups by date descending (newest first)
        sorted_groups = sorted(
            groups_dict.values(),
            key=lambda g: g['date'],
            reverse=True,
        )
        for g in sorted_groups:
            g['scripts'].sort(key=lambda s: s['step'])

        return {
            'scripts': script_list,
            'groups': sorted_groups,
        }

    @http.route('/pbi_dashboards/config/cancel_query', type='json', auth='user')
    def cancel_query(self, **kw):
        """Attempts to cancel any long-running diagnostic or script backend query."""
        if not self._has_access():
            return {'error': 'forbidden'}
        try:
            cr = request.env.cr
            cr.execute("""
                SELECT pid 
                FROM pg_stat_activity 
                WHERE state = 'active'
                  AND pid <> pg_backend_pid()
                  AND (
                      query ILIKE '%v_pbi_sales%'
                      OR query ILIKE '%v_sales_budget%'
                      OR query ILIKE '%sync_and_repair%'
                      OR query ILIKE '%diagnose_master%'
                      OR query ILIKE '%catalog%'
                  )
            """)
            pids = [r[0] for r in cr.fetchall()]
            cancelled_count = 0
            for pid in pids:
                cr.execute("SELECT pg_cancel_backend(%s)", (pid,))
                cancelled_count += 1
            _logger.info("pbi config page: cancelled %d active queries on user request", cancelled_count)
            return {'status': 'ok', 'cancelled': cancelled_count}
        except Exception as exc:
            _logger.warning("pbi config page: cancel_query error: %s", exc)
            return {'error': str(exc)}

    @http.route('/pbi_dashboards/config/run_script', type='json', auth='user')
    def run_script(self, key=None, **kw):
        """Run one committed script and return everything it said.

        Reviewed, idempotent SQL scripts that diagnose before changing data
        and are safe to run multiple times.
        """
        if not self._has_access():
            return {'error': 'forbidden'}
        spec = SCRIPTS.get(key)
        if not spec:
            return {'error': 'unknown_script'}

        statements, narration, err = load_statements(spec)
        if err:
            return {'error': 'file_missing', 'file': spec['file'], 'message': err}

        cr = request.env.cr
        cnx = getattr(cr, '_cnx', None)
        blocks, failed = [], None

        _logger.info("pbi config page: %s running %s (%d statements, writes=%s)",
                     request.env.user.login, spec['file'], len(statements),
                     spec['writes'])

        try:
            with cr.savepoint():
                cr.execute("SET LOCAL statement_timeout = %s", (_STATEMENT_TIMEOUT,))
                cr.execute("SET LOCAL jit = off")
                cr.execute("SET LOCAL enable_nestloop = off")
                for idx, stmt in enumerate(statements):
                    if cnx is not None:
                        del cnx.notices[:]
                    cr.execute(stmt)
                    block = {
                        'index': idx,
                        'sql': first_line(stmt),
                        'notices': [n.strip() for n in (cnx.notices if cnx else [])],
                        'columns': [],
                        'rows': [],
                        'rowcount': cr.rowcount,
                        'truncated': False,
                    }
                    # description is None for anything that returns no rows,
                    # which is how a DO block and a CREATE INDEX come back.
                    if cr.description:
                        block['columns'] = [d[0] for d in cr.description]
                        rows = cr.fetchmany(_MAX_ROWS + 1)
                        block['truncated'] = len(rows) > _MAX_ROWS
                        block['rows'] = [[_render(v) for v in r]
                                         for r in rows[:_MAX_ROWS]]
                    blocks.append(block)
        except Exception as exc:                    # noqa: BLE001 - reported, not swallowed
            failed = {'index': len(blocks), 'message': str(exc).strip()}
            _logger.warning("pbi config page: %s failed at statement %d: %s",
                            spec['file'], failed['index'], failed['message'])

        return {
            'key': key,
            'name': spec['name'],
            'writes': spec['writes'],
            'narration': narration,
            'blocks': blocks,
            'failed': failed,
            'statements': len(statements),
        }


def _render(value):
    """JSON-safe cell. Dates and Decimals do not serialise on their own."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
