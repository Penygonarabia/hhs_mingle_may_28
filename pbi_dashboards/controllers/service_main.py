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
import calendar
import dataclasses
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request

from . import service_sql
from .access import menu_allowed
from .service_config import BOARDS, resolve_scope_info, resolve_item_info

# The 7 period options every board's filter bar offers — same vocabulary
# and date math as ks_dashboard_ninja's own date-filter dropdown
# (t_year/t_month/t_week = "This X" -> the FULL current period, not
# "to date"; ls_year/ls_month/ls_week = "Last X" -> the previous full
# calendar period; l_custom = an explicit caller-supplied range). Default
# is t_month, matching every source board's own ks_date_filter_selection.
DATE_FILTER_LABELS = {
    "t_year": "This Year", "t_month": "This Month", "t_week": "This Week",
    "ls_year": "Last Year", "ls_month": "Last Month", "ls_week": "Last Week",
    "l_custom": "Custom",
}
DEFAULT_DATE_FILTER = "t_month"


def _month_range(year, month):
    last_day = calendar.monthrange(year, month)[1]
    return datetime(year, month, 1), datetime(year, month, last_day, 23, 59, 59)


def _week_range(now, offset_weeks=0):
    """Monday-start week (matches ks_dashboard_ninja's default week_start=1
    locale behaviour), offset in whole weeks (0 = this week, -1 = last)."""
    monday = now - timedelta(days=now.weekday()) + timedelta(weeks=offset_weeks)
    start = datetime(monday.year, monday.month, monday.day)
    end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return start, end


