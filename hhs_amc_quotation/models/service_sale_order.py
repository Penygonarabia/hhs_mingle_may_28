from odoo import models, fields, api

class ServiceSaleOrder(models.Model):
    _inherit = 'service.sale.order'

    quotation_payment_term_ids = fields.One2many(
        'quotation.payment.term',
        'payment_order_id',
        string="Payment Terms"
    )