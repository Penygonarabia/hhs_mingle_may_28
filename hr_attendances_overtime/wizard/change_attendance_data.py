# See LICENSE file for full copyright and licensing details

from odoo import models, fields


class HrChangeAttendance(models.TransientModel):
    """Wizard to change differnt late_in nad overtime."""

    _name = 'hr.change.attendance'
    _description = "change attendance data"

    overtime = fields.Float("Overtime")
    latein = fields.Float("Late in")
    difftime = fields.Float(string='Time Different')
    reason = fields.Text("Reason for Changing")

    def apply_changes(self):
        """Appled Changes."""
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        get_changes = self.env[active_model].browse(active_id)
        get_changes.update({'overtime': self.overtime,
                            'latein': self.latein,
                            'difftime': self.difftime,
                            'note': self.reason})
