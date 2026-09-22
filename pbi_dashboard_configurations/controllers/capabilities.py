# -*- coding: utf-8 -*-
"""What this server can and cannot do, and what to run to change it.

WHY THIS IS THE FIRST SECTION. A disabled Export to PowerPoint button on a
board says the feature is unavailable, and nothing more: not which package,
not whether someone already installed it, not what to do next. That answer
belongs somewhere a person can find it without reading source, and it belongs
above the rest of this page because it explains why other things look broken.

IT CAN INSTALL, AND THE CONDITIONS MATTER MORE THAN THE BUTTON DOES.

The danger in "run pip from a web request" is arbitrary code execution, so the
request never carries a package name -- it carries a KEY, looked up in
optional_deps' own capability list. Anything not on that list is refused before
a subprocess exists, and the version comes from the same place, pinned to what
the Dockerfile installs, so a server that gets the package this way lands on the
version a server built from the image already has.

It installs with --user, which is the only thing that can work here: Odoo runs
unprivileged and every system site-packages directory is root-owned. $HOME is
/var/lib/odoo, which on this deployment is a named Docker volume, so the install
SURVIVES container recreation -- better than the usual container caveat, and
worth checking on any other server rather than assuming either way.

Two things it still cannot do, and says rather than implies:

  * IT CANNOT ENABLE THE FEATURE. optional_deps probes at import time, so the
    boards keep their old answer until Odoo restarts.
  * IT IS NOT A SUBSTITUTE FOR THE IMAGE. A fresh volume, another host or a
    rebuilt stack starts without it. The Dockerfile is still where a package
    belongs for a reproducible server; this is for the one already running.

TWO STATES THAT LOOK THE SAME AND ARE NOT. `optional_deps` probes at IMPORT
time, so its answer is what the boards actually use and it cannot change until
Odoo restarts. Someone who has just run the pip command therefore still sees a
disabled button, with nothing to tell them whether it failed or whether they
simply need to restart. So this re-probes LIVE as well, and reports the pair:

    active  = what the boards are using now (optional_deps, fixed at startup)
    present = whether the package imports right now

  present and active          -> working
  present and NOT active      -> installed; restart Odoo and it turns on
  NOT present                 -> not installed; here is the command

That middle case is the one worth having, and it is invisible from anywhere
else.
"""

import importlib
import logging
import subprocess
import sys

from odoo import http
from odoo.http import request

from odoo.addons.pbi_dashboards.controllers import optional_deps

_logger = logging.getLogger(__name__)

# Which boards lose what, so the consequence is named rather than left for the
# reader to discover by pressing things.
AFFECTS = {
    'pptx': 'The Export to PowerPoint button on Sales Analysis with Salesman '
            'and Sales Dashboard With Salesman. Export PDF is unaffected — it '
            'prints from the browser and needs nothing installed.',
    'xlsx': 'The Export to Excel button on the Service boards\' detail drawer. '
            'Export CSV is unaffected — it carries the same rows and needs '
            'nothing installed.',
}

