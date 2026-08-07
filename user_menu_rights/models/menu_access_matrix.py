# -*- coding: utf-8 -*-
"""Single-page master/detail screen for per-user menu access.

    ┌── Users ─────────┬── Menus for the selected user ──────────────┐
    │ [search user…]   │ [search menu…] [Expand][Collapse] … [Save]  │
    │ ● Daniel Koh     │  Service Operations           4 / 6   [x]   │
    │   daniel@x.com   │      Work Orders                      [x]   │
    │ ● Priya Nair     │      Technician Dispatch              [x]   │
    │   priya@x.com    │          Dispatch Board               [x]   │
    │ …                │  Payroll                      0 / 5   [ ]   │
    └──────────────────┴─────────────────────────────────────────────┘

Clicking a user in the left panel loads that user's menu tree on the right;
there is no separate list page and no "Load Menus" step.

Toggling ANY menu row cascades down to its whole sub-tree and rolls up into
its ancestors, so the same control handles "one menu", "one sub-menu
branch", or "one whole app".
"""

import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Header model — the page itself
# ---------------------------------------------------------------------------
class MenuAccessMatrix(models.TransientModel):
    _name = "menu.access.matrix"
    _description = "Menu Access Rights — Page"

    # This is what the breadcrumb shows. depends on user_id so picking
    # someone on the left re-renders the title with their name appended.
    @api.depends("user_id", "user_id.name", "user_id.login")
    def _compute_display_name(self):
        title = _("Menu Access Rights")
        for rec in self:
            if rec.user_id:
                email = rec.user_id.login or ""
                rec.display_name = "%s - %s / %s" % (title, rec.user_id.name, email) if email else "%s - %s" % (title, rec.user_id.name)
            else:
                rec.display_name = title

    user_id = fields.Many2one(
        "res.users",
        string="User",
        domain=[("share", "=", False), ("active", "=", True)],
        help="The user whose menu access is shown on the right.",
    )
    user_email = fields.Char(related="user_id.login", readonly=True)
    is_user_admin = fields.Boolean(compute="_compute_is_user_admin")
    line_ids = fields.One2many(
        "menu.access.matrix.line",
        "matrix_id",
        string="Menus",
    )
    user_list_ids = fields.One2many(
        "menu.access.matrix.user",
        "matrix_id",
        string="Users",
    )
    lines_loaded = fields.Boolean(default=False)
    has_pending_bulk = fields.Boolean(
        default=False,
        help="True while a Grant All / Revoke All is staged but not yet "
             "committed to menu.access.rights.",
    )
    access_status = fields.Char(
        string="Menus Granted",
        compute="_compute_access_status",
        help="Live '<granted> / <total>' count across every loaded menu.",
    )
    # NB: both search boxes are deliberately NOT fields. They're plain DOM
    # inputs in the form arch, read client-side by the JS in static/src/js.
    # Backing them with real Char fields made every keystroke dirty the form
    # and re-render it, which reset the tree's expand/collapse state.

    @api.depends("user_id")
    def _compute_is_user_admin(self):
        Rights = self.env["menu.access.rights"].sudo()
        for rec in self:
            rec.is_user_admin = Rights._is_admin_user(rec.user_id) if rec.user_id else False

    @api.depends("line_ids.has_access")
    def _compute_access_status(self):
        for rec in self:
            granted = sum(1 for l in rec.line_ids if l.has_access)
            rec.access_status = "%d / %d" % (granted, len(rec.line_ids))

    # ------------------------------------------------------------------
    # Entry point (wired to the Settings menu via an ir.actions.server)
    # ------------------------------------------------------------------
    @api.model
    def action_open_page(self):
        record = self.create({})
        record._load_user_list()
        return record._reload_self()

    def _load_user_list(self):
        self.ensure_one()
        UserLine = self.env["menu.access.matrix.user"].sudo()
        UserLine.search([("matrix_id", "=", self.id)]).unlink()
        users = self.env["res.users"].sudo().search(
            [("share", "=", False), ("active", "=", True)], order="name, id",
        )
        if users:
            UserLine.create([
                {"matrix_id": self.id, "user_id": u.id} for u in users
            ])

    def action_select_user(self, user_id):
        """Switch the right-hand panel to ``user_id`` and load their menus.

        Called from the left panel (see static/src/js/menu_access_users_list.js).
        """
        self.ensure_one()
        if not user_id:
            return False
        self.line_ids.unlink()
        # Switching user drops any staged bulk change with it: the rows it
        # applied to are gone, so there is nothing left to commit.
        self.write({
            "user_id": int(user_id),
            "lines_loaded": False,
            "has_pending_bulk": False,
        })
        return self.action_load_menus()

    # ------------------------------------------------------------------
    # Build the menu tree for the selected user
    # ------------------------------------------------------------------
    def action_load_menus(self):
        self.ensure_one()
        if not self.user_id:
            raise ValidationError(_("Please select a user first."))

        Line = self.env["menu.access.matrix.line"].sudo()
        Rights = self.env["menu.access.rights"].sudo()
        Line.search([("matrix_id", "=", self.id)]).unlink()

        managed_ids = Rights.managed_menu_ids()
        if not managed_ids:
            self.lines_loaded = True
            return False

        is_admin = Rights._is_admin_user(self.user_id)
        menus = self.env["ir.ui.menu"].sudo().browse(managed_ids)

        children_of = {}
        for m in menus:
            pid = m.parent_id.id if m.parent_id and m.parent_id.id in managed_ids else False
            children_of.setdefault(pid, []).append(m)
        for kids in children_of.values():
            kids.sort(key=lambda m: (m.sequence, m.id))

        granted_ids = set(
            Rights.search([
                ("user_id", "=", self.user_id.id),
                ("menu_id", "in", list(managed_ids)),
                ("has_access", "=", True),
            ]).mapped("menu_id").ids
        )

        # Build parent mapping to resolve ancestors
        parent_map = {}
        for m in menus:
            if m.parent_id and m.parent_id.id in managed_ids:
                parent_map[m.id] = m.parent_id.id

        # Expand to include all parent menu ancestors of any granted menu
        all_granted_ids = set(granted_ids)
        for g_id in granted_ids:
            cur = g_id
            while cur in parent_map:
                cur = parent_map[cur]
                all_granted_ids.add(cur)

        vals_list = []

        def walk(menu, parent_path, depth):
            path = "%s%d/" % (parent_path, menu.id)
            has_access = True if is_admin else (menu.id in all_granted_ids)
            kids = children_of.get(menu.id, [])
            vals_list.append({
                "matrix_id": self.id,
                "menu_id": menu.id,
                "menu_path": path,
                "depth": depth,
                "sequence": len(vals_list),
                "is_group": bool(kids),
                "has_access": has_access,
                "is_user_admin": is_admin,
                "owner_user_id": self.user_id.id,
            })
            for kid in kids:
                walk(kid, path, depth + 1)

        for top in children_of.get(False, []):
            walk(top, "/", 0)

        if vals_list:
            Line.create(vals_list)

        self.lines_loaded = True
        # Return False so Odoo just reloads the current form in place.
        return False

    # ------------------------------------------------------------------
    # Grant / Revoke all
    # ------------------------------------------------------------------
    # These two are STAGED: they set every row on screen but write nothing to
    # menu.access.rights until Save Changes. A mis-aimed "Revoke All" on the
    # wrong user is a 800-row mistake, so it gets a way back that does not
    # depend on remembering the previous state.
    #
    # A single row toggle is staged too, but through Odoo's own dirty state —
    # the switch calls record.update() and the breadcrumb Save / Discard take
    # it from there (see MarAccessToggleField). These two buttons cannot use
    # that: a type="object" button force-saves the form before the method even
    # runs, so there is no unsaved client state left for those controls to act
    # on. Their staging therefore lives in the transient lines (which the
    # button IS allowed to write) plus the has_pending_bulk flag, with an
    # explicit Save/Discard pair of our own.
    #
    # skip_cascade: every row is being set to the SAME value, so the per-row
    # cascade has nothing to work out — and without this it would run once
    # per row (764x a 764-row search), which is what made these two buttons
    # crawl. skip_propagate: see MenuAccessMatrixLine.write.
    def action_grant_all(self):
        return self._stage_all(True)

    def action_revoke_all(self):
        return self._stage_all(False)

    def _stage_all(self, value):
        self.ensure_one()
        self.line_ids.with_context(
            skip_cascade=True, skip_propagate=True,
        ).write({"has_access": value})
        self.has_pending_bulk = True
        # False, not _reload_self(): returning an act_window for the record we
        # are already on pushes a SECOND breadcrumb, so the page title rendered
        # twice and stacked another entry per click. False reloads in place.
        return False

    def action_save_pending(self):
        """Commit the staged rows to menu.access.rights."""
        self.ensure_one()
        if self.line_ids:
            self.line_ids._propagate_to_rights()
        self.has_pending_bulk = False
        return False

    def action_discard_pending(self):
        """Throw the staged rows away and rebuild them from what is stored.

        Rebuilding from menu.access.rights rather than remembering a previous
        state means an individual toggle made after the bulk action — which
        persisted immediately, as those still do — correctly survives the
        discard.
        """
        self.ensure_one()
        self.has_pending_bulk = False
        self.action_load_menus()
        return False

    def _reload_self(self):
        view_id = self.env.ref("user_menu_rights.view_menu_access_matrix_form").id
        return {
            "type": "ir.actions.act_window",
            "name": _("Menu Access Rights"),
            "res_model": "menu.access.matrix",
            "view_mode": "form",
            "view_id": view_id,
            "views": [[view_id, "form"]],
            "res_id": self.id,
            "target": "current",
            "context": dict(self.env.context),
        }


