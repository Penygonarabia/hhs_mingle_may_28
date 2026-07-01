from odoo import api, models

from ..hooks import loyalty_dashboard_rebuild_layouts


class KsDashboardBoard(models.Model):
    _inherit = "ks_dashboard_ninja.board"

    @api.model
    def loyalty_dashboard_rebuild_layouts(self):
        loyalty_dashboard_rebuild_layouts(self.env)
