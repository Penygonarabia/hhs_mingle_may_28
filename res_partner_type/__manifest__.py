

{
    'name': "Partner Type",

    'summary': """
         Res Partner Types""",

    'author': "RajGanesh",
    'category': 'res.partner',
    'version': '17.0',
    "license": "LGPL-3",
    'depends': ['base', 'account', 'sale', 'product'],
    'data': [
       "views/res_partner_views.xml",
       "views/account_move_partner_type_views.xml",
    ],

    
}
