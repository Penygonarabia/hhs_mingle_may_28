# -*- coding: utf-8 -*-
"""Per-user access rights for plain ir.ui.menu items (not KS boards).

The dashboard rights matrix governs KS dashboard *boards* via
:class:`dashboard.rights`. Every OTHER plain ``ir.ui.menu`` item — including
the My Dashboard app's own tree — needs per-user grant/revoke too, and is
stored here:

* the "Quick Access" and "Configuration" menus' sub-items (Overview, Inbox,
  Settings, Dashboards, Dashboard Layouts, Import Dashboards);
* every menu (any depth) of every top-level application in the system —
  Machine Repair, Promoter, Payroll, My Dashboard, ... — see "Module Rights
  Setup" (access_rights_module_matrix.py). Every app is managed
  automatically; there is no allow-list/registry step. Only Settings is
  excluded (governed by real Odoo groups, not this per-user overlay).

My Dashboard's own boards ALSO have a separate, authoritative board-level
gate (:class:`dashboard.rights`, edited from Users Setup). A board's leaf
menu is therefore governed by BOTH mechanisms at once — the menu is only
visible if neither one forbids it — so the two must never disagree.
``_dr_sync_board_and_menu`` below is the single write path both matrix line
models (``dashboard.rights.matrix.line`` and
``access.rights.module.matrix.line``) call to keep a board's
``dashboard.rights`` row and its ``dashboard.rights.menu`` row identical,
whichever page the grant/revoke came from.

Like dashboard boards, these menus are **hidden until granted**: a user sees a
managed menu only when they have an explicit ``has_access=True`` row here. The
true superuser bypasses the check. Enforcement lives in
``ir_ui_menu._dr_restricted_menu_ids``.
"""

from odoo import api, fields, models

# The dashboard-app utility menus whose direct children this model governs.
_MANAGED_PARENT_XMLIDS = (
    "ks_dashboard_ninja.quick_access_menu",
    "ks_dashboard_ninja.configuration_menu",
)

# Top-level (parent-less) menus excluded from the "every app" gating — see
# the module docstring above. Settings only; the My Dashboard app (whose
# real top-level root is "board_menu_root" — NOT the similarly-named but
# one-level-deeper "dashboards_menu_root", "My Dashboards" plural) is
# deliberately included, kept in sync with dashboard.rights for boards via
# _dr_sync_board_and_menu.
_EXCLUDED_TOP_MENU_XMLIDS = (
    "base.menu_administration",
)


