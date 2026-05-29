from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class CancelledReasonWizard(models.TransientModel):
    _name = "cancelled.reason.wizard"
    _description = "Cancelled Reason Wizard"

    job_card_id = fields.Many2one('project.task', string="Job Card")
    cancellation_reason_id = fields.Many2one('cancellation.reason', string="Cancellation Reason")

    def action_confirm_reason(self):
        for rec in self:
            if rec.job_card_id:
                if rec.cancellation_reason_id:
                    # if rec.job_card_id.job_state.code == '124':
                    # rec.job_card_id.cancellation_reason_id = rec.cancellation_reason_id.id
                    rec.job_card_id.write({'cancellation_reason_id': rec.cancellation_reason_id.id,
                                           'cancel_status_check': False
                                           })
                    rec.job_card_id._send_whatsapp_for_cancellation()
                if not rec.cancellation_reason_id:
                    raise ValidationError(_("Please Select at least anyone Reason in The Cancellation Reason "))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'form',
            'res_id': self.job_card_id.id,
            'target': 'current',
        }

    def action_cancel(self):
        for rec in self:
            if rec.job_card_id:
                if rec.job_card_id.previous_job_card_state_code:
                    stage_search = self.env['project.task.type'].search(
                        [('code', '=', rec.job_card_id.previous_job_card_state_code)], limit=1)

                    if stage_search:
                        rec.job_card_id.write({
                            'job_state': stage_search.id,
                            'job_card_state_code': stage_search.code,
                            'job_card_state': stage_search.name
                        })
                        rec.job_card_id.service_request_id.service_request_state = stage_search.name
                        rec.job_card_id.service_request_id.service_request_state_code = stage_search.code
                        rec.job_card_id.service_request_id.state = stage_search.id

                    rec.job_card_id.cancel_status_check = False

        return {

            'type': 'ir.actions.client',
            'tag': 'reload',
        }
