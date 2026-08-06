{
    'name': "Partner Classification",
    'summary': """
         Partner type Classification""",
    'author': "Penygonarabia",
    'category': 'res.partner',
    'version': '17.0',
    "license": "LGPL-3",
    'depends': ['base','partner_type_hhs','sale'],
    'data': [
          'security/ir.model.access.csv',
          'views/partner_classification_views.xml',
          'views/res_partner_views.xml',
    ],

    
}
