{
    'name': 'Res Partner Loyalty Management',
    'version': '1.0',
    'category': 'res partner',
    'summary': 'Manage customer loyalty points and transactions with a feature toggle.',
    'description': """
Loyalty Management Module
=========================
Features:
- Enable/Disable Loyalty Program from Settings.
- Customer Loyalty Points tracking.
- Loyalty Transaction history (Earn/Redeem).
- Integration with Sales and Invoicing.
    """,
    'author': 'Kartheeswaran A',
    'depends': ['base', 'hhs_loyalty_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner.xml'
    ],
    'installable': True,
    'application': True,
}
