# -*- coding: utf-8 -*-
"""Backs every "PBI Dashboards > Service Dashboards" leaf — a single
generic controller for all 15 dashboards (see service_config.py's
``BOARDS`` registry), each identified by a ``board`` key. Reads live from
``project_task``/``machine_repair_support``/``mail_message`` directly
(see service_sql.py) — no ``ks_dashboard_ninja`` or ``dbmodel.*.ct``
dependency.

Access is gated the same way as every other pbi_dashboards menu. When
user_menu_rights is installed (an optional overlay, not a dependency) the
menu is hidden until an admin grants it there; otherwise ordinary Odoo
groups decide. Either way it is
enforced both on the menu (existing mechanism) and here on the JSON data
routes themselves — same double-gate pattern as sales_kpi_main.py.
"""
from odoo import http
from odoo.http import request

from . import service_sql
from .service_config import BOARDS, resolve_scope_info, resolve_item_info
from odoo.addons.pbi_dashboards.controllers.board_engine import PbiDashboardBoardEngineMixin  # noqa: F401


class _ServiceMixin(PbiDashboardBoardEngineMixin):
    """Thin override layer: supplies service-specific item info strings from
    resolve_item_info (service_config.py). All other mixin methods are
    inherited unchanged from PbiDashboardBoardEngineMixin."""

    def _resolve_item_info(self, board_cfg, item_cfg):
        return resolve_item_info(board_cfg, item_cfg)


class PbiServiceDashboardController(_ServiceMixin, http.Controller):

    @http.route('/pbi_dashboards/service/board', type='json', auth='user')
    def board_data(self, board, dateFilter=None, customStart=None, customEnd=None, region=None):
        if not self._has_access(board):
            return {'error': 'You do not have access to this dashboard.'}
        board_cfg = BOARDS.get(board)
        if not board_cfg:
            return {'error': 'Unknown dashboard.'}
        try:
            date_from, date_to, resolved_filter, label = self._resolve_date_range(dateFilter, customStart, customEnd)
            effective_board = self._effective_board(board_cfg, region)
            uid = request.env.uid
            period_months = self._period_months(date_from, date_to)
            items = [self._item_payload(effective_board, item_cfg, date_from, date_to, uid, period_months)
                     for item_cfg in board_cfg.items]
            result = {
                "title": board_cfg.title,
                "scopeInfo": resolve_scope_info(board_cfg),
                "period": {"dateFilter": resolved_filter, "label": label},
                "regionFilterable": board_cfg.region_filterable,
                "items": items,
            }
            if board_cfg.region_filterable:
                result["regionOptions"] = self._region_options(request.env)
            return result
        except Exception as e:
            return {'error': str(e)}

    @http.route('/pbi_dashboards/service/chart', type='json', auth='user')
    def chart_data(self, board, item, drillPath=None, dateFilter=None, customStart=None, customEnd=None, region=None):
        if not self._has_access(board):
            return {'error': 'You do not have access to this dashboard.'}
        board_cfg = BOARDS.get(board)
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
            period_months = self._period_months(date_from, date_to)
            breakdown = service_sql.run_breakdown(request.env, uid, effective_board, item_cfg, date_from, date_to,
                                                  drill_path, period_months)
            if breakdown is None:
                model, domain = service_sql.run_terminal_domain(request.env, uid, effective_board, item_cfg, drill_path, date_from, date_to)
                return {'terminal': True, 'model': model, 'domain': domain, 'name': item_cfg.name}
            return {'terminal': False, 'breakdown': breakdown, 'level': len(drill_path)}
        except Exception as e:
            return {'error': str(e)}
