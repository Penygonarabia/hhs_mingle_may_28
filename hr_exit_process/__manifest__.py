# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'HR Exit Process Management',
    'version': '1.0',
    'license': 'Other proprietary',
    'category': 'Human Resources',
    'summary': 'Employee Out/Exit/Termination Process Management',
    'description': """
        Employee Exit process:
            ---> Configure CheckLists
            ---> Employee Exit Request
            ---> Employee Exit Checklists
            ---> Print Employee Exit Report 

Tags:
exit process
employee exit process
employee termination process
employee leave process
employee leave company
employee exit company
hr exit process
human resource exit process
checklist for exit process
Termination terminate
            """,
    'author': 'Arunagiri K',
    'website': 'http://www.appscomp.com/',
    'depends': ['hr', 'hr_contract', 'calendar', 'om_hr_payroll', 'hr_saudi', 'hr_recruitment', 'base', 'mail', 'survey'],
    'data': [
            'security/hr_exit_security.xml',
            'security/ir.model.access.csv',
            'views/hr_exit_view.xml',
            # 'views/hr_employee_view.xml',
            'report/hr_exit_process_report.xml',
             ],
    'installable': True,
    'application': True,
}

