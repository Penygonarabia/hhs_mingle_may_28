# -*- coding: utf-8 -*-
"""Seed the admin grant for the new "Sales Dashboard - VQ" leaf.

views/pbi_sales_dashboards_menus.xml declares the menu, and a menuitem that does not
exist yet IS created on upgrade even inside a ``noupdate="1"`` block — noupdate
only stops EXISTING records from being rewritten. So the menu arrives on its
own; what does not arrive is a grant.

user_menu_rights hides a menu from everyone without an explicit has_access=True
row, and post_init_hook — which seeds those rows — runs on install only. Without
this script the board would be invisible on every already-installed database,
including to the admin who just upgraded, and would look broken rather than
ungranted.

Grants the bootstrap admin and nobody else, exactly as post_init_hook does for a
fresh install. Deliberately NOT copied from "Sales Dashboard With Salesman"'s
own grants: this is a new board and who may read it is an admin's decision to
make in Settings > User Menu Rights, not one to infer from a different board.

Idempotent, and a no-op where user_menu_rights is not installed — there is no
per-user overlay there, so ordinary Odoo group visibility governs the menu and
there is nothing to seed.
"""

from odoo import SUPERUSER_ID, api

MENU = "pbi_sales_dashboards.menu_pbi_sales_vq"


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    if "menu.access.rights" not in env:
        return
    admin = env.ref("base.user_admin", raise_if_not_found=False)
    menu = env.ref(MENU, raise_if_not_found=False)
    if not (admin and menu):
        return
    Rights = env["menu.access.rights"].sudo()
    existing = Rights.search([("user_id", "=", admin.id),
                              ("menu_id", "=", menu.id)], limit=1)
    if existing:
        existing.has_access = True
    else:
        Rights.create({"user_id": admin.id, "menu_id": menu.id,
                       "has_access": True})
