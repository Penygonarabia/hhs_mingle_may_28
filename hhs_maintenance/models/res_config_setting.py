from odoo import fields, api, models, _

class ResConfigSetting(models.TransientModel):
    _inherit="res.config.settings"

    maintenance_equipment_show=fields.Boolean(string="Maintenance Equipment Required.",default=False,
                                              config_parameter="hhs_maintenance.maintenance_equipment_show")


    @api.model
    def get_values(self):
        res = super(ResConfigSetting, self).get_values()
        params = self.env['ir.config_parameter'].sudo()

        res.update(
            maintenance_equipment_show=params.get_param('hhs_maintenance.maintenance_equipment_show')
        )
        return res

    def set_values(self):
        res = super(ResConfigSetting, self).set_values()

        self.env['ir.config_parameter'].sudo().set_param('hhs_maintenance.maintenance_equipment_show',
                                                         self.maintenance_equipment_show),
        return res