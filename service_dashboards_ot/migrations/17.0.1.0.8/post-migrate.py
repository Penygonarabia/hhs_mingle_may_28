import ast
import json
from odoo import api, SUPERUSER_ID


def _parse_pos(raw):
    """Parse a grid_corners value (Python-dict or JSON string) into a dict."""
    if not raw:
        return None
    try:
        pos = ast.literal_eval(raw) if isinstance(raw, str) else raw
    except Exception:
        try:
            pos = json.loads(raw)
        except Exception:
            return None
    if isinstance(pos, dict) and 'x' in pos and 'y' in pos:
        return {
            'x': int(pos.get('x', 0)),
            'y': int(pos.get('y', 0)),
            'w': int(pos.get('w', 12)),
            'h': int(pos.get('h', 7)),
        }
    return None


def migrate(cr, version):
    """Align the 'Service Dashboards - Custom Theme' boards with their sources.

    1. Position every chart exactly as on the matching 'Service Dashboards'
       board — rebuild each Custom Theme board's gridstack config (parent AND
       per-company child boards) from the source item positions, keyed by the
       Custom Theme item ids.
    2. Set the chart colour palette (ks_chart_item_color) to 'custom-1' on all
       Custom Theme chart items.
    Idempotent: safe to re-run.
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

    chart_types = [
        'ks_bar_chart',
        'ks_horizontalBar_chart',
        'ks_pie_chart',
        'ks_doughnut_chart',
        'ks_line_chart',
        'ks_area_chart',
        'ks_polarArea_chart',
    ]

    Board = env['ks_dashboard_ninja.board']
    sd_boards_by_name = {
        b.name: b
        for b in Board.search([('ks_dashboard_top_menu_id', '=', sd_menu.id)])
    }
    ct_boards = Board.search([('ks_dashboard_top_menu_id', '=', ct_menu.id)])

    for ct_board in ct_boards:
        sd_board = sd_boards_by_name.get(ct_board.name)
        if not sd_board:
            continue

        sd_items = sd_board.ks_dashboard_items_ids.sorted('id')
        ct_items = ct_board.ks_dashboard_items_ids.sorted('id')
        if len(sd_items) != len(ct_items):
            # Counts diverged — skip layout sync for this board to stay safe,
            # but still apply the palette below.
            pass
        else:
            gridstack = {}
            for sd_item, ct_item in zip(sd_items, ct_items):
                pos = _parse_pos(sd_item.grid_corners)
                if pos is None:
                    continue
                # Keep grid_corners on the Custom Theme item in sync as well.
                ct_item.grid_corners = json.dumps(pos)
                gridstack[str(ct_item.id)] = pos
            if gridstack:
                ct_board.ks_gridstack_config = json.dumps(gridstack)

        # Repair per-company child render configs from the (now correct) parent
        # gridstack. They may still hold stale source item ids from the original
        # board.copy(). Always sync — even for boards whose layout comes from the
        # board-level gridstack rather than per-item grid_corners.
        if ct_board.ks_gridstack_config:
            for child in ct_board.ks_child_dashboard_ids:
                child.ks_gridstack_config = ct_board.ks_gridstack_config

        # Palette: custom-1 for every chart item on the Custom Theme board.
        chart_items = ct_board.ks_dashboard_items_ids.filtered(
            lambda i: i.ks_dashboard_item_type in chart_types
        )
        if chart_items:
            chart_items.write({'ks_chart_item_color': 'custom-1'})
