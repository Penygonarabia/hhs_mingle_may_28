# -*- coding: utf-8 -*-
from odoo import models, fields, service, _, api
import logging


class ResPartner(models.Model):
    _inherit = 'res.partner'

    pos_shop_ids = fields.One2many(
        'pos.config',
        'company_id',
        string="POS Shops"
    )