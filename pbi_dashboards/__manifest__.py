{
    'name': 'PBI Sales Dashboard',
    'version': '17.0.1.8.0',
    'category': 'Sales/Dashboard',
    'summary': 'Custom BI sales and loyalty dashboards under PBI Dashboards',
    'description': """
PBI Sales Dashboard
====================
Adds "My Dashboard > PBI Dashboards > Sales Dashboard" — a custom OWL
dashboard (not a ks_dashboard_ninja board) reading live aggregates from the
``v_bidata_live`` view: Year and Franchise filters (All/2023/2024/2025 and a
"Compare 2024 -> 2025" mode), sales-vs-budget charts across region,
franchise, customer type, product group and salesman, and narrative
insight text with numbered citations. Exported PowerPoint speaker notes can
be hand-edited and re-imported: matching text replaces the on-screen
narrative for that section, period and franchise (pbi.dashboard.note).

Also adds "PBI Dashboards > Loyalty Dashboards > Loyalty Analysis" — a
second custom OWL dashboard, same visual style, reading directly from the
raw legacy ``transaction_header``/``transaction_details`` tables (customers
per tier, points issued, points redeemed, newly added users — all region
wise with City/Customer drill-down and redirects into the customer list or
loyalty points history list).

Also adds "PBI Dashboards > Sales Analysis" — Report-1 (Amount) and
Report-2 (Qty), each a Region -> City -> Main -> Main Sub -> Prod Group ->
Product Sub Group -> Customer -> Transaction list drill-down, reading from
``v_pbi_sales_analysis`` (pbi.sales.analysis.view), a view over the real
``bidata`` sales fact table that resolves every caption in one place.
Credit notes are already netted into signed amounts upstream, so summing
nets them against invoices.

Also adds "PBI Dashboards > Sales Dashboards > Sales Analysis" — a KPI
tile + chart dashboard (MTD/YTD sales vs target vs prior year, broken down
by Sales Type Group as grouped bar + contribution-% donut charts for both
Amount and Qty), reading live from ``bidata`` directly (same AMOUNT_EXPR/
qty-gate formula and t_salpurgroup-derived channel grouping as Sales Mail
Content) with Year, Month, Franchise, Customer Groups and Sales Type Group
filters. Customer Groups is resolved via ``v_customergroups`` (cst_no ->
customer group), a coarser dimension than Sales Type Group and not itself a
bidata column. Deliberately kept as a separate menu/action from the "Sales
Analysis" drill-down above — the two share a display name by design, not by
accident.

Also adds "PBI Dashboards > Sales Dashboards > Sales Dashboard - New" — the
same MTD/YTD KPI tile + Sales Type Group chart data as "Sales Dashboard"
above (same bidata-direct engine, own JSON route), but with an Amount/Qty
toggle: only the selected measure's 12 KPI tiles and MTD/YTD chart pair
render at a time, and each chart row is one widened bar chart paired with
its contribution-% donut (MTD row, then YTD row below it) instead of the
original's 4-across Bar/Donut/Bar/Donut grid. Gated by its own menu grant,
independent of "Sales Dashboard".

Also adds "PBI Dashboards > Sales Dashboards > Sales Mail Content" — an
11-page report-style dashboard mirroring the client's monthly PPTX sales
report (Total Company, Channel, Region, Division/Category breakdowns,
Distribution, Sub-brand, Key Takeaways), reading live from ``v_bidata_live``
with just Period (Year+Month) and Franchise filters — every other dimension
is an in-page toggle. No drill-down. Supports Export PDF (prints every page),
Export PowerPoint, and the same hand-edited-speaker-notes round-trip as
Sales Dashboard (pbi.dashboard.note, keys prefixed ``sales_mail_``).

Also adds "PBI Dashboards > Sales Dashboards > Sales Analysis - New" — the
same 17-page report data as "Sales Analysis" above (same bidata-direct
engine, own JSON route/PPTX-export/notes-import), but without the Prev/
Next/page-picker navigation: every page renders stacked, one after another
in header order, instead of showing only one page at a time. Gated by its
own menu grant, independent of "Sales Analysis".

Also adds "PBI Dashboards > Service Dashboards" — all 15 direct-table
replicas of the service_dashboards_ct ks_dashboard_ninja boards (job-card/
service analysis: region variants C/E/W, the user's-own-work-center (UWC)
variant, JCs, role-scoped CC/CRD/Parts/Technician boards, Sales & Cost
Analysis, and the 4 per-logged-in-user "_users" boards), reading live from
project_task/machine_repair_support/mail_message directly (see
pbi_dashboards/controllers/service_sql.py, which ports the dbmodel.*.ct
view SQL rather than depending on those views or on ks_dashboard_ninja) —
no ks_dashboard_ninja board dependency for this feature. One generic
controller + one generic OWL component render every board from a
declarative per-board config (pbi_dashboards/controllers/service_config.py)
with per-chart independent drill-down (each tile drills through its own
field chain, ending in a native Odoo list/form), instead of a
copy-pasted file set per dashboard.

Also adds "PBI Dashboards > Promoter Dashboards" — 2 boards ("Promoters",
"Promoter - Sales Comparison") reading live from the ``promoter`` module's
own tables (promoter.showroom, promoter.showroom.sales, sales.target)
directly, sharing the exact same generic engine as Service Dashboards
(pbi_dashboards/controllers/service_sql.py's promoter_showrooms/
promoter_sales/sales_comparison CTEs, registered alongside the jobcards/
usergroup/message_log ones; promoter_config.py/promoter_main.py add the
board registry and the 2 JSON routes, reusing
PbiDashboardBoardEngineMixin instead of duplicating the date-range/access/
KPI-payload logic). "Promoters" shows employee counts and sales quantity
by region/city/showroom/product group (drill-down, same click-through-
each-dimension UX as Service Dashboards). "Promoter - Sales Comparison"
shows target vs actual quantity as dual-series bars, region/city/month
wise (same dual-measure-bar pattern as Service Dashboards' "Estimated vs
Actual Hours" tile) — sales.target.actual_qty is already kept in sync
with promoter.showroom.sales by that model's own create/write/unlink, so
no join is needed for the comparison. A lightweight "Promoter Analysis"
entry under "My Dashboard" points at these same two boards.

Also adds "PBI Dashboards > Contract Dashboards" — 1 board ("Contract
Analysis"), reading live from the ``subscription_contracts`` table
directly (see pbi_dashboards/controllers/service_sql.py's "contracts"
CTE, registered alongside the jobcards/usergroup/message_log/promoter
ones; contract_config.py/contract_main.py add the board registry and the
2 JSON routes, reusing PbiDashboardBoardEngineMixin instead of
duplicating the date-range/access/KPI-payload logic) — no
ks_dashboard_ninja or contract_dashboards module dependency. Ports
contract_dashboards' own "Contract Analysis" board 1:1: 6 bar charts
(Amount/Quantity by Region, by Month, by Salesman, each with the same
3-level drill chain as the source; Maintenance Service Analysis vs
Contract Value, a 2-measure top-20 bar per contract) plus 1 new 'table'
item type (Visits Comparison - Preventive & Corrective, a flat 50-row
listing mirroring the source's ks_list_view) — the first pbi_dashboards
board to need a raw-table tile alongside kpi/bar/pie, added generically
to the shared engine (service_config.py's ChartItemConfig.table_columns /
service_sql.py's run_table) rather than as one-off code. A lightweight
"Contract Analysis" entry under "My Dashboard" points at this same board.

Access is gated the same way as every other menu under My Dashboard: hidden
until an admin grants it via Module Rights Setup (dashboard.rights.menu) —
enforced both on the menu (existing mechanism) and on the JSON data route
itself. A post_init_hook seeds an access grant for the bootstrap admin user
so the feature isn't invisible immediately after install.
""",
    'author': 'Cielo Digital',
    'depends': [
        'ks_dashboard_ninja', 'dashboard_rights', 'loyalty_dashboard', 'project',
        'machine_repair_management', 'promoter', 'sales_contract_and_recurring_invoices',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/pbi_dashboards_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pbi_dashboards/static/src/js/pbi_i18n.js',
            'pbi_dashboards/static/src/js/sales_dashboard.js',
            'pbi_dashboards/static/src/xml/sales_dashboard.xml',
            'pbi_dashboards/static/src/css/sales_dashboard.css',
            'pbi_dashboards/static/src/js/loyalty_dashboard.js',
            'pbi_dashboards/static/src/xml/loyalty_dashboard.xml',
            'pbi_dashboards/static/src/css/loyalty_dashboard.css',
            'pbi_dashboards/static/src/js/sales_analysis_dashboard.js',
            'pbi_dashboards/static/src/xml/sales_analysis_dashboard.xml',
            'pbi_dashboards/static/src/css/sales_analysis_dashboard.css',
            'pbi_dashboards/static/src/js/sales_kpi_dashboard.js',
            'pbi_dashboards/static/src/xml/sales_kpi_dashboard.xml',
            'pbi_dashboards/static/src/css/sales_kpi_dashboard.css',
            'pbi_dashboards/static/src/js/sales_kpi_dashboard_new.js',
            'pbi_dashboards/static/src/xml/sales_kpi_dashboard_new.xml',
            'pbi_dashboards/static/src/css/sales_kpi_dashboard_new.css',
            'pbi_dashboards/static/src/js/sales_mail_dashboard.js',
            'pbi_dashboards/static/src/xml/sales_mail_dashboard.xml',
            'pbi_dashboards/static/src/css/sales_mail_dashboard.css',
            'pbi_dashboards/static/src/js/sales_mail_dashboard_new.js',
            'pbi_dashboards/static/src/xml/sales_mail_dashboard_new.xml',
            'pbi_dashboards/static/src/css/sales_mail_dashboard_new.css',
            'pbi_dashboards/static/src/js/pbi_chart_lib.js',
            'pbi_dashboards/static/src/js/service_config_client.js',
            'pbi_dashboards/static/src/js/service_dashboard.js',
            'pbi_dashboards/static/src/xml/service_dashboard.xml',
            'pbi_dashboards/static/src/css/service_dashboard.css',
            'pbi_dashboards/static/src/js/promoter_config_client.js',
            'pbi_dashboards/static/src/js/promoter_dashboard.js',
            'pbi_dashboards/static/src/xml/promoter_dashboard.xml',
            'pbi_dashboards/static/src/css/promoter_dashboard.css',
            'pbi_dashboards/static/src/js/contract_config_client.js',
            'pbi_dashboards/static/src/js/contract_dashboard.js',
            'pbi_dashboards/static/src/xml/contract_dashboard.xml',
            'pbi_dashboards/static/src/css/contract_dashboard.css',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
