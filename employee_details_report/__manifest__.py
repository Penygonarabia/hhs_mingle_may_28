# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Employee Report ',
    'summary': 'Report for Employee Details',
    'sequence': 15,
    'license': 'LGPL-3',
    'author': 'Raj Ganesh Cielo',
    'description': """
        Employee Details report
    """,
    'category': 'report',
    'depends' : ['hr','base','om_hr_payroll','report_xlsx', 'web'],
    'data': [
        
        
          'security/ir.model.access.csv',
          "wizard/views_employee_detail_report.xml",
          "wizard/employee_template.xml",
          "report/report_employee_detail_xlsx.xml",
      
             
         
    ],
    'installable': True,
    
    'auto_install': False,
    
}
