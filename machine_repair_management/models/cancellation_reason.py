from odoo import api, fields, models, _

from odoo.exceptions import ValidationError


class CancellationReason(models.Model):
    _name = "cancellation.reason"
    _description = "Cancellation Reason"
    _rec_name = "complete_name"

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")
    complete_name = fields.Char(string="Complete name", compute="_compute_complete_name", store=True)
    arabic_name = fields.Char(string="Arabic Name")

    @api.depends('name', 'code')
    def _compute_complete_name(self):
        for rec in self:
            rec.complete_name = False
            if rec.name and rec.code:
                rec.complete_name = "[%s]-%s" % (rec.code, rec.name)
            else:
                rec.complete_name = rec.name

    @api.constrains('code')
    def _check_code_validation(self):
        for rec in self:
            code_search = self.env['cancellation.reason'].search([('code', '=', rec.code), ('id', '!=', rec.id)])

            if len(code_search) > 1:
                raise ValidationError(_("Already Code is added to some other name.Please change it"))
