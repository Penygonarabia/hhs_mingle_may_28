# -*- coding: utf-8 -*-
from odoo import models, fields, tools


class VIProductTaskList(models.Model):
    _name = 'vi.product.task.namelist'
    _description = 'VI Product Task Namelist'
    _auto = False
    _table = 'vi_product_task_namelist'  # explicitly set table name

    id = fields.Integer(readonly=True)
    inv_whouse = fields.Char()
    inv_manualinvno = fields.Char()

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
               CREATE OR REPLACE VIEW {self._table} AS (
                   SELECT
                       pt.id AS id,
                       invwh.inv_whouse,
                       pt.name AS inv_manualinvno
                   FROM project_task pt
                   LEFT JOIN LATERAL (
                       SELECT sw2.code AS inv_whouse
                       FROM stock_warehouse sw2
                       JOIN project_task pt2 ON pt2.warehouse_id = sw2.id
                       WHERE (
                        (pt2.job_card_state = 'Closed' AND pt2.closed_datetime IS NOT NULL)
                        OR (pt2.job_card_state = 'Cancelled' AND pt2.inspection_charges_amount > 0))
                        AND pt2.name = pt.name
                       LIMIT 1
                   ) invwh ON true
                   WHERE ((pt.job_card_state = 'Closed' AND pt.closed_datetime IS NOT NULL)
                    OR (pt.job_card_state = 'Cancelled' AND pt.inspection_charges_amount > 0))
                    AND pt.export_bool = false                    
                    AND pt.id in (select project_task_id from product_lines)
               );
           """)