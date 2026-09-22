# -*- coding: utf-8 -*-
{
    'name': 'Menu & Submenu Search Bar',
    'version': '17.0.1.0.0',
    'summary': 'Search option for menu and sub-menu at any level with clear button in the sidebar menu',
    'description': """
        Menu & Submenu Search Bar
        =========================
        - Fast search for menus and sub-menus at any level (root, 2nd, 3rd, 4th+ level)
        - Search input control with clear 'x' button
        - Positioned at the top of the sidebar, under the company logo and above the menu list
        - Displays full breadcrumb hierarchy paths for easy discovery
        - Keyboard navigation (Arrow keys, Enter, Escape)
        - Instant 1-click navigation to any target view/menu
    """,
    'category': 'Extra Tools',
    'author': 'Antigravity',
    'website': 'https://github.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'clarity_backend_theme_bits'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'menu_search_bar/static/src/scss/menu_search.scss',
            'menu_search_bar/static/src/xml/menu_search.xml',
            'menu_search_bar/static/src/js/menu_search.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
