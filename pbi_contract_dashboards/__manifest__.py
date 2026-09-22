{
    'name': 'PBI Contract Dashboards',
    'version': '17.0.2.0.0',
    'category': 'Sales/Dashboard',
    'summary': 'PBI Contract Dashboards & Contract Analysis',
    'author': 'Cielo Digital',
    'depends': [
        'pbi_dashboards',
        'sales_contract_and_recurring_invoices',
    ],
    'data': [
        'views/pbi_contract_dashboards_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pbi_contract_dashboards/static/src/js/contract_config_client.js',
            'pbi_contract_dashboards/static/src/js/contract_dashboard.js',
            'pbi_contract_dashboards/static/src/xml/contract_dashboard.xml',
            'pbi_contract_dashboards/static/src/css/contract_dashboard.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
