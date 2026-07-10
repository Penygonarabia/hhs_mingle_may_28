{
    'name': 'PBI Sales Dashboard',
    'version': '17.0.1.3.0',
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
by Customer Type as grouped bar + contribution-% donut charts for both
Amount and Qty), reading live from ``v_bidata_live`` with Period, Franchise,
Customer Groups and Customer Type filters. Customer Groups is resolved via
``v_customergroups`` (cst_no -> customer group), a coarser dimension than
Customer Type not otherwise exposed on v_bidata_live. Deliberately kept as
a separate menu/action from the "Sales Analysis" drill-down above — the two
share a display name by design, not by accident.

Access is gated the same way as every other menu under My Dashboard: hidden
until an admin grants it via Module Rights Setup (dashboard.rights.menu) —
enforced both on the menu (existing mechanism) and on the JSON data route
itself. A post_init_hook seeds an access grant for the bootstrap admin user
so the feature isn't invisible immediately after install.
""",
    'author': 'Cielo Digital',
    'depends': ['ks_dashboard_ninja', 'dashboard_rights', 'loyalty_dashboard'],
    'data': [
        'security/ir.model.access.csv',
        'views/pbi_dashboards_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
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
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
