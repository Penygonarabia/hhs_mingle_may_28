from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    
    _inherit = "res.config.settings"
    
    number_of_days = fields.Integer(string="Number of days", default = 7, config_parameter = 'hr.number_of_days'  )
    
    def set_values(self):
        res = super(ResConfigSettings,self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'hr.number_of_days',self.number_of_days)
    
        return res
    
    @api.model
    def get_values(self):
       res = super(ResConfigSettings, self).get_values()
       params = self.env['ir.config_parameter'].sudo()
       res.update(
           number_of_days=params.get_param('hr.number_of_days')
       )
       return res