import ast
import json


# KS grid is 12 columns wide.
GRID_W = 12
KPI_W, KPI_H = 2, 3
CHART_W, CHART_H = 12, 7


def _clean_layout(items, start_y=0):
    """Deterministic, non-overlapping layout: KPIs as small tiles in a
    left-aligned row (w=2, h=3, six per row), charts full-width stacked below."""
    cfg = {}
    kpis = [i for i in items if i.ks_dashboard_item_type == 'ks_kpi']
    charts = [i for i in items if i.ks_dashboard_item_type != 'ks_kpi']
    x = 0
    y = start_y
    for item in kpis:
        if x + KPI_W > GRID_W:
            x = 0
            y += KPI_H
        cfg[str(item.id)] = {'x': x, 'y': y, 'w': KPI_W, 'h': KPI_H}
        x += KPI_W
    if kpis:
        y += KPI_H
    for item in charts:
        cfg[str(item.id)] = {'x': 0, 'y': y, 'w': CHART_W, 'h': CHART_H}
        y += CHART_H
    return cfg


def _board_layout_from_items(env, board):
    """Build a gridstack config {str(item_id): {x, y, w, h}}.

    Use each item's stored grid_corners as-is when present — this preserves the
    board's original arrangement and order (including multi-column layouts where
    e.g. a count chart sits beside its percentage chart). Items with no stored
    position get a sensible default (KPIs as small tiles, charts full-width)
    appended below.

    Only when a board's stored positions are *degenerate* — every positioned
    chart piled on the exact same spot (a few legacy boards stored stale /
    duplicated grid_corners) — do we discard them and re-flow that board cleanly,
    so KPIs don't float mid-row and charts don't sit on top of each other."""
    items = env['ks_dashboard_ninja.item'].search(
        [('ks_dashboard_ninja_board_id', '=', board.id)], order='id')
    cfg = {}
    max_y = 0
    unpositioned = []
    chart_positions = []  # (x, y) of positioned non-KPI items
    for item in items:
        gc = None
        if item.grid_corners:
            try:
                gc = ast.literal_eval(item.grid_corners)
            except Exception:
                gc = None
        if isinstance(gc, dict) and 'x' in gc and 'y' in gc:
            entry = {
                'x': int(gc.get('x', 0)),
                'y': int(gc.get('y', 0)),
                'w': int(gc.get('w', CHART_W)),
                'h': int(gc.get('h', CHART_H)),
            }
            cfg[str(item.id)] = entry
            max_y = max(max_y, entry['y'] + entry['h'])
            if item.ks_dashboard_item_type != 'ks_kpi':
                chart_positions.append((entry['x'], entry['y']))
        else:
            unpositioned.append(item)

    # Degenerate layout: 2+ charts all stored at the exact same position.
    degenerate = len(chart_positions) >= 2 and len(set(chart_positions)) == 1
    if degenerate:
        return _clean_layout(items, start_y=0)

    # Otherwise keep the original positions and append any position-less items.
    cfg.update(_clean_layout(unpositioned, start_y=max_y))
    return cfg


def ks_rebuild_board_layouts(env):
    """Restore chart size/position for the Service Dashboards.

    KS Dashboard Ninja renders a board's layout from the (per-company) child
    board's ks_gridstack_config, which is seeded from board.ks_gridstack_config.
    On a fresh data-XML install both are empty, so charts auto-stack and lose
    their size/position. Here we rebuild the gridstack config from each item's
    grid_corners (captured in the data XML) so the layout is reproduced
    deterministically on every install."""
    xmlids = env['ir.model.data'].search([
        ('module', '=', 'service_dashboard'),
        ('model', '=', 'ks_dashboard_ninja.board'),
    ])
    boards = env['ks_dashboard_ninja.board'].browse(xmlids.mapped('res_id')).exists()
    for board in boards:
        cfg_json = json.dumps(_board_layout_from_items(env, board))
        board.ks_gridstack_config = cfg_json
        # Update any already-created per-company child boards too.
        for child in board.ks_child_dashboard_ids:
            child.ks_gridstack_config = cfg_json


def post_init_hook(env):
    """Set the chart colour palette and rebuild board layouts from grid_corners.

    The "Service Dashboards - Custom Theme" boards (xmlids prefixed `ct_`) are
    excluded from the palette reset — their per-item palettes come from the
    reference JSON dashboards and must not be flattened back to custom-1.
    """
    chart_types = [
        'ks_bar_chart',
        'ks_horizontalBar_chart',
        'ks_pie_chart',
        'ks_doughnut_chart',
    ]
    items = env['ks_dashboard_ninja.item'].search([
        ('ks_dashboard_item_type', 'in', chart_types),
    ])
    if items:
        custom_theme_xmlids = env['ir.model.data'].search([
            ('module', '=', 'service_dashboard'),
            ('model', '=', 'ks_dashboard_ninja.item'),
            ('name', '=like', 'ct_%'),
        ])
        custom_theme_ids = set(custom_theme_xmlids.mapped('res_id'))
        items = items.filtered(lambda i: i.id not in custom_theme_ids)
        if items:
            items.write({'ks_chart_item_color': 'custom-1'})

    ks_rebuild_board_layouts(env)
