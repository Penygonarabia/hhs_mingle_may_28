# -*- coding: utf-8 -*-
"""Header + detail page for managing dashboard access (user-centric).

User flow on the page:

    Header
    ──────
    User Name : [ Alice Smith   ▼ ]
    Email     : alice@example.com     (read-only)
    User Role : Technician            (read-only)
                                      [ Load Dashboards ]

    Detail — Dashboards tab (one row per dashboard)
    ────────────────────────────────────────────────
    Menu                  Dashboard Name               Has Access
    ──────────────────────────────────────────────────────────────
    Service Dashboards    Service Analysis - New          [x]
    Service Dashboards    Technician Analysis - New       [ ]
    My Dashboards         My Dashboard                    [ ]
    ...

Clicking **Load Dashboards** materialises one
:class:`DashboardRightsMatrixLine` per active board, then inline toggles
write through to :class:`dashboard.rights`.
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Header model — the page itself
# ---------------------------------------------------------------------------
class DashboardRightsMatrix(models.TransientModel):
    _name = "dashboard.rights.matrix"
    _description = "Dashboard Rights — Page"

    def _compute_display_name(self):
        # Avoid duplicating the action name ("Dashboard Rights Setup") in the
        # breadcrumb — use the selected user's name, or "New" before pick.
        for rec in self:
            rec.display_name = rec.user_id.name or _("New")

    @api.model
    def action_new_wizard(self):
        """Create a blank wizard record and open it as an existing record (no dirty state on load)."""
        record = self.create({})
        return record._reload_self()

    def action_select_user_id(self, user_id):
        """Switch this matrix to a specific user without relying on the
        matrix.user line ID, which is unstable: the Users-tab refresh
        unlinks-and-recreates those lines to bypass OWL's stale cache,
        so a click can land on an obsolete line id."""
        self.ensure_one()
        if not user_id:
            return False
        self.line_ids.unlink()
        self.write({"user_id": user_id, "lines_loaded": False})
        return self.action_load_dashboards()

    def action_reload_users_tab(self):
        """Refresh Users tab data without a page reload.
        Recreates user_list_ids so new record IDs bypass the client's stale pool cache.
        Returns False — the JS side calls record.load() to pick up the fresh data,
        which preserves the breadcrumb navigation."""
        self.ensure_one()
        if not self.user_list_ids:
            return False
        UserLine = self.env["dashboard.rights.matrix.user"].sudo()
        existing_users = self.user_list_ids.mapped("user_id")
        self.user_list_ids.unlink()
        user_vals = [{"matrix_id": self.id, "user_id": u.id} for u in existing_users]
        if user_vals:
            UserLine.create(user_vals)
        return False

    # ----- Header fields -----------------------------------------------
    user_id = fields.Many2one(
        "res.users",
        string="User Name",
        domain=[("share", "=", False), ("active", "=", True)],
        help="Select an internal user to manage their dashboard access.",
    )
    user_email = fields.Char(
        string="Email",
        related="user_id.login",
        readonly=True,
    )
    user_role = fields.Char(
        string="User Role",
        compute="_compute_user_role",
        readonly=True,
    )
    is_user_admin = fields.Boolean(
        string="Is Admin",
        compute="_compute_is_user_admin",
        readonly=True,
    )
    line_ids = fields.One2many(
        "dashboard.rights.matrix.line",
        "matrix_id",
        string="Dashboards",
    )
    visible_line_ids = fields.Many2many(
        "dashboard.rights.matrix.line",
        string="Visible Dashboards",
        compute="_compute_visible_line_ids",
    )
    lines_loaded = fields.Boolean(
        string="Lines Loaded",
        default=False,
    )
    search_text = fields.Char(
        string="Search",
        default="",
        help="Search by Menu or Dashboard Name (case-insensitive substring).",
    )

    # ----- Users tab fields --------------------------------------------
    user_list_ids = fields.One2many(
        "dashboard.rights.matrix.user",
        "matrix_id",
        string="Users",
    )
    user_search_text_tab = fields.Char(
        string="Search Users",
        default="",
        help="Search by User Name, Email or User Role (case-insensitive substring).",
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("user_id", "user_id.groups_id")
    def _compute_user_role(self):
        Rights = self.env["dashboard.rights"].sudo()
        for rec in self:
            rec.user_role = Rights._dr_role_for_user(rec.user_id) if rec.user_id else False

    @api.depends("user_id", "user_id.groups_id")
    def _compute_is_user_admin(self):
        Rights = self.env["dashboard.rights"].sudo()
        for rec in self:
            rec.is_user_admin = Rights._is_admin_user(rec.user_id) if rec.user_id else False

    @api.depends(
        "line_ids",
        "line_ids.menu_name",
        "line_ids.dashboard_name",
        "search_text",
    )
    def _compute_visible_line_ids(self):
        for rec in self:
            q = (rec.search_text or "").strip().lower()
            if not q:
                rec.visible_line_ids = rec.line_ids
                continue
            rec.visible_line_ids = rec.line_ids.filtered(
                lambda l: q in (l.menu_name or "").lower()
                or q in (l.dashboard_name or "").lower()
            )

    # ------------------------------------------------------------------
    # Onchange: reset lines when user changes
    # ------------------------------------------------------------------
    @api.onchange("user_id")
    def _onchange_user_id(self):
        self.lines_loaded = False

    # ------------------------------------------------------------------
    # Button: load all dashboards for the selected user
    # ------------------------------------------------------------------
    def action_load_dashboards(self):
        self.ensure_one()
        if not self.user_id:
            raise ValidationError(_("Please select a User first."))

        Line = self.env["dashboard.rights.matrix.line"].sudo()
        UserLine = self.env["dashboard.rights.matrix.user"].sudo()
        Rights = self.env["dashboard.rights"].sudo()

        # Wipe any previous lines (user may have switched selection).
        Line.search([("matrix_id", "=", self.id)]).unlink()
        UserLine.search([("matrix_id", "=", self.id)]).unlink()

        Boards = self.env["ks_dashboard_ninja.board"].sudo().search(
            [], order="ks_dashboard_top_menu_id, name"
        )

        # Pre-load existing rights for this user.
        existing = {
            r.dashboard_id.id: r.has_access
            for r in Rights.search([
                ("user_id", "=", self.user_id.id),
                ("dashboard_id", "in", Boards.ids),
            ])
        }

        is_admin = Rights._is_admin_user(self.user_id)

        vals_list = []
        for b in Boards:
            access_val = True if is_admin else existing.get(b.id, False)
            vals_list.append({
                "matrix_id": self.id,
                "dashboard_id": b.id,
                "has_access": access_val,
                "has_access_original": access_val,
                "is_user_admin": is_admin,
            })
        if vals_list:
            Line.create(vals_list)

        # Load all internal users into the Users tab lines.
        Users = self.env["res.users"].sudo().search(
            [("share", "=", False), ("active", "=", True)], order="name"
        )
        # dashboard_rights_given is a non-stored computed field; it is filled
        # on read by _compute_dashboard_rights_given, so it must not be passed
        # into create() (the value would just be discarded on the next recompute).
        user_vals = [
            {"matrix_id": self.id, "user_id": u.id}
            for u in Users
        ]
        if user_vals:
            UserLine.create(user_vals)

        self.lines_loaded = True
        # Return False so Odoo just reloads the current form in place,
        # rather than pushing a duplicate action onto the breadcrumb stack
        # (which would show the same user name twice).
        return False

    # ------------------------------------------------------------------
    # Bulk grant / revoke — server-side persistence
    # ------------------------------------------------------------------
    def action_bulk_set_access(self, value, line_ids=None):
        """Set has_access=value on the given matrix lines AND write straight
        through to dashboard.rights, without waiting for the form Save.

        The JS bulk buttons call this so the persistence does not depend on
        the parent matrix form's save round-trip (which routes through the
        computed/non-stored ``visible_line_ids`` and has been observed to
        drop updates on some servers).
        """
        self.ensure_one()
        if not self.user_id:
            return False
        Line = self.env["dashboard.rights.matrix.line"].sudo()
        if line_ids:
            lines = Line.browse(line_ids).exists().filtered(
                lambda l: l.matrix_id.id == self.id
            )
        else:
            lines = self.line_ids
        if not lines:
            return False
        val = bool(value)
        # Skip admin: their toggles are locked True by view logic.
        Rights = self.env["dashboard.rights"].sudo()
        if Rights._is_admin_user(self.user_id):
            return False
        # 1) Update transient lines so the UI re-reads the same values.
        lines.write({"has_access": val})
        # 2) Hard-write to dashboard.rights so a refresh sees the change.
        board_ids = lines.mapped("dashboard_id").ids
        existing = Rights.search([
            ("user_id", "=", self.user_id.id),
            ("dashboard_id", "in", board_ids),
        ])
        existing_by_board = {r.dashboard_id.id: r for r in existing}
        to_create = []
        for bid in board_ids:
            rec = existing_by_board.get(bid)
            if rec:
                if rec.has_access != val:
                    rec.has_access = val
            else:
                to_create.append({
                    "user_id": self.user_id.id,
                    "dashboard_id": bid,
                    "has_access": val,
                })
        if to_create:
            Rights.create(to_create)
        return True

    def action_reset_dashboards(self):
        self.ensure_one()
        if not self.lines_loaded:
            return False
        for line in self.line_ids:
            if line.has_access != line.has_access_original:
                line.write({"has_access": line.has_access_original})
        return False

    def _reload_self(self):
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
            "res_id": self.id,
            "target": "current",
            "context": dict(self.env.context),
        }


# ---------------------------------------------------------------------------
# Detail-line model — one row per dashboard
# ---------------------------------------------------------------------------
class DashboardRightsMatrixLine(models.TransientModel):
    _name = "dashboard.rights.matrix.line"
    _description = "Dashboard Rights — Dashboard Row"
    _order = "menu_name, dashboard_name"

    matrix_id = fields.Many2one(
        "dashboard.rights.matrix",
        string="Matrix",
        ondelete="cascade",
        required=True,
        index=True,
    )
    dashboard_id = fields.Many2one(
        "ks_dashboard_ninja.board",
        string="Dashboard",
        required=True,
        readonly=True,
        index=True,
    )
    menu_name = fields.Char(
        string="Menu",
        compute="_compute_menu_name",
        store=True,
        readonly=True,
    )
    dashboard_name = fields.Char(
        string="Dashboard Name",
        related="dashboard_id.name",
        store=True,
        readonly=True,
    )
    has_access = fields.Boolean(
        string="Has Access",
        default=False,
    )
    has_access_original = fields.Boolean(
        string="Original Access",
        default=False,
        readonly=True,
    )
    is_user_admin = fields.Boolean(
        string="User Is Admin",
        default=False,
        readonly=True,
        help="Mirrors whether the parent user is the admin — used to lock "
             "the Has Access toggle in the view.",
    )

    @api.depends("dashboard_id")
    def _compute_menu_name(self):
        for rec in self:
            top = rec.dashboard_id.ks_dashboard_top_menu_id if rec.dashboard_id else False
            rec.menu_name = top.name if top else False

    # ------------------------------------------------------------------
    # Propagate Has Access toggles to dashboard.rights
    # ------------------------------------------------------------------
    def write(self, vals):
        if "has_access" in vals:
            res = super().write(vals)
            self._propagate_to_dashboard_rights()
            return res
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        recs._propagate_to_dashboard_rights()
        return recs

    def _propagate_to_dashboard_rights(self):
        Rights = self.env["dashboard.rights"].sudo()
        to_create = []
        for rec in self:
            if not rec.dashboard_id or not rec.matrix_id.user_id:
                continue
            user = rec.matrix_id.user_id
            val = bool(rec.has_access)
            existing = Rights.search(
                [("user_id", "=", user.id),
                 ("dashboard_id", "=", rec.dashboard_id.id)],
                limit=1,
            )
            if existing:
                if existing.has_access != val:
                    existing.has_access = val
            else:
                to_create.append({
                    "user_id": user.id,
                    "dashboard_id": rec.dashboard_id.id,
                    "has_access": val,
                })
        if to_create:
            Rights.create(to_create)


# ---------------------------------------------------------------------------
# Users-tab line model — one row per internal user
# ---------------------------------------------------------------------------
class DashboardRightsMatrixUser(models.TransientModel):
    _name = "dashboard.rights.matrix.user"
    _description = "Dashboard Rights — User Row"
    _order = "user_role, user_name"

    matrix_id = fields.Many2one(
        "dashboard.rights.matrix",
        string="Matrix",
        ondelete="cascade",
        required=True,
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        readonly=True,
        index=True,
    )
    user_name = fields.Char(
        string="User Name",
        related="user_id.name",
        store=True,
        readonly=True,
    )
    user_email = fields.Char(
        string="Email",
        related="user_id.login",
        store=True,
        readonly=True,
    )
    user_role = fields.Char(
        string="User Role",
        compute="_compute_user_role",
        store=True,
        readonly=True,
    )
    dashboard_rights_given = fields.Char(
        string="Rights Given Dashboards",
        compute="_compute_dashboard_rights_given",
        readonly=True,
    )

    @api.depends("user_id", "user_id.groups_id")
    def _compute_user_role(self):
        Rights = self.env["dashboard.rights"].sudo()
        for rec in self:
            rec.user_role = Rights._dr_role_for_user(rec.user_id) or False

    @api.depends("matrix_id.line_ids.has_access")
    def _compute_dashboard_rights_given(self):
        all_rights = self.env["dashboard.rights"].sudo().search([
            ("user_id", "in", self.mapped("user_id").ids),
            ("has_access", "=", True),
        ])
        by_user = {}
        for r in all_rights:
            by_user.setdefault(r.user_id.id, []).append(r.dashboard_id.name)
        for rec in self:
            names = by_user.get(rec.user_id.id, [])
            rec.dashboard_rights_given = ", ".join(names) if names else False

    def action_select(self):
        """Select this user on the matrix and reload with their dashboards."""
        self.ensure_one()
        matrix = self.matrix_id
        matrix.line_ids.unlink()
        matrix.write({"user_id": self.user_id.id, "lines_loaded": False})
        return matrix.action_load_dashboards()
