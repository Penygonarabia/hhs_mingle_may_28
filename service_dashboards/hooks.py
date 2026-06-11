import json


def post_init_hook(env):
    """Rebuild ks_gridstack_config on each board from items' grid_corners.

    The XML data file sets grid_corners per-item (position is stable and
    item-scoped), but ks_gridstack_config maps {str(item_db_id): position}
    and cannot be written in XML because IDs are only known at runtime.
    This hook repairs it after all records are loaded.
    """
    Board = env['ks_dashboard_ninja.board']
    # Find all boards created by this module via their external IDs
    xids = env['ir.model.data'].search([
        ('module', '=', 'service_dashboards'),
        ('model', '=', 'ks_dashboard_ninja_board'),
    ])
    boards = Board.browse([x.res_id for x in xids])
    for board in boards:
        gridstack = {}
        for item in board.ks_dashboard_items_ids:
            if item.grid_corners:
                try:
                    pos = json.loads(item.grid_corners.replace("'", '"'))
                    gridstack[str(item.id)] = pos
                except Exception:
                    pass
        if gridstack:
            board.ks_gridstack_config = json.dumps(gridstack)
