# -*- coding: utf-8 -*-
"""Repair the developer-mode menus the 17.0.1.3.0 seeding got wrong.

That migration grandfathered the Settings subtree from
``_visible_menu_ids()`` — which defaults to ``debug=False`` and therefore
omits every ``base.group_no_one`` menu, i.e. Technical and its whole subtree.
Those menus were seeded as revoked for everyone, so a user who switched
developer mode on would no longer see Technical even though their real Odoo
groups still allow it. Invisible until someone actually toggles developer
mode, which is what makes it worth a migration rather than a note.

Re-seeds the same subtree from the MAXIMAL group-based visibility
(``debug=True``). Only flips False -> True, and only where group membership
already permits it: a menu the user cannot reach through their groups is left
revoked, and no grant is ever taken away here.

Idempotent, and a no-op on a database whose 17.0.1.3.0 run already used the
corrected code.
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

    for user in users:
        if Rights._is_admin_user(user):
            continue
        revoked = Rights.search([
            ("user_id", "=", user.id),
            ("menu_id", "in", list(target_ids)),
            ("has_access", "=", False),
        ])
        if not revoked:
            continue
        visible_ids = set(
            IrUiMenu.with_user(user)
            .with_context(mar_skip_enforcement=True)
            ._visible_menu_ids(debug=True)
        )
        to_grant = revoked.filtered(lambda r: r.menu_id.id in visible_ids)
        if to_grant:
            to_grant.write({"has_access": True})
