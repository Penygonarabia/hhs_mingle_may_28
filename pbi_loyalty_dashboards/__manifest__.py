{
    'name': 'PBI Loyalty Dashboards',
    'version': '17.0.2.1.0',
    'category': 'Sales/Dashboard',
    'summary': 'PBI Loyalty Dashboards & Loyalty Analysis',
    'author': 'Cielo Digital',
    # pbi_sales_dashboards dropped 2026-09-23: the Loyalty Customers Sales
    # Analysis dashboard used to read pbi_sales_dashboards'
    # v_pbi_sales_sman_fact for its Main/Sub-Category/Product Group/Product
    # Sub Group levels; loyalty_sales_analysis_main.py's own FC_CTE now
    # resolves the same 4 levels itself (catalog + product_category, no
    # read of anything that module owns) — see its module docstring. Base
    # .pbi-sales-dashboard styling comes from pbi_dashboards (kept below),
    # not from pbi_sales_dashboards, so nothing else here needed it either.
    'depends': [
        'pbi_dashboards',
        'loyalty_dashboard',
    ],
    'data': [
        'views/pbi_loyalty_dashboards_menus.xml',
    ],
    'assets': {
        # NOTE: Odoo's bundle hash (assetsbundle.py get_checksum) is built
        # from each asset's (url, last_modified) pair, and for a plain addon
        # static file (not go through ir.attachment) last_modified never
        # resolves and falls back to a constant -1 — so editing a file
        # already in this list, with no path added/removed/reordered, keeps
        # the SAME bundle hash/URL, and browsers holding that URL cached
        # (served with Cache-Control: immutable, max-age=1y) never re-fetch
        # it. The list's ORDER is part of the hashed string though, so
        # touching the order below (not just re-upgrading the module) is
        # what actually busts the cache for a content-only change to
        # loyalty_sales_analysis_dashboard.js/.xml — confirmed on dbprod
        # 2026-09-23: reordering these two lines changed 47f.../assets
        # hash even though their content, not their paths, was what changed.
        'web.assets_backend': [
            'pbi_loyalty_dashboards/static/src/js/loyalty_dashboard.js',
            'pbi_loyalty_dashboards/static/src/xml/loyalty_dashboard.xml',
            'pbi_loyalty_dashboards/static/src/css/loyalty_dashboard.css',
            'pbi_loyalty_dashboards/static/src/js/loyalty_sales_analysis_dashboard.js',
            'pbi_loyalty_dashboards/static/src/xml/loyalty_sales_analysis_dashboard.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
