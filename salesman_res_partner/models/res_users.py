from odoo import api, fields, models, _

class ResUsers(models.Model):
    
    _inherit = "res.users"
    
    is_salesman = fields.Boolean(string = "Is SalesMan", default = False)
    
    
    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        for user in users:
            if user.partner_id:
                user.partner_id.is_salesman = user.is_salesman
        return users

    def write(self, vals):
        res = super().write(vals)
        if 'is_salesman' in vals and not self.env.context.get('skip_partner_sync'):
            for user in self:
                if user.partner_id and user.partner_id.is_salesman != user.is_salesman:
                    user.partner_id.with_context(skip_partner_sync=True).write({'is_salesman': user.is_salesman})
        return res