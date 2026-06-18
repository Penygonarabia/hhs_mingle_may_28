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
    trnd_part = fields.Char(string='Product #', readonly=True)
    trnd_desc = fields.Char(string='Product Name', readonly=True)
    qty = fields.Float(string='Qty', readonly=True)
    net_sales = fields.Float(string='Net Sales', readonly=True)
    net_sales_with_vat = fields.Float(string='Net Sales With VAT', readonly=True)
    clph_promoref = fields.Char(string='Promotion #', readonly=True)
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
                    COALESCE(ph.clph_regpoints, 0) as clph_points,
                    COALESCE(ph.clph_bonuspoints, 0) as clph_bonuspoint,
                    COALESCE(ph.clph_regpoints, 0) + COALESCE(ph.clph_bonuspoints, 0) as total_points

                FROM transaction_header th
                JOIN transaction_details td ON th.trnh_no = td.trnd_no
                LEFT JOIN res_partner rp ON rp.ref = th.trnh_cstno
                LEFT JOIN sl_salesman sm ON sm.sm_code = th.trnh_sman
                LEFT JOIN (
                    SELECT 
                        clph_docnumber, 
                        clph_cstcode, 
                        MAX(clph_promoref) as clph_promoref,
                        SUM(COALESCE(clph_regpoints, 0)) as clph_regpoints,
                        SUM(COALESCE(clph_bonuspoints, 0)) as clph_bonuspoints
                    FROM customer_loyalty_points_history
                    GROUP BY clph_docnumber, clph_cstcode
                ) ph ON ph.clph_docnumber = th.trnh_no AND ph.clph_cstcode = th.trnh_cstno
            )
        """ % (self._table,))
