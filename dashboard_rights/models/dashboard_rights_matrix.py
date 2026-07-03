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


def _dr_count_label(children):
    """`<granted> / <total>` for a group's child dashboard lines."""
    granted = sum(1 for c in children if c.has_access)
    return "%d / %d" % (granted, len(children))


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

    # ------------------------------------------------------------------
    # Save = the single commit point
    # ------------------------------------------------------------------
    # The Dashboards tree is bound directly to the real ``line_ids`` field, so
    # toggling rows only changes the form's in-memory state — native Save and
    # native Discard (the Refresh icon) therefore behave normally and revert
    # cleanly. Persistence to dashboard.rights happens here, only when the form
    # is actually saved (i.e. ``line_ids`` appears in the write vals).
    def write(self, vals):
        res = super().write(vals)
        if "line_ids" in vals and not self.env.context.get("skip_line_commit"):
            for rec in self:
                rec._commit_lines_to_rights()
        return res

    def _commit_lines_to_rights(self):
        """Push the current line state to dashboard.rights (called on Save)."""
        from collections import defaultdict
        self.ensure_one()
        if not self.line_ids:
            return

        children_by_menu = defaultdict(
            lambda: self.env["dashboard.rights.matrix.line"]
        )
        parent_by_menu = {}
        for line in self.line_ids:
            if line.is_group:
                parent_by_menu[line.menu_name] = line
            else:
                children_by_menu[line.menu_name] |= line

        for menu, parent in parent_by_menu.items():
            children = children_by_menu.get(menu)
            if not children:
                continue
            # The live cascade already reconciled group vs. child state in the
            # browser; re-assert the group row + its count defensively so a
            # saved record is always self-consistent on reload.
            all_on = all(c.has_access for c in children)
            if parent.has_access != all_on:
                parent.has_access = all_on
            count = _dr_count_label(children)
            if parent.dashboard_name != count:
                parent.dashboard_name = count

        # Persist child rows to dashboard.rights, then snapshot the saved state
        # so the next toggle is detected against this baseline.
        self.line_ids._propagate_to_dashboard_rights()
        for line in self.line_ids:
            if line.has_access_original != line.has_access:
                line.has_access_original = line.has_access
            if line.has_access_prev != line.has_access:
                line.has_access_prev = line.has_access

    # ------------------------------------------------------------------
    # The live group cascade/roll-up + count are handled entirely client-side
    # by reactive widgets (see static/src/js/dashboard_rights_matrix_list.js:
    # `dr_access_toggle` for the master group toggle, `dr_group_count` for the
    # count). No server onchange is needed, which avoids the fragile
    # group-vs-child detection that previously re-forced dashboards back ON.
    # Nothing is committed until Save -> write() -> _commit_lines_to_rights.
    # ------------------------------------------------------------------

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
        Boards = Boards.filtered(
            # Keep only boards that belong to the My Dashboard menu: the special
            # "My Dashboard" board, or any board that has a top-menu. Menu-less
            # boards (e.g. the standalone "Actual vs Target") are NOT part of the
            # My Dashboard menu and must not appear as stray rows in the matrix.
            lambda b: (b.id == 1 or b.name == "My Dashboard" or b.ks_dashboard_top_menu_id)
            and not (b.name == "Service Analysis - New" and b.ks_dashboard_top_menu_id and b.ks_dashboard_top_menu_id.name == "My Dashboard")
            # Exclude the Quick Access / Configuration system boards (top menu is
            # the app root). Those menus are governed via their real sub-items
            # (dashboard.rights.menu), injected as separate groups below.
            and not (b.id != 1 and b.ks_dashboard_top_menu_id
                     and not b.ks_dashboard_top_menu_id.parent_id
                     and b.ks_dashboard_top_menu_id.name == "My Dashboard")
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

        # First, compute menu names for all boards
        board_menu_map = []
        my_dashboard_menu = self.env['ir.ui.menu'].sudo().search([('name', '=', 'My Dashboard'), ('parent_id', '=', False)], limit=1)
        my_menu_name = my_dashboard_menu.name if my_dashboard_menu else "My Dashboard"

        # Order the groups the same way they appear under the My Dashboard menu:
        # map each menu name to the sequence of its menu item (OT, CT, Promoter,
        # Contract, Loyalty, ...). Menus not found there sort last (9999).
        seq_by_name = {}
        if my_dashboard_menu:
            for child in my_dashboard_menu.sudo().child_id:
                seq_by_name[child.name] = child.sequence

        for b in Boards:
            # Group each board under the menu category it appears in beneath the
            # "My Dashboard" app (see _dr_group_menu_name). Falls back to the app
            # root name for the rare menu-less board.
            menu_name = Line._dr_group_menu_name(b) or my_menu_name

            access_val = True if is_admin else existing.get(b.id, False)
            board_menu_map.append({
                'board': b,
                'menu_name': menu_name,
                'menu_sequence': seq_by_name.get(menu_name, 9999),
                # Real menu-item sequence, so children list in the same order
                # as they appear under the actual My Dashboard menu.
                'sub_sequence': b.ks_dashboard_menu_id.sequence if b.ks_dashboard_menu_id else 9999,
                'access_val': access_val
            })

        # Group by menu_name
        from collections import defaultdict
        grouped = defaultdict(list)
        for item in board_menu_map:
            grouped[item['menu_name']].append(item)

        vals_list = []
        for menu_name, items in grouped.items():
            if not menu_name:
                for item in items:
                    vals_list.append({
                        "matrix_id": self.id,
                        "dashboard_id": item['board'].id,
                        "dashboard_name": Line._dr_board_display_name(item['board']),
                        "menu_sequence": item['menu_sequence'],
                        "sub_sequence": item['sub_sequence'],
                        "has_access": item['access_val'],
                        "has_access_original": item['access_val'],
                        "has_access_prev": item['access_val'],
                        "is_user_admin": is_admin,
                    })
                continue

            # Check if all children are ON
            all_on = all(item['access_val'] for item in items)

            # Group row "Dashboard Name" column shows the live selection count:
            # <granted children> / <total children> for this menu.
            granted = sum(1 for item in items if item['access_val'])
            count_label = "%d / %d" % (granted, len(items))
            menu_seq = items[0]['menu_sequence']

            # Create group row
            vals_list.append({
                "matrix_id": self.id,
                "dashboard_id": False,
                "is_group": True,
                "menu_name": menu_name,
                "menu_sequence": menu_seq,
                "sub_sequence": -1,
                "dashboard_name": count_label,
                "has_access": all_on,
                "has_access_original": all_on,
                "has_access_prev": all_on,
                "is_user_admin": is_admin,
            })

            # Create children rows
            for item in items:
                vals_list.append({
                    "matrix_id": self.id,
                    "dashboard_id": item['board'].id,
                    "dashboard_name": Line._dr_board_display_name(item['board']),
                    "menu_sequence": item['menu_sequence'],
                    "sub_sequence": item['sub_sequence'],
                    "has_access": item['access_val'],
                    "has_access_original": item['access_val'],
                    "has_access_prev": item['access_val'],
                    "is_user_admin": is_admin,
                })

        # Inject the menu-governed groups: Quick Access / Configuration sub-items
        # are plain ir.ui.menu records (not boards), controlled per user via
        # dashboard.rights.menu. Like dashboards, they are hidden until granted.
        RightsMenu = self.env["dashboard.rights.menu"].sudo()
        granted_menu_ids = set(
            RightsMenu.search([
                ("user_id", "=", self.user_id.id),
                ("has_access", "=", True),
            ]).mapped("menu_id").ids
        )
        for parent_xmlid in (
            "ks_dashboard_ninja.quick_access_menu",
            "ks_dashboard_ninja.configuration_menu",
        ):
            parent = self.env.ref(parent_xmlid, raise_if_not_found=False)
            if not parent:
                continue
            # Fetch the children with raw SQL + browse rather than
            # ``parent.sudo().child_id``: ``.sudo()`` only flips ``su`` while
            # keeping ``env.user`` as the *logged-in* user (e.g. the uid-2
            # "Administrator", who is NOT the superuser). Reading ``child_id``
            # then goes through the bridge's ``ir.ui.menu.search`` override,
            # which hides any managed menu that user hasn't been granted — so
            # the children vanish and the whole group is skipped. SQL + browse
            # reads the rows directly, never re-entering the search override.
            self.env.cr.execute(
                "SELECT id FROM ir_ui_menu WHERE parent_id = %s "
                "ORDER BY sequence, id",
                (parent.id,),
            )
            kid_ids = [row[0] for row in self.env.cr.fetchall()]
            if not kid_ids:
                continue
            kids = self.env["ir.ui.menu"].sudo().browse(kid_ids)
            parent_seq = seq_by_name.get(parent.name, 9999)
            child_access = [
                (k, True if is_admin else (k.id in granted_menu_ids))
                for k in kids
            ]
            all_on = all(acc for _k, acc in child_access)
            granted = sum(1 for _k, acc in child_access if acc)
            vals_list.append({
                "matrix_id": self.id,
                "dashboard_id": False,
                "is_group": True,
                "menu_name": parent.name,
                "menu_sequence": parent_seq,
                "sub_sequence": -1,
                "dashboard_name": "%d / %d" % (granted, len(child_access)),
                "has_access": all_on,
                "has_access_original": all_on,
                "has_access_prev": all_on,
                "is_user_admin": is_admin,
            })
            for k, acc in child_access:
                vals_list.append({
                    "matrix_id": self.id,
                    "menu_id": k.id,
                    "menu_name": parent.name,
                    "dashboard_name": k.name,
                    "menu_sequence": parent_seq,
                    "sub_sequence": k.sequence,
                    "has_access": acc,
                    "has_access_original": acc,
                    "has_access_prev": acc,
                    "is_user_admin": is_admin,
                })

        if vals_list:
            Line.with_context(skip_propagation=True).create(vals_list)

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
    # Bulk grant / revoke is now fully client-side (staged, Save-gated):
    # see static/src/js/dashboard_bulk_buttons.js. It selects/unselects every
    # loaded dashboard row in the browser and leaves the form dirty, so the
    # change is committed only on Save and reverted by the Refresh (discard)
    # icon. The group cascade + count is handled live by
    # _onchange_line_ids_cascade.
    # ------------------------------------------------------------------

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
    _order = "menu_sequence, menu_name, sub_sequence, dashboard_name"

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
        readonly=True,
        index=True,
    )
    menu_id = fields.Many2one(
        "ir.ui.menu",
        string="Menu Item",
        readonly=True,
        index=True,
        help="Set on rows that govern a plain utility menu (Quick Access / "
             "Configuration sub-items) rather than a KS dashboard board. "
             "Persisted to dashboard.rights.menu on Save.",
    )
    is_group = fields.Boolean(
        string="Is Group Row",
        default=False,
        readonly=True,
        help="True for a menu/category header row (the master toggle + count); "
             "False for an individual dashboard or menu-item row. Used by the "
             "list widgets to tell groups from children.",
    )
    menu_name = fields.Char(
        string="Menu",
        compute="_compute_menu_name",
        store=True,
        readonly=True,
    )
    menu_sequence = fields.Integer(
        string="Menu Sequence",
        default=9999,
        readonly=True,
        help="Sequence of this dashboard's menu under the My Dashboard menu, "
             "so the groups list in the same order as the menu (OT, CT, "
             "Promoter, ...). Menus not found there sort last.",
    )
    sub_sequence = fields.Integer(
        string="Sub Sequence",
        default=9999,
        readonly=True,
        help="Ordering within a menu group: -1 for the group row itself (so it "
             "always sorts first), otherwise the real ir.ui.menu sequence of the "
             "board/menu-item, so children list in the same order as the actual "
             "menu instead of alphabetically.",
    )
    dashboard_name = fields.Char(
        string="Dashboard Name",
        readonly=True,
        help="For a dashboard row: the board's name. For a group (menu) row: "
             "the live '<granted> / <total>' selection count. Kept as a plain "
             "field (not computed) so the onchange that recomputes the count on "
             "every toggle is reflected in the browser before Save.",
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
    has_access_prev = fields.Boolean(
        string="Previous Access",
        default=False,
        readonly=True,
        help="Tracks the last-known Has Access value between onchanges so the "
             "live parent/child cascade can tell whether the group row or a "
             "child row was the one toggled. UI-only; never persisted to "
             "dashboard.rights.",
    )
    is_user_admin = fields.Boolean(
        string="User Is Admin",
        default=False,
        readonly=True,
        help="Mirrors whether the parent user is the admin — used to lock "
             "the Has Access toggle in the view.",
    )

    @api.depends("dashboard_id", "menu_id")
    def _compute_menu_name(self):
        for rec in self:
            if rec.dashboard_id:
                # Group a board under its menu category so the child row matches
                # its group row (the JS pairs children to groups by menu_name).
                rec.menu_name = self._dr_group_menu_name(rec.dashboard_id)
            elif rec.menu_id:
                # Menu-item child: grouped under its parent menu (Quick Access /
                # Configuration).
                rec.menu_name = rec.menu_id.parent_id.name or rec.menu_id.name
            # Group header rows carry no dashboard_id/menu_id; their menu_name is
            # set explicitly at creation and left untouched here.

    @staticmethod
    def _dr_group_menu_name(board):
        """The matrix group (category) a board belongs to: the menu directly
        under the "My Dashboard" app root in the board's menu ancestry.

        For most boards that's the top menu (e.g. "My Dashboards",
        "Service Dashboards - OT"). System boards like Quick Access /
        Configuration hang straight off the app root, so their top menu is the
        root itself — for those, the board's own leaf menu IS the category.
        """
        if not board:
            return False
        top = board.ks_dashboard_top_menu_id
        if top and not top.parent_id and top.name == "My Dashboard":
            leaf = board.ks_dashboard_menu_id
            return leaf.name if leaf else top.name
        return top.name if top else False

    @staticmethod
    def _dr_board_display_name(board):
        """Label shown in the Dashboard Name column for a dashboard row."""
        return board.name or False

    # ------------------------------------------------------------------
    # Propagate Has Access toggles to dashboard.rights
    # ------------------------------------------------------------------
    # NOTE: matrix line edits are intentionally NOT propagated to
    # dashboard.rights here. The whole page is Save-gated: toggling rows only
    # changes the transient line state in the browser, the live parent/child
    # cascade is handled by
    # DashboardRightsMatrix._onchange_line_ids_cascade, and the single commit
    # point is DashboardRightsMatrix.write -> _commit_lines_to_rights (the form
    # Save). Discard (the Refresh icon) therefore reverts cleanly to the loaded
    # state because nothing was written.

    def _propagate_to_dashboard_rights(self):
        Rights = self.env["dashboard.rights"].sudo()
        RightsMenu = self.env["dashboard.rights.menu"].sudo()
        to_create = []
        menu_to_create = []
        for rec in self:
            if rec.is_group or not rec.matrix_id.user_id:
                continue
            user = rec.matrix_id.user_id
            val = bool(rec.has_access)
            # Menu-item row -> dashboard.rights.menu.
            if rec.menu_id:
                existing = RightsMenu.search(
                    [("user_id", "=", user.id),
                     ("menu_id", "=", rec.menu_id.id)],
                    limit=1,
                )
                if existing:
                    if existing.has_access != val:
                        existing.has_access = val
                else:
                    menu_to_create.append({
                        "user_id": user.id,
                        "menu_id": rec.menu_id.id,
                        "has_access": val,
                    })
                continue
            # Dashboard board row -> dashboard.rights.
            if not rec.dashboard_id:
                continue
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
        if menu_to_create:
            RightsMenu.create(menu_to_create)


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
