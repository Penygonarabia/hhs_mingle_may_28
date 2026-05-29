from odoo import api, fields, models, _, re
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class ServiceWarranty(models.Model):
    _name = "service.warranty"
    _description = "Service Warranty"

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.user.company_id
    )
    warranty_applicable_bool = fields.Boolean(
        string="Warranty Applicable", default=False
    )
    misuse_warranty_bool = fields.Boolean(string="Mis-Use Warranty", default=False)
    customer_need_quote_hide_bool = fields.Boolean(
        string="Customer Need Quote Hide",
        default=False,
    )
    job_card_status_hide = fields.Char(string="Job Card Status Hide")
    """Code Added by Vengatesh On Mar 25 2026"""
    amount_required = fields.Boolean(string="Amount Required", default=False)
    
    '''Code Added on May 05 2026 by Vijaya Bhaskar'''
    warranty_expire_alert_bool = fields.Boolean(string = "Warranty Expire Alert Y/N", default = False, help = "Warranty Expire Alert Shown or Not")
    

    @api.constrains("code")
    def _valid_check_service_warranty_code(self):
        for rec in self:
            warranty_search = self.env["service.warranty"].search(
                [("code", "=", rec.code), ("id", "!=", rec.id)]
            )
            if len(warranty_search) > 1:
                raise ValidationError("Service Warranty Code must be unique")


