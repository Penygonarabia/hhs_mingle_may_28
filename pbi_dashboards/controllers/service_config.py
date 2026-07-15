# -*- coding: utf-8 -*-
"""Declarative board/chart-item configuration for "PBI Dashboards >
Service Dashboards" — the direct-table replicas of the 15
``service_dashboards_ct`` ``ks_dashboard_ninja`` boards (see that module's
``data/legacy_service_boards.xml`` and ``data/service_user_boards.xml``).

One ``BoardConfig`` per dashboard, one ``ChartItemConfig`` per chart/KPI
tile — a single generic controller (``service_main.py``) and a single
generic OWL component (``service_dashboard.js``) render every board from
this data, so adding a new dashboard is "add a BoardConfig entry", not
"write a new controller/JS/XML/CSS file set".

Domain operators are deliberately restricted to the ones actually used
anywhere across all 15 source boards' ``ks_domain``/``ks_domain_2``
fields: ``=``, ``!=``, ``in``, ``not in``. The literal value ``"%UID"``
means "substitute the current user's id" (used by the 4 "_users" boards),
matching ks_dashboard_ninja's own domain-substitution convention.
"""
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

DomainTuple = Tuple[str, str, Any]


@dataclass
class MeasureConfig:
    field: str
    agg: str = "sum"  # 'sum' | 'avg' | 'count'


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
    # Region -> City -> Salesman -> Month chain (see contract_config.py).
    interval: Optional[str] = None


@dataclass
class TableColumnConfig:
    """One column of a 'table' item — a flat, ungrouped row listing (e.g.
    Contract Analysis's "Visits Comparison" list-view mirror). field is
    resolved the SAME way a bar/pie groupby label is (service_sql.py's
    _groupby_sql): an id-lookup field (region/city/salesman/customer)
    renders its display name, a plain numeric/text field passes through
    unchanged."""
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
    # item — most boards keep the shared default (15); a few (e.g. Contract
    # Analysis's per-contract "top 20" bar, its 50-row visits table) need
    # their own cap, matching the source's own ks_record_data_limit.
    limit: int = 15
    table_columns: List[TableColumnConfig] = field(default_factory=list)  # 'table' type only


@dataclass
class BoardConfig:
    key: str
    title: str
    sequence: int
    scope: List[DomainTuple] = field(default_factory=list)  # ANDed onto every item's own domain
    role_scope: Optional[str] = None  # None | 'Coordinator' | 'Parts' | 'Call Center' | 'Technician'
    own_records_only: bool = False  # True for the 4 "_users" boards
    # True on exactly the 4 source boards that carry a ks_dashboard_ninja.board_custom_filters
    # "Regions" filter (on work_center_group_id): CRD, Parts, Technician Analysis, Sales & Cost
    # Analysis — the boards with no region already baked into their scope (unlike C/E/W) and no
    # per-user work-location scope (unlike UWC). When set, the controller ANDs an extra
    # ("work_center_group_id", "=", "@region:<name>") clause onto board.scope for the request,
    # picked by the viewer from a region dropdown (default: all regions, no extra clause).
    region_filterable: bool = False
    items: List[ChartItemConfig] = field(default_factory=list)


