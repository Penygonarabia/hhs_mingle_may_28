from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PropertyTypeMaintenanceDetails(models.Model):
    _name = "property.type.maintenance.details"
    _description = "Property Type Maintenance Details"
    _rec_name = "complete_name"

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")
    type_of_property = fields.Selection([('commercial', 'Commercial'), ('residential', 'Residential')],
                                        string="Type of Property")
    complete_name = fields.Char(string="Complete name", compute="_compute_complete_name", store=True)

    @api.constrains('code')
    def _check_name_paroerty(self):
        for rec in self:
            name_property_search = self.env['property.type.maintenance.details'].search([('code', '=', rec.code)])
            if len(name_property_search) > 1:
                raise ValidationError(_("Already code is there"))

    @api.depends('name', 'code')
    def _compute_complete_name(self):
        for rec in self:
            rec.complete_name = False
            if rec.name and rec.code:
                rec.complete_name = '[%s]-%s' % (rec.code, rec.name)
            else:
                rec.complete_name = rec.name
