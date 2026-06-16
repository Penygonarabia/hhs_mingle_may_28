# -*- coding: utf-8 -*-
"""Persistent per-user, per-dashboard access rights.

This model is independent of `dashboard_user_rights_roles` and is the single
source of truth for whether a given user can see/use a given ks_dashboard
board.

One record per (user, dashboard). Defaults to has_access=False for every
non-admin user. The admin user (base.group_system / base.user_admin) is
always considered to have access — see ``user_has_dashboard_access`` — so we
do not need to maintain explicit rows for admin.
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DashboardRights(models.Model):
    _name = "dashboard.rights"
    _description = "Dashboard Rights"
    _rec_name = "user_id"
    _order = "user_id, dashboard_id"

    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        ondelete="cascade",
        index=True,
    )
    user_role = fields.Char(
        string="User Role",
        compute="_compute_user_role",
        store=True,
        readonly=True,
    )
    dashboard_id = fields.Many2one(
        "ks_dashboard_ninja.board",
        string="Dashboard",
        required=True,
        ondelete="cascade",
        index=True,
    )
    dashboard_top_menu_id = fields.Many2one(
        "ir.ui.menu",
        string="Dashboard Category",
        related="dashboard_id.ks_dashboard_top_menu_id",
        store=True,
        index=True,
        readonly=True,
        help="Top-level dashboard menu the dashboard belongs to "
             "(e.g. Service Dashboards, Contract Dashboards).",
    )
    has_access = fields.Boolean(
        string="Has Access",
        default=False,
        help="If ticked, the user can see and use this dashboard. "
             "If unticked, the dashboard is hidden for this user.",
    )
    has_access_int = fields.Integer(
        string="Granted",
        compute="_compute_has_access_int",
        store=True,
        group_operator="sum",
        help="1 when has_access is True, 0 otherwise. Used for group-by aggregation.",
    )

    _sql_constraints = [
        (
            "user_dashboard_uniq",
            "unique(user_id, dashboard_id)",
            "A user can only have one rights record per dashboard.",
        ),
    ]

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    # Mapping mirrors ``dbmodel.jobcards.analysis.user_role_map`` in
    # ``service_dashboard``: the user's role label is derived from the
    # four service-side groups defined in ``machine_repair_management``.
    # Multi-role users get a comma-joined string.
    _DR_ROLE_GROUPS = (
        ("machine_repair_management.group_parts_user",                "Parts"),
        ("machine_repair_management.group_technical_allocation_user", "Coordinator"),
        ("machine_repair_management.group_call_center_user",          "Call Center"),
        ("machine_repair_management.group_job_card_mobile_user",      "Technician"),
    )

    @api.model
    def _dr_role_for_user(self, user):
        """Return the same role label that service_dashboard charts show.

        Resolved from ``machine_repair_management`` group memberships.
        Falls back to ``False`` when the user is in none of those groups
        (matches the chart behaviour, which leaves user_role NULL).
        """
        if not user:
            return False
        labels = []
        for xmlid, label in self._DR_ROLE_GROUPS:
            try:
                if user.has_group(xmlid):
                    labels.append(label)
            except ValueError:
                # Group not present in this DB — ignore.
                continue
        return ", ".join(labels) if labels else False

    @api.depends("has_access")
    def _compute_has_access_int(self):
        for rec in self:
            rec.has_access_int = 1 if rec.has_access else 0

    @api.depends("user_id", "user_id.groups_id")
    def _compute_user_role(self):
        for rec in self:
            rec.user_role = self._dr_role_for_user(rec.user_id)

    # ------------------------------------------------------------------
    # Public helpers — used by enforcement (ir.ui.menu / ks board)
    # ------------------------------------------------------------------
    @api.model
    def _is_admin_user(self, user):
        """Admin = the superuser only. Every other user — including the
        bootstrap Administrator (``base.user_admin``) — must have an
        explicit ``has_access=True`` row in :class:`dashboard.rights` to
        see a dashboard, so their toggles in the matrix wizard are fully
        configurable.
        """
        if not user:
            return False
        return user._is_superuser()

    @api.model
    def user_has_dashboard_access(self, user, dashboard):
        """Return True iff ``user`` is allowed to see/use ``dashboard``."""
        if not dashboard:
            return True
        if self._is_admin_user(user):
            return True
        rec = self.sudo().search(
            [("user_id", "=", user.id), ("dashboard_id", "=", dashboard.id)],
            limit=1,
        )
        return bool(rec and rec.has_access)

    def action_open_matrix(self):
        """Open the rights-matrix wizard pre-filled and loaded for self.user_id.

        Called when a row is clicked in the Dashboard Rights list view.
        Creates a fresh matrix transient record, loads all dashboards and
        the users tab, then navigates to the matrix form.
        """
        self.ensure_one()
        Matrix = self.env["dashboard.rights.matrix"]
        matrix = Matrix.create({"user_id": self.user_id.id})
        # Load dashboards + users tab (ignore the returned reload action)
        matrix.action_load_dashboards()
        view_id = self.env.ref(
            "dashboard_rights.view_dashboard_rights_matrix_form"
        ).id
        return {
            "type": "ir.actions.act_window",
            "name": _("Dashboard Rights Setup"),
            "res_model": "dashboard.rights.matrix",
            "view_mode": "form",
            "view_id": view_id,
            "views": [[view_id, "form"]],
            "res_id": matrix.id,
            "target": "current",
        }

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None,
                   orderby=False, lazy=True):
        result = super().read_group(
            domain, fields, groupby,
            offset=offset, limit=limit, orderby=orderby, lazy=lazy,
        )
        if not groupby:
            return result
        first_gb = groupby[0].split(":")[0]
        if first_gb == "user_role":
            # Replace __count with the number of distinct users in each group
            all_ids = self.search(domain).ids
            if all_ids:
                self.env.cr.execute(
                    "SELECT COALESCE(user_role, ''), COUNT(DISTINCT user_id) "
                    "FROM dashboard_rights WHERE id = ANY(%s) GROUP BY user_role",
                    [all_ids],
                )
                role_user_count = {r[0]: r[1] for r in self.env.cr.fetchall()}
                for grp in result:
                    role_key = grp.get("user_role") or ""
                    grp["__count"] = role_user_count.get(role_key, 0)
        return result

    @api.model
    def _sync_missing_records(self):
        """Ensure every active internal non-admin user has a dashboard.rights
        row for every ks_dashboard board.  Missing rows are created with
        has_access=False.  Idempotent — safe to call on every list load.
        """
        board_ids = self.env["ks_dashboard_ninja.board"].sudo().search([]).ids
        if not board_ids:
            return

        admin = self.env.ref("base.user_admin", raise_if_not_found=False)
        exclude_ids = [admin.id] if admin else []

        user_ids = self.env["res.users"].sudo().search([
            ("share", "=", False),
            ("active", "=", True),
            ("id", "not in", exclude_ids),
        ]).ids
        if not user_ids:
            return

        # One SQL query to find all existing (user, board) pairs
        self.env.cr.execute(
            "SELECT user_id, dashboard_id FROM dashboard_rights "
            "WHERE user_id = ANY(%s) AND dashboard_id = ANY(%s)",
            [user_ids, board_ids],
        )
        existing = {(r[0], r[1]) for r in self.env.cr.fetchall()}

        to_create = [
            {"user_id": uid, "dashboard_id": bid, "has_access": False}
            for uid in user_ids
            for bid in board_ids
            if (uid, bid) not in existing
        ]
        if to_create:
            self.sudo().create(to_create)

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None,
                        order=None, count_limit=None):
        """Sync missing rows before every list-view load so all users always
        appear for every dashboard."""
        self._sync_missing_records()
        return super().web_search_read(
            domain, specification,
            offset=offset, limit=limit,
            order=order, count_limit=count_limit,
        )

    @api.model
    def allowed_dashboard_ids(self, user):
        """Return the set of dashboard ids the user is allowed to access.

        Admin users get every active dashboard.
        """
        Board = self.env["ks_dashboard_ninja.board"].sudo()
        if self._is_admin_user(user):
            return set(Board.search([]).ids)
        records = self.sudo().search(
            [("user_id", "=", user.id), ("has_access", "=", True)]
        )
        return set(records.mapped("dashboard_id").ids)
