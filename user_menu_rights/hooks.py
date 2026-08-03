# -*- coding: utf-8 -*-
"""Grandfather every existing user's CURRENT menu visibility on install.

Without this, installing the module would flip every non-superuser to
"nothing granted" the moment enforcement (ir_ui_menu._mar_restricted_menu_ids)
goes live, since no menu.access.rights rows exist yet. Instead, for each
active internal user, we ask ir.ui.menu what they can see TODAY under their
real Odoo group membership — bypassing our own not-yet-populated enforcement
via the mar_skip_enforcement context flag (see models/ir_ui_menu.py) — and
persist exactly that as their starting grants. Only future changes go
through the Menu Rights screens.
"""


def post_init_hook(env):
    Rights = env["menu.access.rights"].sudo()
    managed_ids = Rights.managed_menu_ids()
    if not managed_ids:
        return

    users = env["res.users"].sudo().search([
        ("share", "=", False),
        ("active", "=", True),
    ])
    IrUiMenu = env["ir.ui.menu"].sudo()

    to_create = []
    for user in users:
        if Rights._is_admin_user(user):
            # The true superuser bypasses the check entirely; no rows needed.
            continue
        visible_ids = set(
            IrUiMenu.with_user(user)
            .with_context(mar_skip_enforcement=True)
            ._visible_menu_ids()
        )
        granted_ids = visible_ids & managed_ids
        for menu_id in managed_ids:
            to_create.append({
                "user_id": user.id,
                "menu_id": menu_id,
                "has_access": menu_id in granted_ids,
            })

    if to_create:
        Rights.create(to_create)
