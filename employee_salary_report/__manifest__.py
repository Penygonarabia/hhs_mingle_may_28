# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Employee Salary Report ',
    'version' : '17.1',
    'summary': 'report for employee salary',
    'sequence': 15,
    'description': """
        Employee salary report
    """,
    'license':'LGPL-3',
    'category': 'report',
    'depends' : ['hr','base','om_hr_payroll','hr_contract'],
    'data': [
        
        
          'security/ir.model.access.csv',
          "wizard/views_employee_salary_report.xml",
          "report/report_employee_salary_xlsx.xml",
             
         
    ],
    'installable': True,
    
    'auto_install': False,
    
}
