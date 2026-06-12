from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Drop the duplicate 'Employee Performance Analysis - Estimated vs Actual
    Hours' chart from the Service Analysis - New board (legacy_board_main).

    The same chart still lives on the Technician Analysis board
    (legacy_item_697) — only the copy on the main service board is removed.
    legacy_service_boards.xml loads with noupdate=1 so deleting the XML node
    alone wouldn't touch an installed DB; this migration unlinks the existing
    record (and its ir.model.data row, via ondelete cascade)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    xmlid = env['ir.model.data'].search([
        ('module', '=', 'service_dashboards_ot'),
        ('model', '=', 'ks_dashboard_ninja.item'),
        ('name', '=', 'legacy_item_estimated_vs_actual'),
    ], limit=1)
    if not xmlid:
        return
    item = env['ks_dashboard_ninja.item'].browse(xmlid.res_id).exists()
    if item:
        item.unlink()
