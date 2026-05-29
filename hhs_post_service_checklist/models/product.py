from odoo import models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def name_get(self):
        result = []
        for rec in self:
            name = rec.name
            if not self.env.context.get('display_default_code'):
                # hide default_code
                result.append((rec.id, name))
            else:
                # default behavior
                if rec.default_code:
                    name = f"[{rec.default_code}] {name}"
                result.append((rec.id, name))
        return result