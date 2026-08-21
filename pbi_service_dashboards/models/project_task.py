# -*- coding: utf-8 -*-
from odoo import api, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        """Let a dashboard drill-through list exactly the records its chart counted.

        machine_repair_management overrides search_fetch on project.task and,
        for a user in both group_job_card_back_office_user and
        group_technical_allocation_user who has a default_work_center_id,
        silently appends ("work_center_id", "in", <the user's work centres>) and
        ("amc_project_id", "in", <the user's projects>) to EVERY list read.
        web_search_read goes through search_fetch while search_count does not,
        so a drilled list could come back empty while the bar that opened it
        counted hundreds — most starkly on the "no work centre" bucket, where
        work_center_id IS NULL satisfies neither clause and the list lost every
        row it was supposed to show.

        The dashboard has already done its own scoping by the time this runs:
        the drill-through domain is an explicit id whitelist built under the
        board scope, the item domain, the technician/promoter row guards and
        the selected period. There is nothing left for the vendor's filters to
        restrict here.

        Bypassing means calling BaseModel's implementation directly — super()
        would run machine_repair_management's override, and there is no way to
        ask that override for "everything except the clauses you inject".
        Record rules are NOT bypassed: BaseModel.search_fetch still goes
        through _search, which applies them. Only reads carrying our own
        context flag take this path; every other project.task list, this
        module's included, behaves exactly as before.
        """
        if not self.env.context.get("pbi_dashboard_drilldown"):
            return super().search_fetch(domain, field_names, offset, limit, order)
        return models.BaseModel.search_fetch(self, domain, field_names, offset, limit, order)
