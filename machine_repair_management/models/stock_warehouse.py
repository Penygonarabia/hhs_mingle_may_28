from odoo import api, fields, models, _


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"
    _rec_name = "complete_name"

    cst_no = fields.Char(string="Customer Number")
    complete_name = fields.Char(string="Complete name", compute="_compute_complete_name")
    product_category_ids = fields.Many2many(
        'product.category',
        'warehouse_product_category_rel',  # table name
        'warehouse_id',  # column referring to stock.warehouse
        'category_id',  # column referring to product.category
        string="Product Category"
    )
    work_center_id = fields.Many2one('work.center.location', string="Work Center")
    default_work_center_bool = fields.Boolean(string="Default Warehouse", default=False)
    region_default_warehouse_bool = fields.Boolean(string=" Region Default Warehouse", default=False)

    # Added by Raj - 12-03-2026
    warehouse_type = fields.Selection(
        [('technician_warehouse', 'Technician Warehouse'), ('main_warehouse', 'Main Warehouse')],
        string="Warehouse Type")
    
    work_center_ids = fields.Many2many('work.center.location','stock_warehouse_work_center_rel','warehouse_id','work_center_id',string = "Work Centers")

    @api.depends('name', 'code')
    def _compute_complete_name(self):
        for rec in self:
            rec.complete_name = False
            if rec.name and rec.code:
                rec.complete_name = '[%s]-%s' % (rec.code, rec.name)

            elif rec.name:
                rec.complete_name = rec.name
