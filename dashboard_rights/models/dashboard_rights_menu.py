# -*- coding: utf-8 -*-
"""Per-user access rights for the My Dashboard *utility* menus.

The dashboard rights matrix governs KS dashboard *boards* via
:class:`dashboard.rights`. The "Quick Access" and "Configuration" menus,
however, contain plain ``ir.ui.menu`` items (Overview, Inbox, Settings,
Dashboards, Dashboard Layouts, Import Dashboards) that are not boards. This
model stores access for those menu items so they can be granted/revoked
per user in the same Users Setup screen.

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
        """ir.ui.menu ids this model governs: the direct children of the
        Quick Access and Configuration menus under the My Dashboard app.

        Children are fetched via raw SQL: this method is called from inside
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
        if not parent_ids:
            return set()
        self.env.cr.execute(
            "SELECT id FROM ir_ui_menu WHERE parent_id IN %s",
            (tuple(parent_ids),),
        )
        return {row[0] for row in self.env.cr.fetchall()}

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
