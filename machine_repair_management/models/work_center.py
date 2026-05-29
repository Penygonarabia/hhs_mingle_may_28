from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class WorkCenter(models.Model):
    _name = "work.center.location"
    _description = " Work Center Location"

    name = fields.Char(string='Name', required=True, ondelete="cascade")
    code = fields.Char(string="Code", required=True, ondelete="cascade")
    # location_id = fields.Many2one('hr.work.location',string="Location")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)

    work_center_group_id = fields.Many2one('work.center.group', string="Work Center Group")

    default_mail_send_parts = fields.Char('Default Mail Send Parts User',
                                          help="Default Mail send to Parts User when on Hold Spare Parts required given by Technician for Spare Parts Required")

    mail_cc_send_parts = fields.Char('Mail CC Parts User',
                                     help="Default Mail CC Send to Parts User when on Hold Spare Parts required given by Technician for Spare Parts Required")

    default_mail_send_coordinator = fields.Char('Default Mail Send Co-ordinator',
                                                help="Default Mail send to Co-ordinator for parts is ready given by Parts User")

    mail_cc_send_coordinator = fields.Char('Mail CC Co-ordinator',
                                           help="Default Mail CC send to Co-ordinator for Parts Is ready given by Parts User to the Co-ordinator")

    '''Code Added on March 10 2026'''
    # Added by Raj - 12-03-2026
    technician_warehouse_required_bool = fields.Boolean(string='Technician Warehouse Required', default=False)

    # complete_name = fields.Char(string="Complete Name" , compute = "_compute_complete_name")

    @api.constrains('code')
    def _check_validity_code(self):
        for rec in self:
            code_search = self.env['work.center.location'].search([('code', '=', rec.code)])
            if len(code_search) > 1:
                raise ValidationError('Code is unique one.Please enter code for the work location')

    @api.constrains('default_mail_send_parts')
    def _default_mail_send_parts_check(self):
        for rec in self:
            if rec.default_mail_send_parts:
                if '@' not in rec.default_mail_send_parts or '.' not in rec.default_mail_send_parts:
                    raise ValidationError(
                        _("Please enter a valid email address must contain @ and . in the Default Mail Send Parts User"))

                if not re.match(r'^[a-zA-Z0-9,_%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', rec.default_mail_send_parts):
                    raise ValidationError(
                        _("Please enter a properly formatted email address in the Default Mail Send Parts User"))

    @api.constrains('mail_cc_send_parts')
    def _mail_send_check(self):
        email_regex = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        for rec in self:
            if not rec.mail_cc_send_parts:
                continue

            emails = [email.strip() for email in rec.mail_cc_send_parts.split(',') if email.strip()]

            for email in emails:
                if '@' not in email or '.' not in email:
                    raise ValidationError(_(
                        "Mail CC Parts User must contain '@' and '.' characters."
                    ))
                # Per-email format validation
                if not email_regex.match(email):
                    raise ValidationError(_(
                        "Invalid email address in Mail CC Parts User: %s\n"
                        "Please enter valid email IDs separated by commas."
                    ) % email)

    @api.constrains('default_mail_send_coordinator')
    def _default_mail_send_coordinator_check(self):
        for rec in self:
            if rec.default_mail_send_coordinator:
                if '@' not in rec.default_mail_send_coordinator or '.' not in rec.default_mail_send_coordinator:
                    raise ValidationError(
                        _("Please enter a valid email address must contain @ and . in the Default Mail Send Coordinator"))

                if not re.match(r'^[a-zA-Z0-9,_%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', rec.default_mail_send_coordinator):
                    raise ValidationError(
                        _("Please enter a properly formatted email address in the Default Mail Send Coordinator"))

    @api.constrains('mail_cc_send_coordinator')
    def _mail_cc_send_coordinator_check(self):
        email_regex = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        for rec in self:
            if not rec.mail_cc_send_coordinator:
                continue

            emails = [email.strip() for email in rec.mail_cc_send_coordinator.split(',') if email.strip()]

            for email in emails:
                if '@' not in email or '.' not in email:
                    raise ValidationError(_(
                        "Mail CC Coordinator must contain '@' and '.' characters."
                    ))
                # Per-email format validation
                if not email_regex.match(email):
                    raise ValidationError(_(
                        "Invalid email address in Mail CC: %s\n"
                        "Please enter valid email IDs separated by commas."
                    ) % email)
