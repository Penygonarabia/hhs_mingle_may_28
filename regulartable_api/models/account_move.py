from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_no = fields.Char(string="Invoice No")
    export_bool = fields.Boolean(string="Export",  default=False)
    invoice_date_custom = fields.Date(string="Invoice Date")