class DashboardRightsMenu(models.Model):
    _name = "dashboard.rights.menu"
    _description = "Dashboard Rights — Menu Access"
    _rec_name = "menu_id"

    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        ondelete="cascade",
        index=True,
    )
    menu_id = fields.Many2one(
        "ir.ui.menu",
        string="Menu",
        required=True,
        ondelete="cascade",
        index=True,
    )
    has_access = fields.Boolean(string="Has Access", default=False)

    _sql_constraints = [
        (
            "dashboard_rights_menu_user_menu_uniq",
            "unique(user_id, menu_id)",
            "A user can have only one access row per menu.",
        ),
    ]

    # ------------------------------------------------------------------
    # CRUD — invalidate the menu visibility cache on any rights change
    # (mirrors dashboard.rights / base ir.ui.menu; see that fix for why).
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env.registry.clear_cache()
        return records

    def write(self, values):
        res = super().write(values)
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache()
        return res

    # ------------------------------------------------------------------
    # Helpers — used by the matrix builder and the menu enforcement
    # ------------------------------------------------------------------
    @api.model
    def _managed_menu_ids(self):
        """ir.ui.menu ids this model governs:
          * the direct children of the Quick Access and Configuration menus
            under the My Dashboard app, and
          * every menu (any depth) under every top-level app menu EXCEPT
            the excluded ones (see _EXCLUDED_TOP_MENU_XMLIDS) — Module
            Rights Setup's app gating, now including My Dashboard's own
            tree. Folding these in here means enforcement
            (ir_ui_menu._dr_restricted_menu_ids) needs no per-app logic at
            all: it already forbids any managed menu the current user
            lacks an explicit grant for.

        Fetched via raw SQL: this method is called from inside
        ``ir_ui_menu._dr_restricted_menu_ids`` (itself invoked by our
        ``ir.ui.menu.search`` override), so reading ``menu.child_id`` through
        the ORM would re-enter that override and recurse infinitely. ``env.ref``
        is safe (it resolves via ir.model.data + browse, not a menu search).
        """
        parent_ids = []
        for xmlid in _MANAGED_PARENT_XMLIDS:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu:
                parent_ids.append(menu.id)
        ids = set()
        if parent_ids:
            self.env.cr.execute(
                "SELECT id FROM ir_ui_menu WHERE parent_id IN %s",
                (tuple(parent_ids),),
            )
            ids.update(row[0] for row in self.env.cr.fetchall())

        excluded_top_ids = set()
        for xmlid in _EXCLUDED_TOP_MENU_XMLIDS:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu:
                excluded_top_ids.add(menu.id)

        self.env.cr.execute("SELECT id, parent_id FROM ir_ui_menu")
        parent_of = dict(self.env.cr.fetchall())
        top_cache = {}

        def top_of(mid):
            if mid in top_cache:
                return top_cache[mid]
            cur, seen = mid, set()
            while parent_of.get(cur) and cur not in seen:
                seen.add(cur)
                cur = parent_of[cur]
            top_cache[mid] = cur
            return cur

        ids.update(
            mid for mid in parent_of if top_of(mid) not in excluded_top_ids
        )
        return ids

    @api.model
    def allowed_menu_ids(self, user):
        """Managed-menu ids ``user`` is allowed to see. Superuser sees all."""
        if not user:
            return set()
        if user._is_superuser():
            return self._managed_menu_ids()
        return set(
            self.sudo()
            .search([("user_id", "=", user.id), ("has_access", "=", True)])
            .mapped("menu_id")
            .ids
        )

    # ------------------------------------------------------------------
    # Keep a KS dashboard board's two grants (dashboard.rights, the
    # board-level gate; dashboard.rights.menu, this model's menu-level
    # gate) identical, regardless of which page wrote the change.
    # ------------------------------------------------------------------
    @api.model
    def _dr_sync_board_and_menu(self, user, val, dashboard=None, menu=None):
        """Set ``has_access = val`` for ``user`` on BOTH grant rows for a KS
        dashboard board — its ``dashboard.rights`` row and its
        ``dashboard.rights.menu`` row for the board's leaf menu — so Users
        Setup and Module Rights Setup never disagree about a board's
        visibility. Pass whichever side is known (``dashboard`` — a
        ``ks_dashboard_ninja.board`` — or ``menu`` — its leaf ``ir.ui.menu``);
        the other side is resolved automatically.

        If ``menu`` doesn't correspond to any board (an ordinary app menu,
        or a My Dashboard category folder), this is a no-op on the
        dashboard.rights side — only the menu-level row is written, by the
        caller, as normal.
        """
        Board = self.env["ks_dashboard_ninja.board"].sudo()
        if dashboard is None and menu is not None:
            dashboard = Board.search([("ks_dashboard_menu_id", "=", menu.id)], limit=1)
        if menu is None and dashboard is not None:
            menu = dashboard.ks_dashboard_menu_id
        if dashboard:
            Rights = self.env["dashboard.rights"].sudo()
            existing = Rights.search(
                [("user_id", "=", user.id), ("dashboard_id", "=", dashboard.id)],
                limit=1,
            )
            if existing:
                if existing.has_access != val:
                    existing.has_access = val
            else:
                Rights.create({
                    "user_id": user.id, "dashboard_id": dashboard.id, "has_access": val,
                })
        if menu:
            existing = self.sudo().search(
                [("user_id", "=", user.id), ("menu_id", "=", menu.id)], limit=1,
            )
            if existing:
                if existing.has_access != val:
                    existing.has_access = val
            else:
                self.sudo().create({
                    "user_id": user.id, "menu_id": menu.id, "has_access": val,
                })
