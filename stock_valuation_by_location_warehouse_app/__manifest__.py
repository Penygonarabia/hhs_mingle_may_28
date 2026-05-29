# -*- coding: utf-8 -*-

{
    'name' : 'Stock Valuation Synchronization | Warehouse Stock Valuation | Stock Inventory Valuation | Inventory Valuation by Location | Inventory Stock Valuation',
    'author': "Edge Technologies",
    'version' : '17.0.1.0',
    'live_test_url':'https://youtu.be/wQnDqmQjFTE',
    "images":['static/description/main_screenshot.png'],
    'summary' : 'Inventory valuation inventory stock valuation by warehouse stock valuation by location stock inventory valuation location wise product stock valuation by warehouse inventory valuation by location product stock management sync stock valuation reports',
    'description' : """
        Odoo stock valuation by location/warehouse app is a powerful tool designed to provide stock valuation information based on different locations or warehouses within your organization. With this app, you can easily evaluate the value of your stock on a per-location and warehouse basis. This app allows you to group the value of product location and warehouse in the tree view.
     """,
    "license" : "LGPL-3",
    'depends': ['base','stock','account'],
    'data': [
        
        'views/stock_valuation_views.xml',
        
    ],
    'qweb' : [
    ],
    'installable' : True,
    'auto_install' : False,
    'price': 35,
    'currency': "EUR",
    'category' : 'Warehouse',
}
