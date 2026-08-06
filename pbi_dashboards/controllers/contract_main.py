# -*- coding: utf-8 -*-
"""Backs every "PBI Dashboards > Contract Dashboards" leaf. Inherits
PbiDashboardBoardEngineMixin (service_main.py) to reuse
_has_access/_resolve_date_range/_effective_board/_region_options/
_value_format/_item_payload as-is (all already generic, keyed by
whichever BoardConfig/ChartItemConfig is passed in) — only the routes and
which registry (CONTRACT_BOARDS, not BOARDS) they read from differ.
Deliberately does NOT subclass PbiServiceDashboardController itself: that
class is already a concrete http.Controller, and Odoo's route-generation
walks the whole MRO of every controller class it finds, so subclassing it
directly would re-register /pbi_dashboards/service/board and .../chart a
second time under this controller too. The mixin holds the shared logic
without itself being scanned as a controller. Reads live from
subscription_contracts directly (see service_sql.py's "contracts" CTE) —
no ks_dashboard_ninja or contract_dashboards module dependency.

Access is gated the same way as every other pbi_dashboards menu. When
user_menu_rights is installed (an optional overlay, not a dependency) the
menu is hidden until an admin grants it there; otherwise ordinary Odoo
groups decide. Either way it is
enforced both on the menu (existing mechanism) and here on the JSON data
routes themselves (inherited _has_access, keyed by the same
"pbi_dashboards.menu_pbi_<board>" xmlid convention).
"""
from odoo.http import request

from odoo import http

from . import service_sql
from .contract_config import CONTRACT_BOARDS
from .service_main import PbiDashboardBoardEngineMixin


class PbiContractDashboardController(PbiDashboardBoardEngineMixin, http.Controller):

    @http.route('/pbi_dashboards/contract/board', type='json', auth='user')
    def contract_board_data(self, board, dateFilter=None, customStart=None, customEnd=None, region=None):
        if not self._has_access(board):
            return {'error': 'You do not have access to this dashboard.'}
        board_cfg = CONTRACT_BOARDS.get(board)
        if not board_cfg:
            return {'error': 'Unknown dashboard.'}
        try:
            date_from, date_to, resolved_filter, label = self._resolve_date_range(dateFilter, customStart, customEnd)
            effective_board = self._effective_board(board_cfg, region)
            uid = request.env.uid
            items = [self._item_payload(effective_board, item_cfg, date_from, date_to, uid)
                     for item_cfg in board_cfg.items]
            result = {
                "title": board_cfg.title,
                "period": {"dateFilter": resolved_filter, "label": label},
                "regionFilterable": board_cfg.region_filterable,
                "items": items,
            }
            if board_cfg.region_filterable:
                result["regionOptions"] = self._region_options(request.env)
            return result
        except Exception as e:
            return {'error': str(e)}

    @http.route('/pbi_dashboards/contract/chart', type='json', auth='user')
    def contract_chart_data(self, board, item, drillPath=None, dateFilter=None, customStart=None, customEnd=None, region=None):
        if not self._has_access(board):
            return {'error': 'You do not have access to this dashboard.'}
        board_cfg = CONTRACT_BOARDS.get(board)
        if not board_cfg:
            return {'error': 'Unknown dashboard.'}
        item_cfg = next((i for i in board_cfg.items if i.key == item), None)
        if not item_cfg:
            return {'error': 'Unknown chart.'}
        try:
            date_from, date_to, _resolved_filter, _label = self._resolve_date_range(dateFilter, customStart, customEnd)
            effective_board = self._effective_board(board_cfg, region)
            uid = request.env.uid
            drill_path = drillPath if isinstance(drillPath, list) else []
            breakdown = service_sql.run_breakdown(request.env, uid, effective_board, item_cfg, date_from, date_to, drill_path)
            if breakdown is None:
                model, domain = service_sql.run_terminal_domain(request.env, uid, effective_board, item_cfg, drill_path, date_from, date_to)
                return {'terminal': True, 'model': model, 'domain': domain, 'name': item_cfg.name}
            return {'terminal': False, 'breakdown': breakdown, 'level': len(drill_path)}
        except Exception as e:
            return {'error': str(e)}
