from odoo import api, SUPERUSER_ID

def post_init_assign_group(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    group = env.ref('all_user_access.group_all_user_access', raise_if_not_found=False)
    if not group:
        return
    users = env['res.users'].search([])
    if users:
        users.write({'groups_id': [(4, group.id)]})
