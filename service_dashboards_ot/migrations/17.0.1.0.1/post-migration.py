from odoo import api, SUPERUSER_ID


CHART_TYPES = (
    'ks_bar_chart',
    'ks_horizontalBar_chart',
    'ks_line_chart',
    'ks_area_chart',
    'ks_pie_chart',
    'ks_doughnut_chart',
)


def migrate(cr, version):
    """Enable value labels on every chart of the legacy service boards.

    The boards are loaded with noupdate=1, so re-installing the module does
    not push ks_show_data_value onto records that already exist in the DB.
    Find them via their ir.model.data xmlids (legacy_item_*) and set the
    flag directly."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    xmlids = env['ir.model.data'].search([
        ('module', '=', 'service_dashboards_ot'),
        ('model', '=', 'ks_dashboard_ninja.item'),
        ('name', '=like', 'legacy_item_%'),
    ])
    if not xmlids:
        return
    items = env['ks_dashboard_ninja.item'].browse(xmlids.mapped('res_id')).exists()
    charts = items.filtered(lambda i: i.ks_dashboard_item_type in CHART_TYPES)
    if charts:
        charts.write({'ks_show_data_value': True})
