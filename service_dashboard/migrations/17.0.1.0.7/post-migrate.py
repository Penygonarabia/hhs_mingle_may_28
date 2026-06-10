import json
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Populate the 'Service Dashboards - Custom Theme' boards with chart items.

    Migration 17.0.1.0.6 created the board copies but Odoo's board.copy() does
    not auto-copy the One2many items, so all 15 CT boards ended up empty.
    This migration copies items from each matching 'Service Dashboards' board and
    rebuilds the gridstack layout on the copied board.
    """
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

    sd_boards_by_name = {
        b.name: b
        for b in env['ks_dashboard_ninja.board'].search([
            ('ks_dashboard_top_menu_id', '=', sd_menu.id),
        ])
    }

    ct_boards = env['ks_dashboard_ninja.board'].search([
        ('ks_dashboard_top_menu_id', '=', ct_menu.id),
    ])

    for ct_board in ct_boards:
        if ct_board.ks_dashboard_items_ids:
            continue  # Already populated — skip (safe to re-run)

        sd_board = sd_boards_by_name.get(ct_board.name)
        if not sd_board:
            continue

        # Build old_item_id → gridstack position from source board
        id_to_pos = {}
        if sd_board.ks_gridstack_config:
            try:
                for k, v in json.loads(sd_board.ks_gridstack_config).items():
                    id_to_pos[int(k)] = v
            except Exception:
                pass

        # Copy items and remap gridstack keys to the new item IDs
        new_gridstack = {}
        for item in sd_board.ks_dashboard_items_ids:
            new_item = item.copy({'ks_dashboard_ninja_board_id': ct_board.id})
            if item.id in id_to_pos:
                new_gridstack[str(new_item.id)] = id_to_pos[item.id]

        if new_gridstack:
            ct_board.ks_gridstack_config = json.dumps(new_gridstack)
