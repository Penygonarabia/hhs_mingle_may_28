from odoo import api, fields, models , _

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    is_salesman = fields.Boolean(string = "Is Salesman", default = False)
    
    
    def write(self, vals):
        res = super().write(vals)
        if 'is_salesman' in vals:
            for partner in self:
                user = partner.user_ids and partner.user_ids[0]
                if user and user.is_salesman != partner.is_salesman:
                    user.with_context(skip_partner_sync=True).is_salesman = partner.is_salesman
        return res