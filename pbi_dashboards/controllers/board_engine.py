# -*- coding: utf-8 -*-
"""Generic controller mixin shared by all PBI dashboard sub-module
controllers (PbiServiceDashboardController, PbiContractDashboardController,
PbiPromoterDashboardController).

Deliberately NOT an http.Controller subclass — Odoo's route-registration
scan walks the full MRO of every class it sees that inherits http.Controller,
so a mixin that is itself an http.Controller would re-register every @http.route
method onto each concrete subclass too. Plain class + multiple inheritance in
the concrete controller avoids that duplication exactly.
"""
import calendar
import dataclasses
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request

from . import board_sql
from .access import menu_allowed

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
    """Shared instance methods for every generic-engine dashboard controller.
    Concrete controllers inherit this alongside http.Controller — but NOT
    PbiServiceDashboardController itself (which is already a concrete
    http.Controller), to avoid Odoo re-registering that class's routes.

    Override _resolve_item_info() in concrete controllers that supply
    per-item tooltip/info strings derived from module-specific data."""

    def _has_access(self, board_key):
        return (
            menu_allowed(f"pbi_service_dashboards.menu_pbi_{board_key}")
            or menu_allowed(f"pbi_dashboards.menu_pbi_{board_key}")
        )

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
        working-hours-per-month denominator. "This Month"/"Last Month" give
        exactly 1; "This Year" gives 12. A week-long range still counts as 1
        (never 0) — a partial month is the smallest meaningful unit here."""
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
        """Matches ks_dashboard_ninja's own convention — any *_hours measure
        renders as H:MM, *_amount renders compact ("0.4M"), *_pct renders
        as "96.59%"."""
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

    def _resolve_item_info(self, board_cfg, item_cfg):
        """Return per-item info/tooltip string. Override in concrete
        controllers that supply module-specific info strings (e.g.
        PbiServiceDashboardController overrides this to call
        service_config.resolve_item_info). Returns None by default (no
        tooltip rendered for contract/promoter boards)."""
        return None

    def _item_payload(self, board_cfg, item_cfg, date_from, date_to, uid, period_months=1):
        value_format = self._value_format(item_cfg)
        info = self._resolve_item_info(board_cfg, item_cfg)
        if item_cfg.type in ("kpi_single", "kpi_dual"):
            data = board_sql.run_kpi(request.env, uid, board_cfg, item_cfg, date_from, date_to, period_months)
            return {"key": item_cfg.key, "name": item_cfg.name, "type": item_cfg.type,
                    "info": info, "valueFormat": value_format, **data}
        if item_cfg.type in ("bar", "pie"):
            breakdown = board_sql.run_breakdown(request.env, uid, board_cfg, item_cfg, date_from, date_to, [],
                                                period_months)
            payload = {"key": item_cfg.key, "name": item_cfg.name, "type": item_cfg.type,
                       "info": info, "breakdown": breakdown or [], "level": 0, "valueFormat": value_format}
            if item_cfg.measure_2:
                payload["seriesLabels"] = list(item_cfg.series_labels or ["Series 1", "Series 2"])
            return payload
        if item_cfg.type == "table":
            rows = board_sql.run_table(request.env, uid, board_cfg, item_cfg, date_from, date_to)
            return {"key": item_cfg.key, "name": item_cfg.name, "type": "table",
                    "info": info, "recordModel": item_cfg.record_model,
                    "columns": [{"field": c.field, "label": c.label, "numeric": c.numeric}
                                for c in item_cfg.table_columns],
                    "rows": rows}
        raise ValueError(f"Unknown item type {item_cfg.type!r}")
