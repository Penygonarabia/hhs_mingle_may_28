import ast
import json
import logging

from .drill_actions_data import DRILL_ACTIONS

_logger = logging.getLogger(__name__)


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
    apply_drill_actions(env)


def apply_drill_actions(env):
    """Re-create every ``ks_dashboard_ninja.item_action`` row owned by
    service_dashboards_ct from :data:`DRILL_ACTIONS`.

    The drill-down configuration is the single source of truth and lives in
    :mod:`drill_actions_data`. We wipe the existing CT-owned rows and rebuild
    so the in-DB state always matches the data file — both on fresh install
    (post_init_hook) and on upgrade (post-migrate).

    Items and boards are matched by ``name`` per the JSON export schema; a
    missing item is logged and skipped (no exception, so a partially-edited
    board can't break upgrades).
    """
    Action = env['ks_dashboard_ninja.item_action'].sudo()
    Item = env['ks_dashboard_ninja.item'].sudo()
    Board = env['ks_dashboard_ninja.board'].sudo()
    Field = env['ir.model.fields'].sudo()
    ModelData = env['ir.model.data'].sudo()

    # 1) Resolve CT-owned boards and their items, keyed by name.
    ct_board_xmlids = ModelData.search([
        ('module', '=', CT_MODULE),
        ('model', '=', 'ks_dashboard_ninja.board'),
    ])
    ct_boards = Board.browse(ct_board_xmlids.mapped('res_id')).exists()
    board_by_name = {b.name: b for b in ct_boards}

    ct_item_xmlids = ModelData.search([
        ('module', '=', CT_MODULE),
        ('model', '=', 'ks_dashboard_ninja.item'),
    ])
    ct_items = Item.browse(ct_item_xmlids.mapped('res_id')).exists()
    items_by_board = {}
    for it in ct_items:
        if it.ks_dashboard_ninja_board_id:
            items_by_board.setdefault(it.ks_dashboard_ninja_board_id.id, {})[it.name] = it

    # 2) Wipe every action row attached to a CT-owned item, then drop any
    #    leftover CT-owned xmlid for the action model. We key on the parent
    #    item's ownership (not on the action's xmlid) because rows created by
    #    this helper are anonymous — no ir.model.data is written for them.
    if ct_items:
        Action.search([
            ('ks_dashboard_item_id', 'in', ct_items.ids),
        ]).unlink()
    leftover_xmlids = ModelData.search([
        ('module', '=', CT_MODULE),
        ('model', '=', 'ks_dashboard_ninja.item_action'),
    ])
    if leftover_xmlids:
        leftover_xmlids.unlink()

    # 3) Field lookup cache.
    field_cache = {}

    def _resolve_field(model_name, field_name):
        key = (model_name, field_name)
        if key in field_cache:
            return field_cache[key]
        rec = Field.search([
            ('model', '=', model_name),
            ('name', '=', field_name),
        ], limit=1)
        field_cache[key] = rec.id if rec else False
        if not rec:
            _logger.warning(
                "service_dashboards_ct drill: %s.%s not found in ir.model.fields",
                model_name, field_name,
            )
        return field_cache[key]

    # 4) Recreate action rows from the data file.
    created = 0
    skipped_items = 0
    for board_name, items_data in DRILL_ACTIONS.items():
        board = board_by_name.get(board_name)
        if not board:
            _logger.warning(
                "service_dashboards_ct drill: board %r not found, skipping", board_name,
            )
            continue
        item_lookup = items_by_board.get(board.id, {})
        for item_name, actions in items_data.items():
            item = item_lookup.get(item_name)
            if not item:
                skipped_items += 1
                _logger.warning(
                    "service_dashboards_ct drill: item %r not found on board %r",
                    item_name, board_name,
                )
                continue
            for action in actions:
                field_id = _resolve_field(action['model'], action['field'])
                if not field_id:
                    continue
                vals = {
                    'ks_dashboard_item_id': item.id,
                    'ks_item_action_field': field_id,
                    'sequence': action['sequence'],
                }
                if action.get('date_groupby'):
                    vals['ks_item_action_date_groupby'] = action['date_groupby']
                if action.get('chart_type'):
                    vals['ks_chart_type'] = action['chart_type']
                if action.get('record_limit'):
                    vals['ks_record_limit'] = action['record_limit']
                Action.create(vals)
                created += 1
    _logger.info(
        "service_dashboards_ct drill: created %s action rows (skipped %s items)",
        created, skipped_items,
    )
