# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Advance Transaction Report',
    'summary': 'Report for Employees Advance Details',
    'sequence': 15,
    'version': '17.0',
    'license' :'LGPL-3',
    'author': 'Raj Ganesh Cielo',
    'description': """
        Employee Advance report
    """,
    'category': 'report',
    'depends' : ['hr','base','om_hr_payroll','report_xlsx','hr_loan_advance'],
    'data': [
        
        
          'security/ir.model.access.csv',
          "wizard/views_employee_advance_report.xml",
          "wizard/employee_advance_template.xml",
          "report/report_employee_advance_xlsx.xml",
      
             
         
    ],
    'installable': True,
    
    'auto_install': False,
    
}
