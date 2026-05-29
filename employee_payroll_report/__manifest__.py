# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Employee Payroll Report ',
    'version' : '17.1',
    'summary': 'report for employee payroll',
    'sequence': 15,
    'license': 'LGPL-3',
    'description': """
        Employee salary report
    """,
    'category': 'report',
    'depends' : ['hr','base','om_hr_payroll'],
    'data': [
        
        
           'security/ir.model.access.csv',
          "wizard/views_employee_payroll_report.xml",
          "report/report_employee_payroll.xml",
             
         
    ],
    'installable': True,
    
    'auto_install': False,
    
}
