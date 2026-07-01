from odoo import api, models

from ..hooks import ks_rebuild_board_layouts


class KsDashboardBoard(models.Model):
    _inherit = "ks_dashboard_ninja.board"

    @api.model
    def service_dashboard_ct_unfreeze_layout_items(self):
        """Clear ``ir_model_data.noupdate`` for CT-owned dashboard items so the
        ``grid_corners`` records in service_dashboard_layout.xml (noupdate="0")
        actually re-apply on every ``-u``.

        The items are first defined in legacy_service_boards.xml, which is
        ``noupdate="1"`` and loads *before* the layout file. That creates the
        xmlids with ``noupdate=True``; Odoo's ``_load_records`` then only adds a
        record to ``to_update`` when its *stored* noupdate is False
        (``if not (update and d_noupdate)``), so on upgrade the layout file's
        position updates are silently skipped and the board reverts to whatever
        the last full *install* wrote.

        This runs from the TOP of the layout file, before its ``<record>``
        nodes, so the positions below it apply. It is paired with the re-freeze
        in :meth:`service_dashboard_ct_rebuild_layouts`, which restores
        ``noupdate=True`` afterwards so any manual edits to the items' other
        fields stay preserved across future upgrades.
        """
        self.env.cr.execute(
            "UPDATE ir_model_data SET noupdate = FALSE "
            "WHERE module = 'service_dashboards_ct' "
            "AND model = 'ks_dashboard_ninja.item'"
        )
        # Drop ORM cache so the subsequent record loads see noupdate=False.
        self.env['ir.model.data'].invalidate_model(['noupdate'])

    @api.model
    def service_dashboard_ct_rebuild_layouts(self):
        """CT counterpart of service_dashboard_rebuild_layouts — rebuilds the
        gridstack config for boards owned by service_dashboards_ct only, then
        re-freezes the items (see
        :meth:`service_dashboard_ct_unfreeze_layout_items`)."""
        ks_rebuild_board_layouts(self.env)
        # Re-freeze the items so the next upgrade preserves any manual edits to
        # their other fields (legacy_service_boards.xml is noupdate="1"); the
        # layout file unfreezes them again at the top of its load to re-apply
        # grid_corners.
        self.env.cr.execute(
            "UPDATE ir_model_data SET noupdate = TRUE "
            "WHERE module = 'service_dashboards_ct' "
            "AND model = 'ks_dashboard_ninja.item'"
        )
        self.env['ir.model.data'].invalidate_model(['noupdate'])
