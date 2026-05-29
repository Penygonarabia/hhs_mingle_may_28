from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ManualPromotionReasonTypes(models.Model):
    _name = 'manual.promotion.reason.types'
    _description = 'Manual Promotion Reason Types'
    _rec_name = 'reason_name'

    reason_code = fields.Char(string="Reason Code", required=True)
    reason_name = fields.Char(string="Reason Name", required=True)

    # _rec_name = 'reason_complete_name'
    #
    # reason_code = fields.Char(string="Reason Code", required=True)
    # reason_name = fields.Char(string="Reason Name", required=True)
    #
    # reason_complete_name = fields.Char(
    #     string="Complete Name",
    #     compute="_compute_reason_complete_name",
    #     store=True
    # )
    # def name_get(self):
    #     result = []
    #     for rec in self:
    #         result.append((rec.id, rec.reason_name or ''))
    #     return result

    active = fields.Boolean(default=True)
    note = fields.Text(string="Note")

    _sql_constraints = [
        (
            'unique_reason_code',
            'unique(reason_code)',
            'Reason Code must be unique.'
        ),
        (
            'unique_reason_name',
            'unique(reason_name)',
            'Reason Name must be unique.'
        ),
    ]

    @api.depends('reason_code', 'reason_name')
    def _compute_reason_complete_name(self):
        for rec in self:
            if rec.reason_code and rec.reason_name:
                rec.reason_complete_name = '[%s] %s' % (
                    rec.reason_code,
                    rec.reason_name
                )
            else:
                rec.reason_complete_name = rec.reason_name or ''