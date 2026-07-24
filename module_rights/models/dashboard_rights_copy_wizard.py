# -*- coding: utf-8 -*-
"""Copy one user's rights (dashboards AND module menus) to other users.

Covers both persistent grant tables in one shot — dashboard.rights (KS
boards) and dashboard.rights.menu (Quick Access/Configuration sub-items
AND every Controlled Module menu) — since "copy this user's rights" means
everything they can currently see, not just one of the two pages that let
you edit it.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class DashboardRightsCopyWizard(models.TransientModel):
    _name = "dashboard.rights.copy.wizard"
    _description = "Copy Rights To Other Users"

    source_user_id = fields.Many2one(
        "res.users",
        string="Copy Rights From",
        required=True,
        domain=[("share", "=", False), ("active", "=", True)],
    )
    source_role = fields.Char(
        string="Source User Role",
        compute="_compute_source_role",
        readonly=True,
    )
    copy_scope = fields.Selection(
        [
            ("users", "Specific User(s)"),
            ("role", "Everyone With the Same Role"),
            ("all", "All Users"),
        ],
        string="Copy To",
        default="users",
        required=True,
    )
    target_user_ids = fields.Many2many(
        "res.users",
        string="Target User(s)",
        domain=[("share", "=", False), ("active", "=", True)],
        help="Used only when 'Copy To' is 'Specific User(s)'.",
    )

    @api.depends("source_user_id", "source_user_id.groups_id")
    def _compute_source_role(self):
        Rights = self.env["dashboard.rights"].sudo()
        for rec in self:
            rec.source_role = Rights._dr_role_for_user(rec.source_user_id) if rec.source_user_id else False

    def _target_users(self):
        self.ensure_one()
        Users = self.env["res.users"].sudo()
        base_domain = [("share", "=", False), ("active", "=", True),
                        ("id", "!=", self.source_user_id.id)]
        if self.copy_scope == "all":
            return Users.search(base_domain)
        if self.copy_scope == "role":
            Rights = self.env["dashboard.rights"].sudo()
            role = Rights._dr_role_for_user(self.source_user_id)
            candidates = Users.search(base_domain)
            return candidates.filtered(
                lambda u: Rights._dr_role_for_user(u) == role
            )
        return (self.target_user_ids - self.source_user_id)

    def action_copy_rights(self):
        self.ensure_one()
        if not self.source_user_id:
            raise ValidationError(_("Please select a user to copy rights from."))
        targets = self._target_users()
        if not targets:
            raise UserError(_("No target users found for the selected scope."))

        Rights = self.env["dashboard.rights"].sudo()
        RightsMenu = self.env["dashboard.rights.menu"].sudo()

        source_board_access = {
            r.dashboard_id.id: r.has_access
            for r in Rights.search([("user_id", "=", self.source_user_id.id)])
        }
        source_menu_access = {
            r.menu_id.id: r.has_access
            for r in RightsMenu.search([("user_id", "=", self.source_user_id.id)])
        }

        target_ids = targets.ids
        existing_board_rows = {
            (r.user_id.id, r.dashboard_id.id): r
            for r in Rights.search([("user_id", "in", target_ids)])
        }
        existing_menu_rows = {
            (r.user_id.id, r.menu_id.id): r
            for r in RightsMenu.search([("user_id", "in", target_ids)])
        }

        board_to_create = []
        menu_to_create = []
        for target_id in target_ids:
            for board_id, val in source_board_access.items():
                row = existing_board_rows.get((target_id, board_id))
                if row:
                    if row.has_access != val:
                        row.has_access = val
                else:
                    board_to_create.append({
                        "user_id": target_id, "dashboard_id": board_id, "has_access": val,
                    })
            for menu_id, val in source_menu_access.items():
                row = existing_menu_rows.get((target_id, menu_id))
                if row:
                    if row.has_access != val:
                        row.has_access = val
                else:
                    menu_to_create.append({
                        "user_id": target_id, "menu_id": menu_id, "has_access": val,
                    })
        if board_to_create:
            Rights.create(board_to_create)
        if menu_to_create:
            RightsMenu.create(menu_to_create)

        message = _(
            "Copied dashboard and module rights from %(source)s to %(count)s user(s)."
        ) % {"source": self.source_user_id.name, "count": len(targets)}
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Copy Rights"),
                "message": message,
                "sticky": False,
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
