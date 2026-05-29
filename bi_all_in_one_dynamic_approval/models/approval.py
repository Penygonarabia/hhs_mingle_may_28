# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models,api, _
from odoo.exceptions import ValidationError

class Approval(models.Model):
    _name = "approval.approval"
    _description = "Dynamic Approval"

    name = fields.Char(required=True, index=True, string="Name")
    minimum_amount = fields.Float(string='Minimum Amount')
    is_sale_person = fields.Boolean('Sales Person Always in CC')
    approval_line_ids = fields.One2many('approval.approval.line', 'approval_id', string='Approval Lines')

    @api.onchange('approval_line_ids')
    def _onchange_approval_line_ids(self):
        approval_level = []
        for approval in self.approval_line_ids:
            if approval.level in approval_level:
                raise ValidationError(_('Make sure approval levels are must be unique!'))
            approval_level.append(approval.level)
