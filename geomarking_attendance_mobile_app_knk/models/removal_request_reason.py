from odoo import fields, models


class RemovalRequestReason(models.Model):
    _name = "removal.request.reason"
    _description = "Removal Request Reason"

    name = fields.Char()
