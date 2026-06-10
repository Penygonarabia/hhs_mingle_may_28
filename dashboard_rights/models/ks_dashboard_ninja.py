# -*- coding: utf-8 -*-
"""Enforcement layer for the ks_dashboard_ninja.board model.

We block direct access (via URL / action_id) to dashboards the current user
does not have rights for. Menu-level filtering is handled separately in
``ir_ui_menu.py``.
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
        to_create = [
            {"user_id": uid, "dashboard_id": bid, "has_access": False}
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
