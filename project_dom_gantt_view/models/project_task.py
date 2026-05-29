from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    planned_date_begin = fields.Datetime("Appt Start Date & Time", tracking=True)
    planned_date_end = fields.Datetime("Appt End Date & Time", tracking=True)
    color = fields.Char(string="Color")  # For color picker widget

    _sql_constraints = [
        (
            "planned_date_check",
            "CHECK ((planned_date_begin <= planned_date_end))",
            "The start date must be prior to the end date.",
        ),
    ]
