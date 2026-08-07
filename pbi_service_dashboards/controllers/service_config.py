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
# Dataclasses live in the shared base module — import them from there so
# contract_config.py and promoter_config.py can import from pbi_dashboards
# without depending on pbi_service_dashboards.
from odoo.addons.pbi_dashboards.controllers.board_config import (
    DomainTuple,
    MONTHLY_WORKING_HOURS,
    MeasureConfig,
    GroupByConfig,
    DrillStep,
    TableColumnConfig,
    ChartItemConfig,
    BoardConfig,
)


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
        # -------------------------------------------------------------
        # The 3 coordinator KPIs. Each is attributed to the user who
        # actually performed the transition (read off the job_state
        # tracking log — see service_sql.py's task_timeline), not to the
        # job card's scheduled_uid/closed_jobcard_user_id columns, which
        # are overwritten on every re-schedule/re-close.
        #
        # "for each coordinator under the area which is handling" needs no
        # extra domain: this board is region_filterable, so the viewer's
        # region dropdown already ANDs work_center_group_id onto every
        # item below.
        #
        # avg() over the rows that HAVE the interval is exactly the spec's
        # "total time / number of such jobs" — the derived hour columns are
        # NULL (not 0) whenever the card never reached the end state, so
        # those rows leave both the numerator and the denominator.
        # -------------------------------------------------------------
        ChartItemConfig(
            key="scheduling_performance", name="Scheduling Performance",
            type="bar", source="jobcards",
            domain=[("scheduled_by_uid", "!=", False)],
            measure=MeasureConfig("scheduling_hours", "avg"),
            groupby=GroupByConfig("scheduled_by_uid"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="job_closing_performance", name="Job Closing Performance",
            type="bar", source="jobcards",
            domain=[("closed_by_uid", "!=", False)],
            measure=MeasureConfig("job_closing_hours", "avg"),
            groupby=GroupByConfig("closed_by_uid"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="total_closed_job_cards_coordinator", name="Total Closed Job Cards",
            type="bar", source="jobcards",
            domain=[("closed_by_uid", "!=", False), ("job_card_status", "=", "Closed")],
            groupby=GroupByConfig("closed_by_uid"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
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
        # -------------------------------------------------------------
        # The 4 spare-parts KPIs, all per Spare Parts Coordinator
        # (parts_handler_uid — the first Parts-group user to act on the
        # request, see service_sql.py's task_timeline; the technician who
        # RAISED the request is not its handler).
        #
        # The three waiting periods are averages over the requests that
        # actually reached the end state — the derived hour columns are
        # NULL, not 0, for the ones still waiting, so a request that has
        # not been handed over yet leaves the average alone instead of
        # counting as "0 hours waited".
        # -------------------------------------------------------------
        ChartItemConfig(
            key="total_spare_part_requests", name="Total Spare Part Requests",
            type="bar", source="jobcards",
            # is_spare_part_request, not job_card_status: the spec counts
            # requests placed On Hold and raised for Customer Need
            # Quotation, which is "ever entered that state", whereas
            # job_card_status is only the state the card is in right now
            # — filtering on it would drop every request the coordinator
            # has already finished handling.
            domain=[("parts_handler_uid", "!=", False),
                    ("is_spare_part_request", "=", True)],
            groupby=GroupByConfig("parts_handler_uid"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            # Was sum(onhold_hours), which measured the WRONG interval:
            # the stored onhold_hours is job_resume_date - job_hold_date,
            # and job_resume_date is written by BOTH "Parts Ready &
            # Reschedule" (122) and "Spare Parts Handover to me" (123) —
            # the handover overwrites the parts-ready timestamp, so the
            # figure silently spanned On Hold -> handover. Now the real
            # On Hold -> Parts Ready interval, from the tracking log.
            key="waiting_onhold_to_parts_ready", name="Average Waiting Period: On Hold to Parts Ready",
            type="bar", source="jobcards",
            domain=[("parts_handler_uid", "!=", False)],
            measure=MeasureConfig("onhold_to_ready_hours", "avg"),
            groupby=GroupByConfig("parts_handler_uid"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            # Not expressible at all before the timeline CTE — both ends
            # of this interval collapse onto job_resume_date on
            # project_task (see the note above).
            key="waiting_parts_ready_to_handover", name="Average Waiting Period: Parts Ready to Hand Over",
            type="bar", source="jobcards",
            domain=[("parts_handler_uid", "!=", False)],
            measure=MeasureConfig("ready_to_handover_hours", "avg"),
            groupby=GroupByConfig("parts_handler_uid"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            # Was sum(cstneedquote_hours) = job_resume_date -
            # cstneedquote_date, i.e. quotation -> job resumed. The
            # requirement is quotation -> "Parts Added Req Service Charge"
            # (131), which writes no datetime on project_task at all, so
            # this too comes from the tracking log.
            key="waiting_quotation_to_parts_ready",
            name="Average Time: Customer Quotation Request to Parts Added & Service Charge Request",
            type="bar", source="jobcards",
            domain=[("parts_handler_uid", "!=", False)],
            measure=MeasureConfig("quote_to_parts_added_hours", "avg"),
            groupby=GroupByConfig("parts_handler_uid"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
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
            # "Display the total number of Closed Job Cards completed by
            # each technician" — the source item counted every job card in
            # any state, so it answered "jobs assigned", not "jobs closed".
            key="technician_jobs", name="Technician Closed Job Cards",
            type="bar", source="jobcards",
            domain=[("technician_id", "!=", False), ("is_user_work_location", "=", True),
                    ("job_card_status", "=", "Closed")],
            groupby=GroupByConfig("technician_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            # Average RTAT over Closed job cards only. rtat_hours is
            # machine_repair_management's own working-hours-aware compute
            # (service_created -> closed, excluding non-working days via
            # the company calendar), and it is left at 0 for cards that
            # were never closed — so without the Closed filter every
            # open card drags the average toward zero.
            key="technician_jobs_rtat_avg", name="Technician Jobs - Average RTAT",
            type="bar", source="jobcards",
            domain=[("technician_id", "!=", False), ("is_user_work_location", "=", True),
                    ("job_card_status", "=", "Closed")],
            measure=MeasureConfig("rtat_hours", "avg"),
            groupby=GroupByConfig("technician_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            # Utilization (%) = ((Labor Hours + Travel Hours) / 176) * 100,
            # per technician. A ratio of two sums against a period-scaled
            # constant, so it cannot be a plain sum/avg measure — see
            # MeasureConfig.agg == 'expr' and service_main.py's
            # _period_months for the {period_months} scaling.
            key="technician_utilization", name="Technician Utilization",
            type="bar", source="jobcards",
            domain=[("technician_id", "!=", False), ("is_user_work_location", "=", True)],
            measure=MeasureConfig(
                "utilization_pct", "expr",
                expr=(
                    "(COALESCE(sum(labor_hours), 0) + COALESCE(sum(travel_time_hours), 0)) "
                    f"/ NULLIF({{period_months}} * {MONTHLY_WORKING_HOURS}, 0) * 100"
                ),
            ),
            groupby=GroupByConfig("technician_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            # The Labor Hours half of the utilization formula, surfaced on
            # its own so the percentage above is auditable: Ready to
            # Invoice - "Technician Reached - Job Started", per technician.
            key="technician_labor_hours", name="Technician Labor Hours",
            type="bar", source="jobcards",
            domain=[("technician_id", "!=", False), ("is_user_work_location", "=", True)],
            measure=MeasureConfig("labor_hours", "sum"),
            groupby=GroupByConfig("technician_id"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            # The Travel Hours half: "Technician Reached" - "Technician
            # Travel Started". Grouped by technician, not by region — the
            # requirement is a per-technician figure, and it has to line up
            # with the utilization bars above to be checkable.
            #
            # (Source's ks_chart_measure_field pointed at rtat_hours, not a
            # travel measure at all — a copy/paste artifact matching the
            # same pattern already fixed on Sales & Cost Analysis.)
            key="technician_travel_hours", name="Technician Travel Hours",
            type="bar", source="jobcards",
            domain=[("technician_id", "!=", False), ("is_user_work_location", "=", True)],
            measure=MeasureConfig("travel_time_hours", "sum"),
            groupby=GroupByConfig("technician_id"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
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
        # -------------------------------------------------------------
        # The personal mirror of Service Analysis (CRD)'s 3 coordinator
        # KPIs — same measures and same transition-author attribution,
        # scoped to the viewer's own transitions and grouped by month so
        # each coordinator sees their own trend.
        # -------------------------------------------------------------
        ChartItemConfig(
            key="my_scheduling_performance", name="My Scheduling Performance",
            type="bar", source="jobcards",
            domain=[("scheduled_by_uid", "in", ["%UID"])],
            measure=MeasureConfig("scheduling_hours", "avg"),
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="my_job_closing_performance", name="My Job Closing Performance",
            type="bar", source="jobcards",
            domain=[("closed_by_uid", "in", ["%UID"])],
            measure=MeasureConfig("job_closing_hours", "avg"),
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="my_closed_job_cards", name="My Closed Job Cards",
            type="bar", source="jobcards",
            domain=[("closed_by_uid", "in", ["%UID"]), ("job_card_status", "=", "Closed")],
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
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
        # -------------------------------------------------------------
        # The personal mirror of Service Analysis (Parts)' 4 KPIs, scoped
        # to the requests this parts coordinator actually handled and
        # grouped by month. The two pre-existing "Hours" items below are
        # re-pointed at the same timeline-derived intervals the team board
        # now uses, so the personal and team figures cannot disagree.
        # -------------------------------------------------------------
        ChartItemConfig(
            key="my_spare_part_requests", name="My Spare Part Requests",
            type="bar", source="jobcards",
            domain=[("parts_handler_uid", "in", ["%UID"]),
                    ("is_spare_part_request", "=", True)],
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="onhold_sp_req_hours", name="Average Waiting Period: On Hold to Parts Ready",
            type="bar", source="jobcards",
            domain=[("parts_handler_uid", "in", ["%UID"])],
            measure=MeasureConfig("onhold_to_ready_hours", "avg"),
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="parts_ready_to_handover_hours", name="Average Waiting Period: Parts Ready to Hand Over",
            type="bar", source="jobcards",
            domain=[("parts_handler_uid", "in", ["%UID"])],
            measure=MeasureConfig("ready_to_handover_hours", "avg"),
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="cust_need_quote_hours",
            name="Average Time: Customer Quotation Request to Parts Added & Service Charge Request",
            type="bar", source="jobcards",
            domain=[("parts_handler_uid", "in", ["%UID"])],
            measure=MeasureConfig("quote_to_parts_added_hours", "avg"),
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
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
        # -------------------------------------------------------------
        # The personal mirror of Technician Analysis's 4 technician KPIs.
        # Scoped on technician_id (the tech who did the work), not on the
        # jobcards CTE's user_id — that column is the work LOCATION's
        # assigned user, so on a one-technician board it is the wrong
        # identity. Grouped by month rather than by technician: a
        # per-technician axis on a single technician's own board is one
        # bar, whereas the trend over the period is the useful reading.
        # -------------------------------------------------------------
        ChartItemConfig(
            key="my_closed_job_cards", name="My Closed Job Cards",
            type="bar", source="jobcards",
            domain=[("technician_id", "in", ["%UID"]), ("job_card_status", "=", "Closed")],
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="my_rtat_avg", name="My Jobs - Average RTAT",
            type="bar", source="jobcards",
            domain=[("technician_id", "in", ["%UID"]), ("job_card_status", "=", "Closed")],
            measure=MeasureConfig("rtat_hours", "avg"),
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="my_utilization", name="My Utilization",
            type="bar", source="jobcards",
            domain=[("technician_id", "in", ["%UID"])],
            # Deliberately NOT {period_months}-scaled, unlike Technician
            # Analysis's utilization bar: each bar here IS one month
            # (groupby month_year), so the denominator is one month's
            # working hours no matter how long the selected range is.
            measure=MeasureConfig(
                "utilization_pct", "expr",
                expr=(
                    "(COALESCE(sum(labor_hours), 0) + COALESCE(sum(travel_time_hours), 0)) "
                    f"/ {MONTHLY_WORKING_HOURS} * 100"
                ),
            ),
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="my_labor_hours", name="My Labor Hours",
            type="bar", source="jobcards",
            domain=[("technician_id", "in", ["%UID"])],
            measure=MeasureConfig("labor_hours", "sum"),
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_id", "Work Center")],
        ),
        ChartItemConfig(
            key="technician_travel_hours", name="Technician Travel Hours",
            type="bar", source="jobcards",
            domain=[("technician_id", "in", ["%UID"])],
            measure=MeasureConfig("travel_time_hours", "sum"),
            groupby=GroupByConfig("service_created_datetime", interval="month_year"),
            drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "Work Center")],
        ),
    ],
)


SCOPE_INFO_DESCRIPTIONS = {
    "service_analysis": "Scope: All company-wide service job cards (project_task) in the selected period.",
    "service_analysis_c": "Scope: Filtered to Central Region (work_center_group_id = 'Central').",
    "service_analysis_e": "Scope: Filtered to Eastern Region (work_center_group_id = 'Eastern').",
    "service_analysis_w": "Scope: Filtered to Western Region (work_center_group_id = 'Western').",
    "service_analysis_uwc": "Scope: Filtered to current user's assigned work center location.",
    "service_analysis_jcs": "Scope: Lifecycle and job card status analysis across work centers.",
    "service_analysis_cc": "Scope: Filtered to Call Center role job cards.",
    "service_analysis_crd": "Scope: Filtered to Coordinator role job cards.",
    "service_analysis_parts": "Scope: Filtered to Parts Coordinator role job cards.",
    "technician_analysis": "Scope: Filtered to Technician role job cards and performance metrics.",
    "sales_cost_analysis": "Scope: Financial breakdown of service revenue vs labor & parts costs.",
    "service_analysis_cc_users": "Scope: Personal dashboard for current Call Center user (user_id = current user).",
    "service_analysis_crd_users": "Scope: Personal dashboard for current Coordinator user (user_id = current user).",
    "service_analysis_parts_users": "Scope: Personal dashboard for current Parts user (user_id = current user).",
    "service_analysis_technicians": "Scope: Personal dashboard for current Technician user (technician_id = current user).",
}

ITEM_INFO_DESCRIPTIONS = {
    # Dual KPIs
    "total_closed_job_cards": "<b>Formula:</b> Total = COUNT(job cards); Closed = COUNT(job cards WHERE state = 'Closed').<br><b>Scope:</b> All job cards created in selected period.",
    "coordinator_job_cards": "<b>Formula:</b> Total = COUNT(coordinator job cards); Closed = COUNT(job cards WHERE state = 'Closed').<br><b>Scope:</b> Job cards assigned to Coordinator role.",
    "parts_job_cards": "<b>Formula:</b> Total = COUNT(parts job cards); Closed = COUNT(job cards WHERE state = 'Closed').<br><b>Scope:</b> Job cards assigned to Parts Coordinator role.",
    "cc_job_cards": "<b>Formula:</b> Total = COUNT(call center job cards); Closed = COUNT(job cards WHERE state = 'Closed').<br><b>Scope:</b> Job cards assigned to Call Center role.",
    "my_job_cards": "<b>Formula:</b> Total = COUNT(user's job cards); Closed = COUNT(job cards WHERE state = 'Closed').<br><b>Scope:</b> Job cards assigned to current user (user_id = %UID).",

    # Single KPIs - Revenue & Costs
    "total_service_revenue": "<b>Formula:</b> SUM(Labor Revenue + Non-Warranty Spare Parts Sales + Warranty Spare Parts Cost).<br><b>Source:</b> Product lines across job cards.",
    "labor_revenue": "<b>Formula:</b> SUM(subtotal of labor/service product lines).<br><b>Source:</b> Billed labor charges on job cards.",
    "spare_parts_revenue": "<b>Formula:</b> SUM(subtotal of non-warranty spare parts product lines).<br><b>Source:</b> Customer-billed spare parts.",
    "spare_parts_warranty": "<b>Formula:</b> SUM(cost price × quantity) for spare parts issued under warranty.<br><b>Source:</b> Cost of parts replaced under warranty.",

    # Single KPIs - Turnaround & Utilization
    "avg_rtat": "<b>Formula:</b> AVG(rtat_hours) for Closed job cards.<br><b>Calculation:</b> (Closed Date − Created Date) in float hours (displayed as H:MM).",
    "my_rtat_avg": "<b>Formula:</b> AVG(rtat_hours) for current technician's Closed job cards.<br><b>Calculation:</b> (Closed Date − Created Date) in float hours (displayed as H:MM).",
    "technician_utilization_pct": "<b>Formula:</b> ((SUM(Labor Hours) + SUM(Travel Hours)) ÷ (176 hrs × Period Months)) × 100.<br><b>Denominator:</b> 176 working hours per technician per month.",
    "my_utilization": "<b>Formula:</b> ((SUM(Labor Hours) + SUM(Travel Hours)) ÷ 176 hrs) × 100.<br><b>Scope:</b> Current technician's monthly working hours.",

    # Single KPIs - Role Specific & Pending
    "total_job_cards_scheduled": "<b>Formula:</b> COUNT(job cards where state = 'Scheduled').<br><b>Scope:</b> Job cards scheduled for service.",
    "total_job_cards_closed": "<b>Formula:</b> COUNT(job cards where state = 'Closed').<br><b>Scope:</b> Completed and closed job cards.",
    "cst_need_quote": "<b>Formula:</b> COUNT(job cards in 'Customer Quotation Request' state).<br><b>Scope:</b> Pending quotation approval.",
    "on_hold_sp_req": "<b>Formula:</b> COUNT(job cards in 'On Hold - SP Required' state).<br><b>Scope:</b> Pending spare parts availability.",
    "total_spare_part_requests": "<b>Formula:</b> COUNT(spare part request lines) for job cards in selected period.",

    # Single KPIs - Turnaround Times
    "avg_wait_on_hold_parts_ready": "<b>Formula:</b> AVG(Hours from 'On Hold - SP Required' to 'Parts Ready').<br><b>Source:</b> State transition timestamp logs.",
    "avg_wait_parts_ready_hand_over": "<b>Formula:</b> AVG(Hours from 'Parts Ready' to 'Handed Over to Technician').<br><b>Source:</b> State transition timestamp logs.",
    "avg_wait_quote_parts_added": "<b>Formula:</b> AVG(Hours from 'Customer Quote Request' to 'Parts Added & Service Charge Request').",

    # Bar / Pie / Breakdown Charts
    "month_wise_jobs_count": "<b>Formula:</b> COUNT(Closed job cards) grouped by created month (YYYY-MM).",
    "total_job_cards_month_wise": "<b>Formula:</b> COUNT(all job cards) grouped by created month (YYYY-MM).",
    "total_scheduled_job_cards_month_wise": "<b>Formula:</b> COUNT(Scheduled job cards) grouped by created month (YYYY-MM).",
    "total_closed_job_cards_month_wise": "<b>Formula:</b> COUNT(Closed job cards) grouped by created month (YYYY-MM).",
    "jobcards_status_weekly": "<b>Formula:</b> COUNT(job cards created) grouped by week and status.",
    "jobcards_not_closed_status_weekly": "<b>Formula:</b> COUNT(job cards WHERE status = 'Not Closed') grouped by week.",
    "job_status_wise_count_1": "<b>Formula:</b> COUNT(job cards) grouped by action status (Closed / Cancelled / Not Closed).",
    "job_status_wise_count_2": "<b>Formula:</b> COUNT(job cards WHERE status NOT IN ('Closed', 'Cancelled')) grouped by detailed job card state.",
    "job_card_status_wise_analysis": "<b>Formula:</b> COUNT(job cards) grouped by job card status.",

    "warranty_sts_region_jobs_count": "<b>Formula:</b> COUNT(Closed job cards) grouped by Warranty Status.",
    "warranty_status_jobs_pct": "<b>Formula:</b> (COUNT(Closed Jobs in Warranty Type) ÷ Total Closed Jobs) × 100.",
    "job_cards_warranty_wise_pct": "<b>Formula:</b> (COUNT(Jobs in Warranty Type) ÷ Total Jobs) × 100.",

    "region_wise_rtat_avg": "<b>Formula:</b> AVG(RTAT hours) for Closed job cards grouped by Region (Work Center Group).",
    "region_wise_rtat_avg_pct": "<b>Formula:</b> (Region Avg RTAT ÷ SUM(All Region Avg RTATs)) × 100.",
    "region_wise_jobs_count": "<b>Formula:</b> COUNT(Closed job cards) grouped by Region.",
    "region_wise_jobs_pct": "<b>Formula:</b> (Region Closed Jobs ÷ Total Closed Jobs) × 100.",

    "job_cards_default_work_centre_wise": "<b>Formula:</b> COUNT(job cards) grouped by Default Work Center Location.",
    "job_cards_status_wise_closed_cancelled": "<b>Formula:</b> COUNT(job cards WHERE status IN ('Closed', 'Cancelled')) grouped by status.",
    "job_cards_status_wise_except_closed_cancelled": "<b>Formula:</b> COUNT(job cards WHERE status NOT IN ('Closed', 'Cancelled')) grouped by status.",

    "total_service_revenue_month_wise": "<b>Formula:</b> SUM(Total Revenue) grouped by created month (YYYY-MM).",
    "total_service_revenue_month_wise_pct": "<b>Formula:</b> (Monthly Revenue ÷ Total Period Revenue) × 100.",
    "total_service_revenue_region_wise": "<b>Formula:</b> SUM(Total Revenue) grouped by Region.",
    "total_service_revenue_region_wise_pct": "<b>Formula:</b> (Region Revenue ÷ Total Revenue) × 100.",

    "labour_revenue_region_wise": "<b>Formula:</b> SUM(Labor Revenue) grouped by Region.",
    "labour_revenue_region_wise_pct": "<b>Formula:</b> (Region Labor Revenue ÷ Total Labor Revenue) × 100.",
    "spare_parts_revenue_region_wise": "<b>Formula:</b> SUM(Parts Revenue) grouped by Region.",
    "spare_parts_revenue_region_wise_pct": "<b>Formula:</b> (Region Parts Revenue ÷ Total Parts Revenue) × 100.",
    "spare_parts_warranty_revenue_region_wise": "<b>Formula:</b> SUM(Warranty Parts Cost) grouped by Region.",
    "spare_parts_warranty_revenue_region_wise_pct": "<b>Formula:</b> (Region Warranty Parts ÷ Total Warranty Parts) × 100.",

    "total_job_cards_user_wise": "<b>Formula:</b> COUNT(job cards) grouped by assigned User / Coordinator.",
    "job_cards_users_wise": "<b>Formula:</b> COUNT(job cards) grouped by assigned User / Coordinator.",
    "job_card_user_wise_analysis": "<b>Formula:</b> COUNT(job cards) grouped by User / Coordinator.",

    "employee_performance_actual_hours": "<b>Formula:</b> Total Worked Hours = SUM(actual labor hours logged on job card work logs) grouped by Region.<br><b>Field:</b> <code>total_worked_hours</code> (timesheet &amp; work log entries).",
    "actual_hours_worked": "<b>Formula:</b> Total Worked Hours = SUM(actual labor hours logged on job card work logs) grouped by Region / Work Center.<br><b>Field:</b> <code>total_worked_hours</code>.",
    "my_closed_job_cards": "<b>Formula:</b> COUNT(Closed job cards) for current technician grouped by created month.",
    "my_labor_hours": "<b>Formula:</b> Labor Hours = SUM(hours elapsed from Technician Reached to Job Completion) for current technician grouped by created month.",
    "technician_travel_hours": "<b>Formula:</b> Travel Hours = SUM(hours elapsed from Travel Started to Technician Reached at site) grouped by Region / Work Center.<br><b>Field:</b> <code>travel_time_hours</code> (travel log timestamps).",

    # Sales & Cost Analysis
    "sales_cost_analysis": "<b>Formula:</b> Revenue = SUM(total_revenue); Cost = SUM(labor_cost + parts_cost); Gross Profit = Revenue − Cost; Margin (%) = (Gross Profit ÷ Revenue) × 100.",
    "estimated_vs_actual_hours": "<b>Formula:</b> Estimated Hours = SUM(assigned completion hours) vs Actual Hours = SUM(actual logged work hours) grouped by Region / Work Center.",
}

FIELD_BUSINESS_DESCRIPTIONS = {
    "total_worked_hours": "actual labor hours logged on job card work logs",
    "labor_hours": "hours elapsed from Technician Reached at site to Job Completion",
    "travel_time_hours": "hours elapsed from Travel Started to Technician Reached at site",
    "technician_travel_hours": "hours elapsed from Travel Started to Technician Reached at site",
    "rtat_hours": "hours elapsed from Service Created Date to Job Completion",
    "total_revenue": "billed labor charges + billed spare parts subtotal",
    "labour_revenue": "billed subtotal of Service & Inspection charges",
    "parts_revenue": "billed subtotal of non-warranty spare parts",
    "warranty_spareparts_revenue": "cost price × quantity of warranty replacement parts",
    "onhold_hours": "hours elapsed while job card was on hold for spare parts",
    "cstneedquote_hours": "hours elapsed while job card was pending customer quotation",
    "onhold_to_ready_hours": "hours elapsed from On Hold - SP Req to Parts Ready",
    "ready_to_handover_hours": "hours elapsed from Parts Ready to Handed Over to Technician",
    "quote_to_parts_added_hours": "hours elapsed from Customer Need Quote to Parts Added",
    "expected_completion_hours": "estimated labor completion hours assigned to job cards",
    "qty": "quantity of spare parts issued on job cards",
}


def resolve_scope_info(board_cfg):
    return SCOPE_INFO_DESCRIPTIONS.get(board_cfg.key, f"Scope: Filtered data for {board_cfg.title}.")


def resolve_item_info(board_cfg, item_cfg):
    if item_cfg.info:
        return item_cfg.info
    if item_cfg.key in ITEM_INFO_DESCRIPTIONS:
        return ITEM_INFO_DESCRIPTIONS[item_cfg.key]

    name = item_cfg.name
    m = item_cfg.measure
    gb = item_cfg.groupby

    field_label = m.field if m else ""
    if m and m.field in FIELD_BUSINESS_DESCRIPTIONS:
        field_label = FIELD_BUSINESS_DESCRIPTIONS[m.field]
    elif m and m.field:
        field_label = m.field.replace("_", " ").title()

    if item_cfg.type in ("kpi_single", "kpi_dual"):
        if m and m.agg == "sum":
            return f"<b>Formula:</b> SUM({field_label}) across job cards in the selected period."
        elif m and m.agg == "avg":
            return f"<b>Formula:</b> AVG({field_label}) across job cards in the selected period."
        elif m and m.agg == "expr":
            return f"<b>Formula:</b> Calculated expression for {name}."
        else:
            return f"<b>Formula:</b> COUNT(job cards) in the selected period."

    if gb:
        gb_label = gb.field.replace("_id", "").replace("_", " ").title()
        if m and m.agg == "sum":
            return f"<b>Formula:</b> SUM({field_label}) grouped by {gb_label}."
        elif m and m.agg == "avg":
            return f"<b>Formula:</b> AVG({field_label}) grouped by {gb_label}."
        else:
            return f"<b>Formula:</b> COUNT(job cards) grouped by {gb_label}."

    return f"<b>Formula:</b> Calculation metrics for {name}."

