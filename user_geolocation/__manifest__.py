{
    'name': 'User Geolocation',
    'version': '1.0',
    'category': 'Tools',
    'summary': 'Capture and display the login user location',
    'description': 'This module captures the login user latitude and longitude using the browser geolocation API and shows it in the user form with a map.',
    'author': 'Raj Ganesh',
    'depends': ['base', 'web'],
    'data': [
        # 'views/assets.xml',
        'views/res_users_view.xml',
    ],
    'assets': {
        'web.assets_web': [
            'user_geolocation/static/src/js/user_location.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}