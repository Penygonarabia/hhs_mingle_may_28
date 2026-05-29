# -*- coding: utf-8 -*-
{
    'name': "Employee Arrival",
    'summary': """
       Employee Arrival""",
    'description': """
        Arrival of the Employee 
    """,
    'author': "Cielo Digital Solutions Pvt.Ltd",
    'website': "http://cielodigitals.com/",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base','web', 'hr', 'hr_contract', 'hr_holidays','om_hr_payroll'],
    'data': [
         'security/ir.model.access.csv',
         'views/views_leave_arrival.xml',
         'views/views_res_config_settings.xml',
        
    ],
    
    'license': 'LGPL-3',
     'installable': True,
    'auto_install': False,
}
