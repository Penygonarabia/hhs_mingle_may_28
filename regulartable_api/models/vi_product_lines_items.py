# -*- coding: utf-8 -*-
from odoo import models, fields, tools

class VIProductLinesItems(models.Model):
    _name = 'vi.product.lines.items'
    _description = 'VI Product Lines Items (PostgreSQL View)'
    _auto = False  # Prevent Odoo from creating a physical table

    inv_whouse = fields.Char()
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
        tools.drop_view_if_exists(self._cr, self._table)  # Ensure the view is recreated if it exists
        self._cr.execute("""
            CREATE OR REPLACE VIEW vi_product_lines_items AS (
                SELECT
                    id AS id,
                    warehouse AS inv_whouse,
                    subslno AS inv_subslno,
                    orcr AS inv_orcr,
                    orcpno AS inv_orcpno,
                    product_no AS inv_pno,
                    pact AS inv_pact,
                    nonstock AS inv_nonstock,
                    description::json AS inv_desc,
                    stock AS inv_stock,
                    group_code AS inv_group,
                    part_code AS inv_part,
                    detail_1 AS inv_det1,
                    detail_2 AS inv_det2,
                    qty_required AS inv_qtyreq,
                    qty_issued AS inv_qtyiss,
                    cost AS inv_cost,
                    price AS inv_price,
                    discount AS inv_disc,
                    promo_discount AS inv_pdisc,
                    vat_code AS inv_vatcode,
                    return_flag AS inv_ret,
                    pid_ref AS inv_pidref,
                    xface AS inv_xface,
                    fleet_sale_flag AS inv_fleetsale,
                    transaction_slno AS inv_trnslno,
                    transaction_sub_slno AS inv_trnsubslno,
                    sub_transaction_type AS inv_subtrntype,
                    sub_transaction_ref AS inv_subtrnref,
                    customer_order_flag AS inv_cstordflag,
                    source_warehouse AS inv_sourcewh,
                    discount_percentage AS inv_discp,
                    required_group AS inv_reqgroup,
                    required_stock AS inv_reqstock,
                    required_part AS inv_reqpart,
                    required_description AS inv_reqdesc,
                    original_request_qty AS inv_orgreqqty,
                    cost_price_flag AS inv_cstpriceflg,
                    issue_warehouse AS inv_isswhouse,
                    export_flag AS inv_export,
                    warehouse_qty AS inv_wqty,
                    dsi_amount AS inv_dsiamt,
                    sales_category AS inv_salcat,
                    vat_export_flag AS inv_vatexp,
                    promo_discount_amount AS inv_promodisc,
                    promo_message_1 AS inv_promomsg1,
                    promo_message_2 AS inv_promomsg2,
                    promo_message_3 AS inv_promomsg3,
                    campaign_id AS inv_campaign,
                    campaign_ref AS inv_campaignref,
                    auto_credit_note_value AS inv_autocrnoteval,
                    auto_credit_note_status AS inv_autocrnotestatus
                FROM product_lines  -- Replace 'product_lines' with the actual source table
            );
        """)

