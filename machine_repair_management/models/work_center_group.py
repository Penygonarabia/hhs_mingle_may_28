from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class WorkCenterGroup(models.Model):
    _name = "work.center.group"
    _description = "Work Center Group"
    _rec_name = "complete_name"

    name = fields.Char(string="Name", ondelete="cascade")
    code = fields.Char(string="Code", ondelete="cascade")
    description = fields.Text(string="Description")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)
    complete_name = fields.Char(string="Complete Name", store=True, compute="_compute_complete_name")

    @api.constrains('code')
    def _check_constraint_work(self):
        for rec in self:
            group_search = self.env['work.center.group'].search([('code', '=', rec.code)])
            if len(group_search) > 1:
                raise ValidationError("Already Name and code is present.Please Change it")

    @api.depends('name', 'code')
    def _compute_complete_name(self):
        for rec in self:
            if rec.name and rec.code:
                rec.complete_name = '[%s] - %s' % (rec.code, rec.name)
            else:
                rec.complete_name = rec.name
