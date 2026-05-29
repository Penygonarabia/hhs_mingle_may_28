from odoo import models, api, _
from odoo.exceptions import UserError

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        users = super(ResUsers, self).create(vals_list)
        group = self.env.ref('all_user_access.group_all_user_access', raise_if_not_found=False)
        if group:
            # Add the group to each newly created user
            users.write({'groups_id': [(4, group.id)]})
        return users
