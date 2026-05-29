# -*- coding: utf-8 -*-
{
    'name': 'Iqama Management',
    'version': '17.0',
    'license': 'LGPL-3',
    'category': 'Custom',
    'summary': 'Module to manage Iqama IDs and numbers',
    'description': """
        A module to manage Iqama IDs and numbers in Odoo 15.
    """,
    'author': 'Raj Ganesh',
    'website': 'http://www.yourwebsite.com',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/iqama_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
