# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'payroll payment bank format one',
    'version' : '17.1',
    'license': 'LGPL-3',
    'summary': 'report for payroll payment advice for bank format one',
    'sequence': 12,
    'description': """
    Payroll payment Bank format one for employees 
    """,
    'category': 'report',
    # 'website': 'https://www.odoo.com/page/billing',
    # 'images' : ['images/accounts.jpeg','images/bank_statement.jpeg','images/cash_register.jpeg','images/chart_of_accounts.jpeg','images/customer_invoice.jpeg','images/journal_entries.jpeg'],
    'depends' : ['hr','base_setup','om_hr_payroll','report_xlsx','hr_saudi'],
    'data': [
  
          'views/payroll_payment_bank_format1_views.xml',
            'security/ir.model.access.csv',
           'report/report.xml',
         'report/report_payroll.xml',
      

         
    ],
    'installable': True,
    
    'auto_install': False,
    
}
