{
    'name': 'HHS Contract Payment Terms',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Adds a Payment Terms tab with auto-generated payment schedule to Contracts',
    'description': """
        Extends the Subscription Contracts module to add a Payment Terms tab.
        - Auto-generates payment schedule lines based on contract value, frequency, and installments.
        - Shows Annual Contract Value (including VAT).
        - Displays individual payment dates and amounts.
        - Includes late payment policy note.
    """,
    'author': 'HHS',
    'depends': [
        'sales_contract_and_recurring_invoices',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/contract_payment_terms_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
