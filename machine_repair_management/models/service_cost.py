from odoo import models, fields


class ServiceCost(models.Model):
    _name = 'service.cost'
    _description = 'Service Cost'

    name = fields.Char(string='Unit Type', required=True)
    standard_hours = fields.Float(string='Standard Hours', required=True)
    cost_service_only = fields.Float(string='Cost - Service Only', required=True)

