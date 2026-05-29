# Copyright 2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models,fields,api, _


class PurchaseOrderLine(models.Model):

    _inherit = "purchase.order.line"
    
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if self.order_id.picking_type_id.warehouse_id.analytic_id:
                self.analytic_distribution = {str(self.order_id.picking_type_id.warehouse_id.analytic_id.id):100}
    

    def _prepare_stock_moves(self, picking):
        res = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
        for line in res:
            analytic_distribution = self.analytic_distribution
            if analytic_distribution:
                line.update({'analytic_distribution':analytic_distribution})
            # account_analytic = self.account_analytic_id
            # analytic_tags = self.analytic_tag_ids
            # if account_analytic:
            #     line.update({"analytic_account_id": account_analytic.id})
            # if analytic_tags:
            #     line.update({"analytic_tag_ids": [(6, 0, analytic_tags.ids)]})
        return res
