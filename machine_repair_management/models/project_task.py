# -*- coding: utf-8 -*-
from odoo import models, api

class ProjectTask(models.Model):
    _inherit = 'project.task'

    def action_print_preventive_job_card(self):
        """Prints the custom bilingual Preventive Job Card PDF report."""
        self.ensure_one()
        return self.env.ref('machine_repair_management.action_report_preventive_job_card').report_action(self)
