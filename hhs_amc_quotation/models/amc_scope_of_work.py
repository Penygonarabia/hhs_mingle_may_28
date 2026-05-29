from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ScopofWork(models.Model):
    _name = 'amc.scope.of.work'
    _order = 'amc_sortorder ASC'
    #_rec_name = 'display_name_scope'

    amc_soc_work = fields.Char("Code")
    #amc_soc_name = fields.Char("Name")
    amc_soc_description = fields.Char("Description")
    amc_auto_populate = fields.Boolean("Auto Populate Y/N")
    amc_sortorder=fields.Char("Sort Order")

    # display_name_scope = fields.Char(
    #     string="Display Name",
    #     compute="_compute_display_name",
    #     store=True
    # )

    @api.depends('amc_soc_work', 'amc_soc_description')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.amc_soc_description




    @api.constrains('amc_soc_description')
    def _valid_check_ac_type_code(self):
        for rec in self:
            amc_scope = self.env['amc.scope.of.work'].search([
                ('amc_soc_description', '=', rec.amc_soc_description),
                ('id', '!=', rec.id)
            ])

            if amc_scope:
                raise ValidationError("Description must be unique")
