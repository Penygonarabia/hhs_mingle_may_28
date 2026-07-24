"""Purge the cached web.assets_* bundle, and grandfather every active user
onto every app menu now managed by "Module Rights Setup".

Covers 17.0.2.0.0: removed the access.rights.controlled.module registry and
its Discover Candidate Modules wizard (and the standalone "Rights Setup"
menu, which was never anything but a second entry point to the same
dashboard.rights.matrix wizard Users Setup already opens). Module Rights
Setup now manages EVERY top-level app menu automatically — no
registration step. Without this migration, upgrading would instantly hide
every app menu (Machine Repair, Promoter, Payroll, ...) from every
non-admin user, since none of them have an explicit dashboard.rights.menu
grant for menus that were never gated before. This grants every currently
active internal user access to every menu that exists today (mirrors
access.rights.controlled.module._grandfather_existing_access, just for
every app instead of one at a time); only new users / future revokes go
through the normal grant flow afterwards.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.module_rights.hooks import purge_web_assets

    _logger.info("module_rights: purging web.assets_* bundle on upgrade.")
    purge_web_assets(env)

    _grandfather_all_app_menus(env)


def _grandfather_all_app_menus(env):
    # "board_menu_root" (not "dashboards_menu_root", a child category one
    # level down) is the actual top-level, parent-less "My Dashboard" app
    # root — see the same note in dashboard_rights_menu.py.
    excluded_ids = []
    for xmlid in ("base.menu_administration", "ks_dashboard_ninja.board_menu_root"):
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu:
            excluded_ids.append(menu.id)

    cr = env.cr
    cr.execute("SELECT id, parent_id FROM ir_ui_menu")
    parent_of = dict(cr.fetchall())

    def top_of(mid):
        cur, seen = mid, set()
        while parent_of.get(cur) and cur not in seen:
            seen.add(cur)
            cur = parent_of[cur]
        return cur

    menu_ids = [mid for mid in parent_of if top_of(mid) not in excluded_ids]
    if not menu_ids:
        return

    user_ids = env["res.users"].sudo().search([
        ("share", "=", False), ("active", "=", True),
    ]).ids
    if not user_ids:
        return

    cr.execute(
        "SELECT user_id, menu_id FROM dashboard_rights_menu "
        "WHERE user_id = ANY(%s) AND menu_id = ANY(%s)",
        [user_ids, menu_ids],
    )
    existing = {(row[0], row[1]) for row in cr.fetchall()}
    to_create = [
        {"user_id": uid, "menu_id": mid, "has_access": True}
        for uid in user_ids
        for mid in menu_ids
        if (uid, mid) not in existing
    ]
    if to_create:
        env["dashboard.rights.menu"].sudo().create(to_create)
    _logger.info(
        "module_rights: grandfathered %s grant(s) across %s user(s) x "
        "%s menu(s) for the all-apps 'Module Rights Setup' gating.",
        len(to_create), len(user_ids), len(menu_ids),
    )
