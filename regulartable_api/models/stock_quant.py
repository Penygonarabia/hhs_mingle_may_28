from odoo import models, fields, api

class ResLangCustom(models.Model):
    _name = 'stock.quant'
    _description = 'stock_quant Model'

    product_id = fields.Integer(string='product_id')
    company_id = fields.Integer(string='company_id')
    location_id = fields.Integer(string='location_id')
    storage_category_id = fields.Integer(string='storage_category_id')
    lot_id = fields.Integer(string='lot_id')
    package_id = fields.Integer(string='package_id')
    owner_id = fields.Integer(string='owner_id')
    user_id = fields.Integer(string='user_id')
    inventory_date = fields.Date(string='Inventory_date')
    quantity = fields.Float(string='Quantity')
    reserved_quantity = fields.Float(string='Reserved_quantity')
    inventory_quantity = fields.Float(string='Inventory_quantity')
    inventory_diff_quantity = fields.Float(string='Inventory_diff_quantity')
    inventory_quantity_set = fields.Boolean(string='Inventory_quantity_set')
    in_date = fields.Datetime(string='In_date', default=fields.Datetime.now)
    accounting_date = fields.Date(string='Accounting_date')
    is_reserved = fields.Boolean(string='Is Reserved')


    

