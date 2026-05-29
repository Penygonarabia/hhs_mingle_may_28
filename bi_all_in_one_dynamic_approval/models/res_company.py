# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    approval_type = fields.Selection([
        ('total', 'Total'),
        ('before_tax_amount', 'Before Tax Amount'),
    ], string='Approval Type', default="total")
    dynamic_approval = fields.Boolean(string='Dynamic Approval', default=False)
    group_access_for_bill = fields.Boolean(string='On Vendor Bill',implied_group="bi_all_in_one_dynamic_approval.group_access_for_bill", default=False)
    group_access_for_invoice = fields.Boolean(string='On Customer Invoice', implied_group="bi_all_in_one_dynamic_approval.group_access_for_invoice",default=False)

    def _valid_field_parameter(self, field, name):
        # EXTENDS models
        return name == 'implied_group' or super()._valid_field_parameter(field, name)
