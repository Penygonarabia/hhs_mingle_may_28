# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    dynamic_approval = fields.Boolean(
        string='Dynamic Approval', related='company_id.dynamic_approval', readonly=False)
    approval_type = fields.Selection(string='Approval Type', related='company_id.approval_type', readonly=False)
    group_access_for_bill = fields.Boolean(string='On Vendor Bill',related='company_id.group_access_for_bill', default=False,readonly=False)
    group_access_for_invoice = fields.Boolean(string='On Customer Invoice',related='company_id.group_access_for_invoice' ,default=False,readonly=False)

    @api.onchange('dynamic_approval')
    def _onchange_dynamic_approval(self):
        if not self.dynamic_approval:
            self.approval_type = False
            self.group_access_for_bill = False
            self.group_access_for_invoice = False
        if self.dynamic_approval and not self.approval_type:
            self.approval_type = 'total'