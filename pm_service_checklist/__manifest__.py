{
    'name': 'PM Service Checklist',
    'version': '1.0',
    'category': 'Services',
    'summary': 'Adds PM Service Checklist tab to Service Sale Orders',
    'description': """
        This module introduces a new tab "PM Service Check List" in service sale orders
        with dynamic data population and validations based on PM Service Master configuration.
    """,
    'author': 'Antigravity',
    'depends': ['base', 'service_sale_approvals', 'hhs_amc_quotation', 'hhs_pm_service'],
    'data': [
        'security/ir.model.access.csv',
        'views/service_sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}