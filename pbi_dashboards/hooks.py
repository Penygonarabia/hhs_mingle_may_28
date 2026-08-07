def post_init_hook(env):
    """Seed menu.access.rights grant for the bootstrap admin user for the root menu."""
    if 'menu.access.rights' not in env:
        return
    admin = env.ref('base.user_admin', raise_if_not_found=False)
    if not admin:
        return
    menu = env.ref('pbi_dashboards.pbi_dashboards_app_root', raise_if_not_found=False)
    if menu:
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
