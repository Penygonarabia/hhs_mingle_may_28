# -*- coding: utf-8 -*-

{
    'name': 'Zatca CRN For Multi Shops',
    'version': '17.0.1.0',
    'license': 'LGPL-3',
    'sequence': '0',
    'category': "Saudi Zatca Multi Branch CRN for Sinlge Company",
    'website': '',
    'author': 'Arunagiri K',
    'summary': 'Multi CRN Added in CRN ZATCA',
    'description': """
     Multi CRN For Single Company
""",
    'depends': ['base', 'account', 'l10n_sa_edi'],
    'data': [
        # Views
        'views/account_journal_views.xml',
        'views/res_company_view.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}