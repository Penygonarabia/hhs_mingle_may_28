from odoo import fields, models
import json


class PromoterAssignmentConflictWizard(models.TransientModel):
    _name = "promoter.assignment.conflict.wizard"
    _description = "Promoter Assignment Conflict Wizard"

    conflict_text = fields.Text("Conflict Details", readonly=True)
    conflicting_assignment_id = fields.Many2one("promoter.assignment", string="Existing Assignment", readonly=True)
    pending_vals = fields.Text("Pending Values (internal use)")
    mode = fields.Selection([("create", "Create"), ("write", "Write")], default="create")
    record_id = fields.Integer("Record ID")

    def action_confirm(self):
        if self.conflicting_assignment_id:
            self.conflicting_assignment_id.write({"active": False})

        vals = json.loads(self.pending_vals or "{}")
        if self.mode == "create":
            self.env["promoter.assignment"].create(vals)
        else:
            record = self.env["promoter.assignment"].browse(self.record_id)
            if record.exists():
                record.write(vals)
        return {"type": "ir.actions.act_window_close"}

    def action_cancel(self):
        return {"type": "ir.actions.act_window_close"}

