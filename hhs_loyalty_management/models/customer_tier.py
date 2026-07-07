from odoo import models, fields, api
from odoo.exceptions import ValidationError

class CustomerTier(models.Model):
    _name = 'customer.tier'
    _description = 'Customer Tier'
    _rec_name = 'name'
    _order = 'sort_order asc'

    name = fields.Char(string='Name', required=True, help='Name of the customer tier')
    min_loyalty_points = fields.Integer(string='Min Loyalty Points', required=True, help='Minimum loyalty points required for this tier')
    sort_order = fields.Integer(
        string='Sort Order',
        default=lambda self: self._get_next_sort_order(),
        help='Used for ordering tiers'
    )
    tier_icon = fields.Many2one(
        'loyalty.tier.icon',
        string='Tier Icon',
        help='Select an icon to represent this tier'
    )



    @api.model
    def _get_next_sort_order(self):
        last_record = self.search([], order='sort_order desc', limit=1)
        return (last_record.sort_order or 0) + 1

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'The name of the Customer Tier must be unique!')
    ]

    @api.constrains('min_loyalty_points')
    def _check_min_loyalty_points(self):
        for record in self:
            if record.min_loyalty_points < 0:
                raise ValidationError("Minimum loyalty points cannot be negative.")