# ---------------------------------------------------------------------------
# THE OTHER KIND OF THIRD PARTY: ODOO MODULES, NOT PYTHON PACKAGES.
#
# The boards read tables owned by modules developed and released separately --
# dashboard_groups, sales_budget, partner_classification, salesman_res_partner,
# machine_repair_management, and whichever module declares res.region on this
# server. pbi_sales_dashboards deliberately depends on NONE of them (see the
# comment in its manifest and pbi_dashboards/controllers/optional_schema.py):
# declaring a dependency would drag this repository's copy of that work into a
# server already running its own.
#
# The cost of that choice is that an absent module does not fail to install --
# it DEGRADES. A caption goes blank, a dimension reads Unassigned, a target
# column reads zero, and the board still looks like it is answering. That is
# the single largest source of "the new server's dashboard is wrong", and it is
# invisible from anywhere in the UI. So it is reported here, next to the Python
# packages, because to whoever is standing up a server they are the same
# question: what does this box not have yet.
#
# Probed against the LIVE SCHEMA, not against ir_module_module. A module can be
# installed at a version that predates the column, and the boards resolve what
# they read at build time from the catalog -- so the catalog is the only answer
# that matches what a board will actually do. The module state is read as well
# and reported alongside, because it is what tells "never installed" apart from
# "installed, but not the version this needs".
#
# `required`  -- absent means the named damage happens.
# `optional`  -- absent costs the one caption named in `degrades`, no more.
# Entries are (table,) tables or (table, column) pairs, as optional_schema
# spells them.
COMPANION_APPS = [
    {
        'key': 'machine_repair_management',
        'name': 'Machine Repair Management',
        'modules': ['machine_repair_management'],
        'critical': True,
        'provides': 'product_category.code — the ERP category code every board '
                    'joins the catalogue on — and res_city.report_region, which '
                    'is how a customer with no region of its own still lands in '
                    'one.',
        'required': [('product_category', 'code')],
        'optional': [('res_city', 'report_region')],
        'impact': 'THE BOARDS DO NOT WORK WITHOUT THIS ONE. product_category.code '
                  'is not optional to the fact snapshot: without it '
                  'v_pbi_sales_sman_fact is not built at all, so every sales board '
                  'opens empty rather than merely incomplete. Install this before '
                  'anything else on this page.',
        'degrades': 'Region falls back to whatever the invoice header carries, so '
                    'customers whose region is only known through their city read '
                    'Unassigned.',
    },
    {
        'key': 'dashboard_groups',
        'name': 'Dashboard Groups',
        'modules': ['dashboard_groups'],
        'critical': False,
        'provides': 'The taxonomy masters behind four of the ten levels: '
                    'salestypes_group and sale_types (Sales Type Group), '
                    'main_category and sub_category (Main and Sub-Category), and '
                    'the two link columns on product_category that point at them.',
        'required': ['salestypes_group', 'sale_types', 'main_category',
                     'sub_category'],
        'optional': [('product_category', 'sub_category'),
                     ('product_category', 'merged_subcategory')],
        'impact': 'Sales Type Group, Main Category and Sub-Category read '
                  '"Unassigned" on every board and in every export. The figures '
                  'stay correct — these are labels — so the board looks like it is '
                  'answering, which is why this is worth checking rather than '
                  'waiting to notice.',
        'degrades': 'The category links are absent, so Main and Sub-Category stay '
                    'blank even where the masters themselves are here — the module '
                    'is installed at a version older than the one that added them.',
    },
    {
        'key': 'sales_budget',
        'name': 'Sales Budget',
        'modules': ['sales_budget'],
        'critical': False,
        'provides': 'v_sales_budget_month, sales_budget_line, and v_pbi_sales_budget_live — the target '
                    'engine across all 10 levels.',
        'required': ['v_sales_budget_month', 'sales_budget_line'],
        'optional': ['v_pbi_sales_budget_live'],
        'impact': 'Every Target, Budget, Achievement % and variance figure reads '
                  'zero, while actuals stay correct. The budget meets the sales '
                  'side through a FULL OUTER JOIN, so no sales row is lost — the '
                  'board simply shows a target of nothing, exactly as a month with '
                  'no budget captured already looks.',
        'degrades': 'Live target materialization view is absent, falling back to batch snapshot.',
    },
    {
        'key': 'partner_classification',
        'name': 'Partner Classification & CRM Links',
        'modules': ['partner_classification'],
        'critical': False,
        'provides': 'The partner_classification master and res_partner links (partner_classification_id, ref).',
        'required': ['partner_classification', ('res_partner', 'partner_classification_id')],
        'optional': [('res_partner', 'ref')],
        'impact': 'Partner Classification and Customer links read "Unassigned" everywhere, and the '
                  'budget\'s classification-to-group assignment has nothing to '
                  'resolve against.',
        'degrades': 'Customer ERP codes (ref) are missing, so CRM partner matching is unlinked.',
    },
    {
        'key': 'res_region',
        'name': 'A module declaring res.region',
        'modules': ['base_territory', 'dealer', 'promoter'],
        'critical': False,
        'provides': 'The res_region master — level 3. Several modules in this '
                    'repository declare it and ANY ONE of them is enough; which '
                    'one is right is whatever the rest of this server already '
                    'uses, so install the one already carrying its regions rather '
                    'than adding a second.',
        'required': ['res_region'],
        'optional': [],
        'impact': 'Region reads "Unassigned" on every board, including the region '
                  'filter, which then has nothing to offer.',
        'degrades': '',
    },
    {
        'key': 'res_city',
        'name': 'Extended Addresses (base_address_extended)',
        'modules': ['base_address_extended'],
        'critical': False,
        'provides': 'res_city — level 4, and the hop that fills the region in for '
                    'a customer that has none of its own.',
        'required': ['res_city'],
        'optional': [('res_city', 'code')],
        'impact': 'City reads "Unassigned", and any customer whose region was only '
                  'reachable through its city loses that too. This one ships with '
                  'Odoo — it is in Apps, not a third party — and is simply not '
                  'installed by default.',
        'degrades': 'The city code is absent, so cities match by name only.',
    },
    {
        'key': 'salesman_res_partner',
        'name': 'Salesman on Partner',
        'modules': ['salesman_res_partner'],
        'critical': False,
        'provides': 'res_partner.is_salesman and res_partner.salesman_ref — ERP salesman mapping.',
        'required': [('res_partner', 'is_salesman')],
        'optional': [('res_partner', 'salesman_ref')],
        'impact': 'The salesman join is closed off deliberately rather than left '
                  'to match any partner and caption a line with the wrong person\'s '
                  'name. Salesman then falls through to the ERP feed\'s own '
                  'salesman name, which is the same text.',
        'degrades': 'Salesman ERP ref is missing, falling back to name/ID match.',
    },
    {
        'key': 'product_tags',
        'name': 'Product Unit Tags (product_tag)',
        'modules': ['product'],
        'critical': False,
        'provides': 'product_tag and product_tag_product_template_rel — unit gating (flag 02) and AC scope.',
        'required': ['product_tag', 'product_tag_product_template_rel'],
        'optional': [],
        'impact': 'Unit gating (02) falls back to legacy catalogflags. If catalogflags is absent, '
                  'machine unit counts double-count split AC systems.',
        'degrades': '',
    },
    {
        'key': 'product_family',
        'name': 'Product Sub-Group master (product_family)',
        'modules': [],
        'critical': False,
        'provides': 'product_family and product_category.product_family — the '
                    'Product Sub-Group level.',
        'required': ['product_family', ('product_category', 'product_family')],
        'optional': [('product_family', 'pfam_merged_into')],
        'impact': 'NO MODULE OWNS THIS ANY MORE. dashboard_groups once carried a '
                  'product.family model and it was removed, so on a new server '
                  'nothing creates the table and Product Sub-Group shows Target '
                  'only, with This Year and Last Year at zero. Do not install '
                  'anything for it — the Master Setup section below creates the '
                  'table, restores the column and rebuilds the view.',
        'degrades': '"Report under another family" is absent, so every family '
                  'reports under itself.',
    },
]


