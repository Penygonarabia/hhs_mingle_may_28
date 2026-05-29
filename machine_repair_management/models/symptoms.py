from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Symptoms(models.Model):
    _name = 'symptoms'
    _description = "Symptoms"
    _rec_name = "sym_complete_name"
    _order = "sym_desc Asc"

    sym_servicetypeid = fields.Many2one('service.nature', string='Service Type', required=True, ondelete="cascade")
    sym_code = fields.Char(string='Code', required=True)
    sym_desc = fields.Char(string='Name', required=True, translate=True)
    sym_complete_name = fields.Char(string="Complete Name", compute="_compute_sym_complete_name", store=True)
    symptom_product_category_id = fields.Many2one('product.category', string = "Product Category")

    @api.constrains("sym_servicetypeid", "sym_code")
    def _check_unique_servicetype_symptoms(self):
        for rec in self:
            domain = [
                ("sym_servicetypeid", "=", rec.sym_servicetypeid.id),
                ("sym_code", "=", rec.sym_code),
            ]
            existing = self.env['symptoms'].search(domain)
            if len(existing) > 1:
                raise ValidationError("The combination of Service Type and Symptoms Code must be unique!")

    @api.depends('sym_code', 'sym_desc')
    def _compute_sym_complete_name(self):
        for rec in self:
            if rec.sym_code and rec.sym_desc:
                rec.sym_complete_name = '[%s] %s' % (rec.sym_code, rec.sym_desc)
            else:
                rec.sym_complete_name = rec.sym_desc