# -*- coding: utf-8 -*-

{
    'name': 'Employee Shift Management | HRMS Employee Shift | HR Employee Work Shift | HR Shift Allocation | Employee Management System',
    "author": "Edge Technologies",
    'version': '17.0.1.0',
    'live_test_url': "https://youtu.be/0GILl7Q2Us4",
    "images":['static/description/main_screenshot.png'],
    'summary': "Create work shift schedule employee shift schedule hr employee shift management employee bulk shift scheduling hr employee work schedule hrms employee work shift scheduling hr shift allocation for employee shift rotation request employee shift report",
    'description': """This app feature has we create employee shift schedule also create bulk of shift scheduling, and employee can request for changes shift, also print roster report and send mail feature""",
    'license': 'LGPL-3',
    'depends': ['hr_holidays','hr','base','hr_employee_updation','ag_employee_self_service','hr_saudi'],
    'data': [
           'security/ir.model.access.csv',
           'data/sequence.xml',
           'data/paperformat.xml',
           'report/report.xml',
           # 'data/mail_template.xml',
           'views/employee_weekoff_view.xml',
           'views/shift_type_view.xml',
           'views/employee_week_day_view.xml',
           'views/employee_shift_view.xml',
           'views/employee_shift_allocation_view.xml',
           'wizard/bulk_allocation_wizard_view.xml',
           'report/shift_allocation_report.xml',
           'views/employee_shift_changes_view.xml',
           'wizard/employee_shift_roster_report_view.xml',
            ],
    'installable': True,
    'auto_install': False,
    'price': 35,
    'currency': "EUR",
    'category': 'Human Resources',

}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
