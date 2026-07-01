import ast
import json


GRID_W = 12
CHART_W, CHART_H = 12, 7


def _board_layout(env, board):
    items = env["ks_dashboard_ninja.item"].search(
        [("ks_dashboard_ninja_board_id", "=", board.id)], order="id"
    )
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
        if isinstance(gc, dict) and "x" in gc and "y" in gc:
            entry = {
                "x": int(gc.get("x", 0)),
                "y": int(gc.get("y", 0)),
                "w": int(gc.get("w", CHART_W)),
                "h": int(gc.get("h", CHART_H)),
            }
            cfg[str(item.id)] = entry
            max_y = max(max_y, entry["y"] + entry["h"])
        else:
            unpositioned.append(item)
    y = max_y
    for item in unpositioned:
        cfg[str(item.id)] = {"x": 0, "y": y, "w": CHART_W, "h": CHART_H}
        y += CHART_H
    return cfg


def loyalty_dashboard_rebuild_layouts(env):
    xmlids = env["ir.model.data"].search([
        ("module", "=", "loyalty_dashboard"),
        ("model", "=", "ks_dashboard_ninja.board"),
    ])
    boards = env["ks_dashboard_ninja.board"].browse(xmlids.mapped("res_id")).exists()
    for board in boards:
        cfg_json = json.dumps(_board_layout(env, board))
        board.ks_gridstack_config = cfg_json
        for child in board.ks_child_dashboard_ids:
            child.ks_gridstack_config = cfg_json


def post_init_hook(env):
    loyalty_dashboard_rebuild_layouts(env)
