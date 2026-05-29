{
    'name': 'AMC Quotation Report',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Custom AMC Quotation QWeb Report for Service Sale Orders',
    'description': 'Provides a beautifully styled custom PDF quotation for Annual Maintenance Contracts.',
    'author': 'Hussein and Al Hassan G. Shaker Bros',
    'depends': ['base', 'machine_repair_management'], # Assuming service.sale.order is handled by an existing custom module.
    'data': [
        #'reports/amc_quotation_action.xml',
        'reports/amc_quotation_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
