{
    'name': 'Dashboard Groups',
    'version': '1.0',
    'summary': 'Module for Dashboard Groups',
    'sequence': 10,
    'description': """
Dashboard Groups
=================
A custom module for managing Dashboard Groups.
    """,
    'category': 'Inventory/Configuration',
    'depends': ['base', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/salestypes_group_views.xml',
        'views/sale_types_views.xml',
        'views/main_category_views.xml',
        'views/sub_category_views.xml',
        'views/product_category_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
