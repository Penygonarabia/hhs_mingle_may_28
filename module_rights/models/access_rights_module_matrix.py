# -*- coding: utf-8 -*-
"""Header + detail page for managing every app's menu access (per-user).

A SEPARATE page from dashboard.rights.matrix (Users Setup's matrix), which
grants access to KS dashboard *boards* themselves (the underlying
dashboard.rights row). This page lists every app's menu tree — Machine
Repair, Promoter, Payroll, My Dashboard, ... — kept on its own screen, with
its own User selector and its own Load button, so the two lists are never
visually mixed.

Every installed app's menu shows up automatically — there is no
registry/allow-list step. Only Settings is excluded (governed by real Odoo
groups, not this per-user overlay). See ``_EXCLUDED_TOP_MENU_XMLIDS`` in
dashboard_rights_menu.py, the single source of truth this page's loader and
the enforcement in ``ir_ui_menu._dr_restricted_menu_ids`` both read from.

My Dashboard's own boards ALSO have their authoritative board-level gate in
Users Setup (dashboard.rights) — a board granted/revoked there is
automatically kept in sync with its row here too (see
``dashboard.rights.menu._dr_sync_board_and_menu``), and vice versa, so a
board's visibility never depends on which page last touched it.

Field names on this page's models deliberately mirror
dashboard.rights.matrix / dashboard.rights.matrix.line (``line_ids``,
``is_group``, ``has_access``, ``is_user_admin``, ``menu_name``,
``dashboard_name``, ``menu_sequence``, ``sub_sequence``) so the existing
``dr_access_toggle`` / ``dr_group_count`` / ``dashboard_rights_matrix_list_field``
/ ``dashboard_bulk_buttons`` JS widgets work here completely unchanged —
those widgets read record field names off ``record.model.root.data.line_ids``,
not the underlying model name, so no new JS is needed for this page.
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from .dashboard_rights_menu import _EXCLUDED_TOP_MENU_XMLIDS


class AccessRightsModuleMatrix(models.TransientModel):
    _name = "access.rights.module.matrix"
    _description = "Module Rights Setup — Page"

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.user_id.name or _("New")

    @api.model
    def action_new_wizard(self):
        """Create a blank wizard record and open it as an existing record
        (no dirty state on load) — mirrors dashboard.rights.matrix."""
        record = self.create({})
        return record._reload_self()

    # ----- Header fields -----------------------------------------------
    role_filter = fields.Selection(
        selection="_selection_role_filter",
        string="User Role",
        default="all",
        help="Filter the User Name list by role. Select All to see every user.",
    )
    user_id = fields.Many2one(
        "res.users",
        string="User Name",
        help="Select an internal user to manage their module-menu access.",
    )
    role_user_ids = fields.Many2many(
        "res.users",
        compute="_compute_role_user_ids",
        help="Users matching the selected role — the view's user_id field "
             "domain references this field by name so the User Name "
             "dropdown re-filters whenever User Role changes. (A plain "
             "onchange 'domain' return is ignored by this Odoo version's "
             "onchange dispatcher, so the filter is expressed declaratively "
             "against a computed field instead.)",
    )
    user_email = fields.Char(
        string="Email",
        related="user_id.login",
        readonly=True,
    )
    is_user_admin = fields.Boolean(
        string="Is Admin",
        compute="_compute_is_user_admin",
        readonly=True,
    )
    line_ids = fields.One2many(
        "access.rights.module.matrix.line",
        "matrix_id",
        string="Modules",
    )
    lines_loaded = fields.Boolean(
        string="Lines Loaded",
        default=False,
    )
    search_text = fields.Char(
        string="Search",
        default="",
        help="Search by Module or Menu Name (case-insensitive substring).",
    )
    access_status = fields.Char(
        string="Menus Granted",
        compute="_compute_access_status",
        help="Live '<granted> / <total>' count across every loaded menu "
             "row, for the smart button — a quick glance without opening "
             "every group.",
    )

    # ------------------------------------------------------------------
    # Role filter — options + the domain it drives on user_id
    # ------------------------------------------------------------------
    @api.model
    def _selection_role_filter(self):
        options = [("all", _("All"))]
        options += [
            (label, label)
            for _xmlid, label in self.env["dashboard.rights"]._DR_ROLE_GROUPS
        ]
        return options

    def _dr_user_domain_for_role(self, role):
        """Base user_id domain, narrowed to ``role`` (a label from
        ``dashboard.rights._DR_ROLE_GROUPS``) unless ``role`` is falsy/"all"."""
        domain = [("share", "=", False), ("active", "=", True)]
        if not role or role == "all":
            return domain
        xmlid = next(
            (x for x, label in self.env["dashboard.rights"]._DR_ROLE_GROUPS if label == role),
            None,
        )
        group = self.env.ref(xmlid, raise_if_not_found=False) if xmlid else False
        if group:
            domain.append(("groups_id", "in", group.id))
        return domain

    @api.depends("role_filter")
    def _compute_role_user_ids(self):
        Users = self.env["res.users"].sudo()
        for rec in self:
            rec.role_user_ids = Users.search(rec._dr_user_domain_for_role(rec.role_filter))

    @api.onchange("role_filter")
    def _onchange_role_filter(self):
        # Deselect a chosen user who no longer matches the new role filter —
        # the dropdown's own domain (see role_user_ids) already keeps future
        # searches restricted, but an already-picked user must be cleared
        # explicitly since it's not re-validated on its own.
        if self.user_id and self.user_id not in self.role_user_ids:
            self.user_id = False

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("user_id", "user_id.groups_id")
    def _compute_is_user_admin(self):
        Rights = self.env["dashboard.rights"].sudo()
        for rec in self:
            rec.is_user_admin = Rights._is_admin_user(rec.user_id) if rec.user_id else False

    @api.depends("line_ids.has_access", "line_ids.is_group")
    def _compute_access_status(self):
        for rec in self:
            children = rec.line_ids.filtered(lambda l: not l.is_group)
            granted = sum(1 for c in children if c.has_access)
            rec.access_status = "%d / %d" % (granted, len(children))

    # ------------------------------------------------------------------
    # Smart button: read-only drill-down into everything this user has
    # ------------------------------------------------------------------
    def action_view_rights_summary(self):
        self.ensure_one()
        if not self.user_id:
            raise ValidationError(_("Please select a User first."))
        # Scope to this page's own menus ONLY (not Quick Access/
        # Configuration, which also live in dashboard.rights.menu but belong
        # to Users Setup's matrix) — so this matches exactly what the "Menus
        # Granted" badge counted and what this page's own list shows.
        menu_ids = [
            mid for top in self._dr_managed_top_menus()
            for mid in self._dr_menu_subtree_ids(top).ids
        ]
        return {
            "type": "ir.actions.act_window",
            "name": _("Module Rights — %s") % self.user_id.name,
            "res_model": "dashboard.rights.menu",
            "view_mode": "tree,form",
            "views": [
                [self.env.ref("module_rights.view_dashboard_rights_menu_list").id, "tree"],
                [self.env.ref("module_rights.view_dashboard_rights_menu_form").id, "form"],
            ],
            "domain": [("user_id", "=", self.user_id.id), ("menu_id", "in", menu_ids)],
            "search_view_id": [self.env.ref("module_rights.view_dashboard_rights_menu_search").id, "search"],
            "context": {"search_default_filter_granted": 1},
            "target": "current",
        }

    # ------------------------------------------------------------------
    # Save = the single commit point (mirrors dashboard.rights.matrix.write)
    # ------------------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)
        if "line_ids" in vals and not self.env.context.get("skip_line_commit"):
            for rec in self:
                rec._commit_lines_to_rights()
        return res

    def _commit_lines_to_rights(self):
        """Push the current line state to dashboard.rights.menu (on Save)."""
        from collections import defaultdict
        self.ensure_one()
        if not self.line_ids:
            return

        children_by_menu = defaultdict(
            lambda: self.env["access.rights.module.matrix.line"]
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
            all_on = all(c.has_access for c in children)
            if parent.has_access != all_on:
                parent.has_access = all_on
            granted = sum(1 for c in children if c.has_access)
            count = "%d / %d" % (granted, len(children))
            if parent.dashboard_name != count:
                parent.dashboard_name = count

        self.line_ids._propagate_to_dashboard_rights()
        for line in self.line_ids:
            if line.has_access_original != line.has_access:
                line.has_access_original = line.has_access
            if line.has_access_prev != line.has_access:
                line.has_access_prev = line.has_access

    # ------------------------------------------------------------------
    # Onchange: reset lines when user changes
    # ------------------------------------------------------------------
    @api.onchange("user_id")
    def _onchange_user_id(self):
        self.lines_loaded = False

    # ------------------------------------------------------------------
    # Helpers — which menus this page manages (every other app's menus)
    # ------------------------------------------------------------------
    @api.model
    def _dr_managed_top_menus(self):
        """Every top-level (parent-less) menu EXCEPT the excluded ones —
        see _EXCLUDED_TOP_MENU_XMLIDS in dashboard_rights_menu.py, the same
        list ir_ui_menu._dr_restricted_menu_ids reads via
        dashboard.rights.menu._managed_menu_ids, so this page's list and
        enforcement always agree on scope.

        Raw SQL, not ``ir.ui.menu.search()``: that method is overridden to
        filter out whatever the CURRENT env.user (the admin running this
        page) lacks access to — ``.sudo()`` doesn't help, it only flips
        ``su`` while ``env.user`` stays the logged-in admin — which would
        silently drop apps from this list that the admin themselves hasn't
        been granted, even while configuring a different target user.
        """
        excluded_ids = []
        for xmlid in _EXCLUDED_TOP_MENU_XMLIDS:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu:
                excluded_ids.append(menu.id)
        if excluded_ids:
            self.env.cr.execute(
                "SELECT id FROM ir_ui_menu WHERE parent_id IS NULL "
                "AND id NOT IN %s ORDER BY sequence, id",
                (tuple(excluded_ids),),
            )
        else:
            self.env.cr.execute(
                "SELECT id FROM ir_ui_menu WHERE parent_id IS NULL "
                "ORDER BY sequence, id"
            )
        ids = [row[0] for row in self.env.cr.fetchall()]
        return self.env["ir.ui.menu"].sudo().browse(ids)

    @api.model
    def _dr_menu_subtree_ids(self, root_menu):
        """``root_menu`` plus every descendant, any depth.

        Raw recursive SQL, not ``menu.child_id``: reading children through
        the ORM would re-enter our own ``ir.ui.menu.search`` override (see
        ``dashboard.rights.menu._managed_menu_ids``, which has the same
        constraint) and, depending on call context, recurse or return a
        filtered/incomplete tree.
        """
        if not root_menu:
            return self.env["ir.ui.menu"]
        self.env.cr.execute(
            """
            WITH RECURSIVE tree AS (
                SELECT id FROM ir_ui_menu WHERE id = %s
                UNION ALL
                SELECT m.id FROM ir_ui_menu m JOIN tree t ON m.parent_id = t.id
            )
            SELECT id FROM tree
            """,
            (root_menu.id,),
        )
        ids = [row[0] for row in self.env.cr.fetchall()]
        return self.env["ir.ui.menu"].sudo().browse(ids)

    # ------------------------------------------------------------------
    # Button: load every other app's menus for the selected user
    # ------------------------------------------------------------------
    def action_load_modules(self):
        self.ensure_one()
        if not self.user_id:
            raise ValidationError(_("Please select a User first."))

        Line = self.env["access.rights.module.matrix.line"].sudo()
        RightsMenu = self.env["dashboard.rights.menu"].sudo()
        Rights = self.env["dashboard.rights"].sudo()

        Line.search([("matrix_id", "=", self.id)]).unlink()

        is_admin = Rights._is_admin_user(self.user_id)

        vals_list = []
        for seq, top in enumerate(self._dr_managed_top_menus()):
            kids = self._dr_menu_subtree_ids(top)
            if not kids:
                continue
            granted_ids = set(
                RightsMenu.search([
                    ("user_id", "=", self.user_id.id),
                    ("menu_id", "in", kids.ids),
                    ("has_access", "=", True),
                ]).mapped("menu_id").ids
            )
            child_access = [
                (k, True if is_admin else (k.id in granted_ids))
                for k in kids
            ]
            all_on = all(acc for _k, acc in child_access)
            granted = sum(1 for _k, acc in child_access if acc)
            group_label = top.name

            vals_list.append({
                "matrix_id": self.id,
                "is_group": True,
                "menu_name": group_label,
                "menu_sequence": seq,
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
                    # Real immediate parent (a folder like "Configuration",
                    # or nothing for the app's own root row) — lets the
                    # popup nest rows into a tree. Plain field read on an
                    # already-browsed recordset, not a search() call, so
                    # it's safe even though k.parent_id sits outside this
                    # app's subtree for the root row itself (parent_id is
                    # simply empty there).
                    "parent_menu_id": k.parent_id.id if k.parent_id else False,
                    "menu_name": group_label,
                    "dashboard_name": k.name,
                    "menu_sequence": seq,
                    "sub_sequence": k.sequence,
                    "has_access": acc,
                    "has_access_original": acc,
                    "has_access_prev": acc,
                    "is_user_admin": is_admin,
                })

        if vals_list:
            Line.with_context(skip_propagation=True).create(vals_list)

        self.lines_loaded = True
        # Return False so Odoo just reloads the current form in place.
        return False

    def _reload_self(self):
        view_id = self.env.ref(
            "module_rights.view_access_rights_module_matrix_form"
        ).id
        return {
            "type": "ir.actions.act_window",
            "name": _("Module Rights Setup"),
            "res_model": "access.rights.module.matrix",
            "view_mode": "form",
            "view_id": view_id,
            "views": [[view_id, "form"]],
            "res_id": self.id,
            "target": "current",
            "context": dict(self.env.context),
        }


# ---------------------------------------------------------------------------
# Detail-line model — one row per module-owned menu
# ---------------------------------------------------------------------------
class AccessRightsModuleMatrixLine(models.TransientModel):
    _name = "access.rights.module.matrix.line"
    _description = "Module Rights Setup — Menu Row"
    _order = "menu_sequence, menu_name, sub_sequence, dashboard_name"

    matrix_id = fields.Many2one(
        "access.rights.module.matrix",
        string="Matrix",
        ondelete="cascade",
        required=True,
        index=True,
    )
    menu_id = fields.Many2one(
        "ir.ui.menu",
        string="Menu Item",
        readonly=True,
        index=True,
    )
    parent_menu_id = fields.Many2one(
        "ir.ui.menu",
        string="Parent Menu",
        readonly=True,
        help="This row's REAL immediate parent menu (not the app root) —"
             "e.g. 'Configuration' or 'Reporting' — so the group-children "
             "popup (DrGroupChildrenDialog) can nest rows into an actual "
             "tree instead of one flat list. False for the app's own root "
             "row, which sits at the top of that app's tree.",
    )
    is_group = fields.Boolean(
        string="Is Group Row",
        default=False,
        readonly=True,
        help="True for a module header row (the master toggle + count); "
             "False for an individual menu/sub-menu row.",
    )
    menu_name = fields.Char(
        string="Module",
        compute="_compute_menu_name",
        store=True,
        readonly=True,
    )
    menu_sequence = fields.Integer(
        string="Menu Sequence",
        default=9999,
        readonly=True,
    )
    sub_sequence = fields.Integer(
        string="Sub Sequence",
        default=9999,
        readonly=True,
        help="-1 for the group row itself (sorts first), otherwise the "
             "real ir.ui.menu sequence of the item.",
    )
    dashboard_name = fields.Char(
        string="Menu Name",
        readonly=True,
        help="For a menu row: the menu's own name. For a group (module) "
             "row: the live '<granted> / <total>' selection count. Named "
             "to match dashboard.rights.matrix.line so the existing "
             "dr_group_count / DrGroupChildrenDialog JS widgets work "
             "unchanged on this model too.",
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
    )
    is_user_admin = fields.Boolean(
        string="User Is Admin",
        default=False,
        readonly=True,
    )

    @api.depends("menu_id", "menu_id.parent_id")
    def _compute_menu_name(self):
        # Every row on this page belongs to some top-level app; group by
        # that app's own name regardless of the row's immediate parent (a
        # deeply-nested sub-menu's real parent_id is some intermediate
        # sub-menu, not the top-level app menu) — walk up to the root.
        for rec in self:
            if rec.menu_id:
                top = rec.menu_id
                while top.parent_id:
                    top = top.parent_id
                rec.menu_name = top.name
            # Group header rows carry no menu_id; menu_name is set explicitly
            # at creation and left untouched here.

    # ------------------------------------------------------------------
    # Propagate Has Access toggles to dashboard.rights.menu
    # ------------------------------------------------------------------
    # Same autosave-per-row rationale as DashboardRightsMatrixLine.write —
    # see that model's docstring for why this can't rely solely on the
    # parent form's Save.
    def write(self, vals):
        res = super().write(vals)
        if "has_access" in vals and not self.env.context.get("skip_propagation"):
            lines = self.filtered(
                lambda l: not l.is_group and l.matrix_id.user_id and l.menu_id
            )
            if lines:
                lines._propagate_to_dashboard_rights()
        return res

    def _propagate_to_dashboard_rights(self):
        # Routed through the shared sync helper (not a direct RightsMenu
        # write) because My Dashboard's own tree is included on this page
        # now: if `rec.menu_id` happens to be a KS board's leaf menu, this
        # also keeps that board's dashboard.rights row (Users Setup) in
        # lockstep, so the two pages never disagree about its visibility.
        # For an ordinary app menu (no matching board), this is exactly the
        # same single RightsMenu upsert as before.
        RightsMenu = self.env["dashboard.rights.menu"].sudo()
        for rec in self:
            if rec.is_group or not rec.matrix_id.user_id or not rec.menu_id:
                continue
            RightsMenu._dr_sync_board_and_menu(
                rec.matrix_id.user_id, bool(rec.has_access), menu=rec.menu_id
            )

    def action_bulk_set_access(self, value):
        """Set has_access on every record in this recordset in ONE write —
        one RPC, one transaction. Called by the group-children popup's
        on/off cascade and by Grant All / Revoke All (see the JS
        drApplyCascade) instead of one write per row: N parallel per-row
        RPCs each independently read-then-write a KS board's paired
        dashboard.rights row (_dr_sync_board_and_menu), and under
        concurrent load two of those reads can both see "not created yet"
        before either commits, silently dropping one board's sync —
        reproduced empirically while testing a ~20-row cascade. A single
        write() over the whole recordset runs everything sequentially in
        one transaction, so there is nothing left to race.
        """
        self.write({"has_access": bool(value)})
        return True
