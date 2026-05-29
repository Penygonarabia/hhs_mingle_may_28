from odoo import models, fields


class HyperpayAudit(models.Model):
    _name = 'hyperpay.audit'
    _description = 'Hyperpay Audit'

    jobcard_id = fields.Many2one('project.task', string='Job Card')
    name = fields.Char(string='Jobcard Number', required=True)

    payment_for = fields.Selection([
        ('inspection', 'Inspection'),
        ('final', 'Final Payment')
    ], string='Payment For', required=True)

    payment_receipt_number = fields.Char(string='Payment Receipt Number', required=True)

    payment_reference = fields.Char(string='Payment Reference')

    payment_received = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')
    ], string='Payment Received', default='no')

    received_datetime = fields.Datetime(string='Received Date & Time')

    status = fields.Selection([
        ('success', 'Success'),
        ('pending', 'Pending'),
        ('failure', 'Failure')
    ], string='Status', default='pending')
    
    # custom_319 =  fields.Char(string = "Custom_319" , help = "Eastern Region Job Card Number",deprecated =False)
    #
    # custom_317 = fields.Char(string = "custom_317",help = "Central Region Job Card Number",deprecated =False)
    #
    # region = fields.Char(string = "Region",deprecated =False)
    #

    
    
    
