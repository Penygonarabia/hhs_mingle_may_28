{
    'name': 'Employee Accrual Management',
    'version': '17.0',
    'license': 'LGPL-3',
    'category': 'Human Resources',
    'summary': 'Manage employee accruals and entitlements.',
    'description': """
        This module manages employee accruals including annual leave and ticket entitlements.
    """,
    'author': 'Raj Ganesh',
    'depends': ['hr', 'account', 'hr_holidays', 'base', 'hr_saudi', 'hr_exit_process', 'om_hr_payroll'],
    'data': [
        'views/hr_employee_view.xml',
        'views/hr_contract_views.xml',
        'views/account_journal_views.xml',
        'views/account_move_view.xml',
        'views/employee_accrual_views.xml',
        'reports/report_accruvals_excel.xml',
        # 'data/data.xml',
        # 'data/account_account_data.xml',
        'data/accrual_type_sequence.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
}
