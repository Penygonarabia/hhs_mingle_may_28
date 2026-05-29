# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ApprovalLine(models.Model):
    _name = "approval.approval.line"
    _description = "Approval Line"
    _order = 'level'
    _rec_name = 'level'
    

    group_approve = fields.Selection(string='Approve Process By', selection=[
                                     ('group', 'Group'), ('user', 'User')], default="user")
    level = fields.Integer(string='Level')
    group_ids = fields.Many2many(
        string='Group Name', comodel_name='res.groups', ondelete='restrict')
    user_ids = fields.Many2many('res.users')
    approval_id = fields.Many2one('approval.approval', string='Approvals')
