# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Payroll Transaction Batch',
    'version' : '0.1',
    'summary': 'Batch For Payroll Transaction',
    'sequence': 12,
    'description': """
        Transaction for Payroll Batch 
    """,
    'category': 'Human Resources',
    'depends' : ['base', 'hr_transaction','hr'],
    'data': [
  
          
          'security/ir.model.access.csv',
         "views/batch_payroll_transaction_views.xml",
         "data/sequence.xml"
         
    ],
    'installable': True,
    
    'auto_install': False,
    
}
