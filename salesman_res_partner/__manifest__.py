{
    'name': 'Salesman Res Partner',
    'version': '17.0.1.0.0',
    'summary': """Manage the company properties when it is in the custody of an employee""",
    'description': 'Manage the company properties when it is in the custody of an employee',
    'category': 'Generic Modules/Human Resources',
    'author': 'Penygonarabia',
   
    'depends': ['base'],
    'data': [
        'views/res_partner_views.xml',
        'views/res_users_views.xml'
       
    ],
    
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
