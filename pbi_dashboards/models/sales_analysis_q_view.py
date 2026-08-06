from odoo import models, tools


class PbiSalesAnalysisQView(models.Model):
    _name = 'pbi.sales.analysis.q.view'
    _description = 'PBI Sales Analysis (Q) — transaction tables (SQL view)'
    _auto = False
    _order = 'id'

    def init(self):
        # Seed menu access rights for the admin user
        if 'menu.access.rights' in self.env:
            admin = self.env.ref('base.user_admin', raise_if_not_found=False)
            menu = self.env.ref('pbi_dashboards.menu_pbi_sales_kpi_analysis_q', raise_if_not_found=False)
            if admin and menu:
                existing = self.env['menu.access.rights'].sudo().search([
                    ('user_id', '=', admin.id), ('menu_id', '=', menu.id),
                ], limit=1)
                if not existing:
                    self.env['menu.access.rights'].sudo().create({
                        'user_id': admin.id,
                        'menu_id': menu.id,
                        'has_access': True,
                    })
                else:
                    existing.has_access = True

        # Create salestypes_group table if not exists
        self._cr.execute("""
            CREATE TABLE IF NOT EXISTS salestypes_group (
                id SERIAL PRIMARY KEY,
                salgrp_ref VARCHAR(255) NOT NULL UNIQUE,
                salgrp_name VARCHAR(255) NOT NULL,
                salgrp_name2 VARCHAR(255),
                create_uid INTEGER,
                write_uid INTEGER,
                create_date TIMESTAMP WITHOUT TIME ZONE,
                write_date TIMESTAMP WITHOUT TIME ZONE
            );
        """)

        # Create sale_types table if not exists
        self._cr.execute("""
            CREATE TABLE IF NOT EXISTS sale_types (
                id SERIAL PRIMARY KEY,
                saltype_group INTEGER NOT NULL REFERENCES salestypes_group(id) ON DELETE RESTRICT,
                sal_ref VARCHAR(255) NOT NULL UNIQUE,
                saltype_name VARCHAR(255) NOT NULL,
                saltype_name2 VARCHAR(255),
                create_uid INTEGER,
                write_uid INTEGER,
                create_date TIMESTAMP WITHOUT TIME ZONE,
                write_date TIMESTAMP WITHOUT TIME ZONE
            );
        """)

        # Insert sample data into salestypes_group if empty
        self._cr.execute("SELECT COUNT(*) FROM salestypes_group")
        if self._cr.fetchone()[0] == 0:
            self._cr.execute("""
                INSERT INTO salestypes_group (salgrp_ref, salgrp_name) VALUES
                ('RT', 'Retail'),
                ('WS', 'Wholesale'),
                ('CP', 'Corporate');
            """)

        # Insert sample data into sale_types if empty
        self._cr.execute("SELECT COUNT(*) FROM sale_types")
        if self._cr.fetchone()[0] == 0:
            self._cr.execute("""
                INSERT INTO sale_types (saltype_group, sal_ref, saltype_name) VALUES
                ((SELECT id FROM salestypes_group WHERE salgrp_ref = 'RT' LIMIT 1), 'RT_ON', 'Online Sales'),
                ((SELECT id FROM salestypes_group WHERE salgrp_ref = 'RT' LIMIT 1), 'RT_SR', 'Showroom Sales'),
                ((SELECT id FROM salestypes_group WHERE salgrp_ref = 'WS' LIMIT 1), 'WS_DS', 'Distributor Sales'),
                ((SELECT id FROM salestypes_group WHERE salgrp_ref = 'WS' LIMIT 1), 'WS_DL', 'Dealer Sales'),
                ((SELECT id FROM salestypes_group WHERE salgrp_ref = 'CP' LIMIT 1), 'CP_PR', 'Project Sales'),
                ((SELECT id FROM salestypes_group WHERE salgrp_ref = 'CP' LIMIT 1), 'CP_GV', 'Government Sales');
            """)

        # Update customer table cst_defslt values to link to the new sample sales types
        self._cr.execute("""
            UPDATE customer 
            SET cst_defslt = CASE 
                WHEN id % 3 = 0 THEN 'RT_ON'
                WHEN id % 3 = 1 THEN 'WS_DS'
                ELSE 'CP_PR'
            END
            WHERE cst_defslt IS NULL OR cst_defslt = '' OR cst_defslt NOT IN ('RT_ON', 'RT_SR', 'WS_DS', 'WS_DL', 'CP_PR', 'CP_GV');
        """)

        tools.drop_view_if_exists(self._cr, 'v_pbi_sales_analysis_q')
        self._cr.execute("""
            CREATE OR REPLACE VIEW v_pbi_sales_analysis_q AS (
                SELECT
                    row_number() OVER() AS id,
                    CAST(SUBSTRING(th.trnh_date FROM 1 FOR 4) AS INTEGER) AS bi_year,
                    CAST(SUBSTRING(th.trnh_date FROM 5 FOR 2) AS INTEGER) AS bi_month,
                    TO_DATE(th.trnh_date, 'YYYYMMDD') AS bi_monthdate,
                    sub.sr_region AS bi_cstregioncode,
                    INITCAP(rd.r_desc) AS bi_cstregiondesc,
                    sub.sr_code AS bi_cstsubregioncode,
                    INITCAP(srd.sr_desc) AS bi_cstsubregiondesc,
                    c.cat_pgroup AS bi_pgroupcode,
                    pd.p_desc AS bi_pgroupname,
                    c.cat_psgroup AS bi_psgroupcode,
                    psd.ps_desc AS bi_psgroupname,
                    c.cat_psgroup AS prod_group_code,
                    psd.ps_desc AS prod_group_name,
                    td.trnd_part AS bi_invpartno,
                    td.trnd_part AS product_sub_group_code,
                    COALESCE(c.cat_desc, td.trnd_part) AS product_sub_group_name,
                    th.trnh_cstno AS bi_cstno,
                    th.trnh_cstno AS customer_code,
                    th.trnh_cstname AS bi_cstname,
                    th.trnh_cstname AS customer_name,
                    th.trnh_no AS bi_invno,
                    th.trnh_no AS transaction_no,
                    TO_DATE(th.trnh_date, 'YYYYMMDD') AS transaction_date,
                    th.trnh_whouse AS bi_invwhouse,
                    th.trnh_whouse AS warehouse_code,
                    COALESCE(w.wh_desc, th.trnh_whouse) AS bi_invwhousename,
                    COALESCE(w.wh_desc, th.trnh_whouse) AS warehouse_name,
                    CASE WHEN th.trnh_type IN ('02', '2') THEN COALESCE(td.trnd_ret, 0) * -1
                         ELSE COALESCE(td.trnd_qtyiss, 0) END AS bi_qty,
                    CASE WHEN th.trnh_type IN ('02', '2') THEN 
                              (COALESCE(td.trnd_ret, 0) * (COALESCE(td.trnd_price, 0) - COALESCE(td.trnd_disc, 0) - COALESCE(td.trnd_cstspldisc, 0))) * -1
                         ELSE 
                              (COALESCE(td.trnd_qtyiss, 0) * (COALESCE(td.trnd_price, 0) - COALESCE(td.trnd_disc, 0) - COALESCE(td.trnd_cstspldisc, 0))) END AS bi_amount,
                    0::numeric AS bi_budgetqty,
                    0::double precision AS bi_budgetamount,
                    CASE WHEN c.cat_pgroup LIKE 'AC%' OR c.cat_pgroup = 'ATOM' OR th.trnh_franchise = 'MDA' THEN 'MDA'
                         WHEN c.cat_pgroup LIKE 'BKO%' OR th.trnh_franchise = 'BKO' THEN 'BKO'
                         WHEN c.cat_pgroup LIKE 'CDY%' OR th.trnh_franchise = 'CDY' THEN 'CDY'
                         ELSE 'MDA' END AS bi_franchisecode,
                    CASE WHEN c.cat_pgroup LIKE 'AC%' OR c.cat_pgroup = 'ATOM' OR th.trnh_franchise = 'MDA' THEN 'Midea'
                         WHEN c.cat_pgroup LIKE 'BKO%' OR th.trnh_franchise = 'BKO' THEN 'BEKO'
                         WHEN c.cat_pgroup LIKE 'CDY%' OR th.trnh_franchise = 'CDY' THEN 'CANDY'
                         ELSE 'Midea' END AS bi_franchisename,
                    sg.salgrp_ref AS bi_csttypecode,
                    sg.salgrp_name AS bi_csttypedesc,
                    st.sal_ref AS bi_cstsubtypecode,
                    st.saltype_name AS bi_cstsubtypedesc,
                    th.trnh_sman AS bi_salesmancode,
                    th.trnh_salesmanname AS bi_salesmanname,
                    td.trnd_price AS bi_invprice,
                    td.trnd_disc AS bi_invdisc,
                    td.trnd_cstspldisc AS bi_invcstspldisc,
                    'S' AS bi_type
                FROM transaction_header th
                JOIN transaction_details td ON td.trnd_no = th.trnh_no AND td.trnd_whouse = th.trnh_whouse
                LEFT JOIN (
                    SELECT DISTINCT ON (cat_part) cat_part, cat_grp, cat_pgroup, cat_psgroup, cat_desc
                    FROM catalog
                    ORDER BY cat_part, id
                ) c ON c.cat_part = td.trnd_part
                LEFT JOIN t_productsdesc pd ON pd.p_grp = c.cat_grp AND pd.p_code = c.cat_pgroup AND pd.p_lang = '1'
                LEFT JOIN t_productsubsdesc psd ON psd.ps_grp = c.cat_grp AND psd.ps_pcode = c.cat_pgroup AND psd.ps_psub = c.cat_psgroup AND psd.ps_lang = '1'
                LEFT JOIN customer cust ON cust.cst_no = th.trnh_cstno
                LEFT JOIN sale_types st ON st.sal_ref = cust.cst_defslt
                LEFT JOIN salestypes_group sg ON sg.id = st.saltype_group
                LEFT JOIN t_subregions sub ON sub.sr_code = UPPER(TRIM(cust.cst_subregion))
                LEFT JOIN t_regionsdesc rd ON rd.r_code = sub.sr_region AND rd.r_lang = 1
                LEFT JOIN t_subregionsdesc srd ON srd.sr_code = sub.sr_code AND srd.sr_lang = 1
                LEFT JOIN t_warehousedesc w ON w.wh_code = th.trnh_whouse AND w.wh_lang = 1
            )
        """)
