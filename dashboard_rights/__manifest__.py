{
    "name": "Dashboard Rights",
    "version": "17.0.1.0.25",
    "category": "Settings",
    "summary": "Per-user, per-dashboard access rights (Settings page).",
    "description": """
Dashboard Rights
================

New, independent module (does NOT use dashboard_user_rights_roles).

Adds a Settings menu page "Dashboard Rights" that lets an administrator pick
a dashboard category (Service Dashboards, Contract Dashboards, ...) and tick
which dashboards each user is allowed to see/use.

* Persistent model: ``dashboard.rights`` (user x dashboard x has_access).
* Defaults: every checkbox unticked for every non-admin user.
* Admin: always has access to every dashboard (checkboxes ticked & readonly).
* Enforcement: dashboards are hidden in menus and their action access is
  blocked server-side for users without the right.
""",
    "author": "Cielo Digital",
    # Drop the cached web.assets_* bundle on install AND on every upgrade (see
    # hooks.py + migrations/17.0.1.0.19/) so CSS/JS changes to the matrix — the
    # Has-Access column-width lock in particular — actually take effect via a
    # plain -u, instead of silently serving the stale compiled bundle. Column
    # widths are a JS/CSS-renderer concern and can't be fixed in Python/XML.
    "post_init_hook": "post_init_hook",
    "depends": [
        "base",
        "ks_dashboard_ninja",
    ],
    "data": [
        "security/dashboard_rights_groups.xml",
        "security/ir.model.access.csv",
        # NB: data/dashboard_rights_menus_data.xml (which created placeholder
        # "Quick Access"/"Configuration" KS boards) is intentionally NOT loaded.
        # Those boards are excluded from the matrix anyway, and creating a
        # ks_dashboard board via XML fails on this ks_dashboard_ninja build
        # (missing static/images/dashboardOverview/defaultDashboard.png), which
        # blocked reinstall. The quick_access_menu/configuration_menu xmlids the
        # rest of the module references are governed independently.
        "views/dashboard_rights_views.xml",
        "views/dashboard_rights_matrix_views.xml",
        "views/dashboard_rights_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "dashboard_rights/static/src/css/dashboard_rights_matrix.css",
            "dashboard_rights/static/src/xml/grouped_user_list.xml",
            "dashboard_rights/static/src/xml/dashboard_rights_list.xml",
            "dashboard_rights/static/src/xml/dashboard_bulk_buttons.xml",
            "dashboard_rights/static/src/xml/header_status_gate.xml",
            "dashboard_rights/static/src/xml/parent_breadcrumb_restore.xml",
            "dashboard_rights/static/src/js/grouped_user_list.js",
            "dashboard_rights/static/src/js/email_copy_field.js",
            "dashboard_rights/static/src/js/email_id_copy_field.js",
            "dashboard_rights/static/src/js/dashboard_rights_list.js",
            "dashboard_rights/static/src/js/dashboard_rights_matrix_list.js",
            "dashboard_rights/static/src/js/dashboard_bulk_buttons.js",
            "dashboard_rights/static/src/js/users_tab_refresh.js",
            "dashboard_rights/static/src/js/header_status_gate.js",
            "dashboard_rights/static/src/js/parent_breadcrumb_restore.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
