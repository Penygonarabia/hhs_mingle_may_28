# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare, float_is_zero

class StockQuant(models.Model):
    _inherit = "stock.quant"

    analytic_account_id =fields.Many2one(
        string="Analytic Account", comodel_name="account.analytic.account"
    )
     