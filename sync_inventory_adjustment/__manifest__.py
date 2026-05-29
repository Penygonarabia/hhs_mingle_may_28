# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': 'Inventory Adjustment Screen',
    'version': '1.0',
    'category': 'Project',
    'author': 'Raj Ganesh.S',
    'summary': '',
    
    'description': """
        Inventory Adjustment Screen
""",
    'depends': ['stock','base','stock_account',"account", "sale_stock_analytic"],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_inventory_view.xml',
        'views/stock_adj_reason_views.xml',
        'wizard/stock_adjustment_wizard.xml',
        'reports/report_stock_inventory.xml',
        'wizard/stock_adjustment_wizard.xml',
        'wizard/stock_adjustment_pdf_template.xml',
        'data/stock_adjustment_sequence_data.xml',
    ],
    'images': [
        'static/description/main_screen.png'
    ],
    'demo': [],
    'price': 35.0,
    'currency': 'USD',
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
}
