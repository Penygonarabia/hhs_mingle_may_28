# -*- coding: utf-8 -*-

{
    'name': 'Saudi GOSI Calculations',
    'version': '17.0.1.0',
    'license': 'LGPL-3',

    'sequence': '0',
    'website': '',
    'author': '',
    'summary': 'Saudi GOSI Management',
    'description': """
     Saudi GOSI
""",
    'depends': ['hr', 'om_hr_payroll'],
    'data': [
        # Views
        'views/res_config_settings.xml',
        'views/hr_payslip.xml',
        'views/hr_salary_rule.xml',

    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}