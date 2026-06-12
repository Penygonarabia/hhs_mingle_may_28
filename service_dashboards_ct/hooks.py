import ast
import json


GRID_W = 12
KPI_W, KPI_H = 2, 3
CHART_W, CHART_H = 12, 7

CT_MODULE = 'service_dashboards_ct'
CT_PALETTE = 'custom-1'


def _clean_layout(items, start_y=0):
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
    items = env['ks_dashboard_ninja.item'].search(
        [('ks_dashboard_ninja_board_id', '=', board.id)], order='id')
    cfg = {}
    max_y = 0
    unpositioned = []
    chart_positions = []
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

    degenerate = len(chart_positions) >= 2 and len(set(chart_positions)) == 1
    if degenerate:
        return _clean_layout(items, start_y=0)

    cfg.update(_clean_layout(unpositioned, start_y=max_y))
    return cfg


def ks_rebuild_board_layouts(env):
    """Rebuild gridstack_config for boards owned by service_dashboards_ct only."""
    xmlids = env['ir.model.data'].search([
        ('module', '=', CT_MODULE),
        ('model', '=', 'ks_dashboard_ninja.board'),
    ])
    boards = env['ks_dashboard_ninja.board'].browse(xmlids.mapped('res_id')).exists()
    for board in boards:
        cfg_json = json.dumps(_board_layout_from_items(env, board))
        board.ks_gridstack_config = cfg_json
        for child in board.ks_child_dashboard_ids:
            child.ks_gridstack_config = cfg_json


def post_init_hook(env):
    """Apply the CT palette to CT-owned chart items, then rebuild layouts.

    Scoped strictly to items owned by service_dashboards_ct so the sibling
    service_dashboards_ot module's items (which use the moonrise palette) are
    not touched.
    """
    chart_types = [
        'ks_bar_chart',
        'ks_horizontalBar_chart',
        'ks_pie_chart',
        'ks_doughnut_chart',
    ]
    own_item_xmlids = env['ir.model.data'].search([
        ('module', '=', CT_MODULE),
        ('model', '=', 'ks_dashboard_ninja.item'),
    ])
    own_item_ids = own_item_xmlids.mapped('res_id')
    if own_item_ids:
        items = env['ks_dashboard_ninja.item'].search([
            ('id', 'in', own_item_ids),
            ('ks_dashboard_item_type', 'in', chart_types),
        ])
        if items:
            items.write({'ks_chart_item_color': CT_PALETTE})

    ks_rebuild_board_layouts(env)
