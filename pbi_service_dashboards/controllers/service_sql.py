# -*- coding: utf-8 -*-
"""Shim — re-exports every symbol from pbi_dashboards.controllers.board_sql
so that existing code in service_main.py (``from . import service_sql`` /
``service_sql.run_kpi(...)``) continues to work unchanged, and external
callers that still import this module by its old path (e.g. old cached
.pyc files, third-party code) do not break.

The real implementation now lives in pbi_dashboards/controllers/board_sql.py,
which is the shared base module's generic SQL engine.
"""
from odoo.addons.pbi_dashboards.controllers.board_sql import *  # noqa: F401,F403
from odoo.addons.pbi_dashboards.controllers.board_sql import (
    ParamBinder,
    STATUS_ALIASES,
    JOBCARDS_FIELD_MAP,
    USERGROUP_FIELD_MAP,
    MESSAGE_LOG_FIELD_MAP,
    PROMOTER_SHOWROOMS_FIELD_MAP,
    PROMOTER_SALES_FIELD_MAP,
    SALES_COMPARISON_FIELD_MAP,
    CONTRACTS_FIELD_MAP,
    get_user_role_codes,
    get_user_work_location_ids,
    region_id_by_name,
    compile_domain,
    run_kpi,
    run_breakdown,
    run_table,
    run_terminal_domain,
)

try:
    from odoo.addons.pbi_dashboards.controllers.board_sql import run_chart_detail
except ImportError:
    # A pbi_dashboards that predates the Formula & Details engine. The
    # controller degrades to a clear "update the base module" message
    # rather than a 500.
    run_chart_detail = None

try:
    from odoo.addons.pbi_dashboards.controllers.board_sql import run_labor_hours_detail
except ImportError:
    run_labor_hours_detail = None

