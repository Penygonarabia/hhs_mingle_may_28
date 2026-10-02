# -*- coding: utf-8 -*-
from odoo import fields, models, api

class ModelApprovalInherit(models.Model):
    _inherit = 'model.approval'

    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        domain="[('model', 'in', ['sale.order', 'purchase.order', 'account.move', 'account.payment', 'service.sale.order', 'crm.commercial.lead', 'crm.commercial.quotation'])]",
        required=True,
        ondelete='cascade'
    )