BOARDS: dict = {
    "service_analysis": BoardConfig(
        key="service_analysis",
        title="Service Analysis",
        sequence=10,
        items=[
            # Order matches the source's actual on-screen grid position
            # (service_dashboards_ct/data/service_dashboard_layout.xml's
            # grid_corners, sorted by y then x) — NOT the XML declaration
            # order, which the item records happen to appear in but which
            # ks_dashboard_ninja ignores for layout purposes.
            ChartItemConfig(
                key="total_closed_job_cards", name="Total / Closed Job Cards",
                type="kpi_dual", source="jobcards",
                domain_2=[("job_card_status", "=", "Closed")],
            ),
            ChartItemConfig(
                key="total_service_revenue", name="Total service Revenue",
                type="kpi_single", source="jobcards",
                measure=MeasureConfig("total_revenue", "sum"),
            ),
            ChartItemConfig(
                key="labor_revenue", name="Labor Revenue",
                type="kpi_single", source="jobcards",
                measure=MeasureConfig("labour_revenue", "sum"),
            ),
            ChartItemConfig(
                key="spare_parts_revenue", name="Spare Parts Revenue",
                type="kpi_single", source="jobcards",
                measure=MeasureConfig("parts_revenue", "sum"),
            ),
            ChartItemConfig(
                key="spare_parts_warranty", name="Spare Parts Warranty",
                type="kpi_single", source="jobcards",
                measure=MeasureConfig("warranty_spareparts_revenue", "sum"),
            ),
            ChartItemConfig(
                key="avg_rtat", name="AVG RTAT",
                type="kpi_single", source="jobcards",
                domain=[("job_card_status", "in", ["Closed"])],
                measure=MeasureConfig("rtat_hours", "avg"),
            ),
            ChartItemConfig(
                key="month_wise_jobs_count", name="Month wise - Jobs Count",
                type="bar", source="jobcards",
                domain=[("job_card_status", "=", "Closed")],
                groupby=GroupByConfig("service_created_datetime", interval="month_year"),
                drill=[DrillStep("work_center_id", "Work Center")],
            ),
            ChartItemConfig(
                # Plain week-bucketed bar (ks_chart_date_groupby='week' on
                # service_created_datetime, confirmed via the live
                # ks_dashboard_ninja item's own stored fields, not the dead
                # ks_custom_query text). No domain in the source — shows
                # every status per week; drilling into a bar breaks it down
                # by action_status first, then region.
                key="jobcards_status_weekly", name="Job Cards - Status analysis on weekly basis",
                type="bar", source="jobcards",
                groupby=GroupByConfig("service_created_datetime", interval="week"),
                drill=[DrillStep("action_status", "Status"), DrillStep("work_center_id", "Work Center")],
            ),
            ChartItemConfig(
                key="jobcards_not_closed_status_weekly", name="Job Cards - Not Closed Status analysis on weekly basis",
                type="bar", source="jobcards",
                domain=[("action_status", "in", ["Not Closed"])],
                groupby=GroupByConfig("service_created_datetime", interval="week"),
                drill=[DrillStep("work_center_id", "Work Center")],
            ),
            ChartItemConfig(
                key="job_status_wise_count_1", name="Job Status Wise - Count",
                type="bar", source="jobcards",
                groupby=GroupByConfig("action_status"),
                drill=[DrillStep("work_center_id", "Work Center")],
            ),
            ChartItemConfig(
                key="job_status_wise_count_2", name="Job Status Wise - Count",
                type="bar", source="jobcards",
                domain=[("job_card_status", "not in", ["Closed", "Cancelled"])],
                groupby=GroupByConfig("job_card_status"),
                drill=[DrillStep("work_center_id", "Work Center")],
            ),
            ChartItemConfig(
                key="warranty_sts_region_jobs_count", name="Warranty Sts & Region - Jobs Count",
                type="bar", source="jobcards",
                domain=[("job_card_status", "=", "Closed")],
                groupby=GroupByConfig("service_warranty_id"),
                drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
            ),
            ChartItemConfig(
                key="warranty_status_jobs_pct", name="Warranty Status - Jobs (%)",
                type="pie", source="jobcards",
                domain=[("job_card_status", "in", ["Closed"])],
                groupby=GroupByConfig("service_warranty_id"),
                drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
            ),
            ChartItemConfig(
                key="region_wise_rtat_avg", name="Region Wise - RTAT (Avg)",
                type="bar", source="jobcards",
                domain=[("job_card_status", "in", ["Closed"])],
                measure=MeasureConfig("rtat_hours", "avg"),
                groupby=GroupByConfig("work_center_group_id"),
                sort=("value", "DESC"),
                drill=[DrillStep("work_center_id", "Work Center")],
            ),
            ChartItemConfig(
                key="region_wise_rtat_avg_pct", name="Region Wise - RTAT (Avg %)",
                type="pie", source="jobcards",
                domain=[("job_card_status", "in", ["Closed"])],
                measure=MeasureConfig("rtat_hours", "avg"),
                groupby=GroupByConfig("work_center_group_id"),
                sort=("value", "ASC"),
                drill=[DrillStep("work_center_id", "Work Center")],
            ),
            ChartItemConfig(
                key="region_wise_jobs_count", name="Region Wise - Jobs Count",
                type="bar", source="jobcards",
                domain=[("job_card_status", "=", "Closed")],
                groupby=GroupByConfig("work_center_group_id"),
                drill=[DrillStep("work_center_id", "Work Center")],
            ),
            ChartItemConfig(
                key="region_wise_jobs_pct", name="Region Wise - Jobs (%)",
                type="pie", source="jobcards",
                domain=[("job_card_status", "=", "Closed")],
                groupby=GroupByConfig("work_center_group_id"),
                drill=[DrillStep("work_center_id", "Work Center")],
            ),
        ],
    ),
}


