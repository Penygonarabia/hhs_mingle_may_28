from odoo import models, fields, api

class ConfirmPromoterOverride(models.TransientModel):
    _name = 'confirm.promoter.override'
    _description = 'Confirm Promoter Assignment Override'

    conflict_message = fields.Html(
        string='',
        readonly=True,
        default=lambda self: (
            "<div style='color:#b94a48; font-weight:bold;'>"
            "⚠️ This promoter is already assigned in this time period.<br/>"
            "Do you want to continue?"
            "</div>"
        )
    )

    conflicting_assignment_id = fields.Many2one(
        'promoter.assignment',
        string="Conflicting Assignment",
        readonly=True
    )

    new_assignment_id = fields.Many2one(
        'promoter.assignment',
        string="New Assignment",
        readonly=True
    )

    @api.model
    def default_get(self, fields_list):
        """Pre-fill the wizard with conflicting and new assignment IDs from context."""
        res = super().default_get(fields_list)
        res['conflicting_assignment_id'] = self.env.context.get('default_conflicting_assignment_id')
        res['new_assignment_id'] = self.env.context.get('default_new_assignment_id')
        return res

    def confirm_override(self):
        """Deactivate the conflicting assignment and activate the new one."""
        self.ensure_one()

        if self.conflicting_assignment_id:
            self.conflicting_assignment_id.active = False

        if self.new_assignment_id:
            self.new_assignment_id.active = True

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Override Successful',
                'message': 'The conflicting assignment was deactivated and the new one activated.',
                'type': 'success',
                'sticky': False,
            }
        }
