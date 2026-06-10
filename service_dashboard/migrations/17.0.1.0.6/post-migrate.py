from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    sd_menu = env.ref(
        'service_dashboards.service_dashboards_menu_root',
        raise_if_not_found=False,
    )
    ct_menu = env.ref(
        'ks_dashboard_ninja.services_dashboards_menu_root',
        raise_if_not_found=False,
    )
    if not sd_menu or not ct_menu:
        return

    # Remove any previously created copies to avoid duplicates on re-run.
    env['ks_dashboard_ninja.board'].search([
        ('ks_dashboard_top_menu_id', '=', ct_menu.id),
    ]).unlink()

    boards = env['ks_dashboard_ninja.board'].search([
        ('ks_dashboard_top_menu_id', '=', sd_menu.id),
    ])
    for board in boards:
        board.copy({'ks_dashboard_top_menu_id': ct_menu.id, 'name': board.name})
