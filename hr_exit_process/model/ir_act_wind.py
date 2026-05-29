from odoo import models, fields, api

class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    @api.model
    def render(self, res_id=None, view_id=None, view_type='form', **options):
        # Call the parent method to get the initial result
        result = super(IrActionsActWindow, self).render(res_id, view_id, view_type, **options)
        print("..................result",result,res_id)
        # Check if the view_type is 'form' and a record ID is provided
        if view_type == 'form' and res_id:
            # Get the record
            record = self.env[result['res_model']].browse(res_id)
            # Check if the record has the exit_date field and if it is set
            if hasattr(record, 'exit_date') and record.exit_date:
                # Make the form read-only
                result['flags'] = result.get('flags', {})
                result['flags']['readonly'] = True
        
        return result
    
    # @api.model
    # def _get_form_view(self, res_id=None, view_id=None, view_type='form', **options):
    #     res = super(IrActionsActWindow, self)._get_form_view(res_id, view_id, view_type, **options)
    #
    #     if res_id and self.env.context.get('hide_edit_button'):
    #         record = self.env[res['res_model']].browse(res_id)
    #         if hasattr(record, 'exit_date') and record.exit_date:
    #             res['flags']['readonly'] = True
    #
    #     return res