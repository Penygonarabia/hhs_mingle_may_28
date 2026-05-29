from datetime import datetime, timedelta
import logging
import pytz
from psycopg2 import sql

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class IrSequenceDateRange(models.Model):
    _inherit = 'ir.sequence.date_range'

    location_id = fields.Many2one('hr.work.location', string="Location", invisible=True)
    location_code = fields.Char(string="Prefix")
    work_center_id = fields.Many2one('work.center.location', string="Work Center")

    @api.constrains('work_center_id', 'location_code', 'date_from', 'date_to')
    def _check_location_code(self):
        for rec in self:
            work_center_date = self.env['ir.sequence.date_range'].search(
                [('id', '!=', rec.id),
                 ('sequence_id', '=', rec.sequence_id.id),
                 ('work_center_id', '=', rec.work_center_id.id),
                 ('date_from', '=', rec.date_from),
                 ('date_to', '=', rec.date_to)],
                limit=1)

            if work_center_date:
                raise ValidationError("Already Work Center has been created for the same date range")

            if rec.sequence_id.use_location_wise and rec.sequence_id.use_date_range:
                if not rec.work_center_id and not rec.location_code:

                    raise ValidationError("Please enter Prefix and  Work Center")

                elif not rec.work_center_id:
                    raise ValidationError("Please enter Work Center")
                elif not rec.location_code:
                    raise ValidationError('Please enter Prefix')

            elif rec.sequence_id.use_date_range:

                if not rec.location_code:
                    raise ValidationError('Please enter Prefix')


class IrSequence(models.Model):
    _inherit = "ir.sequence"

    use_location_wise = fields.Boolean(string='Use subsequences per Work Center', default=False)
