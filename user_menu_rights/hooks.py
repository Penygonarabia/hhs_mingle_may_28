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
    # Clear any existing records from previous incomplete uninstalls to prevent unique constraint violations
    Rights.search([]).unlink()

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
        # debug=True is REQUIRED, not a debugging aid. Odoo's signature is
        # _visible_menu_ids(self, debug=False), and when debug is false it
        # does `groups = groups - base.group_no_one`, hiding every
        # developer-mode menu — Technical and its whole subtree. Seeding from
        # that view grandfathers those menus as REVOKED for everyone, so a
        # user who switches developer mode on finds them gone: access taken
        # away by an install that promises to take nothing away. Measured on
        # this database, that was 8,582 revoked rows across 75 menus.
        #
        # This is the exact defect migrations/17.0.1.4.0 exists to repair, and
        # it chose the same fix — the maximal, group-based visibility. A
        # migration only runs on upgrade though, so until this line carried
        # debug=True a fresh install (or the uninstall/reinstall this hook's
        # own unlink() above anticipates) reproduced the bug.
        #
        # Granting more than the user sees today is safe in the other
        # direction: Odoo still applies its own debug filter at render time,
        # so a menu gated on group_no_one stays hidden until that user
        # actually turns developer mode on. The grant only decides whether
        # THIS module additionally forbids it.
        visible_ids = set(
            IrUiMenu.with_user(user)
            .with_context(mar_skip_enforcement=True)
            ._visible_menu_ids(debug=True)
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
