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
        'service_dashboards_ot.menu_root',
        raise_if_not_found=False,
    )
    ct_menu = env.ref(
        'service_dashboards_ct.menu_root',
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

    Filter = env['ks_dashboard_ninja.board_custom_filters']
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

        # Mirror any board-level custom filters (e.g. "Regions") onto the
        # CT clone. board.copy() does NOT copy the ks_board_custom_filters
        # One2many, so without this the CT side loses the filter UI.
        existing_names = set(
            Filter.search([
                ('ks_dashboard_board_id', '=', ct_board.id),
            ]).mapped('name')
        )
        for f in sd_board.ks_dashboard_custom_filters_ids:
            if f.name in existing_names:
                continue
            Filter.create({
                'ks_dashboard_board_id': ct_board.id,
                'ks_model_id': f.ks_model_id.id,
                'ks_domain_field_id': f.ks_domain_field_id.id,
                'name': f.name,
            })
