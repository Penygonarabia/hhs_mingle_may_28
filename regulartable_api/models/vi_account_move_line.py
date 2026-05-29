# models/vi_account_move_line.py

from odoo import models, fields, tools


class ViAccountMoveLine(models.Model):
    _name = 'vi.account.move.line'
    _description = 'VI Account Move Line'
    _auto = False
    _rec_name = 'inv_no'


    inv_whouse = fields.Char(string='Warehouse')
    inv_no = fields.Char(string='Invoice No')
    inv_slno = fields.Integer(string='SL No')
    inv_subslno = fields.Integer(string='Sub SL No')
    inv_orcr = fields.Integer(string='ORCR')
    inv_orcpno = fields.Integer(string='ORCPNO')
    inv_pno = fields.Char(string='PNO')
    inv_pact = fields.Char(string='PACT')
    inv_nonstock = fields.Char(string='Non Stock')
    inv_desc = fields.Char(string='Description')
    inv_group = fields.Char(string='Group')
    inv_stock = fields.Char(string='Stock')
    inv_part = fields.Char(string='Part Number')
    inv_det1 = fields.Char(string='Detail 1')
    inv_det2 = fields.Char(string='Detail 2')
    inv_qtyreq = fields.Float(string='Qty Requested')
    inv_qtyiss = fields.Float(string='Qty Issued')
    inv_cost = fields.Float(string='Cost')
    inv_price = fields.Float(string='Price')
    inv_disc = fields.Float(string='Discount')
    inv_pdisc = fields.Float(string='Discount %')
    inv_vatcode = fields.Char(string='VAT Code')
    inv_vat = fields.Float(string='VAT')
    inv_ret = fields.Float(string='Return')
    inv_pidref = fields.Char(string='PID Ref')
    inv_xface = fields.Integer(string='XFace')
    inv_fleetsale = fields.Char(string='Fleet Sale')
    inv_trnslno = fields.Integer(string='Transaction Line No')
    inv_trnsubslno = fields.Integer(string='Transaction Sub Line No')
    inv_subtrntype = fields.Char(string='Sub Transaction Type')
    inv_subtrnref = fields.Char(string='Sub Transaction Ref')
    inv_cstordflag = fields.Char(string='Customer Order Flag')
    inv_sourcewh = fields.Char(string='Source Warehouse')
    inv_discp = fields.Float(string='Discount Percentage')
    inv_reqgroup = fields.Float(string='Request Group')
    inv_reqstock = fields.Float(string='Request Stock')
    inv_reqpart = fields.Float(string='Request Part')
    inv_reqdesc = fields.Float(string='Request Desc')
    inv_orgreqqty = fields.Float(string='Original Req Qty')
    inv_cstpriceflg = fields.Integer(string='Customer Price Flag')
    inv_isswhouse = fields.Char(string='Issue Warehouse')
    inv_export = fields.Integer(string='Export')
    inv_wqty = fields.Float(string='WQTY')
    inv_dsiamt = fields.Float(string='Discount Amount')
    inv_salcat = fields.Char(string='Sale Category')
    inv_vatexp = fields.Integer(string='VAT Export')
    inv_promodisc = fields.Float(string='Promo Discount')
    inv_promomsg1 = fields.Float(string='Promo Msg1')
    inv_promomsg2 = fields.Float(string='Promo Msg2')
    inv_promomsg3 = fields.Float(string='Promo Msg3')
    inv_campaign = fields.Float(string='Campaign')
    inv_campaignref = fields.Float(string='Campaign Ref')
    inv_autocrnoteval = fields.Float(string='Auto CR Note Value')
    inv_autocrnotestatus = fields.Char(string='Auto CR Note Status')


    def init(self):
        tools.drop_view_if_exists(self._cr, 'vi_account_move_line')

        self._cr.execute("""
            CREATE OR REPLACE VIEW vi_account_move_line AS (

               SELECT
    aml.id AS id,

    -- Warehouse
    sw.code AS INV_WHOUSE,

    -- Invoice Number
    am.name AS INV_NO,

    -- Auto Number based on Invoice
    ROW_NUMBER() OVER (
        PARTITION BY am.name
        ORDER BY aml.id
    ) AS INV_SLNO,

    -- Sub Line No
    1 AS INV_SUBSLNO,

    -- ORCR
    0 AS INV_ORCR,

    -- ORCPNO
    0 AS INV_ORCPNO,

    -- PNO
    NULL AS INV_PNO,

    -- PACT
    NULL AS INV_PACT,

    -- Non Stock
    'N' AS INV_NONSTOCK,

	-- Description
	pt.name AS INV_DESC,

	-- Group
	pp.category_code AS INV_GROUP,

	-- Stock
	'*' AS INV_STOCK,

	-- Part Number
	pp.default_code AS INV_PART,

    -- Detail Fields
    '' AS INV_DET1,
    '' AS INV_DET2,

    -- Quantity Requested
    aml.quantity AS INV_QTYREQ,

    -- Quantity Issued
    aml.quantity AS INV_QTYISS,

    -- Cost
    0 AS INV_COST,

    -- Price
    aml.price_unit AS INV_PRICE,

    -- Discount
    0 AS INV_DISC,

    -- Discount Percentage
    0 AS INV_PDISC,

    -- VAT Code
    CASE
        WHEN aml.price_unit = 0 THEN '03'
        ELSE '15'
    END AS INV_VATCODE,

    -- VAT Amount Per Qty
     CASE
        WHEN aml.quantity > 0
        THEN ROUND((aml.vat_amt / aml.quantity)::numeric, 2)
        ELSE 0
    END AS INV_VAT,

    -- Return
    0 AS INV_RET,

    -- PID Reference
    NULL AS INV_PIDREF,

    -- XFACE
    777 AS INV_XFACE,

    -- Fleet Sale
    NULL AS INV_FLEETSALE,

    -- Transaction Line No
    0 AS INV_TRNSLNO,

    -- Transaction Sub Line No
    1 AS INV_TRNSUBSLNO,

    -- Sub Transaction Type
    '' AS INV_SUBTRNTYPE,

    -- Sub Transaction Ref
    '' AS INV_SUBTRNREF,

    -- Customer Order Flag
    'N' AS INV_CSTORDFLAG,

    -- Source Warehouse
    sw.code AS INV_SOURCEWH,

    -- Discount Percentage
    0 AS INV_DISCP,

    -- Request Group
    0 AS INV_REQGROUP,

    -- Request Stock
    0 AS INV_REQSTOCK,

    -- Request Part
    0 AS INV_REQPART,

    -- Request Desc
    0 AS INV_REQDESC,

    -- Original Request Qty
    0 AS INV_ORGREQQTY,

    -- Customer Price Flag
    0 AS INV_CSTPRICEFLG,

    -- Issue Warehouse
    'N' AS INV_ISSWHOUSE,

    -- Export
    0 AS INV_EXPORT,

    -- WQTY
    0 AS INV_WQTY,

    -- Discount Amount
    0 AS INV_DSIAMT,

    -- Sale Category
    'N' AS INV_SALCAT,

    -- VAT Export
    0 AS INV_VATEXP,

    -- Promo Discount
    0 AS INV_PROMODISC,

    -- Promo Message 1
    0 AS INV_PROMOMSG1,

    -- Promo Message 2
    0 AS INV_PROMOMSG2,

    -- Promo Message 3
    0 AS INV_PROMOMSG3,

    -- Campaign
    0 AS INV_CAMPAIGN,

    -- Campaign Ref
    0 AS INV_CAMPAIGNREF,

    -- Auto Credit Note Value
    0 AS INV_AUTOCRNOTEVAL,

    -- Auto Credit Note Status
    'N' AS INV_AUTOCRNOTESTATUS

FROM account_move_line aml

LEFT JOIN account_move am
    ON aml.move_id = am.id

LEFT JOIN product_product pp
    ON aml.product_id = pp.id

LEFT JOIN product_template pt
    ON pp.product_tmpl_id = pt.id


LEFT JOIN stock_warehouse sw
                    ON sw.id = am.warehouse_id

WHERE am.move_type = 'out_invoice'
AND am.state in ('posted') 
AND aml.product_id IS NOT NULL

            )
        """)