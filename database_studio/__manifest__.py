{
    'name': 'Database Studio',
    'summary': 'Browse tables/views, inspect field mappings, and run SQL queries',
    'description': """
Database Studio
===============
Adds a "Database Studio" menu with an "Analyser" tool that lets authorised
users:

* Browse existing tables and views (grouped, searchable, multi-select) on the left.
* Inspect a selected object's fields (name / type / precision or length / nullable) with copy-all.
* See the field mapping (foreign-key relationships) for the selected table(s).
* Build, format and execute SQL like a query analyser, with keyword highlighting,
  run-the-selection, and a paginated, copyable result grid.
* Save/star queries and browse them in a History list.

Restricted to database administrators.
""",
    'author': 'Saravanan',
    'category': 'Technical',
    'version': '17.0.2.0.0',
    'depends': ['web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/database_studio_menus.xml',
        'views/database_studio_query_views.xml',
        'views/database_studio_relation_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'database_studio/static/src/css/database_studio.css',
            'database_studio/static/src/js/database_studio_analyser.js',
            'database_studio/static/src/js/database_studio_history_list.js',
            'database_studio/static/src/xml/database_studio.xml',
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
