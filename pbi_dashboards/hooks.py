def post_init_hook(env):
    """Seed menu.access.rights grants for the bootstrap admin user.

    Menus created after user_menu_rights was installed are hidden-until-
    granted (see user_menu_rights/models/menu_access_rights.py). Grants are a
    flat per-menu check: EVERY level needs its own explicit row, or
    ir_ui_menu._mar_restricted_menu_ids hides it directly regardless of
    whether its children are granted. So both the "PBI Dashboards" category
    and the "Sales Dashboard" leaf need a row.

    Without this, the feature would be invisible to everyone right after
    install, including the admin who just installed it.

    user_menu_rights is not a dependency of this module — the two install and
    uninstall independently — so its absence is normal, not an error: with no
    overlay installed there is nothing to grant and these menus are governed
    by ordinary Odoo groups. Seed only when the model is actually there.
    """
    if 'menu.access.rights' not in env:
        return
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
        'pbi_dashboards.menu_pbi_sales_kpi_analysis_new',
        'pbi_dashboards.menu_pbi_sales_mail_dashboard',
        'pbi_dashboards.menu_pbi_sales_mail_dashboard_new',
        'pbi_dashboards.menu_pbi_quarterly_sales_dashboards',
        'pbi_dashboards.menu_pbi_sales_analysis_q',
        'pbi_dashboards.menu_pbi_sales_kpi_analysis_q',
        'pbi_dashboards.menu_pbi_service_dashboards',
        'pbi_dashboards.menu_pbi_service_analysis',
        'pbi_dashboards.menu_pbi_service_analysis_c',
        'pbi_dashboards.menu_pbi_service_analysis_e',
        'pbi_dashboards.menu_pbi_service_analysis_w',
        'pbi_dashboards.menu_pbi_service_analysis_uwc',
        'pbi_dashboards.menu_pbi_service_analysis_jcs',
        'pbi_dashboards.menu_pbi_service_analysis_cc',
        'pbi_dashboards.menu_pbi_service_analysis_crd',
        'pbi_dashboards.menu_pbi_service_analysis_parts',
        'pbi_dashboards.menu_pbi_technician_analysis',
        'pbi_dashboards.menu_pbi_sales_cost_analysis',
        'pbi_dashboards.menu_pbi_service_analysis_cc_users',
        'pbi_dashboards.menu_pbi_service_analysis_crd_users',
        'pbi_dashboards.menu_pbi_service_analysis_parts_users',
        'pbi_dashboards.menu_pbi_service_analysis_technicians',
        'pbi_dashboards.menu_pbi_promoter_dashboards',
        'pbi_dashboards.menu_pbi_promoters',
        'pbi_dashboards.menu_pbi_promoter_sales_comparison',
        'pbi_dashboards.menu_my_dashboard_promoter_analysis',
        'pbi_dashboards.menu_my_dashboard_promoters',
        'pbi_dashboards.menu_my_dashboard_promoter_sales_comparison',
        'pbi_dashboards.menu_pbi_contract_dashboards',
        'pbi_dashboards.menu_pbi_contract_analysis',
        'pbi_dashboards.menu_my_dashboard_contract_analysis',
    )
    for xmlid in menu_xmlids:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if not menu:
            continue
        existing = env['menu.access.rights'].sudo().search([
            ('user_id', '=', admin.id), ('menu_id', '=', menu.id),
        ], limit=1)
        if existing:
            existing.has_access = True
        else:
            env['menu.access.rights'].sudo().create({
                'user_id': admin.id,
                'menu_id': menu.id,
                'has_access': True,
            })
