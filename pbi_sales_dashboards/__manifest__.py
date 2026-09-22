{
    'name': 'PBI Sales Dashboards',
    'version': '17.0.4.8.0',
    'category': 'Sales/Dashboard',
    'summary': 'PBI Sales Dashboards, KPI Tiles, Sales Analysis & Mail Content Reports',
    'author': 'Cielo Digital',
    # DELIBERATELY ONLY pbi_dashboards.
    #
    # These boards read tables owned by modules developed and released
    # separately -- dashboard_groups (salestypes_group, main_category,
    # sub_category, sale_types), sales_budget (v_sales_budget_month),
    # partner_classification, salesman_res_partner,
    # machine_repair_management, and whichever module declares res.region on
    # the server. Depending on them would carry this repository's copy of
    # that work into servers that already run their own, overwriting code
    # maintained elsewhere. So none of them is declared, and every read of
    # their data is resolved against the live schema at build time instead --
    # see pbi_dashboards/controllers/optional_schema.py, and _OPTIONAL_TABLES
    # in models/sales_sman_fact_view.py for what happens where one is absent.
    'depends': [
        'pbi_dashboards',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/pbi_sales_sman_fact_cron.xml',
        'views/pbi_sales_dashboards_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pbi_sales_dashboards/static/src/js/sales_analysis_dashboard.js',
            'pbi_sales_dashboards/static/src/xml/sales_analysis_dashboard.xml',
            'pbi_sales_dashboards/static/src/css/sales_analysis_dashboard.css',
            'pbi_sales_dashboards/static/src/css/sales_kpi_dashboard.css',
            'pbi_sales_dashboards/static/src/css/sales_kpi_dashboard_new.css',
            'pbi_sales_dashboards/static/src/js/sales_sman_dashboard.js',
            'pbi_sales_dashboards/static/src/xml/sales_sman_dashboard.xml',
            'pbi_sales_dashboards/static/src/css/sales_sman_dashboard.css',
            # "Sales Dashboard - VQ" extends the component right above it, so
            # it must load after it.
            'pbi_sales_dashboards/static/src/js/sales_vq_dashboard.js',
            'pbi_sales_dashboards/static/src/xml/sales_vq_dashboard.xml',
            'pbi_sales_dashboards/static/src/css/sales_vq_dashboard.css',
            'pbi_sales_dashboards/static/src/js/sales_study_dashboard.js',
            'pbi_sales_dashboards/static/src/xml/sales_study_dashboard.xml',
            'pbi_sales_dashboards/static/src/css/sales_study_dashboard.css',
            'pbi_sales_dashboards/static/src/js/sales_study_sman_dashboard.js',
            'pbi_sales_dashboards/static/src/css/sales_mail_dashboard.css',
            'pbi_sales_dashboards/static/src/js/sales_mail_sman_dashboard.js',
            'pbi_sales_dashboards/static/src/xml/sales_mail_sman_dashboard.xml',
            'pbi_sales_dashboards/static/src/css/sales_mail_sman_dashboard.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