def _rel_exists(cr, table):
    cr.execute("SELECT to_regclass(%s)", (table,))
    return cr.fetchone()[0] is not None


def _col_exists(cr, table, column):
    cr.execute("""SELECT 1 FROM information_schema.columns
                   WHERE table_name = %s AND column_name = %s""",
               (table, column))
    return bool(cr.fetchone())


def _absent(cr, items):
    """Which of `items` this database does not have, named the way a person
    would name them: "res_region", "product_category.code"."""
    out = []
    for item in items:
        if isinstance(item, str):
            if not _rel_exists(cr, item):
                out.append(item)
        else:
            table, column = item
            if not _col_exists(cr, table, column):
                out.append('%s.%s' % (table, column))
    return out


def _module_states(cr, names):
    """What ir_module_module says about each of `names`.

    Read alongside the schema probe, never instead of it: a module can be
    installed at a version that predates the column the boards read, which
    looks identical to not installed from where a board stands. Reported so
    that case can be told apart from "never installed here".
    """
    if not names:
        return {}
    cr.execute("SELECT name, state, latest_version FROM ir_module_module "
               "WHERE name IN %s", (tuple(names),))
    return {r[0]: {'state': r[1], 'version': r[2]} for r in cr.fetchall()}


def _present(module_name):
    """Does this package import RIGHT NOW, as opposed to when Odoo started?

    A failed import is not cached, so this genuinely re-tests rather than
    replaying the answer optional_deps got at startup.
    """
    if not module_name:
        return True
    optional_deps._ensure_user_site()
    importlib.invalidate_caches()
    try:
        importlib.import_module(module_name)
    except Exception:                                # noqa: BLE001 - any import failure means absent
        return False
    return True


