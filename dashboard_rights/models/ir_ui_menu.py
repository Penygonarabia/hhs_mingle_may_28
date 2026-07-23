# -*- coding: utf-8 -*-
"""Hide ks_dashboard menus from users who don't have rights for them.

We override ``_visible_menu_ids`` so non-admin users never see a dashboard
menu entry for a board they're not allowed to access. The cache is keyed
by uid, so per-user filtering is safe.
"""

from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _dr_restricted_menu_ids(self):
        """Return the ir.ui.menu ids of dashboard menus the current user
        is NOT allowed to access. Admin users get an empty set.

        Logic:
        1. Forbid the leaf board menus the user cannot access.
        2. Forbid any dashboard-category menu (ks_dashboard_top_menu_id)
           that has no accessible boards.
        3. When ALL dashboard-category children of a parent are forbidden,
           also forbid the sibling menus (Quick Access, Configuration…) and
           their full subtrees — so the parent itself can be hidden too.
        4. Walk up the menu tree (via raw SQL — no ORM re-entry risk):
           if every child of a parent is forbidden, forbid the parent.
        """
        Rights = self.env["dashboard.rights"].sudo()
        if Rights._is_admin_user(self.env.user):
            return set()

        Boards = self.env["ks_dashboard_ninja.board"].sudo().search([])
        allowed_ids = Rights.allowed_dashboard_ids(self.env.user)

        forbidden_menu_ids = set()
        all_top_menu_ids = set()
        allowed_top_menu_ids = set()

        for b in Boards:
            if b.ks_dashboard_top_menu_id:
                all_top_menu_ids.add(b.ks_dashboard_top_menu_id.id)
            if b.id in allowed_ids:
                if b.ks_dashboard_top_menu_id:
                    allowed_top_menu_ids.add(b.ks_dashboard_top_menu_id.id)
                continue
            if b.ks_dashboard_menu_id:
                forbidden_menu_ids.add(b.ks_dashboard_menu_id.id)

        # Also treat empty dashboard-category menus (direct children of the
        # ks_dashboard_ninja root menu that point at the dashboard action but
        # currently have no boards — e.g. "Beta Dashboards") as categories,
        # so non-admin users with no accessible boards in them see them hidden.
        root_menu = self.env.ref(
            "ks_dashboard_ninja.board_menu_root", raise_if_not_found=False,
        )
        dash_action = self.env.ref(
            "ks_dashboard_ninja.dashboard_action_window",
            raise_if_not_found=False,
        )
        if root_menu and dash_action:
            dash_action_ref = "%s,%s" % (dash_action._name, dash_action.id)
            # Raw SQL to avoid re-entering our own ir.ui.menu.search() override,
            # which would recurse back into _dr_restricted_menu_ids().
            self.env.cr.execute(
                "SELECT id FROM ir_ui_menu "
                "WHERE parent_id = %s AND action = %s",
                [root_menu.id, dash_action_ref],
            )
            all_top_menu_ids.update(r[0] for r in self.env.cr.fetchall())

        # Step 2: forbid dashboard-category menus with no accessible boards
        forbidden_menu_ids.update(all_top_menu_ids - allowed_top_menu_ids)

        if not forbidden_menu_ids:
            return forbidden_menu_ids

        # Load full menu parent/child map via raw SQL to avoid any ORM
        # re-entry through our own search() / _visible_menu_ids() overrides.
        self.env.cr.execute(
            "SELECT id, parent_id FROM ir_ui_menu WHERE parent_id IS NOT NULL"
        )
        parent_of = {}
        children_of = {}
        for row_id, row_pid in self.env.cr.fetchall():
            parent_of[row_id] = row_pid
            children_of.setdefault(row_pid, set()).add(row_id)

        # Step 3: when ALL dashboard-category children of a parent are
        # forbidden, also forbid every other child in that subtree so that
        # the parent (e.g. "My Dashboard") can be hidden by the walk-up.
        top_parents = set()
        for tid in all_top_menu_ids:
            pid = parent_of.get(tid)
            if pid:
                top_parents.add(pid)

        for pid in top_parents:
            dashboard_children = {
                mid for mid in all_top_menu_ids if parent_of.get(mid) == pid
            }
            if not dashboard_children:
                continue
            if not (dashboard_children <= forbidden_menu_ids):
                # At least one dashboard category is still accessible — keep
                # the sibling menus (Quick Access, Configuration…) visible.
                continue
            # All dashboard categories gone — forbid the whole subtree.
            queue = list(children_of.get(pid, set()) - forbidden_menu_ids)
            while queue:
                mid = queue.pop()
                forbidden_menu_ids.add(mid)
                queue.extend(
                    c for c in children_of.get(mid, set())
                    if c not in forbidden_menu_ids
                )

        # Step 4: walk up — hide any ancestor whose every child is now forbidden.
        changed = True
        while changed:
            changed = False
            for mid in list(forbidden_menu_ids):
                pid = parent_of.get(mid)
                if not pid or pid in forbidden_menu_ids:
                    continue
                if children_of.get(pid, set()) <= forbidden_menu_ids:
                    forbidden_menu_ids.add(pid)
                    changed = True

        return forbidden_menu_ids

    # ------------------------------------------------------------------
    # Visibility hook
    # ------------------------------------------------------------------
    @api.model
    def _visible_menu_ids(self, debug=False):
        ids = super()._visible_menu_ids(debug=debug)
        forbidden = self._dr_restricted_menu_ids()
        if not forbidden:
            return ids
        try:
            return type(ids)(i for i in ids if i not in forbidden)
        except TypeError:
            return [i for i in ids if i not in forbidden]

    # ------------------------------------------------------------------
    # Defensive: also strip on search so settings searches don't
    # surface forbidden dashboard menus.
    # ------------------------------------------------------------------
    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        res = super().search(args, offset=offset, limit=limit, order=order)
        forbidden = self._dr_restricted_menu_ids()
        if not forbidden:
            return res
        return res.filtered(lambda m: m.id not in forbidden)
