# -*- coding: utf-8 -*-
"""Copy Rights From… — clone one user's whole menu grant set onto others.

Opened from the matrix page. Copies every menu.access.rights row the
source user has (both granted and revoked) onto each target user, so a
target ends up with EXACTLY the source's access, not a merge.
"""

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MenuAccessCopyWizard(models.TransientModel):
    _name = "menu.access.copy.wizard"
    _description = "Copy Menu Rights"

    source_user_id = fields.Many2one(
        "res.users",
        string="Copy From",
        required=True,
        domain=[("share", "=", False), ("active", "=", True)],
    )
    target_user_ids = fields.Many2many(
        "res.users",
        string="Copy To",
        domain=[("share", "=", False), ("active", "=", True)],
        required=True,
    )

    def action_copy(self):
        self.ensure_one()
        if self.source_user_id in self.target_user_ids:
            raise ValidationError("The source user can't also be a target.")

        Rights = self.env["menu.access.rights"].sudo()
        source_by_menu = {
            r.menu_id.id: r.has_access
            for r in Rights.search([("user_id", "=", self.source_user_id.id)])
        }

        for target in self.target_user_ids:
            existing_by_menu = {
                r.menu_id.id: r
                for r in Rights.search([("user_id", "=", target.id)])
            }
            to_create = []
            for menu_id, val in source_by_menu.items():
                existing = existing_by_menu.get(menu_id)
                if existing:
                    if existing.has_access != val:
                        existing.has_access = val
                else:
                    to_create.append({
                        "user_id": target.id,
                        "menu_id": menu_id,
                        "has_access": val,
                    })
            if to_create:
                Rights.create(to_create)

        return {"type": "ir.actions.act_window_close"}
