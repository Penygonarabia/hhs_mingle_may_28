# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Employee Loan Report ',
    'summary': 'Report for Employees Loan Details',
    'sequence': 15,
    'license': 'LGPL-3',
    'author': 'Raj Ganesh Cielo',
    'description': """
        Employee Loan report
    """,
    'category': 'report',
    'depends' : ['hr','base','om_hr_payroll','report_xlsx','hr_loan_advance'],
    'data': [
        
        
          'security/ir.model.access.csv',
          "wizard/views_employee_loan_report.xml",
          "wizard/employee_loan_template.xml",
          "report/report_employee_loan_xlsx.xml",
      
             
         
    ],
    'installable': True,
    
    'auto_install': False,
    
}
