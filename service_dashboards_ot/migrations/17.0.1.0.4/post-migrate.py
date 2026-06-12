from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Locate all ct_ boards owned by this module.
    ct_xmlids = env['ir.model.data'].search([
        ('module', '=', 'service_dashboards_ot'),
        ('model', '=', 'ks_dashboard_ninja.board'),
        ('name', '=like', 'ct_%'),
    ])
    ct_boards = env['ks_dashboard_ninja.board'].browse(
        ct_xmlids.mapped('res_id')
    ).exists()

    if ct_boards:
        ct_items = env['ks_dashboard_ninja.item'].search([
            ('ks_dashboard_ninja_board_id', 'in', ct_boards.ids)
        ])
        if ct_items:
            env['ks_dashboard_ninja.item_action'].search([
                ('ks_dashboard_item_id', 'in', ct_items.ids)
            ]).unlink()
            ct_items.unlink()
        ct_boards.unlink()

    menu = env.ref(
        'service_dashboards_ot.service_dashboards_custom_theme_menu_root',
        raise_if_not_found=False,
    )
    if menu:
        menu.unlink()
