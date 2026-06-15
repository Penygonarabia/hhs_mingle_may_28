from odoo import api, models

from ..hooks import ks_rebuild_board_layouts


class KsDashboardBoard(models.Model):
    _inherit = "ks_dashboard_ninja.board"

    @api.model
    def service_dashboard_ct_rebuild_layouts(self):
        """CT counterpart of service_dashboard_rebuild_layouts — rebuilds the
        gridstack config for boards owned by service_dashboards_ct only."""
        ks_rebuild_board_layouts(self.env)
