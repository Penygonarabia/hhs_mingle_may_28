from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProductSize(models.Model):
    _name = 'product.size'
    _description = 'Product Capacity Master'
    _order = 'capacity'
    _rec_name = 'capacity'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    capacity = fields.Char(string='Capacity', required=True, tracking=True)
    code = fields.Char(string='Code', required=True)

    _sql_constraints = [
        # This prevents *exact* duplicates (case-sensitive)
        ('code_size_unique', 'unique(code, capacity)', 'Exact same Code and capacity already exist.')
    ]

    @api.constrains('code', 'capacity')
    def _check_unique_case_insensitive(self):
        for rec in self:
            duplicate = self.search([
                ('id', '!=', rec.id),
                ('code', '=ilike', rec.code),
                ('capacity', '=ilike', rec.capacity),
            ], limit=1)
            if duplicate:
                raise ValidationError("A capacity with this Code and capacity already exists (case-insensitive match).")

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, rec.capacity))
        return result
