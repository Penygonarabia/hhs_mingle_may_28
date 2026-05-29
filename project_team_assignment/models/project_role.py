from odoo import fields, models


class ProjectRole(models.Model):
    _name = "project.role"
    _description = "Project Role"

    code = fields.Char(required=True)
    name = fields.Char(required=True)
