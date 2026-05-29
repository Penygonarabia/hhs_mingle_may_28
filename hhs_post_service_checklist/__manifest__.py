{
    'name': 'HHS Post Service Checklist Template',
    'version': '17.0.1.0.0',
    'category': 'Maintenance',
    'summary': 'Post Service Checklist Template Setup for AC Units',
    'description': """
        Post Service Checklist Template module for HHS.
        - Setup checklist templates per Product Category and Product Group
        - Supports field types: Yes/No, Multiple Options, Numeric, Text, Calculated
        - Multiple options master for dynamic selection lists
        - Copy checklist from one product group to another
        - Groups/sections within checklists
    """,
    'author': 'HHS',
    'depends': ['product','crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/checklist_template_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
