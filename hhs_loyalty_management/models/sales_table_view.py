from odoo import models, fields, api, tools

class LoyaltySalesTableView(models.Model):
    _name = 'loyalty.sales.table.view'
    _description = 'Sales Table View'
    _auto = False

    trnh_region = fields.Char(string='Region', readonly=True)
    trnh_city = fields.Char(string='City', readonly=True)
    trnh_sman = fields.Char(string='Salesman', readonly=True)
    trnh_cstno = fields.Char(string='Customer Code', readonly=True)
    trnh_cstname = fields.Char(string='Customer Name', readonly=True)
    trnh_cstmobile = fields.Char(string='Mobile #', readonly=True)
    tier_name = fields.Char(string='Tier Name', readonly=True)
    activate_loyalty_feature = fields.Boolean(string="Activate Loyalty Feature", readonly=True)
    trnh_type = fields.Char(string='Transaction Type', readonly=True)
    trnh_whouse = fields.Char(string='Warehouse', readonly=True)
    trnh_no = fields.Char(string='Transaction No', readonly=True)
    trnh_date = fields.Date(string='Transaction Date', readonly=True)
    trnd_slno = fields.Char(string='SL #', readonly=True)
    trnd_group = fields.Char(string='Product Category', readonly=True)
    product_group = fields.Char(string='Product Group', readonly=True)
    product_subgroup = fields.Char(string='Product Sub Group', readonly=True)
    trnd_part = fields.Char(string='Product #', readonly=True)
    trnd_desc = fields.Char(string='Product Name', readonly=True)
    qty = fields.Float(string='Qty', readonly=True)
    net_sales = fields.Float(string='Net Sales', readonly=True)
    net_sales_with_vat = fields.Float(string='Net Sales With VAT', readonly=True)
    clph_promoref = fields.Char(string='Promotion #', readonly=True)
    promotion_name = fields.Char(string='Promotion Name', readonly=True)
    clph_points = fields.Integer(string='Regular Points', readonly=True)
    clph_bonuspoint = fields.Integer(string='Bonus Points', readonly=True)
    total_points = fields.Integer(string='Total Points', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER () as id,
                    th.trnh_region,
                    th.trnh_city,
                    COALESCE(sm.sm_name, th.trnh_sman) as trnh_sman,
                    th.trnh_cstno,
                    th.trnh_cstname,
                    th.trnh_cstmobile,
                    rp.tier_name,
                    rp.activate_loyalty_feature as activate_loyalty_feature,
                    CASE 
                        WHEN th.trnh_type = '99' THEN 'Adjustments'
                        WHEN th.trnh_type = '98' THEN 'Redeem'
                        WHEN th.trnh_type = '97' THEN 'Expiry'
                        WHEN th.trnh_type = '01' THEN 'Invoice'
                        WHEN th.trnh_type = '02' THEN 'Credit Note'
                        ELSE th.trnh_type
                    END as trnh_type,
                    th.trnh_whouse,
                    th.trnh_no,
                    TO_DATE(th.trnh_date, 'YYYYMMDD') as trnh_date,
                    CAST(td.trnd_slno AS VARCHAR) as trnd_slno,
                    td.trnd_group,
                    pc_group.name as product_group,
                    pc_subgroup.name as product_subgroup,
                    td.trnd_part,
                    td.trnd_desc,
                    
                    -- Qty logic
                    CASE 
                        WHEN th.trnh_type = '02' THEN COALESCE(td.trnd_ret, 0) * -1
                        ELSE COALESCE(td.trnd_qtyiss, 0)
                    END as qty,

                    -- Net Sales logic
                    CASE 
                        WHEN th.trnh_type = '02' THEN 
                            (COALESCE(td.trnd_ret, 0) * (COALESCE(td.trnd_price, 0) - COALESCE(td.trnd_disc, 0) - COALESCE(td.trnd_cstspldisc, 0))) * -1
                        ELSE 
                            (COALESCE(td.trnd_qtyiss, 0) * (COALESCE(td.trnd_price, 0) - COALESCE(td.trnd_disc, 0) - COALESCE(td.trnd_cstspldisc, 0)))
                    END as net_sales,

                    -- Net Sales With VAT logic
                    CASE 
                        WHEN th.trnh_type = '02' THEN 
                            (COALESCE(td.trnd_ret, 0) * ((COALESCE(td.trnd_price, 0) - COALESCE(td.trnd_disc, 0) - COALESCE(td.trnd_cstspldisc, 0)) + COALESCE(td.trnd_vat, 0))) * -1
                        ELSE 
                            (COALESCE(td.trnd_qtyiss, 0) * ((COALESCE(td.trnd_price, 0) - COALESCE(td.trnd_disc, 0) - COALESCE(td.trnd_cstspldisc, 0)) + COALESCE(td.trnd_vat, 0)))
                    END as net_sales_with_vat,

                    NULLIF(TRIM(td.trnd_promoref), '') as clph_promoref,
                    lsp.promotion_name as promotion_name,
                    -- Regular Points (negate for Credit Notes)
                    CASE 
                        WHEN th.trnh_type = '02' THEN -ABS(COALESCE(td.trnd_regularpts, 0))
                        ELSE COALESCE(td.trnd_regularpts, 0)
                    END as clph_points,
                    -- Bonus Points (negate for Credit Notes)
                    CASE 
                        WHEN th.trnh_type = '02' THEN -ABS(COALESCE(td.trnd_bonuspts, 0))
                        ELSE COALESCE(td.trnd_bonuspts, 0)
                    END as clph_bonuspoint,
                    -- Total Points (negate for Credit Notes)
                    CASE 
                        WHEN th.trnh_type = '02' THEN -ABS(COALESCE(td.trnd_regularpts, 0) + COALESCE(td.trnd_bonuspts, 0))
                        ELSE COALESCE(td.trnd_regularpts, 0) + COALESCE(td.trnd_bonuspts, 0)
                    END as total_points

                FROM transaction_header th
                JOIN transaction_details td ON th.trnh_no = td.trnd_no
                LEFT JOIN res_partner rp ON rp.ref = th.trnh_cstno
                LEFT JOIN sl_salesman sm ON sm.sm_code = th.trnh_sman
                LEFT JOIN product_product pp ON pp.default_code = td.trnd_part
                LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN product_category pc_subgroup ON pc_subgroup.id = pt.categ_id
                LEFT JOIN product_category pc_group ON pc_group.id = pc_subgroup.parent_id
                LEFT JOIN lp_setup_promotions lsp ON lsp.promotion_reference = NULLIF(TRIM(td.trnd_promoref), '')
            )
        """ % (self._table,))
