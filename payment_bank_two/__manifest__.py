# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Payroll payment bank format Two',
    'version' : '0.1',
    'summary': 'report for payroll payment advice for bank format Two',
    'sequence': 12,
    'description': """
    Payroll payment Bank format two for employees 
    """,
    'category': 'report',
    # 'website': 'https://www.odoo.com/page/billing',
    # 'images' : ['images/accounts.jpeg','images/bank_statement.jpeg','images/cash_register.jpeg','images/chart_of_accounts.jpeg','images/customer_invoice.jpeg','images/journal_entries.jpeg'],
    'depends' : ['hr','base_setup','report_xlsx','hr_saudi','om_hr_payroll','employee_payroll_report', 'tw_gosi'],
    'data': [
  
          'views/payroll_bank_two_views.xml',
          'security/ir.model.access.csv',
           'report/report.xml',
          'report/report_payroll_two.xml',
          'views/res_config_settings_views.xml'

         
    ],
    'installable': True,
    
    'auto_install': False,
    
}
