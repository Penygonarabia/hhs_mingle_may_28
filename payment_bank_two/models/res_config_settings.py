from odoo import api,fields,models,_

class ResConfigSettings(models.TransientModel):
    
    _inherit = "res.config.settings"
    
    
    bank_transfer_format = fields.Selection([('sib_format','SIB Format'),('sabb_format','SABB Format'),
                                             ('bank_3_format','Bank III Format')],default='sib_format',
                                             config_parameter='om_hr_payroll.bank_transfer_format')
    
    
    def set_values(self):
        res = super(ResConfigSettings,self).set_values()
        
        self.env['ir.config_parameter'].sudo().set_param('om_hr_payroll.bank_transfer_format',self.bank_transfer_format)
        
        return res 
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings,self).get_values()
        
        params = self.env['ir.config_parameter'].sudo()
        
        res.update(
            bank_transfer_format = params.get_param('om_hr_payroll.bank_transfer_format')
            )
        return res
        
    