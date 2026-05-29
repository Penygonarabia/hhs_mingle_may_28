# -*- coding: utf-8 -*-
from odoo import fields, models

class ServiceSaleApproval(models.Model):
    _name = "service.sale.order.approved"
    _description = "Service Sale order approved details"
    _rec_name = 'approval_level'

    approval_level = fields.Integer('Approval Level')
    user_ids = fields.Many2many('res.users', string='Users')
    group_ids = fields.Many2many('res.groups', string='Groups')
    state = fields.Boolean('State')
    approved_date = fields.Datetime('Approved Date')
    approved_id = fields.Many2one('res.users', string='Approved By')
    service_sale_approval_id = fields.Many2one('approval.approval', string='Service Sale Approval')
    order_id = fields.Many2one('service.sale.order', string='Order')
