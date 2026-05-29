from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Product_service_type(models.Model):
    _inherit = 'product.category'

    def_servicetypeid = fields.Many2one('service.nature', string='Service Type', ondelete="cascade", )
    warranty_period = fields.Integer(string="Warranty Period", help="Default warranty period for the category.")
    warranty_period_combo = fields.Selection([
        ('days', 'Days'),
        ('months', 'Months'),
        ('years', 'Years'),
    ], string="Warranty Period Unit", default='months', help="Unit of the warranty period (Days, Months, Years).")

    # location_id = fields.Many2one('hr.work.location',string = "Location", deprecated=True)
    # warehouse_id = fields.Many2one('stock.warehouse',string = "Warehouse", deprecated=True)

    category_line_ids = fields.One2many('product.category.line', 'category_location_id', string="Warehouse Interface")


class ProductCategoryLocation(models.Model):
    _name = "product.category.line"
    _description = "Product Category Line"

    category_location_id = fields.Many2one('product.category')
    location_id = fields.Many2one('hr.work.location', string="Location")
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")

    @api.constrains('location_id', 'warehouse_id', 'category_location_id')
    def validity_check(self):
        for rec in self:
            if rec.location_id and rec.warehouse_id:
                location_search = self.env['product.category.line'].search(
                    [('location_id', '=', rec.location_id.id), ('warehouse_id', '=', rec.warehouse_id.id),
                     ('id', '!=', rec.id), ('category_location_id', '=', rec.category_location_id.id)])
                if len(location_search) > 1:
                    raise ValidationError('Already location and warehouse is there')
