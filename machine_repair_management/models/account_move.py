from odoo import api, fields, models, _

class AccountMove(models.Model):
    
    _inherit = "account.move"
    
    
    '''Code Added on May 22 2026 by Vijaya Bhaskar'''
    customer_code = fields.Char(string = "Customer Code")
    
    warehouse_id = fields.Many2one('stock.warehouse',string = "Warehouse")
    
    work_center_id = fields.Many2one('work.center.location', string = "Work center")
    
    work_center_group_id = fields.Many2one('work.center.group', string = "Work Center  Group")
    
    '''Code Added on May 26 2026 by Vijaya Bhaskar '''
    
    sales_person_user_id = fields.Many2one('res.users', string  = "SalesPerson")
    