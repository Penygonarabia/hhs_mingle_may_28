{
    'name': 'PBI Service Dashboards',
    'version': '17.0.2.0.0',
    'category': 'Services/Dashboard',
    'summary': 'PBI Service Dashboards - 15 regional & role-scoped service analysis boards',
    'author': 'Cielo Digital',
    'depends': [
        'pbi_dashboards',
        'project',
        'machine_repair_management',
    ],
    'data': [
        'views/pbi_service_dashboards_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pbi_service_dashboards/static/src/js/service_config_client.js',
            'pbi_service_dashboards/static/src/js/service_dashboard.js',
            'pbi_service_dashboards/static/src/xml/service_dashboard.xml',
            'pbi_service_dashboards/static/src/css/service_dashboard.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
