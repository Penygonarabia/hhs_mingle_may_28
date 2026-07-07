from odoo import models, fields, api


class LoyaltyTierIcon(models.Model):
    _name = 'loyalty.tier.icon'
    _description = 'Tier Icon'
    _order = 'sequence, name'

    name = fields.Char(string='Icon Name', required=True)
    fa_icon = fields.Char(
        string='FontAwesome Icon Class',
        required=True,
        default='fa-star',
        help='Enter FontAwesome 4.7 icon class e.g. fa-star, fa-trophy, fa-diamond, fa-shield, fa-heart'
    )
    color = fields.Char(
        string='Color',
        required=True,
        default='#FFD700',
        help='Hex color code e.g. #FFD700 for Gold, #A8A8A8 for Silver, #CD7F32 for Bronze'
    )
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
