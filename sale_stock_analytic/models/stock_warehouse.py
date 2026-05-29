
from odoo import models,fields,api,_


class Warehouse(models.Model):
    _inherit = 'stock.warehouse'

    analytic_id = fields.Many2one("account.analytic.account", string="Analytic account")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('analytic_id','warehouse_id')
    def add_analytic(self):
        for rec in self:
            rec.analytic_account_id = rec.warehouse_id.analytic_id.id
            
            
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if self.order_id.analytic_account_id:
                self.analytic_distribution = {str(self.order_id.analytic_account_id.id):100}
            else:
                self.analytic_distribution = None
                    
                
                
                
        
    
    
    
                