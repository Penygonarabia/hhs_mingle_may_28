{
    'name': 'Service Sale Order Approvals',
    'version': '17.0.1.0.0',
    'summary': 'Dynamic approval workflow for Service Sale Orders',
    'author': 'Raj Ganesh',
    'website': '',
    'category': 'Sales/Service',
    'depends': ['base', 'mail', 'machine_repair_management', 'bi_all_in_one_dynamic_approval',],
    'data': [
        'security/ir.model.access.csv',
        'views/service_sale_order_views.xml',
        'views/service_sale_order_approved_views.xml',
        'wizard/service_sale_order_reject_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
