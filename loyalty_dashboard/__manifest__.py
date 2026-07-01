# -*- coding: utf-8 -*-
{
    'name': 'Loyalty Dashboard',
    'version': '17.0.1.0.0',
    'summary': 'Dashboard for Loyalty Analytics using KS Dashboard Ninja',
    'category': 'Sales/Dashboard',
    'author': 'HHS',
    'depends': [
        'ks_dashboard_ninja',
        'hhs_loyalty_management',
        'hhs_loyalty_res_partner',
        'machine_repair_management',
    ],
    'data': [
        'data/loyalty_dashboard_data.xml',
        'data/loyalty_analysis_dashboard_data.xml',
        'data/loyalty_dashboard_layout.xml',
        'views/loyalty_dashboard_hidden_fields.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'loyalty_dashboard/static/src/js/points_issued_partner_redirect.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
