# -*- coding: utf-8 -*-
from tokenize import String

from odoo import models, fields, api


class machine_repair_request(models.Model):
    _name = 'machine.repair.request'
    _description = 'machine_repair_request.machine_repair_request'

    name = fields.Char()
    partner_id = fields.Many2one('res.partner',String='Customer')
    value = fields.Integer()
    description = fields.Text()

    # @api.depends('value')
    # def _value_pc(self):
    #     for record in self:
    #         record.value2 = float(record.value) / 100

