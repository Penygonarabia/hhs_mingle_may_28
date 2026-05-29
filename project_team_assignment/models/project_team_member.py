from odoo import fields, models


class ProjectTeamMember(models.Model):
    _name = "project.team.member"
    _description = "Project Team Member"
    _order = "role_id"

    role_id = fields.Many2one("project.role", required=True)
    user_id = fields.Many2one("res.users", "Resource", required=True)
    project_id = fields.Many2one("project.project", required=True)
    note = fields.Text()
