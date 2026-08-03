# -*- coding: utf-8 -*-
"""Grandfather the Settings subtree, newly brought under management in 1.2.0.

Until 17.0.1.1.0 the whole ``base.menu_administration`` subtree was excluded
from ``managed_menu_ids``: not listed on the page, not enforced. 17.0.1.2.0
removed that exclusion so every menu is governed — but grant rows had only
ever been created for the menus that were managed at the time, so those ~115
Settings menus arrived with NO row for anybody. Enforcement reads "no row" as
"revoked", which silently took Settings away from every non-superuser, admins
included, the moment the upgrade landed.

This is the same grandfathering the install hook does, scoped to exactly the
menus that changed status: for each active internal user, ask ir.ui.menu what
they can see TODAY under their real Odoo group membership — bypassing our own
enforcement via mar_skip_enforcement (see models/ir_ui_menu.py) — and persist
that as their starting grant for those menus. Nobody gains access they didn't
already have, and nobody loses any.

Deliberately scoped to the Settings subtree rather than to "every managed menu
without a row": a menu belonging to an app installed AFTER user_menu_rights is
also row-less, and that one is meant to stay hidden-until-granted. Only menus
whose managed status this version changed are seeded here.

Rows that already exist are left alone, so a deliberate revoke made between
the upgrade and this migration survives.
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    settings = env.ref("base.menu_administration", raise_if_not_found=False)
    if not settings:
        return

    cr.execute(
        """
        WITH RECURSIVE subtree(id) AS (
            SELECT %s
          UNION
            SELECT m.id FROM ir_ui_menu m JOIN subtree s ON m.parent_id = s.id
        )
        SELECT id FROM subtree
        """,
        (settings.id,),
    )
    target_ids = {row[0] for row in cr.fetchall()}
    if not target_ids:
        return

    Rights = env["menu.access.rights"].sudo()
    IrUiMenu = env["ir.ui.menu"].sudo()

    users = env["res.users"].sudo().search([
        ("share", "=", False),
        ("active", "=", True),
    ])

    to_create = []
    for user in users:
        if Rights._is_admin_user(user):
            # The true superuser bypasses the check entirely; no rows needed.
            continue
        existing = set(
            Rights.search([
                ("user_id", "=", user.id),
                ("menu_id", "in", list(target_ids)),
            ]).mapped("menu_id").ids
        )
        missing = target_ids - existing
        if not missing:
            continue
        # debug=True on purpose: that is the MAXIMAL group-based visibility,
        # including the base.group_no_one menus (Technical and everything
        # under it) that only appear in developer mode. Seeding from the
        # debug=False set would grant those as False and silently take
        # Technical away from anyone who switches developer mode on — a
        # regression invisible until they do.
        visible_ids = set(
            IrUiMenu.with_user(user)
            .with_context(mar_skip_enforcement=True)
            ._visible_menu_ids(debug=True)
        )
        for menu_id in missing:
            to_create.append({
                "user_id": user.id,
                "menu_id": menu_id,
                "has_access": menu_id in visible_ids,
            })

    if to_create:
        Rights.create(to_create)
