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
    sw.code AS inv_whouse,
    pt.name AS inv_manualinvno
FROM project_task pt

LEFT JOIN stock_warehouse sw
    ON sw.id = pt.warehouse_id

WHERE pt.job_card_state = 'Closed'
  AND pt.export_bool = FALSE
  AND pt.closed_datetime IS NOT NULL

  AND EXISTS (
        SELECT 1
        FROM product_lines pl
        JOIN product_product pp
            ON pp.id = pl.product_id
        WHERE pl.project_task_id = pt.id
         AND NOT (
                pl.price_unit = 0
                AND pp.default_code = 'INSPECTION'
          )
        GROUP BY pl.project_task_id
        HAVING

            MAX(CASE WHEN pl.under_warranty_bool = FALSE THEN 1 ELSE 0 END) = 1
            OR
            MAX(CASE WHEN pl.price_unit > 0 THEN 1 ELSE 0 END) = 1
            OR            
            MAX(CASE
                    WHEN pp.default_code NOT IN (
                        'INSPECTION',
                        'SERVICBEKO',
                        'SERVICE',
                        'SERVICEASK',
                        'SERVICECANDY'
                    )
                    THEN 1 ELSE 0
                END) = 1
    )
   )
           """)
