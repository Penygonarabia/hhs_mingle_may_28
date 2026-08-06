# -*- coding: utf-8 -*-
"""Declarative board/chart-item configuration for "PBI Dashboards >
Contract Dashboards > Contract Analysis" — a single BoardConfig ported 1:1
from contract_dashboards/data/contracts_analysis_dashboard_data.xml's
"Contract Analysis" ks_dashboard_ninja.board (6 bar charts + 1 flat list
table, all on subscription.contracts), reading live from
subscription_contracts directly via the same generic engine as Service/
Promoter Dashboards (service_sql.py's "contracts" CTE, registered in its
_SOURCE_CTE) — no ks_dashboard_ninja or contract_dashboards module
dependency for this feature.

Every item's domain/groupby/drill chain matches the source board's own
ks_domain/ks_chart_relation_groupby/ks_dashboard_ninja.item_action chain
exactly (see that XML's per-chart comments) — nothing invented here. The
source board reserves layout space for KPI tiles but never actually
defines any (grep confirms zero ks_kpi items), so none are added here
either.
"""
from .service_config import BoardConfig, ChartItemConfig, MeasureConfig, GroupByConfig, DrillStep, TableColumnConfig

CONTRACT_BOARDS: dict = {
    "contract_analysis": BoardConfig(
        key="contract_analysis", title="Contract Analysis", sequence=10,
        items=[
            # Chart 1 (ca_chart_amount_by_region): sum(amount_total) by
            # Region, drilling Region -> City -> Salesman -> Month.
            ChartItemConfig(
                key="amount_by_region", name="Contract Analysis - Amount (Region wise)",
                type="bar", source="contracts",
                measure=MeasureConfig("contract_amount", "sum"),
                groupby=GroupByConfig("work_center_group_id"),
                drill=[DrillStep("work_center_id", "City"), DrillStep("sales_person_user_id", "Salesman"),
                       DrillStep("date_start", "Month", interval="month_year")],
                record_model="subscription.contracts",
            ),
            # Chart 2 (ca_chart_qty_by_region): same shape, record count
            # instead of sum(amount_total) — ks_chart_data_count_type=count.
            ChartItemConfig(
                key="qty_by_region", name="Contract Analysis - Quantity (Region wise)",
                type="bar", source="contracts",
                groupby=GroupByConfig("work_center_group_id"),
                drill=[DrillStep("work_center_id", "City"), DrillStep("sales_person_user_id", "Salesman"),
                       DrillStep("date_start", "Month", interval="month_year")],
                record_model="subscription.contracts",
            ),
            # Chart 3 (ca_chart_amount_by_month): sum(amount_total) by
            # Month, drilling Month -> Region -> City -> Salesman.
            ChartItemConfig(
                key="amount_by_month", name="Contract Analysis - Amount (Month wise)",
                type="bar", source="contracts",
                measure=MeasureConfig("contract_amount", "sum"),
                groupby=GroupByConfig("date_start", interval="month_year"),
                drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "City"),
                       DrillStep("sales_person_user_id", "Salesman")],
                record_model="subscription.contracts",
            ),
            # Chart 4 (ca_chart_qty_by_month): same shape, record count.
            ChartItemConfig(
                key="qty_by_month", name="Contract Analysis - Quantity (Month wise)",
                type="bar", source="contracts",
                groupby=GroupByConfig("date_start", interval="month_year"),
                drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "City"),
                       DrillStep("sales_person_user_id", "Salesman")],
                record_model="subscription.contracts",
            ),
            # Chart 5 (sa_chart_amount_by_salesman): sum(amount_total) by
            # Salesman, drilling Salesman -> Region -> City -> Month.
            ChartItemConfig(
                key="amount_by_salesman", name="Sales Analysis - Amount (Salesman wise)",
                type="bar", source="contracts",
                measure=MeasureConfig("contract_amount", "sum"),
                groupby=GroupByConfig("sales_person_user_id"),
                drill=[DrillStep("work_center_group_id", "Region"), DrillStep("work_center_id", "City"),
                       DrillStep("date_start", "Month", interval="month_year")],
                record_model="subscription.contracts",
            ),
            # Chart 6 (ca_chart_maint_service_vs_contract_value): 2-measure
            # bar (service_amount vs contract_amount), one bar-pair per
            # contract, maintenance contracts only, top 20 (source's own
            # ks_record_data_limit=20) — default sort is already value DESC
            # (no item.sort set), matching the source's unsorted-but-
            # record-data-limited behaviour closely enough to surface the
            # highest-value contracts first.
            ChartItemConfig(
                key="maint_service_vs_contract_value",
                name="Maintenance Service Analysis vs Contract Value",
                type="bar", source="contracts",
                domain=[("contract_type", "=", "maintenance")],
                measure=MeasureConfig("service_amount", "sum"),
                measure_2=MeasureConfig("contract_amount", "sum"),
                series_labels=("Service Amount (Excl. VAT)", "Contract Amount (Incl. VAT)"),
                groupby=GroupByConfig("name"),
                limit=20,
                drill=[DrillStep("partner_id", "Customer"), DrillStep("work_center_group_id", "Region"),
                       DrillStep("work_center_id", "City")],
                record_model="subscription.contracts",
            ),
            # Chart 7 (ca_chart_visits_estimated_vs_actual): flat, ungrouped
            # list of maintenance contracts — Preventive/Corrective Est vs
            # Actual vs Balance, mirroring the source's ks_list_view exactly
            # (same 11 columns, same 50-row cap, same maintenance-only
            # domain). No drill chain in the source (list views carry no
            # ks_dashboard_ninja.item_action records) — clicking a row opens
            # the contract's own form directly instead (contract_dashboard.js).
            ChartItemConfig(
                key="visits_estimated_vs_actual",
                name="Visits Comparison - Preventive & Corrective (Est vs Actual)",
                type="table", source="contracts",
                domain=[("contract_type", "=", "maintenance")],
                sort=("name", "DESC"), limit=50,
                table_columns=[
                    TableColumnConfig("work_center_group_id", "Region"),
                    TableColumnConfig("work_center_id", "City"),
                    TableColumnConfig("name", "Contract No"),
                    TableColumnConfig("partner_id", "Customer"),
                    TableColumnConfig("sales_person_user_id", "Salesman"),
                    TableColumnConfig("preventive_estimated", "Preventive Est", numeric=True),
                    TableColumnConfig("preventive_actual", "Preventive Actual", numeric=True),
                    TableColumnConfig("preventive_balance", "Preventive Balance", numeric=True),
                    TableColumnConfig("corrective_estimated", "Corrective Est", numeric=True),
                    TableColumnConfig("corrective_actual", "Corrective Actual", numeric=True),
                    TableColumnConfig("corrective_balance", "Corrective Balance", numeric=True),
                ],
                record_model="subscription.contracts",
            ),
        ],
    ),
}
