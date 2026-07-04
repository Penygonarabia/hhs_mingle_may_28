# -*- coding: utf-8 -*-
"""Enforcement layer for the ks_dashboard_ninja.board model.

We block direct access (via URL / action_id) to dashboards the current user
does not have rights for. Menu-level filtering is handled separately in
``ir_ui_menu.py``.

Also filters the "Overview" gallery (the "My Dashboard" app's default landing
page, listing every board as a clickable card): ``fetch_dashboard_overview``
did ``search_read(domain=[], ...)`` with NO rights filter at all, so a
non-admin user saw a card (name, image, chart count) for every dashboard in
the system regardless of dashboard.rights — including ones ``ks_fetch_dashboard_data``
would then correctly refuse to actually open. That mismatch (dashboard listed
but denied on click) is what "the My Dashboard menu doesn't reflect the rights
I set" looks like from the user's side, even though the underlying per-board
access check was never bypassed.
"""

from odoo import api, models, _
from odoo.exceptions import AccessError


class KsDashboardNinjaBoard(models.Model):
    _inherit = "ks_dashboard_ninja.board"

    # ------------------------------------------------------------------
    # Auto-provision dashboard.rights rows on dashboard creation
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        boards = super().create(vals_list)
        new_ids = [b.id for b in boards if b.id]
        if not new_ids:
            return boards
        Rights = self.env["dashboard.rights"].sudo()
        admin = self.env.ref("base.user_admin", raise_if_not_found=False)
        exclude_ids = [admin.id] if admin else []
        user_ids = self.env["res.users"].sudo().search([
            ("share", "=", False),
            ("active", "=", True),
            ("id", "not in", exclude_ids),
        ]).ids
        if not user_ids:
            return boards
        self.env.cr.execute(
            "SELECT user_id, dashboard_id FROM dashboard_rights "
            "WHERE user_id = ANY(%s) AND dashboard_id = ANY(%s)",
            [user_ids, new_ids],
        )
        existing = {(r[0], r[1]) for r in self.env.cr.fetchall()}
        name_by_id = {b.id: b.name or "" for b in boards if b.id}
        top_name_by_id = {
            b.id: (b.ks_dashboard_top_menu_id.name or ""
                   if b.ks_dashboard_top_menu_id else "")
            for b in boards if b.id
        }
        to_create = [
            {
                "user_id": uid,
                "dashboard_id": bid,
                "dashboard_name": name_by_id.get(bid, ""),
                "dashboard_top_menu_name": top_name_by_id.get(bid, ""),
                "has_access": False,
            }
            for bid in new_ids
            for uid in user_ids
            if (uid, bid) not in existing
        ]
        if to_create:
            Rights.create(to_create)
        return boards

    # ------------------------------------------------------------------
    # Access checks
    # ------------------------------------------------------------------
    def _dr_check_access(self, dashboard_id=None):
        """Raise AccessError if the current user can't access the board."""
        if not dashboard_id and self:
            dashboard_id = self.id if isinstance(self.id, int) else (self.ids[0] if self.ids else False)
        if not dashboard_id:
            return
        Rights = self.env["dashboard.rights"].sudo()
        board = self.sudo().browse(int(dashboard_id))
        if not board.exists():
            return
        if not Rights.user_has_dashboard_access(self.env.user, board):
            raise AccessError(
                _(
                    "You do not have permission to access the dashboard '%s'. "
                    "Please contact your administrator."
                )
                % (board.name or board.ks_dashboard_menu_name or _("Dashboard"))
            )

    # ------------------------------------------------------------------
    # Block the main data-fetch entry point used when a dashboard opens
    # ------------------------------------------------------------------
    @api.model
    def ks_fetch_dashboard_data(self, ks_dashboard_id, ks_item_domain=False):
        self._dr_check_access(dashboard_id=ks_dashboard_id)
        return super().ks_fetch_dashboard_data(ks_dashboard_id, ks_item_domain=ks_item_domain)

    # ------------------------------------------------------------------
    # Filter the "Overview" gallery (the My Dashboard app landing page)
    # ------------------------------------------------------------------
    def fetch_dashboard_overview(self, **kwargs):
        """Restrict the Overview cards + counts to dashboards the current
        user has rights for, admins unaffected. The base implementation
        queries with an unconditional empty domain (every board in the
        system), so without this a non-admin user saw a card for every
        dashboard regardless of dashboard.rights — even ones
        ``ks_fetch_dashboard_data`` would then correctly refuse to open."""
        result = super().fetch_dashboard_overview(**kwargs)
        Rights = self.env["dashboard.rights"].sudo()
        if Rights._is_admin_user(self.env.user):
            return result

        allowed_ids = Rights.allowed_dashboard_ids(self.env.user)
        dashboards_info = {
            bid: info for bid, info in result["dashboardsInfo"].items()
            if bid in allowed_ids
        }

        Item = self.env["ks_dashboard_ninja.item"].sudo()
        Board = self.env["ks_dashboard_ninja.board"].sudo()
        allowed_ids_list = list(allowed_ids)
        chart_count = sum(info["chartCount"] for info in dashboards_info.values())
        map_count = Item.search_count([
            ("ks_dashboard_item_type", "=", "ks_map_view"),
            ("ks_dashboard_ninja_board_id", "in", allowed_ids_list),
        ])
        list_view_count = Item.search_count([
            ("ks_dashboard_item_type", "=", "ks_list_view"),
            ("ks_dashboard_ninja_board_id", "in", allowed_ids_list),
        ])
        bookmarked_count = Board.search_count([
            ("is_bookmarked", "=", True),
            ("id", "in", allowed_ids_list),
        ])

        result["dashboardsInfo"] = dashboards_info
        result["overviewInfo"] = [
            len(dashboards_info), chart_count, map_count,
            bookmarked_count, list_view_count,
        ]
        return result
