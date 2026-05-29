# -*- coding: utf-8 -*-

{
    'name': 'HR Leave Balance Report',
    'version': '1.0',
    'license': 'LGPL-3',
    'category': 'Human Resources',
    'summary': 'Generate Leave Balance Reports',
    'description': """
    Custom module to generate leave balance reports for employees.
    """,
    'author': 'Raj Ganesh',
    'depends': ['hr_holidays', 'hr','base'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_leave_balance_report_views.xml',
    ],
    'installable': True,
    'application': True,
}

