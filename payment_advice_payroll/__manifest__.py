# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Payroll Format BanK',
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
    'depends' : ['hr','base_setup', 'base', 'om_hr_payroll','report_xlsx','hr_saudi', 'employee_payroll_report'],
    'data': [

        'views/payroll_payment_bank_format1_views.xml',
        'views/payroll_bank_two_views.xml',
        'views/payment_advice_views.xml',
        'views/menu.xml',
          
        'security/ir.model.access.csv',
        'report/report.xml',
        'report/report_payroll_two.xml',
         
    ],
    'installable': True,
    
    'auto_install': False,
    
}
