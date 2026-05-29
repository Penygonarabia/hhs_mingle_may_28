# -*- coding: utf-8 -*-
from odoo import models, fields, tools


class VIProductLinesServiceItems(models.Model):
    _name = 'vi.product.lines.serviceitems'
    _description = 'VI Product Lines Service Items (PostgreSQL View)'
    _auto = False  # Prevent Odoo from creating a physical table

    id = fields.Integer()
    inv_whouse = fields.Char()
    inv_no = fields.Char()
    inv_slno = fields.Integer()
    inv_subslno = fields.Integer()
    inv_orcr = fields.Integer()
    inv_orcpno = fields.Integer()
    inv_pno = fields.Char()
    inv_pact = fields.Char()
    inv_nonstock = fields.Char()
    inv_desc = fields.Json()
    inv_stock = fields.Char()
    inv_group = fields.Char()
    inv_part = fields.Char()
    inv_det1 = fields.Char()
    inv_det2 = fields.Char()
    inv_qtyreq = fields.Float()
    inv_qtyiss = fields.Float()
    inv_cost = fields.Integer()
    inv_price = fields.Float()
    inv_disc = fields.Integer()
    inv_pdisc = fields.Integer()
    inv_vatcode = fields.Char()
    inv_vat = fields.Char()
    inv_ret = fields.Integer()
    inv_pidref = fields.Char()
    inv_xface = fields.Char()
    inv_fleetsale = fields.Char()
    inv_trnslno = fields.Integer()
    inv_trnsubslno = fields.Integer()
    inv_subtrntype = fields.Char()
    inv_subtrnref = fields.Char()
    inv_cstordflag = fields.Char()
    inv_sourcewh = fields.Char()
    inv_discp = fields.Integer()
    inv_reqgroup = fields.Integer()
    inv_reqstock = fields.Integer()
    inv_reqpart = fields.Integer()
    inv_reqdesc = fields.Integer()
    inv_orgreqqty = fields.Integer()
    inv_cstpriceflg = fields.Integer()
    inv_isswhouse = fields.Char()
    inv_export = fields.Integer()
    inv_wqty = fields.Integer()
    inv_dsiamt = fields.Integer()
    inv_salcat = fields.Char()
    inv_vatexp = fields.Integer()
    inv_promodisc = fields.Integer()
    inv_promomsg1 = fields.Integer()
    inv_promomsg2 = fields.Integer()
    inv_promomsg3 = fields.Integer()
    inv_campaign = fields.Integer()
    inv_campaignref = fields.Integer()
    inv_autocrnoteval = fields.Integer()
    inv_autocrnotestatus = fields.Char()

    # Override the init method to create the view
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                 SELECT
    row_number() OVER () AS id,
    '' AS INV_WHOUSE,
    pt.Name as INV_NO,
    row_number() OVER (PARTITION BY pl.project_task_id ORDER BY pl.id) AS INV_SLNO,
    1 AS INV_SUBSLNO,
    0 AS INV_ORCR,
    0 AS INV_ORCPNO,
    '' AS INV_PNO,
    '' AS INV_PACT,
    'N' AS INV_NONSTOCK,
    ptem.name AS INV_DESC,
    '*' AS INV_STOCK,
    CASE 
        WHEN pc.name = 'Midea' THEN 'MDA'
        WHEN pc.name = 'Beko' THEN 'BKO'
        WHEN pc.name = 'ALASKA' THEN 'ASK'
        WHEN pc.name = 'Candy' THEN 'CDY'
        ELSE NULL
    END AS INV_GROUP,
    pp.default_code AS INV_PART,
    '' AS INV_DET1,
    '' AS INV_DET2,
    pl.qty AS INV_QTYREQ,
    pl.qty AS INV_QTYISS,
    0 AS INV_COST,
    pl.price_unit AS INV_PRICE,
    0 AS INV_DISC,
    0 AS INV_PDISC,
    CASE 
        WHEN pl.price_unit = 0 THEN '03'
        ELSE '15'
    END AS INV_VATCODE,
    (tax_amount/qty) AS INV_VAT,
    0 AS INV_RET,
    '' AS INV_PIDREF,
    CASE 
        WHEN pl.price_unit = 0 THEN '004'
        ELSE '009'
    END AS INV_XFACE,
    '' AS INV_FLEETSALE,
    0 AS INV_TRNSLNO,
    1 AS INV_TRNSUBSLNO,
    '' AS INV_SUBTRNTYPE,
    '' AS INV_SUBTRNREF,
    'N' AS INV_CSTORDFLAG,
    sw.code AS INV_SOURCEWH,
    0 AS INV_DISCP,
    0 AS INV_REQGROUP,
    0 AS INV_REQSTOCK,
    0 AS INV_REQPART,
    0 AS INV_REQDESC,
    0 AS INV_ORGREQQTY,
    0 AS INV_CSTPRICEFLG,
    'N' AS INV_ISSWHOUSE,
    0 AS INV_EXPORT,
    0 AS INV_WQTY,
    0 AS INV_DSIAMT,
    'N' AS INV_SALCAT,
    0 AS INV_VATEXP,
    0 AS INV_PROMODISC,
    0 AS INV_PROMOMSG1,
    0 AS INV_PROMOMSG2,
    0 AS INV_PROMOMSG3,
    0 AS INV_CAMPAIGN,
    0 AS INV_CAMPAIGNREF,
    0 AS INV_AUTOCRNOTEVAL,
    'N' AS INV_AUTOCRNOTESTATUS
FROM product_lines pl
JOIN project_task pt ON pt.id = pl.project_task_id
JOIN product_product pp ON pp.id = pl.product_id
JOIN product_template ptem ON ptem.id = pp.product_tmpl_id
JOIN product_category pc ON pc.id = ptem.categ_id
LEFT JOIN stock_warehouse sw ON pt.warehouse_id = sw.id 				           
            );
        """)
