from odoo import api, models

from ..hooks import contract_dashboard_rebuild_layouts


class KsDashboardBoard(models.Model):
    _inherit = "ks_dashboard_ninja.board"

    @api.model
    def contract_dashboard_rebuild_layouts(self):
        contract_dashboard_rebuild_layouts(self.env)
