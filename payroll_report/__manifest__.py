# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'payroll report',
    'version' : '17.1',
    'license': 'LGPL-3',
    'summary': 'report for payroll',
    'sequence': 15,
    'description': """
    Payroll report for employees 
    """,
    'category': 'report',
    # 'website': 'https://www.odoo.com/page/billing',
    # 'images' : ['images/accounts.jpeg','images/bank_statement.jpeg','images/cash_register.jpeg','images/chart_of_accounts.jpeg','images/customer_invoice.jpeg','images/journal_entries.jpeg'],
    'depends' : ['hr','base_setup','om_hr_payroll','report_xlsx','hr_saudi'],
    'data': [
          # 'wizard/menu.xml',
         'wizard/gosi_payroll_views.xml',
          # 'wizard/department_wise_report_views.xml',
         
          
         'security/ir.model.access.csv',
          # 'report/report.xml',        
         
    ],
    'installable': True,
    
    'auto_install': False,
    
}
