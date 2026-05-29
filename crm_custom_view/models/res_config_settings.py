from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hide_additional_fields = fields.Boolean(
        string="Hide CRM Additional Fields",
        config_parameter = "crm_custom_view.hide_additional_fields",
        default = False
    )
    subject = fields.Char(
        string="Subject",
        config_parameter="crm_custom_view.subject"
    )
    
    '''Code Added on May 25 2026 by Vijaya Bhaskar client asked default values to be assign'''
    scope_of_work = fields.Char(string = "Scope of Work", config_parameter = "crm_custom_view.scope_of_work")
    
    terms_of_execution = fields.Char(string = "Terms Of Execution", config_parameter = "crm_custom_view.terms_of_execution")
    
    exclusions = fields.Char(string = "Exclusions", config_parameter = "crm_custom_view.exclusions")
    
    notes = fields.Char(string = "Notes", config_parameter = "crm_custom_view.notes")
    
    
    

    '''Code Added on April 04 2026 by Vijaya Bhaskar'''
    @api.model
    def get_values(self):
        
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            hide_additional_fields = params.get_param('crm_custom_view.hide_additional_fields'),
            subject = params.get_param('crm_custom_view.subject'),
            scope_of_work = params.get_param('crm_custom_view.scope_of_work'),
            terms_of_execution = params.get_param('crm_custom_view.terms_of_execution'),
            exclusions = params.get_param('crm_custom_view.exclusions'),
            notes = params.get_param('crm_custom_view.notes')
        )
        return res
    
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        IrConfigParameter.set_param('crm_custom_view.hide_additional_fields',
                                                         self.hide_additional_fields)
        IrConfigParameter.set_param('crm_custom_view.subject', self.subject)
        
        IrConfigParameter.set_param('crm_custom_view.scope_of_work',self.scope_of_work)
        
        IrConfigParameter.set_param('crm_custom_view.terms_of_execution',self.terms_of_execution)
        
        IrConfigParameter.set_param('crm_custom_view.exclusions', self.exclusions)
        
        IrConfigParameter.set_param('crm_custom_view.notes',self.notes)
     
     
        
        
    # # -------------------------
    # # LOAD VALUE IN SETTINGS
    # # -------------------------
    # def get_values(self):
    #     res = super().get_values()
    #
    #     group = self.env.ref('crm_custom_view.group_hide_additional_fields')
    #     user = self.env.user
    #
    #     res.update({
    #         'hide_additional_fields': group in user.groups_id
    #     })
    #     return res
    #
    # # -------------------------
    # # SAVE VALUE FROM SETTINGS
    # # -------------------------
    # def set_values(self):
    #     super().set_values()
    #
    #     group = self.env.ref('crm_custom_view.group_hide_additional_fields')
    #     user = self.env.user
    #
    #     if self.hide_additional_fields:
    #         # ✅ Add group
    #         user.write({'groups_id': [(4, group.id)]})
    #     else:
    #         # ❌ Remove group
    #         user.write({'groups_id': [(3, group.id)]})