{
    'name': 'HHS AMC Quotation',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'AMC Quotation extensions and calculations',
    'description': """
        Extends the Machine Repair Management module for AMC Quotation specific fields and calculations.
        - Adds Brand and Contract Type
        - Connects to AMC Pricing templates
        - Auto-calculates Spare parts cost, Selling Price, and per Unit pricing.
    """,
    'author': 'HHS',
    'depends': [
       'machine_repair_management','service_sale_order_revision',
        'hhs_amc_pricing',
        'sales_contract_and_recurring_invoices',
        'crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/service_sale_order_views.xml',
        'views/amc_scope_of_work_views.xml',
        'views/crm_sales_quotation_scope_work_views.xml', 
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
