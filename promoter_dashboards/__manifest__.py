{
    'name': 'Promoter Dashboards',
    'version': '17.0.1.0.2',
    'category': 'Sales/Dashboard',
    'summary': 'Promoter dashboards under My Dashboard',
    'description': """
Promoter Dashboards
===================
Ships three KS Dashboard Ninja boards as JSON snapshots under
``data/`` and a post_init_hook that imports them on install:

  * Promoters Analysis            (data/promoters_analysis.json)
  * Sales Comparison (Actual vs Target)  (data/promoter_sales_comparison.json)
  * Sales Target                  (data/sales_target.json)

After import the hook reparents each board's auto-created menu under
"My Dashboard > Promoter Dashboards" and adopts the menu xmlids into
this module so subsequent module upgrades respect them.

The boards source data from `sales.target`, `sales_target_views` and the
promoter showroom/assignment models defined in the `promoter` module —
both `promoter` and `ks_dashboard_ninja` are listed as hard dependencies
so install order is deterministic.
""",
    'author': 'Cielo Digital',
    'depends': [
        # promoter owns the sales.target / promoter.showroom models the
        # dashboards aggregate over.
        'promoter',
        # ks_dashboard_ninja owns the parent menu (promoter_dashboards_menu_root)
        # and the ks_import_dashboard() API the hook calls.
        'ks_dashboard_ninja',
    ],
    'data': [
        # Menu shell — currently empty (the post_init_hook creates and
        # adopts the per-board menus). Kept on disk so the parent
        # promoter_dashboards_menu_root has at least one child guaranteed by
        # the manifest in case someone uninstalls the imported boards.
        'views/promoter_dashboard_menus.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
