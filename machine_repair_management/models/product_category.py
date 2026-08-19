from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Product_service_type(models.Model):
    _inherit = 'product.category'
    _rec_name = "name"

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
    code = fields.Char(string="Code")

    # old one as per Baskar sir advice change the caption Name 20250923
    # allowed_group_bool = fields.Boolean('Allowed Group', default=False)

    allowed_group_bool = fields.Boolean('Use for Service', default=False)
    # 20250923 Adding Two New Fields By Gokul
    allowed_group_is_promoter = fields.Boolean('Use for Promoters', default=False)
    alternative_description = fields.Char('Alternative Description')
    allowed_is_contract = fields.Boolean('Use for Contract')

    @api.constrains('code')
    def _check_code(self):
        for rec in self:
            if rec.code:
                code_search = self.env['product.category'].search([
                    ('code', '=', rec.code),
                ])
    
                if len(code_search) > 1:
                    raise ValidationError(
                        "This code '%s' is already associated with another category. "
                        "The category code must be unique. Please enter a different code."
                        % rec.code
                    )

class ProductCategoryLocation(models.Model):
    _name = "product.category.line"
    _description = "Product Category Line"

    category_location_id = fields.Many2one('product.category')
    work_center_location_id = fields.Many2one('work.center.location', string="Work Center", ondelete='cascade')
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    location_id = fields.Many2one('hr.work.location', string="Location", ondelete='cascade')

    @api.constrains('work_center_location_id', 'warehouse_id', 'category_location_id')
    def validity_check(self):
        for rec in self:
            if rec.work_center_location_id and rec.warehouse_id:
                location_search = self.env['product.category.line'].search(
                    [('work_center_location_id', '=', rec.work_center_location_id.id),
                     ('warehouse_id', '=', rec.warehouse_id.id),
                     ('id', '!=', rec.id), ('category_location_id', '=', rec.category_location_id.id)])
                if len(location_search) > 1:
                    raise ValidationError('Already location and warehouse is there')
