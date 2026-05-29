from odoo import models, fields

class CustomerLoyaltyPointsHistoryExt(models.Model):
    _inherit = 'customer.loyalty.points.history'

    clph_redemptionprice = fields.Float(string='Redemption Price')
