# models/promoter_assignment_confirm.py
from odoo import models, fields, api

class PromoterAssignmentConfirm(models.TransientModel):
    _name = 'promoter.assignment.confirm'
    _description = 'Confirm Overlapping Assignment'

    overlapping_ids = fields.Many2many('promoter.assignment', string="Overlapping Assignments")
    new_assignment_id = fields.Many2one('promoter.assignment', string="New Assignment")

    def action_confirm_override(self):
        self.overlapping_ids.write({'active': False})
        self.new_assignment_id.write({'active': True})
        return {'type': 'ir.actions.act_window_close'}