from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class OnHoldSpareParstReasonWizard(models.TransientModel):
    _name = "onhold.spareparts.reason.wizard"

    _description = "Onhold Spare Parts Reason Wizard"

    def _default_onhold_spareparts_reason_id(self):
        return self.env['onhold.spareparts.reason'].search(
            [('name', 'ilike', 'damaged%')],
            limit=1
        )

    job_card_id = fields.Many2one('project.task', string="Job Card")

    onhold_spareparts_reason_id = fields.Many2one('onhold.spareparts.reason', string="On hold SpareParts Reason",
                                                  default=_default_onhold_spareparts_reason_id)

    def action_confirm_reason(self):
        for rec in self:
            if rec.job_card_id:
                if rec.onhold_spareparts_reason_id:
                    # if rec.job_card_id.job_state.code == '124':
                    # rec.job_card_id.cancellation_reason_id = rec.cancellation_reason_id.id
                    rec.job_card_id.write({
                        'onhold_spareparts_reason_id': rec.onhold_spareparts_reason_id.id,
                        'onhold_spareparts_status_check': False,
                        'onhold_spareparts_reason_show': True,

                    })
                    # rec.job_card_id._send_whatsapp_for_cancellation()
                if not rec.onhold_spareparts_reason_id:
                    raise ValidationError(_("Please Select at least anyone Reason in The Spare Parts Reason "))

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

                    rec.job_card_id.onhold_spareparts_status_check = False

        return {

            'type': 'ir.actions.client',
            'tag': 'reload',
        }