class PbiDashboardBoardEngineMixin:
    """Shared instance methods for every generic-engine dashboard
    controller (currently PbiServiceDashboardController here and
    PbiPromoterDashboardController in promoter_main.py) — deliberately
    NOT an http.Controller subclass itself, so Odoo's route-registration
    scan never sees it as its own controller: a plain-inheritance mixin
    like this is combined with http.Controller only in each CONCRETE
    controller class, so each of those still contributes exactly its own
    @http.route-decorated methods (a fresh subclass of
    PbiServiceDashboardController itself would inherit — and thus
    re-register — that class's own routes too, which is what this split
    avoids)."""

    def _has_access(self, board_key):
        return menu_allowed(f"pbi_dashboards.menu_pbi_{board_key}")

    def _resolve_date_range(self, date_filter, custom_start, custom_end):
        now = datetime.utcnow()
        date_filter = date_filter if date_filter in DATE_FILTER_LABELS else DEFAULT_DATE_FILTER

        if date_filter == "t_year":
            date_from, date_to = datetime(now.year, 1, 1), datetime(now.year, 12, 31, 23, 59, 59)
        elif date_filter == "ls_year":
            y = now.year - 1
            date_from, date_to = datetime(y, 1, 1), datetime(y, 12, 31, 23, 59, 59)
        elif date_filter == "t_month":
            date_from, date_to = _month_range(now.year, now.month)
        elif date_filter == "ls_month":
            y, m = now.year, now.month - 1
            if m == 0:
                y, m = y - 1, 12
            date_from, date_to = _month_range(y, m)
        elif date_filter == "t_week":
            date_from, date_to = _week_range(now, 0)
        elif date_filter == "ls_week":
            date_from, date_to = _week_range(now, -1)
        elif date_filter == "l_custom":
            try:
                date_from = datetime.strptime(custom_start, "%Y-%m-%d")
                date_to = datetime.strptime(custom_end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            except (TypeError, ValueError):
                date_from, date_to = _month_range(now.year, now.month)
                date_filter = "t_month"
        else:
            date_from, date_to = _month_range(now.year, now.month)

        if date_filter in ("t_month", "ls_month"):
            label = date_from.strftime("%B %Y")
        elif date_filter in ("t_year", "ls_year"):
            label = str(date_from.year)
        else:
            label = f"{date_from:%b %d, %Y} - {date_to:%b %d, %Y}"
        return date_from, date_to, date_filter, label

    def _period_months(self, date_from, date_to):
        """How many calendar months the resolved date range spans — the
        scaling factor for the technician utilization KPI's fixed 176
        working-hours-per-month denominator (see service_config.py's
        MONTHLY_WORKING_HOURS). "This Month"/"Last Month" give exactly 1,
        so the spec's literal formula is what runs in the default view;
        "This Year" gives 12 instead of reporting ~1200% utilization. A
        week-long range still counts as 1 (never 0) — a partial month is
        the smallest meaningful unit here, and it keeps the denominator
        away from zero."""
        months = (date_to.year - date_from.year) * 12 + (date_to.month - date_from.month) + 1
        return max(months, 1)

    def _effective_board(self, board_cfg, region):
        """Boards with region_filterable=True get an extra region clause
        ANDed onto a per-request copy of board.scope — never mutates the
        module-level BOARDS registry. region=None/'' /'all' means no
        restriction (every region, the default)."""
        if not board_cfg.region_filterable or not region or region == "all":
            return board_cfg
        extra = ("work_center_group_id", "=", f"@region:{region}")
        return dataclasses.replace(board_cfg, scope=list(board_cfg.scope) + [extra])

    def _region_options(self, env):
        groups = env["work.center.group"].sudo().search_read([], ["name"], order="name")
        return [g["name"] for g in groups]

    def _value_format(self, item_cfg):
        """Matches ks_dashboard_ninja's own convention (dbmodel_jobcards_analysis.py:
        ``if field_name.endswith("_hours"): field_node.set("widget", "float_time")``)
        — any *_hours measure renders as H:MM instead of a plain decimal, both on
        KPI tiles and on chart value labels/tooltips. Same idea for *_amount
        measures (Contract Analysis's contract_amount/service_amount, values
        running into the hundreds of thousands) — rendered compact as "0.4M"
        instead of "393,758", both on tiles and axis ticks. And *_pct
        measures (technician utilization) render as "96.59%"."""
        for m in (item_cfg.measure, item_cfg.measure_2):
            if m and m.field.endswith("_pct"):
                return "percent"
        for m in (item_cfg.measure, item_cfg.measure_2):
            if m and m.field.endswith("_hours"):
                return "hours"
        for m in (item_cfg.measure, item_cfg.measure_2):
            if m and m.field.endswith("_amount"):
                return "millions"
        return "number"

    def _item_payload(self, board_cfg, item_cfg, date_from, date_to, uid, period_months=1):
        value_format = self._value_format(item_cfg)
        info = resolve_item_info(board_cfg, item_cfg)
        if item_cfg.type in ("kpi_single", "kpi_dual"):
            data = service_sql.run_kpi(request.env, uid, board_cfg, item_cfg, date_from, date_to, period_months)
            return {"key": item_cfg.key, "name": item_cfg.name, "type": item_cfg.type,
                    "info": info, "valueFormat": value_format, **data}
        if item_cfg.type in ("bar", "pie"):
            breakdown = service_sql.run_breakdown(request.env, uid, board_cfg, item_cfg, date_from, date_to, [],
                                                  period_months)
            payload = {"key": item_cfg.key, "name": item_cfg.name, "type": item_cfg.type,
                       "info": info, "breakdown": breakdown or [], "level": 0, "valueFormat": value_format}
            if item_cfg.measure_2:
                payload["seriesLabels"] = list(item_cfg.series_labels or ["Series 1", "Series 2"])
            return payload
        if item_cfg.type == "table":
            rows = service_sql.run_table(request.env, uid, board_cfg, item_cfg, date_from, date_to)
            return {"key": item_cfg.key, "name": item_cfg.name, "type": "table",
                    "info": info, "recordModel": item_cfg.record_model,
                    "columns": [{"field": c.field, "label": c.label, "numeric": c.numeric}
                                for c in item_cfg.table_columns],
                    "rows": rows}
        raise ValueError(f"Unknown item type {item_cfg.type!r}")


class PbiServiceDashboardController(PbiDashboardBoardEngineMixin, http.Controller):

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
