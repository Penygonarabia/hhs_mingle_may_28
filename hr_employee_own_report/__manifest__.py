# custom_addons/hr_employee_own_report/__manifest__.py
{
    'name': 'HR Employee Own Report',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',
    'summary': 'Allow employees to access their own HR reports',
    'category': 'Human Resources',
    'author': 'Raj Ganesh',
    'depends': ['hr', 'base', 'hr_holidays'],
    'data': [
        # 'views/hr_employee_views.xml',
        'reports/hr_employee_own_report.xml',
        'reports/hr_employee_own_report_template.xml',
        'views/hr_employee_leave_allocation.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