def _region_board(key, title, sequence, region_name):
    """Service Analysis (C)/(E)/(W) share one 12-item chart shape, differing
    only by which region their board.scope filters to — see
    legacy_board_c/e/w in service_dashboards_ct/data/legacy_service_boards.xml,
    which are byte-identical except for the hardcoded
    work_center_group_id (7/6/5 there; resolved by NAME here instead).
    One item ("Warranty Sts & Region - Jobs Count") omits the region filter
    from its own ks_domain in the source, unlike every sibling item on the
    same board — treated here as a copy/paste artifact of the source
    (every other item on this board *does* filter by region, and the chart
    only makes sense scoped to one region on a region-specific board), so
    board.scope is applied uniformly to every item instead of literally
    reproducing that one omission.
    """
    scope = [("work_center_group_id", "=", f"@region:{region_name}")]
    return BoardConfig(
        key=key, title=title, sequence=sequence, scope=scope,
        items=[
            # Order matches the source's actual on-screen grid position
            # (service_dashboard_layout.xml grid_corners, sorted by y then
            # x), not XML declaration order.
            ChartItemConfig(
                key="total_closed_job_cards", name="Total / Closed Job Cards",
                type="kpi_dual", source="jobcards",
                domain_2=[("job_card_status", "=", "Closed")],
            ),
            ChartItemConfig(
                key="total_service_revenue", name="Total service Revenue",
                type="kpi_single", source="jobcards",
                measure=MeasureConfig("total_revenue", "sum"),
            ),
            ChartItemConfig(
                key="labor_revenue", name="Labor Revenue",
                type="kpi_single", source="jobcards",
                measure=MeasureConfig("labour_revenue", "sum"),
            ),
            ChartItemConfig(
                key="spare_parts_revenue", name="Spare Parts Revenue",
                type="kpi_single", source="jobcards",
                measure=MeasureConfig("parts_revenue", "sum"),
            ),
            ChartItemConfig(
                key="spare_parts_warranty", name="Spare Parts Warranty",
                type="kpi_single", source="jobcards",
                measure=MeasureConfig("warranty_spareparts_revenue", "sum"),
            ),
            ChartItemConfig(
                key="avg_rtat", name="AVG RTAT",
                type="kpi_single", source="jobcards",
                domain=[("job_card_status", "in", ["Closed"])],
                measure=MeasureConfig("rtat_hours", "avg"),
            ),
            ChartItemConfig(
                key="job_cards_month_wise", name="Job Cards - Month Wise",
                type="bar", source="jobcards",
                domain=[("job_card_status", "=", "Closed")],
                groupby=GroupByConfig("service_created_datetime", interval="month_year"),
                drill=[DrillStep("work_center_id", "Work Center")],
            ),
            ChartItemConfig(
                key="jobcards_status_weekly", name="Job Cards - Status analysis on weekly basis",
                type="bar", source="jobcards",
                groupby=GroupByConfig("service_created_datetime", interval="week"),
                drill=[DrillStep("action_status", "Status"), DrillStep("work_center_id", "Work Center")],
            ),
            ChartItemConfig(
                # Appended separately at the end of legacy_service_boards.xml
                # ("New items for C, E, W boards") rather than inline with
                # this board's other items — a later addition, not present
                # on the UWC/JCs/main boards' own weekly-buckets pair.
                key="jobcards_not_closed_status_weekly", name="Job Cards - Not Closed Status analysis on weekly basis",
                type="bar", source="jobcards",
                domain=[("action_status", "in", ["Not Closed"])],
                groupby=GroupByConfig("service_created_datetime", interval="week"),
                drill=[DrillStep("work_center_id", "Work Center")],
            ),
            ChartItemConfig(
                key="job_status_wise_closed_cancelled", name="Job Cards - Status Wise (Closed & Cancelled)",
                type="bar", source="jobcards",
                groupby=GroupByConfig("action_status"),
                drill=[DrillStep("work_center_id", "Work Center")],
            ),
            ChartItemConfig(
                key="job_status_wise_except_closed_cancelled", name="Job Cards - Status Wise (Except Closed & Cancelled)",
                type="bar", source="jobcards",
                domain=[("job_card_status", "not in", ["Closed", "Cancelled"])],
                groupby=GroupByConfig("job_card_status"),
                drill=[DrillStep("work_center_id", "Work Center")],
            ),
            ChartItemConfig(
                key="warranty_sts_region_jobs_count", name="Warranty Sts & Region - Jobs Count",
                type="bar", source="jobcards",
                domain=[("job_card_status", "=", "Closed")],
                groupby=GroupByConfig("service_warranty_id"),
                drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
            ),
            ChartItemConfig(
                key="job_cards_warranty_status_pct", name="Job Cards - Warranty Status Wise (%)",
                type="pie", source="jobcards",
                domain=[("job_card_status", "=", "Closed")],
                groupby=GroupByConfig("service_warranty_id"),
                drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
            ),
        ],
    )


BOARDS["service_analysis_c"] = _region_board("service_analysis_c", "Service Analysis (C)", 20, "Central Region")
BOARDS["service_analysis_e"] = _region_board("service_analysis_e", "Service Analysis (E)", 30, "Eastern Region")
BOARDS["service_analysis_w"] = _region_board("service_analysis_w", "Service Analysis (W)", 40, "Western Region")


