from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Defects(models.Model):
    _name = 'defects'
    _description = "Defects"
    _rec_name = 'def_complete_name'
    _order = "def_desc Asc"

    def_servicetypeid = fields.Many2one('service.nature', string='Service Type', required=True, ondelete="cascade")
    def_code = fields.Char(string='Code ', required=True)
    def_desc = fields.Char(string='Name ', required=True)
    def_complete_name = fields.Char(string="Complete Name", compute="_compute_def_complete_name", store=True)

    defects_product_catgeory_id = fields.Many2one('product.category', string="Product Category")

    @api.constrains('def_servicetypeid', 'def_code')
    def _check_defectstype_valid_code(self):
        for rec in self:
            defects_search = self.env['defects'].search(
                [('def_servicetypeid', '=', rec.def_servicetypeid.id), ('def_code', '=', rec.def_code)])
            if len(defects_search) > 1:
                raise ValidationError("The combination of Service Type and Defect Code must be unique!")

    @api.depends('def_code', 'def_desc')
    def _compute_def_complete_name(self):
        for rec in self:
            if rec.def_code and rec.def_desc:
                rec.def_complete_name = '[%s] %s' % (rec.def_code, rec.def_desc)
            else:
                rec.def_complete_name = rec.def_desc
