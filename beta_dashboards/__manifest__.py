{
    'name': 'Beta Dashboards',
    'version': '17.0.1.0.0',
    'category': 'Services/Dashboard',
    'summary': 'Beta dashboards (experimental boards) under My Dashboard',
    'description': """
Beta Dashboards
===============
Thin menu-shell module that owns the "Beta Dashboards" parent menu under
"My Dashboard". Experimental / WIP KS Dashboard Ninja boards (e.g. "beta1")
are placed under this menu while they're being validated, before being
promoted into one of the production dashboard modules.

This module deliberately ships no boards or items in its data XML — beta
boards are imported live via the KS Dashboard Ninja Import wizard so the
team can iterate on them without going through a module upgrade cycle.
""",
    'author': 'Cielo Digital',
    'depends': [
        # ks_dashboard_ninja owns the parent menu (board_menu_root) this
        # module's "Beta Dashboards" menu attaches to.
        'ks_dashboard_ninja',
    ],
    'data': [
        'views/beta_dashboards_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
