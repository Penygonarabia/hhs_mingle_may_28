# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models,api, _
from odoo.exceptions import ValidationError

class ModelApproval(models.Model):
    _name = "model.approval"
    _description = "Model Approval"
    _rec_name = "model_id"

    model_id = fields.Many2one('ir.model', string='Model', domain=[('model','in',['sale.order', 'purchase.order', 'account.move', 'account.payment', 'service.sale.order'])], required=True, ondelete='cascade')
    approval_ids = fields.Many2many('approval.approval', string="Approvals", required=True)
    active = fields.Boolean('Active', default=True)

    
    @api.model_create_multi
    def create(self, values):
        for val in values:
            if val.get('model_id'):
                old_data = self.search([('model_id', '=', val.get('model_id'))])
                if old_data:
                    raise ValidationError('Approval configuration already created for same model!')
        return super(ModelApproval, self).create(values)
    
    def write(self, values):
        for record in self:
            if values.get('model_id'):
                old_data = self.search([('model_id', '=', values.get('model_id'))])
                if old_data:
                    raise ValidationError('Approval configuration already created for same model!')
        return super(ModelApproval, self).write(values)
