from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class OnHoldSparePartsReason(models.Model):
    _name = "onhold.spareparts.reason"
    _description = "OnHold Spare Parts Reason"
    _rec_name = "complete_name"

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")
    complete_name = fields.Char(string="Complete Name", compute="_compute_complete_name", store=True)

    @api.depends('name', 'code')
    def _compute_complete_name(self):
        for rec in self:
            rec.complete_name = False
            if rec.name and rec.code:
                rec.complete_name = '[%s]-%s' % (rec.code, rec.name)
            else:
                rec.complete_name = rec.name

    @api.constrains('code')
    def _check_code_valid(self):
        for rec in self:
            code_search = self.env['onhold.spareparts.reason'].search([('code', '=', rec.code), ('id', '!=', rec.id)])
            if len(code_search) > 1:
                raise ValidationError(_("Already Code is added to some other name.Please change it"))