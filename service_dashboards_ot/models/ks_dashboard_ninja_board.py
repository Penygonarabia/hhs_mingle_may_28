from odoo import api, models

from ..hooks import ks_rebuild_board_layouts


class KsDashboardBoard(models.Model):
    _inherit = "ks_dashboard_ninja.board"

    @api.model
    def service_dashboard_rebuild_layouts(self):
        """Rebuild ks_gridstack_config from items' grid_corners for every
        service_dashboard board.

        Called from data/service_dashboard_layout.xml via <function/> so that
        every `-u service_dashboard` (which re-applies the noupdate=0 layout
        file and thus refreshes grid_corners on existing records) also
        refreshes the per-board gridstack_config that actually drives the
        render order. Without this step the layout file would change
        grid_corners but the UI would still display the stale arrangement.
        """
        ks_rebuild_board_layouts(self.env)
