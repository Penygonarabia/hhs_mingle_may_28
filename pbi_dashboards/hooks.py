def post_init_hook(env):
    """Seed dashboard.rights.menu grants for the bootstrap admin user.

    New menus under My Dashboard are hidden-until-granted (see
    dashboard_rights/models/dashboard_rights_menu.py). Unlike ks_dashboard_ninja
    boards (which get a "must keep visible" walk-up to their ancestors once
    granted), plain menus are governed by a flat managed-menu check: EVERY
    level needs its own explicit grant row, or ir_ui_menu._dr_restricted_menu_ids
    hides it directly regardless of whether its children are granted. So both
    the "PBI Dashboards" category and the "Sales Dashboard" leaf need a row.

    Without this, the feature would be invisible to everyone right after
    install, including the admin who just installed it.
    """
    admin = env.ref('base.user_admin', raise_if_not_found=False)
    if not admin:
        return
    menu_xmlids = (
        'pbi_dashboards.pbi_dashboards_app_root',
        'pbi_dashboards.menu_pbi_sales_dashboard_app',
        'pbi_dashboards.menu_pbi_loyalty_dashboards',
        'pbi_dashboards.menu_pbi_loyalty_analysis',
        'pbi_dashboards.menu_pbi_sales_analysis',
        'pbi_dashboards.menu_pbi_sales_dashboards',
        'pbi_dashboards.menu_pbi_sales_kpi_analysis',
    )
    for xmlid in menu_xmlids:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if not menu:
            continue
        existing = env['dashboard.rights.menu'].sudo().search([
            ('user_id', '=', admin.id), ('menu_id', '=', menu.id),
        ], limit=1)
        if existing:
            existing.has_access = True
        else:
            env['dashboard.rights.menu'].sudo().create({
                'user_id': admin.id,
                'menu_id': menu.id,
                'has_access': True,
            })
