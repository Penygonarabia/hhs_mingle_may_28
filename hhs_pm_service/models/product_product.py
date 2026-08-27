from odoo import models

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    
    
    '''Code Commented on August 27 2026 by Vijaya Bhaskar due to unnamed show in the product in mobile view so that i commented three unnamed  and made it in a single one in dealer app
    def name_get(self):
        result = []
        hide_code = self.env.context.get('hide_code')

        for rec in self:
            if hide_code:
                name = rec.name
            else:
                name = f"[{rec.default_code}] {rec.name}" if rec.default_code else rec.name
            result.append((rec.id, name))
        return result

    def _compute_display_name(self):
        hide_code = self.env.context.get('hide_code')

        for rec in self:
            if hide_code:
                rec.display_name = rec.name
            else:
                if rec.default_code:
                    rec.display_name = f"[{rec.default_code}] {rec.name}"
                else:
                    rec.display_name = rec.name
                    
    '''                