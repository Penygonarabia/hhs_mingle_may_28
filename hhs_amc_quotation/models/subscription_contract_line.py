from odoo import models, fields

class SubscriptionContractsLine(models.Model):
    _inherit = 'subscription.contracts.line'

    main_category_id = fields.Many2one(
        't.mainproducts',
        string='Main Group'
    )

    brand_category_id = fields.Many2one(
        'product.category',
        string='Brand Category'
    )

    contract_type_id = fields.Many2one(
        'crm.contract.type',
        string='Contract Type'
    )

    amc_pricing_id = fields.Many2one(
        'amc.pricing',
        string='AMC Pricing'
    )

    unit_cost_price = fields.Float(string='Unit Cost Price')
    unit_selling_price = fields.Float(string='Unit Selling Price')
    spare_parts_cost_per_category = fields.Float(string='Sp.Cost Category')
    spare_parts_cost = fields.Float(string='Sp.Cost')
    spare_parts_selling_price = fields.Float(string='Sp. Selling Price')

    total_selling_price = fields.Float(string='Total Selling Price')

    per_unit_selling_price = fields.Float(string='Per Unit Selling Price')

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )