# -*- coding: utf-8 -*-
{
    'name': "Hyperbill Settings",

    'summary': "This Module is used to configure the hyperpay settings",

    'description': """
This Module is used to configure the hyperpay settings
    """,

    'author': "Maxwell",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',
    "images": ['hyperpay_settings/static/description/icon.png'],

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/res_config_settings_view.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": True,
    "auto_install": False,

}

