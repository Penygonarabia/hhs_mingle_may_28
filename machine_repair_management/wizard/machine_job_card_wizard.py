from odoo import api, fields, models, _


class MachineJobCard(models.TransientModel):
    _name = "job.card.wizard"
    _description = "Machine Job Card Wizard"

    task_ids = fields.Many2many('project.task')

    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}
