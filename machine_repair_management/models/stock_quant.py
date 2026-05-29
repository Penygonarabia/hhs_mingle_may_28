import heapq
import logging
from collections import namedtuple

from ast import literal_eval
from collections import defaultdict
from markupsafe import escape
from psycopg2 import Error

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import check_barcode_encoding, groupby, SQL
from odoo.tools.float_utils import float_compare, float_is_zero


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.model
    def _unlink_zero_quants(self):
        """ _update_available_quantity may leave quants with no
        quantity and no reserved_quantity. It used to directly unlink
        these zero quants but this proved to hurt the performance as
        this method is often called in batch and each unlink invalidate
        the cache. We defer the calls to unlink in this method.
        """
        precision_digits = max(6, self.sudo().env.ref('product.decimal_product_uom').digits * 2)
        # Use a select instead of ORM search for UoM robustness.
        query = """SELECT id FROM stock_quant WHERE (round(quantity::numeric, %s) = 0 OR quantity IS NULL)
                                                     AND round(reserved_quantity::numeric, %s) = 0
                                                     AND (round(inventory_quantity::numeric, %s) = 0 OR inventory_quantity IS NULL)
                                                     AND user_id IS NULL;"""
        params = (precision_digits, precision_digits, precision_digits)
        self.env.cr.execute(query, params)
        quants = self.env['stock.quant'].browse([quant['id'] for quant in self.env.cr.dictfetchall()])
        # quants.sudo().unlink()
