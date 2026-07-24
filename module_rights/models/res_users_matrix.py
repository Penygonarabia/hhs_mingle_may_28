# -*- coding: utf-8 -*-
"""Extend res.users with a stored role label used for group-by in the
Dashboard Rights Users tab.
"""

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    dashboard_user_role = fields.Char(
        string="User Role",
        compute="_compute_dashboard_user_role",
        store=True,
    )

    @api.depends("groups_id")
    def _compute_dashboard_user_role(self):
        Rights = self.env["dashboard.rights"].sudo()
        for user in self:
            user.dashboard_user_role = Rights._dr_role_for_user(user) or ""
