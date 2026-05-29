# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Payroll Transactions Report',
    'summary': 'Report for Payroll Transactions',
    'sequence': 15,
    'license': 'LGPL-3',
    'description': """
        Payroll Transactions report
    """,
    'category': 'report',
    'depends' : ['hr','base','om_hr_payroll','report_xlsx','hrms_salary_al_dt','employee_payroll_report'],
    'data': [
        
        
          'security/ir.model.access.csv',
          "wizard/views_payroll_transactions_detail_report.xml",
          "wizard/payroll_transactions_template.xml",
          "report/report_employee_detail_xlsx.xml",
      
             
         
    ],
    'installable': True,
    
    'auto_install': False,
    
}
