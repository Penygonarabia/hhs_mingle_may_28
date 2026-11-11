# # -*- coding: utf-8 -*-
# # Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
#
# from odoo import fields, models
#
#
# class ApprovalLine(models.Model):
#     _name = "approval.approval.line"
#     _description = "Approval Line"
#     _order = 'level'
#     _rec_name = 'level'
#
#
#     group_approve = fields.Selection(string='Approve Process By', selection=[
#                                      ('group', 'Group'), ('user', 'User')], default="user")
#     level = fields.Integer(string='Level')
#     group_ids = fields.Many2many(
#         string='Group Name', comodel_name='res.groups', ondelete='restrict')
#     user_ids = fields.Many2many('res.users')
#     approval_id = fields.Many2one('approval.approval', string='Approvals')
# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ApprovalLineUserSequence(models.Model):
    """
    Relation model that replaces the flat user_ids Many2many.
    Each row = one user at this approval level, with an explicit sequence
    number so the admin controls exactly who approves first, second, etc.
    """
    _name = "approval.line.user.sequence"
    _description = "Approval Line User Sequence"
    _order = "sequence, id"

    line_id = fields.Many2one(
        'approval.approval.line',
        string='Approval Line',
        required=True,
        ondelete='cascade',
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(
        string='Sequence',
        default=1,
        help="Approval order within this level. Lower number approves first.",
    )


class ApprovalLine(models.Model):
    _name = "approval.approval.line"
    _description = "Approval Line"
    _order = 'level'
    _rec_name = 'level'

    group_approve = fields.Selection(
        string='Approve Process By',
        selection=[('group', 'Group'), ('user', 'User')],
        default="user",
    )
    level = fields.Integer(string='Level')
    group_ids = fields.Many2many(
        string='Group Name', comodel_name='res.groups', ondelete='restrict')
    approval_id = fields.Many2one('approval.approval', string='Approvals')

    # Replaces the old flat user_ids Many2many — now carries a sequence field
    user_sequence_ids = fields.One2many(
        'approval.line.user.sequence', 'line_id',
        string='Users (with Approval Order)',
    )

    # Kept for backward compat — computed from user_sequence_ids
    user_ids = fields.Many2many(
        'res.users',
        compute='_compute_user_ids',
        store=True,
        string='Users',
    )

    @api.depends('user_sequence_ids', 'user_sequence_ids.user_id')
    def _compute_user_ids(self):
        for rec in self:
            rec.user_ids = rec.user_sequence_ids.mapped('user_id')



