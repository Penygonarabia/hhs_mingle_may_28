# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models,api, _


class InvoiceLineApproval(models.Model):
    _name = "invoice.line.approval"
    _description = "Invoice/Bill approved details"
    _rec_name = 'approval_level'

    approval_level = fields.Integer('Approval Level')
    user_ids = fields.Many2many('res.users', string='Users')
    group_ids = fields.Many2many('res.groups', string='Groups')
    state = fields.Boolean('State')
    approved_date = fields.Datetime('Approved Date')
    approved_id = fields.Many2one('res.users', string='Approved By')
    invoice_approval_id = fields.Many2one('approval.approval', string='Sale Approval')
    order_id = fields.Many2one('account.move', string='Order')
