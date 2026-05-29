from odoo import models, fields, tools

class VIProductLinesItems(models.Model):
    _name = 'vi.product.lines.items'
    _description = 'VI Product Lines Items (PostgreSQL View)'
    _auto = False  # This is a view, not a table

    # Primary key
    id = fields.Integer(string='ID', readonly=True)

    # Fields from the SQL view
    inv_whouse = fields.Char(string='Warehouse')
    inv_no = fields.Char(string='Invoice No', index=True)
    inv_slno = fields.Integer(string='SL No')
    inv_subslno = fields.Integer(string='Sub SL No')
    inv_orcr = fields.Integer(string='ORCR')
    inv_orcpno = fields.Integer(string='ORCP No')
    inv_pno = fields.Char(string='P No')
    inv_pact = fields.Char(string='PACT')
    inv_nonstock = fields.Char(string='Non-Stock')
    inv_desc = fields.Char(string='Description')
    inv_stock = fields.Char(string='Stock')
    inv_group = fields.Char(string='Group')
    inv_part = fields.Char(string='Part')
    inv_det1 = fields.Char(string='Detail 1')
    inv_det2 = fields.Char(string='Detail 2')
    inv_qtyreq = fields.Float(string='Qty Required')
    inv_qtyiss = fields.Float(string='Qty Issued')
    inv_cost = fields.Float(string='Cost')
    inv_price = fields.Float(string='Price')
    inv_disc = fields.Float(string='Discount')
    inv_pdisc = fields.Float(string='PDiscount')
    inv_vatcode = fields.Char(string='VAT Code')
    inv_vat = fields.Char(string='VAT')
    inv_ret = fields.Integer(string='Return')
    inv_pidref = fields.Char(string='PID Ref')
    inv_xface = fields.Char(string='XFace')
    inv_fleetsale = fields.Char(string='Fleet Sale')
    inv_trnslno = fields.Integer(string='Trans SL No')
    inv_trnsubslno = fields.Integer(string='Trans Sub SL No')
    inv_subtrntype = fields.Char(string='Sub Trans Type')
    inv_subtrnref = fields.Char(string='Sub Trans Ref')
    inv_cstordflag = fields.Char(string='Cst Ord Flag')
    inv_sourcewh = fields.Char(string='Source Warehouse')
    inv_discp = fields.Integer(string='Disc P')
    inv_reqgroup = fields.Integer(string='Req Group')
    inv_reqstock = fields.Integer(string='Req Stock')
    inv_reqpart = fields.Integer(string='Req Part')
    inv_reqdesc = fields.Integer(string='Req Desc')
    inv_orgreqqty = fields.Integer(string='Org Req Qty')
    inv_cstpriceflg = fields.Integer(string='Cst Price Flag')
    inv_isswhouse = fields.Char(string='Issue Warehouse')
    inv_export = fields.Integer(string='Export')
    inv_wqty = fields.Integer(string='W Qty')
    inv_dsiamt = fields.Integer(string='DSI Amt')
    inv_salcat = fields.Char(string='Sales Category')
    inv_vatexp = fields.Integer(string='VAT Exp')
    inv_promodisc = fields.Integer(string='Promo Disc')
    inv_promomsg1 = fields.Integer(string='Promo Msg 1')
    inv_promomsg2 = fields.Integer(string='Promo Msg 2')
    inv_promomsg3 = fields.Integer(string='Promo Msg 3')
    inv_campaign = fields.Integer(string='Campaign')
    inv_campaignref = fields.Integer(string='Campaign Ref')
    inv_autocrnoteval = fields.Integer(string='Auto CR Note Val')
    inv_autocrnotestatus = fields.Char(string='Auto CR Note Status')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    '' AS inv_whouse,
                    pt.name AS inv_no,
                    row_number() OVER (PARTITION BY pl.project_task_id ORDER BY pl.id) AS inv_slno,
                    1 AS inv_subslno,
                    0 AS inv_orcr,
                    0 AS inv_orcpno,
                    '' AS inv_pno,
                    '' AS inv_pact,
                    'N' AS inv_nonstock,
                    ptem.name AS inv_desc,
                    '*' AS inv_stock,
                    CASE 
                        WHEN pc.name = 'Midea' THEN 'MDA'
                        WHEN pc.name = 'Beko' THEN 'BKO'
                        WHEN pc.name = 'ALASKA' THEN 'ASK'
                        WHEN pc.name = 'Candy' THEN 'CDY'
                        ELSE NULL
                    END AS inv_group,
                    pp.default_code AS inv_part,
                    '' AS inv_det1,
                    '' AS inv_det2,
                    pl.qty AS inv_qtyreq,
                    pl.qty AS inv_qtyiss,
                    0 AS inv_cost,
                    pl.price_unit AS inv_price,
                    0 AS inv_disc,
                    0 AS inv_pdisc,
                    CASE 
                        WHEN pl.price_unit = 0 THEN '03'
                        ELSE '15'
                    END AS inv_vatcode,
                    (tax_amount/qty) AS inv_vat,
                    0 AS inv_ret,
                    '' AS inv_pidref,
                    CASE 
                        WHEN pl.price_unit = 0 THEN '004'
                        ELSE '009'
                    END AS inv_xface,
                    '' AS inv_fleetsale,
                    0 AS inv_trnslno,
                    1 AS inv_trnsubslno,
                    '' AS inv_subtrntype,
                    '' AS inv_subtrnref,
                    'N' AS inv_cstordflag,
                    sw.code AS inv_sourcewh,
                    0 AS inv_discp,
                    0 AS inv_reqgroup,
                    0 AS inv_reqstock,
                    0 AS inv_reqpart,
                    0 AS inv_reqdesc,
                    0 AS inv_orgreqqty,
                    0 AS inv_cstpriceflg,
                    'N' AS inv_isswhouse,
                    0 AS inv_export,
                    0 AS inv_wqty,
                    0 AS inv_dsiamt,
                    'N' AS inv_salcat,
                    0 AS inv_vatexp,
                    0 AS inv_promodisc,
                    0 AS inv_promomsg1,
                    0 AS inv_promomsg2,
                    0 AS inv_promomsg3,
                    0 AS inv_campaign,
                    0 AS inv_campaignref,
                    0 AS inv_autocrnoteval,
                    'N' AS inv_autocrnotestatus
                FROM product_lines pl
                JOIN project_task pt ON pt.id = pl.project_task_id
                JOIN product_product pp ON pp.id = pl.product_id
                JOIN product_template ptem ON ptem.id = pp.product_tmpl_id
                JOIN product_category pc ON pc.id = ptem.product_category_id
                LEFT JOIN stock_warehouse sw ON pt.warehouse_id = sw.id
            );
        """)
