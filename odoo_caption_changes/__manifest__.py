# -*- coding:utf-8 -*-

{
    'name': 'Odoo Caption Changes',
    'category': 'Changes Caption Changes',
    'sequence': 1,
    'summary': 'Caption Change Odoo',
    'description': "Caption Changes Odoo",
    'depends': ["base","iap","website","mail","mail_bot"
       
    ],
    'data': [
        "views/views_res_config_settings.xml",
        "data/data.xml",
       
    ],
    'application': True,
}
