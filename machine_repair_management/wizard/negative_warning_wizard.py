from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class NegativeStockWarningWizard(models.TransientModel):
    _name = 'negative.stock.warning.wizard'
    _description = 'Negative Stock Warning Wizard'

    message = fields.Text(string="Notification Message", readonly=True)
    job_card_id = fields.Many2one('project.task', string="Job Card", readonly=True)

    def action_confirm(self):
        """Confirm the action and update the job card state to '126'."""
        self.ensure_one()
        job_card = self.job_card_id
        if not job_card:
            raise ValidationError(_("No job card found in the wizard context."))

        # Perform validations for state '126'
        if not job_card.control_card_no:
            raise ValidationError(_("Please enter 'Control Card No' in the Job card."))

        if not job_card.closed_datetime:
            raise ValidationError(_("Please enter Completed Date & Time in the Job card"))

        if job_card.planned_date_begin and job_card.closed_datetime and job_card.planned_date_begin > job_card.closed_datetime:
            raise ValidationError(_('Completed Date & Time must be greater than Appt Start Date & Time'))

        if not job_card.product_id:
            raise ValidationError(_("Please enter Model No. in the Job card"))

        if job_card.warranty and not job_card.purchase_invoice_no:
            raise ValidationError(_("Please enter Purchase Invoice No"))

        if job_card.warranty and not job_card.purchase_date:
            raise ValidationError(_("Please enter Purchase date in the Job card"))

        if not job_card.service_warranty_id:
            raise ValidationError(_("Please select any one Service Warranty"))

        if not job_card.product_line_ids:
            raise ValidationError(_("Please give at least one Product in the product consume Part/services"))

        for line in job_card.product_line_ids:
            if line.product_id and not line.parts_reserved_bool:
                raise ValidationError(
                    _("Please check all Products are Reserved. This Product %s is not reserved" % line.product_id.display_name))

            if not self.env['ir.config_parameter'].sudo().get_param(
                    'machine_repair_management.negative_stock_allow') == 'True':
                if line.on_hand_qty == 0.0:
                    raise ValidationError(
                        _("Stock %s is not available. Please Contact Administrator" % line.product_id.display_name))

        if job_card.inspection_charges_bool and job_card.inspection_charges_amount > 0:
            if not any(line.product_id and line.product_id.service_type_bool for line in job_card.product_line_ids):
                raise ValidationError(_("Please enter service charge amount in the product line"))

        # Update job card state to '126'
        job_card.write({
            'job_card_state_code': '126',
            'job_card_completed_time': fields.Datetime.now(),
        })

        # Update related service request fields
        if job_card.service_request_id:
            job_card.service_request_id.write({
                'service_request_state': job_card.job_card_state,
                'service_request_state_code': '126',
                'state': job_card.job_state,
            })

        # Notify finance users
        work_center = job_card.technician_id.default_work_center_id
        finance_users = self.env['res.users'].search([
            ('default_work_center_id', '=', work_center.id),
            ('groups_id', 'in', self.env.ref('machine_repair_management.group_technical_allocation_user').id)
        ])
        odoo_bot = self.env.ref('base.partner_root')
        for user in finance_users:
            if user.partner_id:
                channel_name = f"{odoo_bot.name}, {user.name}"
                channel = self.env['discuss.channel'].search([
                    ('name', 'ilike', channel_name),
                    ('channel_type', '=', 'chat')
                ], limit=1)
                if not channel:
                    channel = self.env['discuss.channel'].create({
                        'name': channel_name,
                        'channel_type': 'chat',
                        'channel_partner_ids': [(4, user.partner_id.id)]
                    })
                channel.message_post(
                    body=f'Job Card {job_card.name} has been completed and is ready to be invoiced.',
                    subject='Job Card State Update',
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                    author_id=odoo_bot.id,
                )

        # Log stock warning in chatter for reference
        if self.message:
            job_card.message_post(
                body="Stock Notification: " + self.message,
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )

        return {'type': 'ir.actions.act_window_close'}
