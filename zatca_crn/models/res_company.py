# -*- coding: utf-8 -*-
from odoo import models, fields, service, _, api
import logging

class ResCompany(models.Model):
    _inherit = 'res.company'

    pos_shop_ids = fields.One2many('pos.config', 'company_id', string="POS Shops",related='partner_id.pos_shop_ids',readonly=False)
