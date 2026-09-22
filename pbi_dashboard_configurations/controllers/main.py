# The Configurations page's server side.
#
# Two JSON routes, both thin, and NEITHER of them rebuilds anything. The
# refresh route queues the cron job and returns; the rebuild happens in the
# cron's own thread. See pbi.sales.sman.fact.queue_refresh for why that matters:
# the rebuild is ~16s of database CPU, and running it inside a request holds a
# worker and a transaction for the duration. Doing it synchronously in a SQL
# client is what took a staging server down, and this page exists partly so
# nobody has to.

import logging
import os
import threading
from datetime import timedelta

from odoo import fields, http
from odoo.http import request

from odoo.addons.pbi_dashboards.controllers.access import menu_allowed

MENU_CONFIG = "pbi_dashboard_configurations.menu_pbi_dashboard_config_page"

REFRESH_CRON_XMLID = "pbi_sales_dashboards.ir_cron_pbi_sales_sman_fact_refresh"
REBUILD_FLOOR_SECONDS = 60

_logger = logging.getLogger(__name__)


class PbiDashboardConfigurations(http.Controller):

    def _has_access(self):
        """Gate on the page's own menu, the way every board gates on its own.

        Whoever is granted this menu may read the freshness of a snapshot and
        ask for it to be rebuilt. That is the whole surface: there is nothing
        here that writes business data.
        """
        return menu_allowed(MENU_CONFIG)

    def _cron(self):
        """The refresh job, sudo'd, or None where it does not exist.

        THE CRON, NOT THE MODEL, is what this page works through, and that is
        deliberate. Reading pbi.sales.sman.fact.refresh_status() tied this page
        to that module's VERSION: on a server whose checkout predated those
        methods the model was present, the probe passed, and the call raised
        AttributeError -- so the page showed "Could not read snapshot status"
        and an upgrade could not fix it, because an upgrade re-reads the same
        old files. Seen on staging 2026-09-03.

        The cron has been there far longer than the methods have, and queueing
        it is the entire mechanism anyway: the model's own queue_refresh writes
        exactly the trigger row written below. Going straight to it means this
        page works against any version of the boards, which is what a page whose
        whole job is diagnosing a stale server ought to do.

        sudo: a dashboard reader may not read ir.cron. Who may use this page is
        decided by the menu check, not by ir.cron's ACL.
        """
        cron = request.env.ref(REFRESH_CRON_XMLID, raise_if_not_found=False)
        return cron.sudo() if cron else None

    def _queued_at(self, cron):
        """Earliest pending trigger for ``cron``, or None."""
        request.env.cr.execute(
            "SELECT min(call_at) FROM ir_cron_trigger WHERE cron_id = %s",
            (cron.id,))
        return request.env.cr.fetchone()[0]

    @http.route('/pbi_dashboards/config/snapshots', type='json', auth='user')
    def snapshots(self, **kw):
        """Every snapshot this page can report on, with its freshness.

        A list rather than one entry, because the next snapshot to grow a card
        here should be an item in this list and nothing else.
        """
        if not self._has_access():
            return {'error': 'forbidden'}
        card = {
            'key': 'sman_fact',
            'name': 'General Database Analytical Snapshot',
            'note': 'Maintains database-wide analytical snapshots and materialized views. '
                    'Synchronizes data nightly and performs on-demand full database refresh '
                    'whenever transactions, master dimensions, or targets are updated.',
            'state': 'unavailable', 'last_run': None, 'due': None,
        }
        cron = self._cron()
        if cron is None:
            card['note'] = ('The database snapshot refresh service is not installed or '
                            'configured on this server.')
        else:
            queued_at = self._queued_at(cron)
            card.update({
                'state': ('pending' if queued_at
                          else 'cron_off' if not cron.active
                          else 'idle'),
                'due': queued_at.isoformat() if queued_at else None,
                # lastcall is when the job last RAN, which is when the snapshot last
                # rebuilt: every path that rebuilds it goes through this cron. A
                # REFRESH run by hand in a SQL client does NOT move it, so read this
                # as "last refreshed by the system".
                'last_run': cron.lastcall.isoformat() if cron.lastcall else None,
            })

        # Field and Model Registry Integrity Diagnostic card.
        #
        # The button below deletes state='manual' rows and nothing else, which
        # is the whole of what it can safely do: a state='base' row comes from
        # live Python on the filesystem, _add_manual_fields never instantiates
        # it, and deleting it neither stops the KeyError nor survives the next
        # module update. So the card counts the two states separately and only
        # offers to clean when there is something it can actually clean.
        # A base-state row is a module load-order problem instead -- run the
        # Upgrade Blockers section's load-order diagnostic for that one.
        request.env.cr.execute(
            """SELECT count(*) FILTER (WHERE state = 'manual'
                                          AND model = 'res.users'),
                      count(*)
                 FROM ir_model_fields
                WHERE name = 'salesman_type_id'"""
        )
        manual_cnt, salesman_cnt = request.env.cr.fetchone()

        if manual_cnt:
            integrity_fact = ('%s Studio field(s) on res.users, %s total'
                              % (manual_cnt, salesman_cnt))
        elif salesman_cnt:
            integrity_fact = ('%s field(s), all Python-declared -- nothing to clean'
                              % salesman_cnt)
        else:
            integrity_fact = 'Clean (0 detected)'

        integrity_card = {
            'key': 'salesman_type_integrity',
            'name': 'Model & Field Diagnostic (salesman_type_id)',
            'note': 'Counts salesman_type_id definitions on res.users in ir_model_fields '
                    'and removes the Studio (state=manual) ones, which are the only kind '
                    'a delete can fix. Fields declared in Python (state=base) are left '
                    'alone: if an upgrade is failing on one of those, the cause is a '
                    'missing manifest dependency, not a stale row -- use the Upgrade '
                    'Blockers section. Also provides the server search command.',
            'command': 'grep -rn "salesman_type_id" /var/odoo/staging-hhsv3.cieloapps.com/ --include=*.py',
            'state': 'cron_off' if manual_cnt else 'idle',
            'status_fact': integrity_fact,
            'btn_label': 'Clean Studio fields' if manual_cnt else 'Re-verify integrity',
            'can_action': True,
            'last_run': None,
            'due': None,
        }

        # Live Target & Budget Engine Diagnostic Card
        cr = request.env.cr
        has_budget_table = False
        has_budget_view = False
        budget_years = []
        try:
            cr.execute("SELECT to_regclass('sales_budget_line'), to_regclass('v_pbi_sales_budget_live')")
            r1, r2 = cr.fetchone()
            has_budget_table = r1 is not None
            has_budget_view = r2 is not None
            if has_budget_table:
                cr.execute("SELECT DISTINCT year FROM sales_budget_line WHERE COALESCE(year, '') <> '' ORDER BY year")
                budget_years = [r[0] for r in cr.fetchall()]
        except Exception:
            pass

        target_status = 'Active (%s years: %s)' % (len(budget_years), ', '.join(budget_years)) if budget_years else 'No budget years loaded'
        target_card = {
            'key': 'target_engine_status',
            'name': 'Live Target & Budget Engine (v_pbi_sales_budget_live)',
            'note': 'Monitors real-time multi-year target delivery via sales_budget_line and v_pbi_sales_budget_live. '
                    'Provides on-demand cache warming and target query path verification across all 10 dimensions.',
            'state': 'idle' if (has_budget_table and has_budget_view) else 'cron_off',
            'status_fact': target_status,
            'btn_label': 'Warm Target Cache',
            'can_action': True,
            'last_run': None,
            'due': None,
        }

        return {'snapshots': [card, integrity_card, target_card]}

    @http.route('/pbi_dashboards/config/queue_refresh', type='json', auth='user')
    def queue_refresh(self, key='sman_fact', **kw):
        """Queue a rebuild or execute an integrity fix.

        `key` is checked against the known actions rather than used to look
        anything up, so an unexpected value is a refusal and never a lookup on
        request input.
        """
        if not self._has_access():
            return {'error': 'forbidden'}
        if key not in ('sman_fact', 'salesman_type_integrity', 'target_engine_status'):
            return {'error': 'unknown_snapshot'}

        if key == 'target_engine_status':
            cr = request.env.cr
            try:
                cr.execute("SELECT to_regclass('v_pbi_sales_budget_live')")
                if cr.fetchone()[0]:
                    cr.execute("EXPLAIN ANALYZE SELECT COUNT(*), MAX(budget_value) FROM v_pbi_sales_budget_live")
                message = 'Target engine cache warmed and query paths verified successfully.'
            except Exception as exc:
                message = 'Target cache warming notice: %s' % exc
            return {'state': 'idle', 'message': message}

        if key == 'salesman_type_integrity':
            request.env.cr.execute(
                "DELETE FROM ir_model_fields WHERE name = 'salesman_type_id' AND model = 'res.users' AND state = 'manual'"
            )
            deleted = request.env.cr.rowcount
            _logger.info("pbi config page: %s cleaned %s manual salesman_type_id definitions",
                         request.env.user.login, deleted)
            if deleted:
                message = ('Cleaned %s Studio salesman_type_id field definition(s) '
                           'from ir_model_fields.' % deleted)
            else:
                message = ('No Studio salesman_type_id definitions to clean. Any '
                           'remaining rows are declared in Python, where a delete '
                           'changes nothing: if an upgrade is failing on one, run the '
                           'load-order diagnostic under Upgrade Blockers and fix the '
                           'manifest on the server.')
            return {'state': 'idle', 'message': message}

        cron = self._cron()
        if cron is None:
            return {'state': 'unavailable',
                    'message': 'The Sales Dashboards module is not installed '
                               'on this server.'}
        last_run = cron.lastcall.isoformat() if cron.lastcall else None

        # The same three rules the master-data triggers apply, for the same
        # reason: a button able to bypass them would be a way to hammer the
        # database that editing a product category is not.
        if not cron.active:
            result = {'state': 'cron_off', 'last_run': last_run,
                      'message': 'The scheduled refresh is switched off. '
                                 'An administrator must re-enable it.'}
        else:
            queued_at = self._queued_at(cron)
            if queued_at:
                # One rebuild answers every request made before it runs; a
                # second row would only buy a second rebuild.
                result = {'state': 'already_queued', 'last_run': last_run,
                          'due': queued_at.isoformat(),
                          'message': 'A refresh is already queued.'}
            else:
                floor = timedelta(seconds=REBUILD_FLOOR_SECONDS)
                now = fields.Datetime.now()
                due = max(now, cron.lastcall + floor) if cron.lastcall else now
                cron._trigger(at=due)
                result = {'state': 'queued', 'last_run': last_run,
                          'due': due.isoformat(),
                          'message': 'Refresh queued. It runs within about a '
                                     'minute.'}

        # Worth a log line: it is a request for database work, it is rare, and
        # when someone asks why the boards rebuilt at an odd hour this answers
        # it. The debounce means a burst of clicks logs a burst of
        # already_queued, which is the useful shape.
        _logger.info("pbi config page: %s requested a refresh of %s -> %s",
                     request.env.user.login, key, result.get('state'))
        return result

    @http.route('/pbi_dashboards/config/purge_web_assets', type='json', auth='user')
    def purge_web_assets(self, **kw):
        """Purges compiled web.assets_* bundles from ir_attachment."""
        if not self._has_access():
            return {'error': 'forbidden'}
        try:
            request.env.cr.execute("DELETE FROM ir_attachment WHERE name LIKE 'web.assets_%'")
            deleted = request.env.cr.rowcount
            request.env.cr.commit()
            _logger.info("pbi config page: %s purged %s web asset attachment(s)",
                         request.env.user.login, deleted)
            return {
                'status': 'ok',
                'deleted': deleted,
                'message': f'Successfully purged {deleted} compiled web asset bundle(s) from database.',
            }
        except Exception as exc:
            _logger.exception("Failed to purge web assets: %s", exc)
            return {'error': str(exc)}

    @http.route('/pbi_dashboards/config/restart_odoo', type='json', auth='user')
    def restart_odoo(self, **kw):
        """Initiates container/process restart in background."""
        if not self._has_access():
            return {'error': 'forbidden'}

        def _do_restart():
            import time
            time.sleep(0.8)
            try:
                os._exit(0)
            except Exception:
                import signal
                os.kill(os.getpid(), signal.SIGKILL)

        t = threading.Thread(target=_do_restart, daemon=True)
        t.start()

        return {
            'status': 'restarting',
            'message': 'Odoo server restart initiated. The container is restarting and reloading...',
        }

    @http.route('/pbi_dashboards/config/purge_and_restart', type='json', auth='user')
    def purge_and_restart(self, **kw):
        """Purges web assets and restarts Odoo container in sequence."""
        if not self._has_access():
            return {'error': 'forbidden'}
        deleted = 0
        try:
            request.env.cr.execute("DELETE FROM ir_attachment WHERE name LIKE 'web.assets_%'")
            deleted = request.env.cr.rowcount
            request.env.cr.commit()
            _logger.info("pbi config page: %s purged %s web assets before restart",
                         request.env.user.login, deleted)
        except Exception as exc:
            _logger.warning("Error purging assets before restart: %s", exc)

        def _do_restart():
            import time
            time.sleep(0.8)
            try:
                os._exit(0)
            except Exception:
                import signal
                os.kill(os.getpid(), signal.SIGKILL)

        t = threading.Thread(target=_do_restart, daemon=True)
        t.start()

        return {
            'status': 'restarting',
            'deleted': deleted,
            'message': f'Purged {deleted} web asset bundles. Odoo container is restarting...',
        }

