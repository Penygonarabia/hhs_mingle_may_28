from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class ResUsers(models.Model):
    _inherit = "res.users"

    dealer_salesman = fields.Boolean(
        string="Dealer Salesman",
        default=False
    )

    floor_sales_approval_auth = fields.Boolean(
        string="Floor Sales Approval Auth",
        default=False
    )

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        group = self.env.ref('dealer.group_floor_sales_approval', raise_if_not_found=False)
        if group:
            for user in users:
                if user.floor_sales_approval_auth:
                    group.sudo().write({'users': [(4, user.id)]})
        return users

    def write(self, vals):
        res = super().write(vals)
        if 'floor_sales_approval_auth' in vals:
            group = self.env.ref('dealer.group_floor_sales_approval', raise_if_not_found=False)
            if group:
                for user in self:
                    if user.floor_sales_approval_auth:
                        group.sudo().write({'users': [(4, user.id)]})
                    else:
                        group.sudo().write({'users': [(3, user.id)]})
        return res

    default_authority = fields.Boolean(string="Default Authority", default=False)
    
    # Legacy field removed to prevent UndefinedColumn error

    @api.constrains('default_authority')
    def _check_single_default_authority(self):
        for record in self:
            if record.default_authority:
                if self.search_count([('default_authority', '=', True)]) > 1:
                    raise UserError(_("Only one Default Authority user is allowed for the whole project."))


    dealer_city_id = fields.Many2one(
        'res.city',
        string="Working City"
    )

    dealer_showroom_id=fields.Many2one(
        'dsales.showroom',
        string='Dealer Showroom'
    )
    
    @api.onchange('dealer_salesman')
    def _onchange_dealer_salesman(self):
        if not self.dealer_salesman:
            self.dealer_city_id = False

