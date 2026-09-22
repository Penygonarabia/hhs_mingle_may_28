# -*- coding: utf-8 -*-
"""Move the four bidata-backed sales dashboards under "Sales Dashboards - Temp".

views/pbi_sales_dashboards_menus.xml already declares the new parent, but every
menuitem in that file sits in a ``noupdate="1"`` block: ir.model.data records
flagged noupdate are skipped on upgrade (models._load_records: ``if not (update
and d_noupdate)``), so the XML alone moves nothing on a database where these
menus already exist. It only takes effect on a fresh install. This closes the
gap for the installed ones.

Deliberately narrow: it sets parent_id and nothing else, and only for menus that
are still under the old parent, so re-running it -- or running it after an admin
has moved a menu on purpose -- changes nothing.

As of pbi_sales_temp_dashboards, these xmlids belong to THAT module and the
env.ref lookups below resolve to nothing — this script is a historical no-op
kept for databases still upgrading past this version from an older one.
"""

from odoo import SUPERUSER_ID, api

MOVED = [
    "pbi_sales_dashboards.menu_pbi_sales_kpi_analysis",        # Sales Dashboard
    "pbi_sales_dashboards.menu_pbi_sales_kpi_analysis_new",    # Sales Dashboard - New
    "pbi_sales_dashboards.menu_pbi_sales_mail_dashboard",      # Sales Analysis
    "pbi_sales_dashboards.menu_pbi_sales_mail_dashboard_new",  # Sales Analysis - New
]


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    old_parent = env.ref("pbi_sales_dashboards.menu_pbi_sales_dashboards",
                         raise_if_not_found=False)
    new_parent = env.ref("pbi_sales_dashboards.menu_pbi_sales_dashboards_temp",
                         raise_if_not_found=False)
    if not new_parent:
        # The data file runs before this script, so a missing Temp menu means
        # something is wrong upstream; leave the menus where they are rather
        # than guessing.
        return
    for xmlid in MOVED:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu and (not old_parent or menu.parent_id == old_parent):
            menu.parent_id = new_parent

    _carry_menu_grants(env, old_parent, new_parent)


def _carry_menu_grants(env, old_parent, new_parent):
    """Give "Sales Dashboards - Temp" the same grants "Sales Dashboards" has.

    user_menu_rights hides a menu from everyone without an explicit
    has_access=True row, and Odoo hides a leaf whose parent is hidden. So a
    brand-new container starts invisible, and moving four working dashboards
    under it would silently take them away from every non-superuser who has
    them today. Copying the old parent's grants keeps visibility exactly as it
    was: whoever could reach these dashboards a minute ago still can.

    user_menu_rights is not a dependency of this module — the two install
    independently — so this is a no-op where it is absent.
    """
    if not (old_parent and new_parent) or "menu.access.rights" not in env:
        return
    Rights = env["menu.access.rights"].sudo()
    existing = set(Rights.search([("menu_id", "=", new_parent.id)]).mapped("user_id").ids)
    vals = [
        {"user_id": row.user_id.id, "menu_id": new_parent.id, "has_access": True}
        for row in Rights.search([("menu_id", "=", old_parent.id),
                                  ("has_access", "=", True)])
        if row.user_id.id not in existing
    ]
    if vals:
        Rights.create(vals)
