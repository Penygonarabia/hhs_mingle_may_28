import ast
import json


GRID_W = 12
KPI_W, KPI_H = 2, 3
CHART_W, CHART_H = 12, 7
LIST_W, LIST_H = 12, 10


def _layout_from_items(items, start_y=0):
    """KPIs as small tiles in a left-aligned row, charts/lists full-width below."""
    cfg = {}
    kpis = [i for i in items if i.ks_dashboard_item_type == 'ks_kpi']
    others = [i for i in items if i.ks_dashboard_item_type != 'ks_kpi']
    x, y = 0, start_y
    for item in kpis:
        if x + KPI_W > GRID_W:
            x = 0
            y += KPI_H
        cfg[str(item.id)] = {'x': x, 'y': y, 'w': KPI_W, 'h': KPI_H}
        x += KPI_W
    if kpis:
        y += KPI_H
    for item in others:
        if item.ks_dashboard_item_type == 'ks_list_view':
            w, h = LIST_W, LIST_H
        else:
            w, h = CHART_W, CHART_H
        cfg[str(item.id)] = {'x': 0, 'y': y, 'w': w, 'h': h}
        y += h
    return cfg


def _board_layout(env, board):
    """Honor each item's stored grid_corners; auto-flow anything without one."""
    items = env['ks_dashboard_ninja.item'].search(
        [('ks_dashboard_ninja_board_id', '=', board.id)], order='id')
    cfg = {}
    max_y = 0
    unpositioned = []
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
        else:
            unpositioned.append(item)
    cfg.update(_layout_from_items(unpositioned, start_y=max_y))
    return cfg


def contract_dashboard_rebuild_layouts(env):
    """Reseed ks_gridstack_config on every contract_dashboard board (and its
    per-company children) so the UI renders items in the order their
    grid_corners specify — without this the board uses whatever stale config
    is already stored."""
    xmlids = env['ir.model.data'].search([
        ('module', '=', 'contract_dashboard'),
        ('model', '=', 'ks_dashboard_ninja.board'),
    ])
    boards = env['ks_dashboard_ninja.board'].browse(xmlids.mapped('res_id')).exists()
    for board in boards:
        cfg_json = json.dumps(_board_layout(env, board))
        board.ks_gridstack_config = cfg_json
        for child in board.ks_child_dashboard_ids:
            child.ks_gridstack_config = cfg_json


def post_init_hook(env):
    contract_dashboard_rebuild_layouts(env)
