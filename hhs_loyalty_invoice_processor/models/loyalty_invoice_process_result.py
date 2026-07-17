from odoo import models, fields


class LoyaltyInvoiceProcessResult(models.TransientModel):
    _name = 'loyalty.invoice.process.result'
    _description = 'Invoice Processing Result'

    total_records = fields.Integer(string='Total Records', readonly=True)
    success_count = fields.Integer(string='Success Count', readonly=True)
    failed_count = fields.Integer(string='Failed Count', readonly=True)
    success_invoices = fields.Text(string='Success Invoice Numbers', readonly=True)
    failed_invoices = fields.Text(string='Failed Invoice Numbers', readonly=True)
