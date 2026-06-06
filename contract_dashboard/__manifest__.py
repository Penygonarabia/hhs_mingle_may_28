# -*- coding: utf-8 -*-
{
    'name': 'Contracts Dashboard',
    'version': '17.0.1.0.3',
    'summary': 'Dashboard for Subscription Contracts Analytics using KS Dashboard Ninja',
    'category': 'Sales/Dashboard',
    'author': 'HHS',
    'depends': [
        'sales_contract_and_recurring_invoices',
        'ks_dashboard_ninja',
        'machine_repair_management',
        'crm',
    ],
    'data': [
        'data/contract_dashboard_data.xml',
        'data/contracts_analysis_dashboard_data.xml',
        'data/contract_dashboard_layout.xml',
        'views/visits_pivot_view.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
