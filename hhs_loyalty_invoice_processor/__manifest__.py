{
    'name': 'HHS Loyalty Invoice & Promotion Processor',
    'version': '17.0.1.0.0',
    'category': 'Loyalty',
    'summary': 'Process ERP invoice/credit notes and calculate loyalty and promotion points.',
    'description': """
        Processes all imported ERP invoice and credit notes to calculate loyalty points and promotions.
        Builds loyalty history audit entries and logs any processing errors natively.
    """,
    'author': 'Antigravity AI / HHS Cloud',
    'depends': [
        'base',
        'regulartable_api',
        'hhs_loyalty_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/loyalty_invoice_processor_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
