from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MachineRepairSupportSymptoms(models.Model):
    _name = "machine.repair.support.symptoms"
    _description = "Machine Repair Support Symptoms"

    machine_repair_support_id = fields.Many2one('machine.repair.support', string="Symptom Service")
    sym_id = fields.Many2one('symptoms', string="Symptoms")

    @api.constrains('sym_id', 'machine_repair_support_id')
    def _check_symptoms(self):
        for rec in self:
            if rec.sym_id and rec.machine_repair_support_id: 
                symptom_search = self.env['machine.repair.support.symptoms'].search([
                    ('sym_id', '=', rec.sym_id.id),
                    ('machine_repair_support_id', '=', rec.machine_repair_support_id.id),
                    ('id', '!=', rec.id)
                ], limit=1)  
                if symptom_search:
                    raise ValidationError("This symptom is already added. Please select a different one.")