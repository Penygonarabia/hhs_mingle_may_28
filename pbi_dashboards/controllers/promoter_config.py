# -*- coding: utf-8 -*-
"""Declarative board/chart-item configuration for "PBI Dashboards >
Promoter Dashboards" — 2 boards ("Promoters", "Promoter - Sales
Comparison"), reading directly from the ``promoter`` module's own tables
(``promoter.showroom``, ``promoter.showroom.sales``, ``sales.target``)
via the same generic engine as "PBI Dashboards > Service Dashboards"
(see service_sql.py's ``promoter_showrooms``/``promoter_sales``/
``sales_comparison`` CTEs, registered in its ``_SOURCE_CTE``) — the
dataclasses, ``run_kpi``/``run_breakdown``/``run_terminal_domain``
runners and the controller (promoter_main.py subclasses
service_main.py's controller) are all shared, not duplicated.

``sales.target.actual_qty`` is kept in lockstep with
``promoter.showroom.sales`` by that model's own create/write/unlink (see
promoter/models/promoter_showroom_sales.py), so "Promoter - Sales
Comparison" reads target_qty/actual_qty side by side off sales.target
directly — no join to promoter.showroom.sales is needed for that board.
"""
from .service_config import BoardConfig, ChartItemConfig, MeasureConfig, GroupByConfig, DrillStep

PROMOTER_BOARDS: dict = {
    "promoters": BoardConfig(
        key="promoters", title="Promoters", sequence=10,
        items=[
            ChartItemConfig(
                key="employees_count_region_city_showroom",
                name="Employees Count By Region, City & Showroom",
                type="bar", source="promoter_showrooms",
                domain=[("promoter_required", "=", True)],
                groupby=GroupByConfig("region_id"),
                drill=[DrillStep("city_id", "City"), DrillStep("showroom_pk", "Showroom")],
                record_model="promoter.showroom",
            ),
            ChartItemConfig(
                key="sales_qty_region_city_group_subgroup",
                name="Sales (Qty) - Region, City, Product Group, Sub-group wise",
                type="bar", source="promoter_sales",
                measure=MeasureConfig("qty", "sum"),
                groupby=GroupByConfig("region_id"),
                drill=[DrillStep("city_id", "City"), DrillStep("group_id", "Product Group"),
                       DrillStep("subgroup_id", "Product Sub Group")],
                record_model="promoter.showroom.sales",
            ),
            ChartItemConfig(
                key="sales_qty_month_region_city_showroom",
                name="Sales (Qty) - Month & Region, City, Showroom wise",
                type="bar", source="promoter_sales",
                measure=MeasureConfig("qty", "sum"),
                groupby=GroupByConfig("date_time", interval="month_year"),
                drill=[DrillStep("region_id", "Region"), DrillStep("city_id", "City"),
                       DrillStep("showroom_id", "Showroom")],
                record_model="promoter.showroom.sales",
            ),
        ],
    ),
    "promoter_sales_comparison": BoardConfig(
        key="promoter_sales_comparison", title="Promoter - Sales Comparison", sequence=20,
        items=[
            ChartItemConfig(
                key="target_vs_actual_overall", name="Target vs Actual (Qty) - Overall",
                type="kpi_dual", source="sales_comparison",
                measure=MeasureConfig("target_qty", "sum"),
                measure_2=MeasureConfig("actual_qty", "sum"),
            ),
            ChartItemConfig(
                key="sales_actual_vs_target_region_wise", name="Sales (Actual vs Target) - Region wise",
                type="bar", source="sales_comparison",
                measure=MeasureConfig("target_qty", "sum"),
                measure_2=MeasureConfig("actual_qty", "sum"),
                series_labels=("Target", "Actual"),
                groupby=GroupByConfig("sc_region"),
                record_model="sales.target",
            ),
            ChartItemConfig(
                key="sales_actual_vs_target_city_wise", name="Sales (Actual vs Target) - City wise",
                type="bar", source="sales_comparison",
                measure=MeasureConfig("target_qty", "sum"),
                measure_2=MeasureConfig("actual_qty", "sum"),
                series_labels=("Target", "Actual"),
                groupby=GroupByConfig("sc_city"),
                record_model="sales.target",
            ),
            ChartItemConfig(
                key="sales_actual_vs_target_month_wise", name="Sales (Actual vs Target) - Month wise",
                type="bar", source="sales_comparison",
                measure=MeasureConfig("target_qty", "sum"),
                measure_2=MeasureConfig("actual_qty", "sum"),
                series_labels=("Target", "Actual"),
                groupby=GroupByConfig("period"),
                sort=("code", "ASC"),
                record_model="sales.target",
            ),
        ],
    ),
}
