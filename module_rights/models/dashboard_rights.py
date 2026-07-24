# -*- coding: utf-8 -*-
"""Persistent per-user, per-dashboard access rights.

This model is independent of `module_user_rights_roles` and is the single
source of truth for whether a given user can see/use a given ks_dashboard
board.

One record per (user, dashboard). Defaults to has_access=False for every
user. Only the true superuser (``__system__``) is always considered to have
access — see ``_is_admin_user`` / ``user_has_dashboard_access``. Every other
user (including Settings admins and the bootstrap Administrator) is governed
by their explicit rows, so their access is configurable from the matrix.
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
        compute="_compute_dashboard_top_menu_id",
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
    access_status = fields.Char(
        string="Status",
        compute="_compute_access_status",
        store=False,
        help="Shows how many dashboards the user can access vs total (e.g. '5 / 12').",
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

    def _compute_access_status(self):
        """Compute 'granted / total' dashboard counts for each user.

        Uses a single SQL query to fetch aggregated counts for all users
        in the current recordset, avoiding N+1 queries.
        """
        if not self:
            return
        user_ids = list({rec.user_id.id for rec in self if rec.user_id})
        if not user_ids:
            for rec in self:
                rec.access_status = "0 / 0"
            return

        self.env.cr.execute(
            """
            SELECT
                user_id,
                SUM(CASE WHEN has_access THEN 1 ELSE 0 END) AS granted,
                COUNT(*) AS total
            FROM dashboard_rights
            WHERE user_id = ANY(%s)
            GROUP BY user_id
            """,
            [user_ids],
        )
        counts = {row[0]: (row[1], row[2]) for row in self.env.cr.fetchall()}
        for rec in self:
            uid = rec.user_id.id
            if uid and uid in counts:
                granted, total = counts[uid]
                rec.access_status = f"{int(granted)} / {int(total)}"
            else:
                rec.access_status = "0 / 0"

    @api.depends("dashboard_id", "dashboard_id.ks_dashboard_top_menu_id")
    def _compute_dashboard_top_menu_id(self):
        my_dashboard_menu = self.env['ir.ui.menu'].sudo().search([('name', '=', 'My Dashboard'), ('parent_id', '=', False)], limit=1)
        for rec in self:
            if rec.dashboard_id.id == 1 or rec.dashboard_id.name == "My Dashboard":
                rec.dashboard_top_menu_id = my_dashboard_menu.id if my_dashboard_menu else False
            else:
                rec.dashboard_top_menu_id = rec.dashboard_id.ks_dashboard_top_menu_id.id if rec.dashboard_id else False

    @api.depends("user_id", "user_id.groups_id")
    def _compute_user_role(self):
        for rec in self:
            rec.user_role = self._dr_role_for_user(rec.user_id)

    # ------------------------------------------------------------------
    # CRUD — invalidate the menu visibility cache on any rights change
    # ------------------------------------------------------------------
    # ir.ui.menu._visible_menu_ids is ormcache'd by the user's groups, and our
    # enforcement (ir_ui_menu._dr_restricted_menu_ids) runs inside it. Changing
    # a dashboard.rights row does NOT touch groups, so without clearing the
    # registry cache the worker keeps serving the old menu (a granted/revoked
    # dashboard stays visible/hidden until restart). Mirror what ir.ui.menu
    # itself does on write.
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
    # Public helpers — used by enforcement (ir.ui.menu / ks board)
    # ------------------------------------------------------------------
    @api.model
    def _is_admin_user(self, user):
        """Admin = ONLY the true superuser (``__system__``), who always sees
        every dashboard and bypasses access checks anyway.

        Everyone else is fully configurable — including Settings administrators
        (``base.group_system``) and the bootstrap Administrator
        (``base.user_admin``). They see a dashboard only when they have an
        explicit ``has_access=True`` row in :class:`dashboard.rights`, so
        Grant/Revoke in the Users Setup matrix persists for them.

        NB: previously every ``base.group_system`` member auto-saw all
        dashboards, which made Revoke silently reset for the ~77 Settings
        admins; that short-circuit was removed so their access is controllable.
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
            "module_rights.view_dashboard_rights_matrix_form"
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
        boards = self.env["ks_dashboard_ninja.board"].sudo().search([])
        boards = boards.filtered(
            # Only boards that belong to the My Dashboard menu: the special
            # "My Dashboard" board, or any board with a top-menu. Menu-less
            # boards (e.g. the standalone "Actual vs Target") are out of scope.
            lambda b: (b.id == 1 or b.name == "My Dashboard" or b.ks_dashboard_top_menu_id)
            and not (b.name == "Service Analysis - New" and b.ks_dashboard_top_menu_id and b.ks_dashboard_top_menu_id.name == "My Dashboard")
        )
        board_ids = boards.ids
        if not board_ids:
            return

        # NB: the admin user (base.user_admin) is intentionally included here so
        # it shows up in the Users Setup list. Its dashboard access is still
        # auto-granted via ``_is_admin_user`` regardless of these rows.
        user_ids = self.env["res.users"].sudo().search([
            ("share", "=", False),
            ("active", "=", True),
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
        appear for every dashboard.

        When the JS controller sets ``unique_users_only=True`` in the request
        context (triggered when all optional columns are hidden), we collapse
        the results to a single representative row per user so no duplicates
        appear in the compact default view.
        """
        self._sync_missing_records()

        ctx = self.env.context
        if ctx.get("unique_users_only"):
            # Compact view: return only the first record per user
            all_records = self.search(domain, order=order)
            seen_users = set()
            unique_ids = []
            for rec in all_records:
                if rec.user_id.id not in seen_users:
                    seen_users.add(rec.user_id.id)
                    unique_ids.append(rec.id)

            total_count = len(unique_ids)
            if offset:
                unique_ids = unique_ids[offset:]
            if limit:
                unique_ids = unique_ids[:limit]

            res_records = self.browse(unique_ids)
            return {
                "records": res_records.web_read(specification),
                "length": total_count,
            }

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
