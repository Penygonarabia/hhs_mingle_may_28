# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'payroll payment advice report',
    'version' : '17.1',
    'license': 'LGPL-3',
    'summary': 'report for payroll payment advice',
    'sequence': 12,
    'description': """
    Payroll payment advice report for employees 
    """,
    'category': 'report',
    # 'website': 'https://www.odoo.com/page/billing',
    # 'images' : ['images/accounts.jpeg','images/bank_statement.jpeg','images/cash_register.jpeg','images/chart_of_accounts.jpeg','images/customer_invoice.jpeg','images/journal_entries.jpeg'],
    'depends' : ['hr','base_setup','om_hr_payroll','report_xlsx','hr_saudi', 'base'],
    'data': [
  
         'views/payment_advice_views.xml',

          
         'security/ir.model.access.csv',
         
          'report/report.xml',
        'report/report_payroll_payment.xml',
      
             
         
    ],
    'installable': True,
    
    'auto_install': False,
    
}
