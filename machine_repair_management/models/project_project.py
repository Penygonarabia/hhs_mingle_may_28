from odoo import api, fields, models, _


class ProjectProject(models.Model):
    _inherit = "project.project"

    related_to_amc = fields.Boolean(string='Related to AMC (Y/N)')
