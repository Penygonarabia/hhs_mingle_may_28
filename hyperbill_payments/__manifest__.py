# -*- coding: utf-8 -*-
{
    'name': "Hyperbill Payments",

    'summary': "This Module is used to configure the hyperbill payments",

    'description': """
This Module is used to configure the hyperbill payments
    """,

    'author': "Arunagiri K",
    'website': "https://www.cielodigitals.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Payment Method',
    'version': '0.1',
    "images": ['static/description/icon.png'],
    # any module necessary for this one to work correctly
    'depends': ['base','project','machine_repair_management'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_view.xml',
        'views/hyperbill_payment_view.xml',
        'views/hyperbill_audit_view.xml',
        'data/scheduler_data.xml',
        'views/job_card_views.xml',
        'views/work_center_group_views.xml',
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