class PbiDashboardConfigCapabilities(http.Controller):

    def _has_access(self):
        from .main import PbiDashboardConfigurations
        return PbiDashboardConfigurations()._has_access()

    @http.route('/pbi_dashboards/config/capabilities', type='json', auth='user')
    def capabilities(self, **kw):
        if not self._has_access():
            return {'error': 'forbidden'}
        out = []
        for key, cap in optional_deps.capabilities().items():
            module = cap.get('module')
            active = bool(cap.get('available'))
            present = _present(module)
            if not cap.get('package'):
                state, note = 'builtin', 'Always available — nothing to install.'
            elif present and active:
                state, note = 'ok', 'Installed and in use.'
            elif present and not active:
                state = 'restart'
                note = ('Installed, but this Odoo process started before it was. '
                        'Restart Odoo and the button turns itself on.')
            else:
                state = 'missing'
                note = 'Not installed on this server.'
            out.append({
                'key': key,
                'feature': cap.get('feature') or key,
                'package': cap.get('package'),
                'install': cap.get('install'),
                'state': state,
                'note': note,
                'affects': AFFECTS.get(key, ''),
            })
        # Missing first: the reason someone opened this page is at the top.
        order = {'missing': 0, 'restart': 1, 'ok': 2, 'builtin': 3}
        out.sort(key=lambda c: (order.get(c['state'], 9), c['feature']))
        _logger.info("config page: %s read server capabilities (%s)",
                     request.env.user.login,
                     ', '.join('%s=%s' % (c['key'], c['state']) for c in out))
        return {'capabilities': out}

    @http.route('/pbi_dashboards/config/requirements', type='json', auth='user')
    def requirements(self, **kw):
        """Which companion Odoo modules this database has, and what each absence costs.

        Read-only, and it installs NOTHING. Installing an Odoo module means
        running its own hooks, its own data files and its own migrations
        against this database; that belongs to Apps, which knows how, not to a
        maintenance page that would only know how to start it.
        """
        if not self._has_access():
            return {'error': 'forbidden'}

        cr = request.env.cr
        names = sorted({m for app in COMPANION_APPS for m in app['modules']})
        states = _module_states(cr, names)

        out = []
        for app in COMPANION_APPS:
            missing_required = _absent(cr, app['required'])
            missing_optional = _absent(cr, app['optional'])
            if missing_required:
                state = 'missing'
            elif missing_optional:
                state = 'partial'
            else:
                state = 'ok'

            mods = []
            for name in app['modules']:
                info = states.get(name)
                mods.append({
                    'name': name,
                    # "absent" means this server does not carry the module's
                    # FOLDER, which is a different fix from "uninstalled" --
                    # one needs a deploy, the other one click in Apps.
                    'state': (info or {}).get('state') or 'absent',
                    'version': (info or {}).get('version') or '',
                })
            # Any one of the res.region declarers satisfies that row, so this
            # is "is one of them installed", never "are all of them".
            installed_any = any(m['state'] == 'installed' for m in mods)

            out.append({
                'key': app['key'],
                'name': app['name'],
                'critical': app['critical'],
                'provides': app['provides'],
                'impact': app['impact'],
                'degrades': app['degrades'],
                'state': state,
                'missing_required': missing_required,
                'missing_optional': missing_optional,
                'modules': mods,
                'installed_any': installed_any,
                # The one row nothing in Apps can fix: its owning model was
                # removed, and the Master Setup section creates the table.
                'fix_here': not app['modules'],
            })

        # Broken first, and the critical one above the rest of those: the
        # reason someone opened this page is at the top.
        order = {'missing': 0, 'partial': 1, 'ok': 2}
        out.sort(key=lambda a: (order.get(a['state'], 9),
                                0 if a['critical'] else 1, a['name']))
        _logger.info("config page: %s read companion app requirements (%s)",
                     request.env.user.login,
                     ', '.join('%s=%s' % (a['key'], a['state']) for a in out))
        return {'requirements': out}

    @http.route('/pbi_dashboards/config/install_capability', type='json', auth='user')
    def install_capability(self, key=None, **kw):
        """Install ONE known package, named by key rather than by the caller.

        THE REQUEST NEVER CARRIES A PACKAGE NAME. It carries a key, looked up in
        optional_deps' own capability list; anything not on that list is refused
        before a subprocess exists. The version comes from the same place and is
        pinned to what the Dockerfile installs. That is the whole safety
        argument -- nothing the caller sends reaches a command line.
        """
        if not self._has_access():
            return {'error': 'forbidden'}

        cap = optional_deps.capabilities().get(key)
        if not cap or not cap.get('package'):
            return {'error': 'Nothing installable is registered under that name.'}
        if cap.get('available') and _present(cap.get('module')):
            return {'error': '%s is already installed and in use.' % cap['package']}

        req = cap['package']
        if cap.get('pin'):
            req = '%s==%s' % (req, cap['pin'])

        in_venv = sys.prefix != getattr(sys, 'base_prefix', sys.prefix)
        cmd = [sys.executable, '-m', 'pip', 'install',
               '--no-input', '--disable-pip-version-check']
        if not in_venv:
            cmd.append('--user')
        cmd.append(req)

        _logger.info("config page: %s is installing %s", request.env.user.login, req)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return {'error': 'pip did not finish within five minutes. That is usually the '
                             'network -- this server may have no route to the package index.'}
        except Exception as exc:                     # noqa: BLE001 - reported, not swallowed
            _logger.exception("config page: could not start pip")
            return {'error': 'Could not run pip: %s' % exc}

        lines = [ln for ln in ((proc.stdout or '') + (proc.stderr or '')).splitlines() if ln.strip()]
        tail = lines[-12:]

        if proc.returncode != 0:
            _logger.warning("config page: install of %s failed (exit %s)", req, proc.returncode)
            return {'ok': False,
                    'message': 'pip exited %d. The output below says why.' % proc.returncode,
                    'output': tail}

        optional_deps._ensure_user_site()
        importlib.invalidate_caches()
        now_present = _present(cap.get('module'))

        if now_present:
            return {'ok': True,
                    'message': '%s installed successfully and is ready to use.' % req,
                    'output': tail}

        return {'ok': True,
                'message': '%s installed. Restart Odoo to turn the feature on -- this process '
                           'probed for it at startup and cannot change its answer until then. '
                           'Add it to the Dockerfile too, or a rebuilt stack starts without it.'
                           % req,
                'output': tail}

