{
    'name': 'PBI Promoter Dashboards',
    'version': '17.0.2.0.0',
    'category': 'Sales/Dashboard',
    'summary': 'PBI Promoter Dashboards & Sales Comparison',
    'author': 'Cielo Digital',
    'depends': [
        'pbi_dashboards',
        'promoter',
    ],
    'data': [
        'views/pbi_promoter_dashboards_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pbi_promoter_dashboards/static/src/js/promoter_config_client.js',
            'pbi_promoter_dashboards/static/src/js/promoter_dashboard.js',
            'pbi_promoter_dashboards/static/src/xml/promoter_dashboard.xml',
            'pbi_promoter_dashboards/static/src/css/promoter_dashboard.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