BOARDS["service_analysis_uwc"] = BoardConfig(
    key="service_analysis_uwc", title="Service Analysis (UWC)", sequence=50,
    scope=[("is_user_work_location", "=", True)],
    items=[
        # Order matches the source's actual on-screen grid position, not
        # XML declaration order.
        ChartItemConfig(
            key="total_closed_job_cards", name="Total / Closed Job Cards",
            type="kpi_dual", source="jobcards",
            domain_2=[("job_card_status", "=", "Closed")],
        ),
        ChartItemConfig(
            key="total_service_revenue", name="Total service Revenue",
            type="kpi_single", source="jobcards",
            measure=MeasureConfig("total_revenue", "sum"),
        ),
        ChartItemConfig(
            key="labor_revenue", name="Labor Revenue",
            type="kpi_single", source="jobcards",
            measure=MeasureConfig("labour_revenue", "sum"),
        ),
        ChartItemConfig(
            key="spare_parts_revenue", name="Spare Parts Revenue",
            type="kpi_single", source="jobcards",
            measure=MeasureConfig("parts_revenue", "sum"),
        ),
        ChartItemConfig(
            key="spare_parts_warranty", name="Spare Parts Warranty",
            type="kpi_single", source="jobcards",
            measure=MeasureConfig("warranty_spareparts_revenue", "sum"),
        ),
        ChartItemConfig(
            key="avg_rtat", name="AVG RTAT",
            type="kpi_single", source="jobcards",
            domain=[("job_card_status", "=", "Closed")],
            measure=MeasureConfig("rtat_hours", "avg"),
        ),
        ChartItemConfig(
            key="job_cards_month_wise", name="Job Cards - Month Wise",
            type="bar", source="jobcards",
            domain=[("job_card_status", "=", "Closed")],
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="jobcards_status_weekly", name="Job Cards - Status analysis on weekly basis",
            type="bar", source="jobcards",
            groupby=GroupByConfig("service_created_datetime", interval="week"),
            drill=[DrillStep("action_status", "Status"), DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="job_cards_default_work_centre_wise", name="Job Cards - Default Work Centre Wise",
            type="bar", source="jobcards",
            domain=[("job_card_status", "=", "Closed")],
            groupby=GroupByConfig("default_work_location"),
            drill=[DrillStep("work_center_group_id", "Region")],
        ),
        ChartItemConfig(
            key="job_status_wise_closed_cancelled", name="Job Cards - Status Wise (Closed & Cancelled)",
            type="bar", source="jobcards",
            groupby=GroupByConfig("action_status"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="job_status_wise_except_closed_cancelled", name="Job Cards - Status Wise (Except Closed & Cancelled)",
            type="bar", source="jobcards",
            domain=[("job_card_status", "not in", ["Closed", "Cancelled"])],
            groupby=GroupByConfig("job_card_status"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="warranty_sts_region_jobs_count", name="Warranty Sts & Region - Jobs Count",
            type="bar", source="jobcards",
            domain=[("job_card_status", "=", "Closed")],
            groupby=GroupByConfig("service_warranty_id"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="job_cards_warranty_wise_pct", name="Job Cards - Warranty Wise (%)",
            type="pie", source="jobcards",
            domain=[("job_card_status", "=", "Closed")],
            groupby=GroupByConfig("service_warranty_id"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
        ),
    ],
)


BOARDS["service_analysis_jcs"] = BoardConfig(
    key="service_analysis_jcs", title="Service Analysis (JCs)", sequence=60,
    items=[
        ChartItemConfig(
            key="jobs_count_overall", name="Jobs Count - Overall",
            type="kpi_single", source="jobcards",
        ),
        ChartItemConfig(
            key="job_cards_overall_closed", name="Job Cards - Overall Closed",
            type="kpi_single", source="jobcards",
            domain=[("action_status", "in", ["Closed"])],
        ),
        ChartItemConfig(
            key="job_cards_overall_cancelled", name="Job Cards - Overall Cancelled",
            type="kpi_single", source="jobcards",
            domain=[("action_status", "in", ["Cancelled"])],
        ),
        ChartItemConfig(
            key="job_cards_overall_not_closed", name="Job Cards - Overall Not Closed",
            type="kpi_single", source="jobcards",
            domain=[("action_status", "in", ["Not Closed"])],
        ),
        ChartItemConfig(
            key="jobcards_status_weekly", name="Job Cards - Status analysis on weekly basis",
            type="bar", source="jobcards",
            domain=[("job_card_status", "=", "Closed")],
            groupby=GroupByConfig("service_created_datetime", interval="week"),
            drill=[DrillStep("work_center_group_id", "Region")],
        ),
    ],
)


BOARDS["sales_cost_analysis"] = BoardConfig(
    key="sales_cost_analysis", title="Sales & Cost Analysis", sequence=110,
    region_filterable=True,
    items=[
        # Order matches the source's actual on-screen grid position, not
        # XML declaration order.
        ChartItemConfig(
            key="total_closed_job_cards", name="Total / Closed Job Cards",
            type="kpi_dual", source="jobcards",
            domain_2=[("job_card_status", "=", "Closed")],
        ),
        ChartItemConfig(
            key="total_service_revenue", name="Total service Revenue",
            type="kpi_single", source="jobcards",
            measure=MeasureConfig("total_revenue", "sum"),
        ),
        ChartItemConfig(
            key="labor_revenue", name="Labor Revenue",
            type="kpi_single", source="jobcards",
            measure=MeasureConfig("labour_revenue", "sum"),
        ),
        ChartItemConfig(
            key="spare_parts_revenue", name="Spare Parts Revenue",
            type="kpi_single", source="jobcards",
            measure=MeasureConfig("parts_revenue", "sum"),
        ),
        ChartItemConfig(
            key="spare_parts_warranty", name="Spare Parts Warranty",
            type="kpi_single", source="jobcards",
            measure=MeasureConfig("warranty_spareparts_revenue", "sum"),
        ),
        ChartItemConfig(
            key="avg_rtat", name="AVG RTAT",
            type="kpi_single", source="jobcards",
            domain=[("job_card_status", "in", ["Closed"])],
            measure=MeasureConfig("rtat_hours", "avg"),
        ),
        ChartItemConfig(
            key="total_service_revenue_month_wise", name="Total Service Revenue - Month Wise",
            type="bar", source="jobcards",
            measure=MeasureConfig("total_revenue", "sum"),
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="total_service_revenue_month_wise_pct", name="Total Service Revenue - Month Wise (%)",
            type="pie", source="jobcards",
            measure=MeasureConfig("total_revenue", "sum"),
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="total_service_revenue_region_wise", name="Total Service Revenue - Region Wise",
            type="bar", source="jobcards",
            measure=MeasureConfig("total_revenue", "sum"),
            groupby=GroupByConfig("work_center_group_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="total_service_revenue_region_wise_pct", name="Total Service Revenue - Region Wise (%)",
            type="pie", source="jobcards",
            measure=MeasureConfig("total_revenue", "sum"),
            groupby=GroupByConfig("work_center_group_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            # Source names this "Labour Revenue - Region Wise" but its own
            # ks_chart_measure_field points at total_revenue, not
            # labour_revenue — a copy/paste artifact (its "(%)" sibling
            # below correctly uses labour_revenue). Using labour_revenue
            # here to match both this item's own name and its counterpart.
            key="labour_revenue_region_wise", name="Labour Revenue - Region Wise",
            type="bar", source="jobcards",
            measure=MeasureConfig("labour_revenue", "sum"),
            groupby=GroupByConfig("work_center_group_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="labour_revenue_region_wise_pct", name="Labour Revenue - Region Wise (%)",
            type="pie", source="jobcards",
            measure=MeasureConfig("labour_revenue", "sum"),
            groupby=GroupByConfig("work_center_group_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="spare_parts_warranty_revenue_region_wise", name="Spare Parts Warranty Revenue - Region Wise",
            type="bar", source="jobcards",
            measure=MeasureConfig("warranty_spareparts_revenue", "sum"),
            groupby=GroupByConfig("work_center_group_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="spare_parts_warranty_revenue_region_wise_pct", name="Spare Parts Warranty Revenue - Region Wise (%)",
            type="pie", source="jobcards",
            measure=MeasureConfig("warranty_spareparts_revenue", "sum"),
            groupby=GroupByConfig("work_center_group_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="spare_parts_revenue_region_wise", name="Spare Parts Revenue - Region Wise",
            type="bar", source="jobcards",
            measure=MeasureConfig("parts_revenue", "sum"),
            groupby=GroupByConfig("work_center_group_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="spare_parts_revenue_region_wise_pct", name="Spare Parts Revenue - Region Wise (%)",
            type="pie", source="jobcards",
            measure=MeasureConfig("parts_revenue", "sum"),
            groupby=GroupByConfig("work_center_group_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
    ],
)


BOARDS["service_analysis_cc"] = BoardConfig(
    key="service_analysis_cc", title="Service Analysis (CC)", sequence=70,
    items=[
        ChartItemConfig(
            key="total_closed_job_cards", name="Total / Closed Job Cards",
            type="kpi_dual", source="usergroup",
            domain=[("user_group", "=", "call-center")],
            # Source ks_domain_2 says job_card_status="Closed", but that
            # field doesn't exist on usergroup (it's a jobcards-vocabulary
            # name copy/pasted onto this item) — usergroup's own status
            # field is service_request_state, which does have a "Closed"
            # value, so that's what "Closed" means here.
            domain_2=[("service_request_state", "=", "Closed"), ("user_group", "=", "call-center")],
        ),
        ChartItemConfig(
            key="total_job_cards_month_wise", name="Total Job Cards - Month wise",
            type="bar", source="usergroup",
            domain=[("user_group", "=", "call-center"), ("work_center_group_id", "!=", False)],
            groupby=GroupByConfig("request_date", interval="month_year"),
            drill=[DrillStep("work_center_group_id", "Region")],
            record_model="machine.repair.support",
        ),
        ChartItemConfig(
            key="total_job_cards_user_wise", name="Total Job Cards - User wise",
            type="bar", source="usergroup",
            domain=[("user_group", "=", "call-center")],
            groupby=GroupByConfig("user_id"),
            drill=[DrillStep("work_center_group_id", "Region")],
            record_model="machine.repair.support",
        ),
    ],
)


BOARDS["service_analysis_crd"] = BoardConfig(
    key="service_analysis_crd", title="Service Analysis (CRD)", sequence=80,
    role_scope="Coordinator", region_filterable=True,
    items=[
        ChartItemConfig(
            key="total_job_cards_scheduled", name="Total Job Cards - Scheduled",
            type="kpi_single", source="jobcards",
            domain=[("job_card_status", "=", "Scheduled"), ("is_user_work_location", "=", True)],
        ),
        ChartItemConfig(
            key="total_job_cards_closed", name="Total Job Cards - Closed",
            type="kpi_single", source="jobcards",
            domain=[("job_card_status", "=", "Closed"), ("is_user_work_location", "=", True)],
        ),
        ChartItemConfig(
            key="total_scheduled_job_cards_month_wise", name="Total Scheduled Job Cards - Month wise",
            type="bar", source="jobcards",
            domain=[("is_user_work_location", "=", True), ("job_card_status", "=", "Scheduled")],
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="total_closed_job_cards_month_wise", name="Total Closed Job Cards - Month wise",
            type="bar", source="jobcards",
            domain=[("is_user_work_location", "=", True), ("job_card_status", "=", "Closed")],
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            # Source ks_domain says user_role in [7] (a dashboard.user.rights
            # numeric id with no live table on this DB — see service_sql.py's
            # message_log CTE docstring) — this board's own role is
            # Coordinator, so that's the role this chart is scoped to.
            key="job_cards_users_wise", name="Job Cards - Users wise",
            type="bar", source="message_log",
            domain=[("user_role", "=", "Coordinator")],
            groupby=GroupByConfig("user_id"),
            drill=[DrillStep("region", "Region"), DrillStep("city", "City")],
        ),
    ],
)


BOARDS["service_analysis_parts"] = BoardConfig(
    key="service_analysis_parts", title="Service Analysis (Parts)", sequence=90,
    role_scope="Parts", region_filterable=True,
    items=[
        ChartItemConfig(
            key="cst_need_quote", name="Cst Need Quote",
            type="kpi_single", source="jobcards",
            domain=[("job_card_status", "in", ["Customer Need Quote"])],
            measure=MeasureConfig("parts_revenue", "sum"),
        ),
        ChartItemConfig(
            key="on_hold_sp_req", name="On Hold - SP Req",
            type="kpi_single", source="jobcards",
            domain=[("job_card_status", "=", "On Hold -SP Req")],
        ),
        ChartItemConfig(
            key="job_card_status_wise", name="Job Card - Status wise Analysis",
            type="bar", source="jobcards",
            domain=[("job_card_status", "in", ["On Hold -SP Req", "Customer Need Quote"])],
            groupby=GroupByConfig("job_card_status"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="job_card_user_wise", name="Job Card - User wise Analysis",
            type="bar", source="message_log",
            domain=[("user_role", "=", "Parts")],
            groupby=GroupByConfig("user_id"),
            drill=[DrillStep("city", "City")],
        ),
        ChartItemConfig(
            # Source has no ks_chart_measure_field at all for this item
            # (a gap, not a deliberate count()) — its sibling below
            # ("...from quotation...") explicitly measures onhold_hours,
            # which duplicates that item's own name instead of this one's;
            # matching each item's own NAME, this one should be
            # onhold_hours and the sibling should be cstneedquote_hours
            # (the field that actually means "waiting on a quote").
            key="waiting_onhold_to_parts_ready", name="Waiting period from On hold to parts ready state",
            type="bar", source="jobcards",
            measure=MeasureConfig("onhold_hours", "sum"),
            groupby=GroupByConfig("work_center_group_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="waiting_quotation_to_parts_ready", name="Waiting period from quotation to parts ready state",
            type="bar", source="jobcards",
            domain=[("is_my_user_group", "=", True)],
            measure=MeasureConfig("cstneedquote_hours", "sum"),
            groupby=GroupByConfig("work_center_group_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
    ],
)


BOARDS["technician_analysis"] = BoardConfig(
    key="technician_analysis", title="Technician Analysis", sequence=100,
    role_scope="Technician", region_filterable=True,
    items=[
        ChartItemConfig(
            key="total_closed_job_cards", name="Total / Closed Job Cards",
            type="kpi_dual", source="jobcards",
            domain=[("is_user_work_location", "=", True)],
            domain_2=[("job_card_status", "=", "Closed"), ("is_user_work_location", "=", True)],
        ),
        ChartItemConfig(
            key="scheduled", name="Scheduled",
            type="kpi_single", source="jobcards",
            domain=[("job_card_status", "in", ["Scheduled"]), ("is_user_work_location", "=", True)],
            measure=MeasureConfig("total_revenue", "sum"),
        ),
        ChartItemConfig(
            key="parts_ready_rescheduled", name="Parts Ready & Rescheduled",
            type="kpi_single", source="jobcards",
            domain=[("job_card_status", "in", ["Parts Ready & Reschedule"]), ("is_user_work_location", "=", True)],
            measure=MeasureConfig("parts_revenue", "sum"),
        ),
        ChartItemConfig(
            key="cst_need_quote", name="Cst Need Quote",
            type="kpi_single", source="jobcards",
            domain=[("job_card_status", "in", ["Customer Need Quote"]), ("is_user_work_location", "=", True)],
            measure=MeasureConfig("parts_revenue", "sum"),
        ),
        ChartItemConfig(
            key="on_hold", name="On hold",
            type="kpi_single", source="jobcards",
            domain=[("job_card_status", "in", ["On Hold -SP Req"]), ("is_user_work_location", "=", True)],
            measure=MeasureConfig("warranty_spareparts_revenue", "sum"),
        ),
        ChartItemConfig(
            key="technician_jobs", name="Technician Jobs",
            type="bar", source="jobcards",
            domain=[("technician_id", "!=", False), ("is_user_work_location", "=", True)],
            groupby=GroupByConfig("technician_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="technician_jobs_rtat_avg", name="Technician Jobs - RTAT AVG",
            type="bar", source="jobcards",
            domain=[("technician_id", "!=", False), ("is_user_work_location", "=", True)],
            measure=MeasureConfig("rtat_hours", "avg"),
            groupby=GroupByConfig("technician_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            # Source's ks_chart_measure_field points at rtat_hours, not
            # technician_travel_hours — a copy/paste artifact matching the
            # same pattern already fixed on Sales & Cost Analysis; using
            # technician_travel_hours to match this item's own name.
            key="technician_travel_hours", name="Technician Travel Hours",
            type="bar", source="jobcards",
            domain=[("is_user_work_location", "=", True)],
            measure=MeasureConfig("technician_travel_hours", "sum"),
            groupby=GroupByConfig("work_center_group_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            # A genuinely separate 10th tile (legacy_item_306), distinct
            # from "...Estimated vs Actual Hours" below — same domain/
            # groupby but a single measure (total_worked_hours only). No
            # drill_actions_data.py entry under this exact name; given the
            # dual-measure sibling immediately below (identical domain/
            # groupby) drills on work_center_id, that's used here too
            # rather than leaving this tile unclickable.
            key="employee_performance_actual_hours", name="Employee Performance Analysis - Actual Hours",
            type="bar", source="jobcards",
            domain=[("is_my_user_group", "=", True), ("total_worked_hours", "!=", 0)],
            measure=MeasureConfig("total_worked_hours", "sum"),
            groupby=GroupByConfig("work_center_group_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            # Genuinely a 2-measure chart in source (ks_chart_measure_field
            # carries BOTH expected_completion_hours and total_worked_hours)
            # — rendered here as a dual-series bar (see service_sql.py's
            # run_breakdown measure_2 support / service_dashboard.js
            # renderChart), not force-fit into the single-measure shape
            # every other bar item uses.
            key="employee_performance_estimated_vs_actual",
            name="Employee Performance Analysis - Estimated vs Actual Hours",
            type="bar", source="jobcards",
            domain=[("is_my_user_group", "=", True), ("total_worked_hours", "!=", 0)],
            measure=MeasureConfig("expected_completion_hours", "sum"),
            measure_2=MeasureConfig("total_worked_hours", "sum"),
            series_labels=("Estimated Hours", "Actual Hours"),
            groupby=GroupByConfig("work_center_group_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
    ],
)


# ---------------------------------------------------------------------
# The 4 "_users" boards (service_dashboards_ct/data/service_user_boards.xml)
# — each scoped to the CURRENT logged-in user's own records ("%UID", not a
# region/role_scope filter), a hybrid of message_log (status-count charts,
# the only source that knows which user made which transition) and
# jobcards (hour-sum charts, one row per task so hours aren't multiplied
# across a task's many transition rows).
# ---------------------------------------------------------------------
BOARDS["service_analysis_cc_users"] = BoardConfig(
    key="service_analysis_cc_users", title="Service Analysis - CC Users", sequence=120,
    role_scope="Call Center", own_records_only=True,
    items=[
        ChartItemConfig(
            key="new_tasks", name="New Tasks",
            type="kpi_single", source="message_log",
            domain=[("ptml_final_taskstatus", "in", ["New"]), ("user_id", "in", ["%UID"]),
                    ("user_role", "in", ["Call Center"])],
        ),
        ChartItemConfig(
            key="tasks_month_wise", name="Tasks - Month wise",
            type="bar", source="message_log",
            domain=[("user_id", "in", ["%UID"]), ("user_role", "in", ["Call Center"])],
            groupby=GroupByConfig("task_date", interval="month_year"),
            drill=[DrillStep("ptml_final_taskstatus", "Status"), DrillStep("city", "City")],
        ),
    ],
)


BOARDS["service_analysis_crd_users"] = BoardConfig(
    key="service_analysis_crd_users", title="Service Analysis - CRD Users", sequence=130,
    role_scope="Coordinator", own_records_only=True,
    items=[
        ChartItemConfig(
            key="scheduled_tasks", name="Scheduled Tasks",
            type="kpi_single", source="message_log",
            domain=[("ptml_final_taskstatus", "in", ["Scheduled"]), ("user_id", "in", ["%UID"])],
        ),
        ChartItemConfig(
            key="closed_tasks", name="Closed Tasks",
            type="kpi_single", source="message_log",
            domain=[("ptml_final_taskstatus", "in", ["Closed"]), ("user_id", "in", ["%UID"])],
        ),
        ChartItemConfig(
            key="tasks_month_wise", name="Tasks - Month wise",
            type="bar", source="message_log",
            domain=[("user_id", "in", ["%UID"])],
            groupby=GroupByConfig("task_date", interval="month_year"),
            drill=[DrillStep("ptml_final_taskstatus", "Status"), DrillStep("city", "City")],
        ),
        ChartItemConfig(
            # Source's own drill chain names its 2 steps "user_name" (=
            # this CTE's user_id — the transition author, whose display
            # name is already resolved via _LABEL_LOOKUP) and
            # "status_transition" (a real message_log column).
            key="tasks_user_role_wise", name="Tasks - User Role wise",
            type="bar", source="message_log",
            domain=[("user_role", "!=", False), ("user_id", "in", ["%UID"])],
            groupby=GroupByConfig("user_role"),
            drill=[DrillStep("user_id", "User"), DrillStep("status_transition", "Status Transition")],
        ),
    ],
)


BOARDS["service_analysis_parts_users"] = BoardConfig(
    key="service_analysis_parts_users", title="Service Analysis - Parts Users", sequence=140,
    role_scope="Parts", own_records_only=True,
    items=[
        ChartItemConfig(
            key="onhold_sp_req_tasks", name="On Hold - SP Req Tasks",
            type="kpi_single", source="jobcards",
            domain=[("is_user_work_location", "=", True), ("job_card_status", "in", ["On Hold -SP Req"])],
        ),
        ChartItemConfig(
            key="cust_need_quote_tasks", name="Customer Need Quote Tasks",
            type="kpi_single", source="jobcards",
            domain=[("is_user_work_location", "=", True), ("job_card_status", "in", ["Customer Need Quote"])],
        ),
        ChartItemConfig(
            key="tasks_month_wise", name="Tasks - Month wise",
            type="bar", source="jobcards",
            domain=[("is_user_work_location", "=", True),
                    ("job_card_status", "in", ["On Hold -SP Req", "Customer Need Quote"])],
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="onhold_sp_req_hours", name="On Hold -SP Req Hours",
            type="bar", source="jobcards",
            domain=[("is_user_work_location", "=", True), ("job_card_status", "in", ["On Hold -SP Req"])],
            measure=MeasureConfig("onhold_hours", "sum"),
            groupby=GroupByConfig("work_center_group_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="cust_need_quote_hours", name="Customer Need Quote Hours",
            type="bar", source="jobcards",
            domain=[("is_user_work_location", "=", True), ("job_card_status", "in", ["Customer Need Quote"])],
            measure=MeasureConfig("cstneedquote_hours", "sum"),
            groupby=GroupByConfig("work_center_group_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
    ],
)


BOARDS["service_analysis_technicians"] = BoardConfig(
    key="service_analysis_technicians", title="Service Analysis - Technicians", sequence=150,
    role_scope="Technician", own_records_only=True,
    items=[
        ChartItemConfig(
            key="req_revisit_tasks", name="Req. Revisit Tasks",
            type="kpi_single", source="message_log",
            domain=[("ptml_final_taskstatus", "in", ["Req. Revisit"]), ("user_id", "in", ["%UID"])],
        ),
        ChartItemConfig(
            key="need_reschedule_tasks", name="Need Reschedule Tasks",
            type="kpi_single", source="message_log",
            domain=[("ptml_final_taskstatus", "in", ["Need Reschedule"]), ("user_id", "in", ["%UID"])],
        ),
        ChartItemConfig(
            key="parts_ready_reschedule_tasks", name="Parts Ready & Reschedule Tasks",
            type="kpi_single", source="message_log",
            domain=[("ptml_final_taskstatus", "in", ["Parts Ready & Reschedule"]), ("user_id", "in", ["%UID"])],
        ),
        ChartItemConfig(
            key="rescheduled_tasks", name="Rescheduled Tasks",
            type="kpi_single", source="message_log",
            domain=[("ptml_final_taskstatus", "in", ["Rescheduled"]), ("user_id", "in", ["%UID"])],
        ),
        ChartItemConfig(
            key="tasks_month_wise", name="Tasks - Month wise",
            type="bar", source="message_log",
            domain=[("user_id", "in", ["%UID"])],
            groupby=GroupByConfig("task_date", interval="month_year"),
            drill=[DrillStep("ptml_final_taskstatus", "Status"), DrillStep("city", "City")],
        ),
        ChartItemConfig(
            key="technician_travel_hours", name="Technician Travel Hours",
            type="bar", source="jobcards",
            domain=[("user_id", "in", ["%UID"])],
            measure=MeasureConfig("technician_travel_hours", "sum"),
            groupby=GroupByConfig("work_center_group_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
    ],
)
