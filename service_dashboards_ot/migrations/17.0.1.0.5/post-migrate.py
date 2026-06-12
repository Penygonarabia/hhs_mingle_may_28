from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    new_menu = env.ref(
        'service_dashboards_ot.menu_root',
        raise_if_not_found=False,
    )
    if not new_menu:
        return
    old_menu = env.ref(
        'service_dashboards_ct.menu_root',
        raise_if_not_found=False,
    )
    if not old_menu:
        return
    boards = env['ks_dashboard_ninja.board'].search([
        ('ks_dashboard_top_menu_id', '=', old_menu.id),
    ])
    boards.write({'ks_dashboard_top_menu_id': new_menu.id})
