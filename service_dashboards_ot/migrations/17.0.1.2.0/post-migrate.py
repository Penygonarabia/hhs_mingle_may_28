"""Flip the chart palette for OT-owned chart items from custom-1 to moonrise.

The 17.0.1.2.0 release moves the custom-1 palette boards to the sibling module
service_dashboards_ct; OT now standardises on the built-in `moonrise` palette.
The data XML records are noupdate=1, so existing items wouldn't get the new
value from a plain `-u` — this script catches them up.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    own_item_xmlids = env['ir.model.data'].search([
        ('module', '=', 'service_dashboards_ot'),
        ('model', '=', 'ks_dashboard_ninja.item'),
    ])
    own_item_ids = own_item_xmlids.mapped('res_id')
    if not own_item_ids:
        return

    chart_types = [
        'ks_bar_chart',
        'ks_horizontalBar_chart',
        'ks_pie_chart',
        'ks_doughnut_chart',
    ]
    items = env['ks_dashboard_ninja.item'].search([
        ('id', 'in', own_item_ids),
        ('ks_dashboard_item_type', 'in', chart_types),
        ('ks_chart_item_color', '!=', 'moonrise'),
    ])
    if items:
        items.write({'ks_chart_item_color': 'moonrise'})
