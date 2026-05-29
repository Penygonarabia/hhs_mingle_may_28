{
    'name': 'HHS AMC Price Calculation',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'AMC Costing Template for HVAC Maintenance Contracts',
    'description': """
        AMC Price Calculation module for HHS.
        - Create costing templates for Semi/Full Comprehensive contracts
        - Auto-calculate costs from product catalog
        - Support for category and brand filtering
    """,
    'author': 'HHS',
    'depends': ['product', 'sale', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/amc_pricing_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
