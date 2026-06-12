from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Sync per-company child render configs for the Custom Theme boards.

    The 17.0.1.0.8 pass only repaired child gridstack configs for boards whose
    layout was rebuilt from per-item grid_corners; boards that lay out purely
    from the board-level gridstack (e.g. 'Service Analysis - Technicians') were
    left with stale source item ids on their child boards. Here we copy each
    Custom Theme board's (correct) parent gridstack onto all of its child
    boards. Idempotent.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    ct_menu = env.ref(
        'service_dashboards_ct.menu_root',
        raise_if_not_found=False,
    )
    if not ct_menu:
        return

    ct_boards = env['ks_dashboard_ninja.board'].search([
        ('ks_dashboard_top_menu_id', '=', ct_menu.id),
    ])
    for board in ct_boards:
        if not board.ks_gridstack_config:
            continue
        for child in board.ks_child_dashboard_ids:
            if child.ks_gridstack_config != board.ks_gridstack_config:
                child.ks_gridstack_config = board.ks_gridstack_config
