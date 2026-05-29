from odoo import api, fields, models, _

class ProjectTask(models.Model):
    
    _inherit = "project.task"
    
    
    hyperpay_line_ids = fields.One2many('hyperpay.line','task_id',string = "Hyper Pay Line")
    
    hyper_pay_line_create_bool = fields.Boolean(default = False, compute = "_compute_hyper_pay_line_create_bool", store = True)
    
    
    @api.depends('inspection_inv_no','payment_insp_link_sent_bool','balance_inv_no','payment_bal_link_sent_bool','hyperpay_line_ids.hyper_pay_audit_id.status')
    def _compute_hyper_pay_line_create_bool(self):
        for rec in self:
            rec.hyper_pay_line_create_bool = False
            if rec.inspection_inv_no or rec.payment_bal_link_sent_bool or rec.balance_inv_no or rec.payment_bal_link_sent_bool:
                rec.hyper_pay_line_create_bool = True
                if rec.hyper_pay_line_create_bool:
                    hyper_pay_audit_search = self.env['hyperpay.audit'].search([('jobcard_id','=',rec.id)])
                    line_vals = [(5,0,0)]
                    for hyper_pay in hyper_pay_audit_search:
                        vals = {
                            'task_id':hyper_pay.jobcard_id.id,
                            'job_card_number':hyper_pay.name,
                            'hyper_pay_payment_for' :hyper_pay.payment_for,
                            'hyper_pay_payment_receipt_number':hyper_pay.payment_receipt_number,
                            'hyper_pay_payment_reference':hyper_pay.payment_reference,
                            'hyper_pay_payment_received':hyper_pay.payment_received,
                            'hyper_pay_received_datetime':hyper_pay.received_datetime,
                            'hyper_pay_status':hyper_pay.status,
                            'hyper_pay_audit_id' : hyper_pay.id,
                            }
                        line_vals.append((0,0,vals))
                    
                    rec.write({'hyperpay_line_ids':line_vals})
        
    
    
    
  
class ProjectTaskLine(models.Model):
    
    _name = "hyperpay.line"
    
    _description = "Hyper Pay Line"
    
    task_id = fields.Many2one('project.task',string = "Project Task")
    
    job_card_number = fields.Char(string = "Job Card Number")
    
    hyper_pay_payment_for = fields.Selection([
        ('inspection', 'Inspection'),
        ('final', 'Final Payment')
    ], string='Payment For',)
    
    
    hyper_pay_payment_receipt_number = fields.Char(string='Payment Receipt Number')

    hyper_pay_payment_reference = fields.Char(string='Payment Reference')

    hyper_pay_payment_received = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')
    ], string='Payment Received', default='no')

    hyper_pay_received_datetime = fields.Datetime(string='Received Date & Time')

    hyper_pay_status = fields.Selection([
        ('success', 'Success'),
        ('pending', 'Pending'),
        ('failure', 'Failure')
    ], string='Status', default='pending')
    
    hyper_pay_audit_id = fields.Many2one('hyperpay.audit',string = "HyperPay Reference")
    
    hyper_pay_status_bool = fields.Boolean(string = "Hyper Pay Status Bool", default = False, compute = "_compute_hyper_pay_status_bool", store = True)
    
    @api.depends('hyper_pay_audit_id','hyper_pay_audit_id.status')
    def _compute_hyper_pay_status_bool(self):
        for rec in self:
            rec.hyper_pay_status_bool = False
            if rec.hyper_pay_audit_id.status in ('pending','success','failure') :
                rec.hyper_pay_status_bool = True
                if rec.hyper_pay_status_bool:
                    rec.hyper_pay_status = rec.hyper_pay_audit_id.status or None
                    rec.hyper_pay_received_datetime = rec.hyper_pay_audit_id.received_datetime or None
                    rec.hyper_pay_payment_received = rec.hyper_pay_audit_id.payment_received or None
                    rec.hyper_pay_status_bool = False
                    
                # if rec.hyper_pay_status == 'success':
                #     rec.task_id.send_whatsapp_service_charges_receipt()
                #

        
    

    
        