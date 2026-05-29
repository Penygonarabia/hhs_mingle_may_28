{
    'name': 'Financial Statements',
    'version': '1.0',
    'summary': 'Manage Balance Sheet, Profit & Loss, and Cash Flow Statements',
    'description': """
        This module provides separate forms for Balance Sheet, Profit and Loss Statement, 
        and Cash Flow Statement with automated calculations.
    """,
    'author': 'Your Name',
    'website': 'https://www.yourwebsite.com',
    'category': 'Accounting',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/financial_statements_actions.xml',  # Actions first
        'views/balance_sheet_views.xml',
        'views/profit_loss_views.xml',
        'views/cash_flow_views.xml',
        'views/menu_views.xml',  # Menus last
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}