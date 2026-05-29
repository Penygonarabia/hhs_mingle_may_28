# -*- coding: utf-8 -*-

{
    'name': 'HRMS Allowances/Detection Salary',
    'version': '17.0.1.0.2',
    'summary': 'Allowances/Detection Salary In HR',
    'description': """
        Helps you to manage Allowances/Detection Salary Request of your company's staff.
        """,
    'category': 'Generic Modules/Human Resources',
    'depends': [
        'om_hr_payroll', 'hr', 'account', 'hr_contract', 'hr_transaction', 'hr_saudi', 'hr_attendances_overtime', 'payroll_transaction_batch'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/salary_structure.xml',
        'views/salary_allowance_detection.xml',
        'data/sequence.xml',
        'data/action_data_done.xml',
    ],
    'demo': [],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

