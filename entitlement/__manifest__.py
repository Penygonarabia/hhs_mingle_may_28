# -*- coding: utf-8 -*-
{
    'name': "Entitlement",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        This is a Entitlement module for leave and air ticket
    """,

    'author': "Cielo Digital Solutions Pvt.Ltd",
    'website': "http://cielodigitals.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'hr_contract', 'hr_holidays', 'om_hr_payroll'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_view.xml',
        'views/update_accrued_leave_view.xml',
        'views/hr_leave_view.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
    'license': 'LGPL-3',
}
