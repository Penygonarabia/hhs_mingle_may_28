# -*- coding: utf-8 -*-
"""Hide menus from users who don't have rights for them.

Overrides ``_visible_menu_ids`` so a non-superuser never sees a managed menu
entry they haven't been explicitly granted. The cache is keyed by uid, so
per-user filtering is safe.
"""

from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _mar_restricted_menu_ids(self):
        """ir.ui.menu ids the current user is NOT allowed to see. Superuser
        gets an empty set.

        Logic:
        1. Forbid every managed menu the user has no explicit grant for.
        2. Walk up the tree (raw SQL — no ORM re-entry risk): if every
           managed child of a managed parent is forbidden, forbid the
           parent too, so a fully-revoked app or sub-menu folder disappears
           instead of showing up empty.
        3. Lockout guard: for a member of group_menu_rights_admin, un-forbid
           this module's own page and its ancestor chain. Settings is
           governed like everything else now, so without this an admin could
           revoke Settings for themselves and lose the only screen that
           could undo it — recoverable then only by raw SQL.
        """
        Rights = self.env["menu.access.rights"].sudo()
        if Rights._is_admin_user(self.env.user):
            return set()

        managed_ids = Rights.managed_menu_ids()
        if not managed_ids:
            return set()

        allowed_ids = Rights.allowed_menu_ids(self.env.user)
        forbidden = managed_ids - allowed_ids
        if not forbidden:
            return forbidden

        # `action` is read too: a menu that opens something of its own is NOT
        # a folder, and must survive the walk-up below.
        self.env.cr.execute("SELECT id, parent_id, action FROM ir_ui_menu")
        parent_of = {}
        children_of = {}
        opens_something = set()
        for mid, pid, action in self.env.cr.fetchall():
            if pid:
                parent_of[mid] = pid
                children_of.setdefault(pid, set()).add(mid)
            if action:
                opens_something.add(mid)

        changed = True
        while changed:
            changed = False
            for mid in list(forbidden):
                pid = parent_of.get(mid)
                if not pid or pid in forbidden or pid not in managed_ids:
                    continue
                # Only fold away an empty FOLDER. Sweeping up a parent that
                # carries its own action takes away a screen the user was
                # granted outright — Discuss is the case that surfaced this:
                # it owns ir.actions.client and has one sub-menu, so revoking
                # that single child silently hid Discuss itself from all 117
                # users while the matrix went on showing it ticked.
                if pid in opens_something:
                    continue
                if children_of.get(pid, set()) <= forbidden:
                    forbidden.add(pid)
                    changed = True

        # Applied last, so it also survives the walk-up above having swept a
        # parent in on account of its other children.
        if self.env.user.has_group("user_menu_rights.group_menu_rights_admin"):
            forbidden -= Rights.self_access_menu_ids()

        return forbidden

    # ------------------------------------------------------------------
    # Visibility hook
    # ------------------------------------------------------------------
    @api.model
    def _visible_menu_ids(self, debug=False):
        ids = super()._visible_menu_ids(debug=debug)
        # Bootstrap escape hatch used ONLY by hooks.post_init_hook to read a
        # user's true group-based visibility before any menu.access.rights
        # rows exist for them (see that file for why this is needed).
        if self.env.context.get("mar_skip_enforcement"):
            return ids
        forbidden = self._mar_restricted_menu_ids()
        if not forbidden:
            return ids
        try:
            return type(ids)(i for i in ids if i not in forbidden)
        except TypeError:
            return [i for i in ids if i not in forbidden]

    # ------------------------------------------------------------------
    # Defensive: also strip on search so other lookups (e.g. Settings
    # searches) don't surface forbidden menus either.
    # ------------------------------------------------------------------
    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        res = super().search(args, offset=offset, limit=limit, order=order)
        if self.env.context.get("mar_skip_enforcement"):
            return res
        forbidden = self._mar_restricted_menu_ids()
        if not forbidden:
            return res
        return res.filtered(lambda m: m.id not in forbidden)
