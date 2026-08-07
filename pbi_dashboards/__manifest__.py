{
    'name': 'PBI Dashboards (Base Core)',
    'version': '17.0.2.0.0',
    'category': 'Sales/Dashboard',
    'summary': 'Base core module providing the PBI Dashboards root menu and shared utilities',
    'description': """
PBI Dashboards Base Core Module
================================
Provides the top-level "PBI Dashboards" root menu and shared components
(chart libraries, i18n, access helpers, and base models) for individual
dashboard modules.
""",
    'author': 'Cielo Digital',
    'depends': [
        'base',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/pbi_dashboards_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pbi_dashboards/static/src/css/pbi_dashboard_base.css',
            'pbi_dashboards/static/src/js/pbi_i18n.js',
            'pbi_dashboards/static/src/js/pbi_chart_lib.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