# ---------------------------------------------------------------------------
# Left panel — one row per user
# ---------------------------------------------------------------------------
class MenuAccessMatrixUser(models.TransientModel):
    _name = "menu.access.matrix.user"
    _description = "Menu Access Rights — User Row"
    _order = "user_name, id"

    matrix_id = fields.Many2one(
        "menu.access.matrix", ondelete="cascade", required=True, index=True,
    )
    user_id = fields.Many2one(
        "res.users", required=True, readonly=True, index=True,
    )
    user_name = fields.Char(related="user_id.name", store=True, readonly=True)
    user_email = fields.Char(related="user_id.login", store=True, readonly=True)
    is_selected = fields.Boolean(compute="_compute_is_selected")

    @api.depends("matrix_id.user_id", "user_id")
    def _compute_is_selected(self):
        for rec in self:
            rec.is_selected = bool(
                rec.matrix_id.user_id and rec.matrix_id.user_id.id == rec.user_id.id
            )


# ---------------------------------------------------------------------------
# Detail-line model — one row per managed menu
# ---------------------------------------------------------------------------
class MenuAccessMatrixLine(models.TransientModel):
    _name = "menu.access.matrix.line"
    _description = "Menu Access Rights — Menu Row"
    _order = "sequence"

    matrix_id = fields.Many2one(
        "menu.access.matrix",
        string="Matrix",
        ondelete="cascade",
        required=True,
        index=True,
    )
    menu_id = fields.Many2one(
        "ir.ui.menu",
        string="Menu Record",
        required=True,
        readonly=True,
        index=True,
    )
    menu_path = fields.Char(
        readonly=True,
        help="Materialized path of menu ids, e.g. '/12/45/302/'. Lets the "
             "cascade find a row's ancestors/descendants by string prefix, "
             "with no relational lookups.",
    )
    depth = fields.Integer(readonly=True, help="0 for a top-level app.")
    sequence = fields.Integer(readonly=True)
    is_group = fields.Boolean(
        readonly=True,
        help="True when this menu has at least one managed child — i.e. "
             "toggling it cascades to a sub-tree, not just itself.",
    )
    display_label = fields.Char(
        string="Menu",
        compute="_compute_display_label",
    )
    count_label = fields.Char(
        string="Status",
        compute="_compute_count_label",
        help="For a row with children: live '<granted> / <total>' count of "
             "its leaf descendants. Blank for a leaf row.",
    )
    has_access = fields.Boolean(string="Has Access", default=False)
    is_user_admin = fields.Boolean(readonly=True)
    owner_user_id = fields.Many2one(
        "res.users",
        readonly=True,
        index=True,
        help="The user this row was built for. Grants are written against "
             "THIS user, never against whoever the page happens to be "
             "showing now — see _propagate_to_rights for why.",
    )

    @api.depends("menu_id", "depth")
    def _compute_display_label(self):
        for rec in self:
            indent = "    " * (rec.depth or 0)
            rec.display_label = "%s%s" % (indent, rec.menu_id.sudo().name or "") if rec.menu_id else ""

    @api.depends("matrix_id.line_ids.has_access")
    def _compute_count_label(self):
        # One pass over the tree, not one scan per row.
        #
        # This used to filter the whole line_ids set for every record. At
        # ~760 rows that is ~580k comparisons, and because it runs inside the
        # form's onchange it fired on EVERY tick/untick — measured at 2.6s
        # per toggle, which was the bulk of the reported slowness. Instead,
        # walk each leaf once and credit its ancestors, giving O(rows x depth).
        from collections import defaultdict

        by_matrix = defaultdict(lambda: self.browse())
        for rec in self:
            by_matrix[rec.matrix_id.id] |= rec

        for recs in by_matrix.values():
            total = defaultdict(int)
            granted = defaultdict(int)
            for line in recs[0].matrix_id.line_ids:
                if line.is_group or not line.menu_path:
                    continue
                segments = [s for s in line.menu_path.strip("/").split("/") if s]
                for i in range(1, len(segments)):
                    ancestor = "/%s/" % "/".join(segments[:i])
                    total[ancestor] += 1
                    if line.has_access:
                        granted[ancestor] += 1
            for rec in recs:
                if not rec.is_group or not rec.menu_path:
                    rec.count_label = ""
                    continue
                count = total.get(rec.menu_path, 0)
                rec.count_label = "%d / %d" % (granted.get(rec.menu_path, 0), count) if count else ""

    # ------------------------------------------------------------------
    # Cascade + persist on every real write to has_access.
    #
    # An earlier version tried this live via @api.onchange, mutating sibling
    # records. That doesn't hold up at this list's size (760+ rows): sibling
    # mutations made inside an onchange on ONE row aren't reliably reflected
    # back to the client for OTHER rows. Doing it here as real ORM writes,
    # found by menu_path prefix, is always correct because it needs no
    # client-side cooperation. skip_cascade guards the recursive writes this
    # method itself issues.
    #
    # PERFORMANCE: everything below is deliberately batched. The first cut
    # did one search + one write PER RECORD, and since menu.access.rights
    # clears the whole registry cache on every write, a single group toggle
    # (which can cascade to 100+ rows) meant 100+ searches, 100+ writes and
    # 100+ full cache clears — the reported "tick/untick is slow". It is now
    # one search and at most a couple of writes for the entire cascade.
    # ------------------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)
        if "has_access" in vals:
            # skip_propagate: the caller is Grant All / Revoke All, which
            # stages into these transient rows and waits for its own Save
            # Changes. A single row toggle reaches here only once Odoo saves
            # the form, i.e. the user has already pressed Save, so it does
            # not pass the flag and lands in menu.access.rights right away.
            if not self.env.context.get("skip_propagate"):
                self._propagate_to_rights()
            if not self.env.context.get("skip_cascade"):
                self._cascade_has_access()
        return res

    def _cascade_has_access(self):
        Line = self.env["menu.access.matrix.line"]
        for rec in self:
            if not rec.matrix_id or not rec.menu_path:
                continue
            value = rec.has_access
            path = rec.menu_path
            siblings = Line.search([("matrix_id", "=", rec.matrix_id.id)])
            by_path = {l.menu_path: l for l in siblings if l.menu_path}

            # Down: every descendant takes the toggled value. One write for
            # the whole sub-tree rather than one per row.
            descendants = siblings.filtered(
                lambda l: l.id != rec.id
                and l.menu_path
                and l.menu_path != path
                and l.menu_path.startswith(path)
                and l.has_access != value
            )
            if descendants:
                descendants.with_context(skip_cascade=True).write({"has_access": value})

            # Up: an ancestor is ticked while ANY of its direct children is —
            # a parent menu has to be reachable for a granted child under it
            # to be reachable at all, so "all" would make granting a single
            # sub-menu impossible. This matches how action_load_menus seeds
            # groups (all_granted_ids walks a grant up to its ancestors).
            # Collected first, then written as at most two batches.
            turn_on = Line.browse()
            turn_off = Line.browse()
            # Roll-up values decided so far, keyed by menu_path. The loop runs
            # nearest-ancestor-first, so each step needs the value the step
            # below it just decided — that ancestor has not been written yet.
            #
            # This used to be done with `ancestor.has_access = new_val`, on
            # the comment "keep the in-memory value in sync". It is not in
            # memory: assigning to a field on an ORM record IS a write(), so
            # it re-entered this very method for the ancestor WITHOUT
            # skip_cascade — and the first thing that does is push the
            # ancestor's value DOWN over its whole sub-tree. Ticking one
            # sub-menu therefore granted every menu in the app (verified:
            # Sales Dashboards turned on all 33 rows under PBI Dashboards).
            # A plain dict cannot write anything.
            rolled_up = {}

            def effective(line):
                if line.menu_path in rolled_up:
                    return rolled_up[line.menu_path]
                return line.has_access

            segment_ids = [s for s in path.strip("/").split("/") if s]
            for i in range(len(segment_ids) - 1, 0, -1):
                ancestor_path = "/" + "/".join(segment_ids[:i]) + "/"
                ancestor = by_path.get(ancestor_path)
                if not ancestor:
                    continue
                depth = ancestor_path.count("/") + 1
                direct_children = siblings.filtered(
                    lambda l: l.menu_path
                    and l.menu_path != ancestor_path
                    and l.menu_path.startswith(ancestor_path)
                    and l.menu_path.count("/") == depth
                )
                if not direct_children:
                    continue
                new_val = any(effective(c) for c in direct_children)
                rolled_up[ancestor_path] = new_val
                if ancestor.has_access == new_val:
                    continue
                if new_val:
                    turn_on |= ancestor
                else:
                    turn_off |= ancestor
            if turn_on:
                turn_on.with_context(skip_cascade=True).write({"has_access": True})
            if turn_off:
                turn_off.with_context(skip_cascade=True).write({"has_access": False})

    def _propagate_to_rights(self):
        """Push this recordset's state into menu.access.rights, in bulk.

        SAFETY: grants are keyed off the row's own ``owner_user_id`` — the
        user the row was built for — not off ``matrix_id.user_id``, which is
        just "whoever the page is showing right now". Those two can diverge:
        the page swaps its rows out when you pick a different user on the
        left, and a save that was already in flight (or a browser tab still
        holding the previous user's rows) would otherwise land one user's
        values on another user's account. That is not hypothetical — it
        corrupted two users' access during development, once silently
        revoking all 526 of a user's menus. A row whose owner no longer
        matches the page is therefore treated as stale and skipped outright
        rather than written anywhere.
        """
        Rights = self.env["menu.access.rights"].sudo()
        wanted_by_user = {}
        stale = 0
        for rec in self:
            if not rec.menu_id:
                continue
            owner = rec.owner_user_id or rec.matrix_id.user_id
            if not owner:
                continue
            current = rec.matrix_id.user_id
            if rec.owner_user_id and current and rec.owner_user_id.id != current.id:
                stale += 1
                continue
            wanted_by_user.setdefault(owner.id, {})[rec.menu_id.id] = bool(rec.has_access)
        if stale:
            _logger.warning(
                "user_menu_rights: ignored %s stale matrix row(s) whose "
                "owner_user_id no longer matches the page's selected user; "
                "refusing to write one user's menu grants onto another.",
                stale,
            )
        if not wanted_by_user:
            return

        for user_id, wanted in wanted_by_user.items():
            existing = Rights.search([
                ("user_id", "=", user_id), ("menu_id", "in", list(wanted)),
            ])
            existing_by_menu = {r.menu_id.id: r for r in existing}
            turn_on = Rights.browse()
            turn_off = Rights.browse()
            to_create = []
            for menu_id, val in wanted.items():
                row = existing_by_menu.get(menu_id)
                if row is None:
                    to_create.append({
                        "user_id": user_id, "menu_id": menu_id, "has_access": val,
                    })
                elif row.has_access != val:
                    if val:
                        turn_on |= row
                    else:
                        turn_off |= row
            if turn_on:
                turn_on.write({"has_access": True})
            if turn_off:
                turn_off.write({"has_access": False})
            if to_create:
                Rights.create(to_create)
