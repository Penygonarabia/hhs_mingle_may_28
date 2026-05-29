# -*- coding: utf-8 -*-

{
    'name': 'Saudi Human Resource System',
    'version': '17.0.1.0',
    'sequence': '0',
    'website': 'https://www.slnee.com',
    # 'author': 'Slnee',
    'summary': 'Saudi Human Resource System',
    'description': """
     Saudi Human Resource System
""",

    'depends': ['base', 'mail','hr', 'hr_contract', 'hr_recruitment','om_hr_payroll','iqama_management', 'sms',],
    'data': [
        'security/hr_groups.xml',
       # 'security/ir_rule.xml',
       'security/ir.model.access.csv',
        #Data
        # 'data/hr_contract_seq_data.xml',
        'data/hr_employee_transaction_seq_data.xml',
        'views/hr_employee_view.xml',
        'views/hr_contract_view.xml',
        'views/hr_department_view.xml',
        'views/hr_branch_view.xml',
        'views/hr_configuration_view.xml',
        # 'views/hr_employee_promotion_view.xml',
        'views/hr_employee_transaction_view.xml',
        # 'views/hr_payslip_views.xml'


    ],
    'sequence':-100,
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',

}
