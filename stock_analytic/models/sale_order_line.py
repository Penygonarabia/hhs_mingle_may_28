from collections import defaultdict
from datetime import timedelta
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare, float_round, format_date, groupby


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'  
  
  
    def _set_analytic_distribution(self, inv_line_vals, **optional_values):
        analytic_account_id = self.order_id.analytic_account_id.id
        if self.analytic_distribution and not self.display_type:
            inv_line_vals['analytic_distribution'] = self.analytic_distribution
        if analytic_account_id and not self.display_type:
            analytic_account_id = str(analytic_account_id)
            if 'analytic_distribution' in inv_line_vals:
                inv_line_vals['analytic_distribution'][analytic_account_id] = inv_line_vals['analytic_distribution'].get(analytic_account_id, 0)
                # inv_line_vals['analytic_distribution'][analytic_account_id] = inv_line_vals['analytic_distribution'].get(analytic_account_id, 0) + 100
            else:
                inv_line_vals['analytic_distribution'] = {analytic_account_id: 100}
                
                