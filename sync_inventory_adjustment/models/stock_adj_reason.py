from odoo import api, fields, models, _


class StockAdjReason(models.Model):
    _name = 'stock.adjustment.reason'

    name = fields.Char('Reason')





