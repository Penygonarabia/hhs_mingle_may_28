from odoo import models, fields, api

class CrmContractTypeConfiguration(models.Model):
    _inherit = 'crm.contract.type'

    sr_warranty_id = fields.Many2one('service.warranty', string="service warranty",required=True)