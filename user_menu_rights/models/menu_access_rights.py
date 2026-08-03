# -*- coding: utf-8 -*-
"""Persistent per-user, per-menu access rights.

One record per (user, menu). A menu is hidden from a user unless an explicit
``has_access=True`` row exists for it — except for the true superuser, who
always sees everything and bypasses this table entirely (see
``_is_admin_user``). Which menus are governed at all is decided by
``managed_menu_ids`` below.
"""

from odoo import api, fields, models

# Top-level (parent-less) menus this module does NOT govern.
#
# Empty on purpose: EVERY menu is listed and governed, Settings and its whole
# subtree included. This used to hold base.menu_administration, on the theory
# that an admin might revoke Settings for themselves and lose the only screen
# that could give it back. That risk is now handled precisely instead of by
# hiding half the tree from the page — see SELF_ACCESS_MENU_XMLIDS below.
EXCLUDED_TOP_MENU_XMLIDS = ()

# The lockout guard. These menus — this module's own page, plus every
# ancestor needed to reach it — are never hidden from a member of
# group_menu_rights_admin, whatever their grant rows say. They still appear
# on the page and can still be toggled (the toggle governs everyone else
# normally); the guard only refuses to make a Menu Rights administrator
# unable to reach the tool that undoes the mistake. Without it the only way
# back would be raw SQL.
SELF_ACCESS_MENU_XMLIDS = (
    "user_menu_rights.menu_user_menu_rights",
)


class MenuAccessRights(models.Model):
    _name = "menu.access.rights"
    _description = "Menu Access Rights"
    _rec_name = "user_id"
    _order = "user_id, menu_id"

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
    has_access = fields.Boolean(
        string="Has Access",
        default=False,
        help="If ticked, the user can see this menu. If unticked, the menu "
             "is hidden for this user.",
    )

    _sql_constraints = [
        (
            "menu_access_rights_user_menu_uniq",
            "unique(user_id, menu_id)",
            "A user can have only one access row per menu.",
        ),
    ]

    # ------------------------------------------------------------------
    # CRUD — invalidate the menu visibility cache on any rights change.
    # ir.ui.menu._visible_menu_ids is ormcache'd by the user's groups; our
    # enforcement runs inside it but a rights change doesn't touch groups,
    # so without clearing the registry cache a worker keeps serving the old
    # menu tree until restart.
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
    # Helpers used by enforcement, the matrix wizard, and the install hook.
    # ------------------------------------------------------------------
    @api.model
    def _is_admin_user(self, user):
        if not user:
            return False
        return user._is_superuser()

    @api.model
    def managed_menu_ids(self):
        """ir.ui.menu ids this module governs: every menu EXCEPT the full
        subtree of any excluded top-level menu (see
        EXCLUDED_TOP_MENU_XMLIDS).

        Raw SQL, not the ORM: this can be called from inside
        ir.ui.menu._mar_restricted_menu_ids (itself invoked by our own
        ir.ui.menu.search override), so reading ``menu.child_id`` through
        the ORM would re-enter that override.
        """
        self.env.cr.execute("SELECT id, parent_id FROM ir_ui_menu")
        rows = self.env.cr.fetchall()

        excluded_top_ids = set()
        for xmlid in EXCLUDED_TOP_MENU_XMLIDS:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu:
                excluded_top_ids.add(menu.id)
        if not excluded_top_ids:
            # The normal case now: everything is governed, so skip the walk.
            return {mid for mid, _pid in rows}

        parent_of = dict(rows)
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

        return {mid for mid, _pid in rows if top_of(mid) not in excluded_top_ids}

    @api.model
    def self_access_menu_ids(self):
        """Ids of this module's own page plus its whole ancestor chain.

        Raw recursive SQL for the same reason managed_menu_ids uses raw SQL:
        this runs inside the ir.ui.menu enforcement path, so walking
        ``menu.parent_id`` through the ORM would re-enter it.
        """
        ids = set()
        for xmlid in SELF_ACCESS_MENU_XMLIDS:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if not menu:
                continue
            self.env.cr.execute(
                """
                WITH RECURSIVE chain(id, parent_id) AS (
                    SELECT id, parent_id FROM ir_ui_menu WHERE id = %s
                  UNION
                    SELECT m.id, m.parent_id
                      FROM ir_ui_menu m
                      JOIN chain c ON m.id = c.parent_id
                )
                SELECT id FROM chain
                """,
                (menu.id,),
            )
            ids.update(row[0] for row in self.env.cr.fetchall())
        return ids

    @api.model
    def allowed_menu_ids(self, user):
        """Managed-menu ids ``user`` is allowed to see. Superuser sees all."""
        if not user:
            return set()
        if self._is_admin_user(user):
            return self.managed_menu_ids()
        return set(
            self.sudo()
            .search([("user_id", "=", user.id), ("has_access", "=", True)])
            .mapped("menu_id")
            .ids
        )
