{
    'name': 'PBI Loyalty Dashboards',
    'version': '17.0.2.1.0',
    'category': 'Sales/Dashboard',
    'summary': 'PBI Loyalty Dashboards & Loyalty Analysis',
    'author': 'Cielo Digital',
    'depends': [
        'pbi_dashboards',
        'loyalty_dashboard',
        'pbi_sales_dashboards',
    ],
    'data': [
        'views/pbi_loyalty_dashboards_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pbi_loyalty_dashboards/static/src/js/loyalty_dashboard.js',
            'pbi_loyalty_dashboards/static/src/xml/loyalty_dashboard.xml',
            'pbi_loyalty_dashboards/static/src/css/loyalty_dashboard.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
