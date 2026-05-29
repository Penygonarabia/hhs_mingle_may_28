from odoo import fields, models


class Project(models.Model):
    _inherit = "project.project"

    team_member_ids = fields.One2many("project.team.member", "project_id")

    def action_team_member_assign(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "project_team_assignment.action_team_member_assignment_task"
        )
        action["domain"] = [
            ("project_id", "=", self.id),
            ("display_in_project", "=", True),
        ]
        action["context"] = {
            "default_project_id": self.id,
            "team_member_ids": self.mapped("team_member_ids.user_id").ids,
        }
        return action
