from odoo import api,fields,models,_

class InvoiceCreationSequence(models.TransientModel):
    
    _name = "invoice.creation.wizard"
    
    _description = "Invoice Creation Wizard"
    
    
    job_task_id = fields.Many2one('project.task', string = "Job Card")
    
    def action_confirm(self):
        
        self.ensure_one()

        rec = self.job_task_id

        if rec.warehouse_id:
            if not rec.project_related_amc_bool:
                sequence_prefix = self.env['ir.config_parameter'].sudo().get_param(
                    'machine_repair_management.service_invoice_creation_prefix'
                ) or ''
    
                rec.invoice_no = (
                    f"{sequence_prefix}"
                    f"{rec.warehouse_id.code}/"
                    f"{rec.warehouse_id.service_next_number:05d}"
                )
    
                rec.warehouse_id.service_next_number += 1
            else :
                amc_sequence_prefix = self.env['ir.config_parameter'].sudo().get_param(
                    'machine_repair_management.amc_invoice_creation_prefix'
                ) or ''
    
                rec.invoice_no = (
                    f"{amc_sequence_prefix}"
                    f"{rec.warehouse_id.code}/"
                    f"{rec.warehouse_id.amc_next_number:05d}"
                )
    
                rec.warehouse_id.amc_next_number += 1
                
                    

        return {'type': 'ir.actions.act_window_close'}
        
        