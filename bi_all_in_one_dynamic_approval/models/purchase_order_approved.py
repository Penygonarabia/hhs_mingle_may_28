# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models,api, _


class PurchaseApproval(models.Model):
    _name = "purchase.order.approved"
    _description = "Purchase order approved details"
    _rec_name = 'approval_level'

    approval_level = fields.Integer('Approval Level')
    user_ids = fields.Many2many('res.users', string='Users')
    group_ids = fields.Many2many('res.groups', string='Groups')
    state = fields.Boolean('State')
    approved_date = fields.Datetime('Approved Date')
    approved_id = fields.Many2one('res.users', string='Approved By')
    purchase_approval_id = fields.Many2one('approval.approval', string='Purchase Approval')
    order_id = fields.Many2one('purchase.order', string='Order')
