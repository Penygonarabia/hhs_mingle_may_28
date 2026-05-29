# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AnalyticLine(models.Model):
    _inherit = "account.analytic.line"
    
    repair_request_id = fields.Many2one(
        'machine.repair.support',
        string="Repair Request"
    )
    
    project_request_id = fields.Many2one(
        'project.task',
        string="Job Card Request"
    )

#    @api.multi odoo13 Not Used
#    @api.onchange('repair_request_id', 'repair_request_id.analytic_account_id')
#    def account_id_change(self):
#        for rec in self:
#            rec.account_id = rec.repair_request_id.analytic_account_id.id
