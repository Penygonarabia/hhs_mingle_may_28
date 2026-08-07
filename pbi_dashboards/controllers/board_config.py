# -*- coding: utf-8 -*-
"""Generic board/chart-item configuration dataclasses shared by all PBI
dashboard sub-modules (pbi_service_dashboards, pbi_contract_dashboards,
pbi_promoter_dashboards).

One ``BoardConfig`` per dashboard, one ``ChartItemConfig`` per chart/KPI
tile — a single generic SQL engine (board_sql.py) and controller mixin
(board_engine.py) render every board from this data, so adding a new
dashboard sub-module is "add a BoardConfig entry", not "write a new
controller/JS/XML/CSS file set".

Domain operators are deliberately restricted to the ones actually used
across all source boards' ``ks_domain``/``ks_domain_2`` fields: ``=``,
``!=``, ``in``, ``not in``. The literal value ``"%UID"`` means "substitute
the current user's id", matching ks_dashboard_ninja's own convention.
"""
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

DomainTuple = Tuple[str, str, Any]


# Nominal working hours in one month — the denominator of the technician
# utilization KPI ("Utilization (%) = ((Labor Hours + Travel Hours) / 176)
# * 100"). Scaled by the number of months the viewer's date filter spans
# (see board_engine.py's _period_months), so "This Year" divides by
# 176 * 12 rather than reporting a ~1200% utilization.
MONTHLY_WORKING_HOURS = 176.0


@dataclass
class MeasureConfig:
    field: str
    # 'sum' | 'avg' | 'count' — or 'expr', for a measure that is not a
    # single aggregate over one column (e.g. utilization, a RATIO of two
    # sums against a period-scaled constant). With agg='expr', `expr`
    # carries the SQL and `field` is only a naming hint — it drives the
    # client-side value format (*_hours renders H:MM, *_pct renders "96.59%"),
    # so it should still end in the right suffix even though no such column exists.
    agg: str = "sum"
    # SQL aggregate expression, used when agg == 'expr'. May contain the
    # placeholder {period_months}, substituted with the number of months
    # the current date filter spans.
    expr: Optional[str] = None


@dataclass
class GroupByConfig:
    field: str
    interval: Optional[str] = None  # None | 'week' | 'month_year' (datetime fields only)


@dataclass
class DrillStep:
    field: str
    label: str
    # None | 'week' | 'month_year' (datetime fields only) — same vocabulary
    # as GroupByConfig.interval, needed when a drill step (not just the
    # top-level groupby) lands on a date field, e.g. Contract Analysis's
    # Region -> City -> Salesman -> Month chain.
    interval: Optional[str] = None


@dataclass
class TableColumnConfig:
    """One column of a 'table' item — a flat, ungrouped row listing (e.g.
    Contract Analysis's "Visits Comparison" list-view mirror). field is
    resolved the same way a bar/pie groupby label is (board_sql.py's
    _groupby_sql): an id-lookup field renders its display name, a plain
    numeric/text field passes through unchanged."""
    field: str
    label: str
    numeric: bool = False


@dataclass
class ChartItemConfig:
    key: str
    name: str
    type: str  # 'kpi_single' | 'kpi_dual' | 'bar' | 'pie' | 'table'
    source: str  # 'jobcards' | 'message_log' | 'usergroup' | 'contracts' | ...
    domain: List[DomainTuple] = field(default_factory=list)
    domain_2: Optional[List[DomainTuple]] = None  # kpi_dual only
    measure: Optional[MeasureConfig] = None  # None => count()
    measure_2: Optional[MeasureConfig] = None  # kpi_dual only, OR a 2nd bar series (bar only)
    series_labels: Optional[Tuple[str, str]] = None  # legend labels for a measure_2 bar item
    groupby: Optional[GroupByConfig] = None  # bar/pie only
    sort: Optional[Tuple[str, str]] = None  # (field, 'ASC'|'DESC'); default: value DESC
    drill: List[DrillStep] = field(default_factory=list)
    record_model: str = "project.task"  # terminal drill target
    # Max rows/categories returned by a bar/pie breakdown level or a table
    # item — most boards keep the shared default (15); a few need their own cap.
    limit: int = 15
    table_columns: List[TableColumnConfig] = field(default_factory=list)  # 'table' type only
    info: Optional[str] = None


@dataclass
class BoardConfig:
    key: str
    title: str
    sequence: int
    scope: List[DomainTuple] = field(default_factory=list)  # ANDed onto every item's own domain
    role_scope: Optional[str] = None  # None | 'Coordinator' | 'Parts' | 'Call Center' | 'Technician'
    own_records_only: bool = False  # True for the per-logged-in-user boards
    # True on boards that carry a region custom filter — the controller ANDs
    # an extra ("work_center_group_id", "=", "@region:<name>") clause onto
    # board.scope for the request, picked from a region dropdown.
    region_filterable: bool = False
    items: List[ChartItemConfig] = field(default_factory=list)
