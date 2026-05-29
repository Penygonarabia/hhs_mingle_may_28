# -*- coding: utf-8 -*-
from odoo import models, fields, tools

class VIProductTask(models.Model):
    _name = 'vi.product.task'
    _description = 'VI Product Task'
    _auto = False  # View-backed model

    id = fields.Integer()
    inv_whouse = fields.Char()
    location_code = fields.Char()
    number_next = fields.Integer()
    work_center_id = fields.Integer()
    inv_no = fields.Char()
    inv_date = fields.Integer()
    inv_batch = fields.Char()
    inv_sman = fields.Char()
    inv_xface = fields.Char()
    inv_cstno = fields.Char()
    inv_cstname = fields.Char()
    inv_cstadd = fields.Char()
    inv_cstref = fields.Char()
    inv_comm = fields.Char()
    inv_mop = fields.Integer()
    inv_ccard = fields.Char()
    inv_ccardno = fields.Char()
    inv_ccardedt = fields.Char()
    inv_deposit = fields.Integer()
    inv_period = fields.Float()
    inv_status = fields.Char()
    user_id = fields.Integer()
    user_lmd = fields.Char()
    inv_headdisc = fields.Integer()
    inv_headdiscper = fields.Integer()
    inv_cashamt = fields.Integer()
    inv_creditamt = fields.Integer()
    inv_ccardamt = fields.Integer()
    inv_deladd = fields.Char()
    user_lmt = fields.Char()
    inv_manualinvno = fields.Char()
    inv_print = fields.Char()
    inv_total = fields.Char()
    inv_discuserid = fields.Char()
    inv_manualdoc = fields.Char()
    inv_franchise = fields.Char()
    inv_pickinglist = fields.Char()
    inv_ccmachine = fields.Char()
    inv_bankcode = fields.Char()
    inv_vatupdstatus = fields.Integer()
    inv_cstvatreg = fields.Char()
    inv_reqapprove = fields.Char()
    inv_crtuserid = fields.Char()
    inv_crtuserlmd = fields.Char()
    inv_crtuserlmt = fields.Char()
    inv_apruserid = fields.Char()
    inv_apruserlmd = fields.Char()
    inv_apruserlmt = fields.Char()
    inv_aprcrlmtuserid = fields.Char()
    inv_aprcrlmtuserlmd = fields.Char()
    inv_aprcrlmtuserlmt = fields.Char()
    inv_onlineorderref = fields.Char()
    inv_onlineprofileid = fields.Char()
    inv_smmodule = fields.Char()
    inv_reqautocrnote = fields.Char()
    inv_cstidtype = fields.Char()
    inv_streetname = fields.Char()
    inv_buildno = fields.Char()
    inv_addno = fields.Char()
    inv_pobox = fields.Char()
    inv_district = fields.Char()
    inv_region = fields.Char()
    inv_nearby = fields.Char()
    inv_city = fields.Char()
    inv_countrycode = fields.Integer()
    inv_countryname = fields.Char()
    inv_vatgroup = fields.Char()
    inv_uuid = fields.Char()
    inv_cstid = fields.Char()
    inv_cstmobile = fields.Char()
    inv_cstemail = fields.Char()
    inv_add2 = fields.Char()
    inv_idno = fields.Char()
    mode_of_payment = fields.Char()
    mode_of_payment_balance_amount = fields.Char()
    contract_id = fields.Integer()
    inspection_charges_amount = fields.Integer()
    balance_paid = fields.Integer()
    final_balance_amount =  fields.Integer()
    inv_detrowscount = fields.Integer()


    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
               WITH seq_data AS (
                SELECT
                    ir_sequence_date_range.work_center_id,
                    ir_sequence_date_range.location_code,
                    ir_sequence_date_range.number_next
                FROM ir_sequence_date_range
                JOIN ir_sequence ON ir_sequence.id = ir_sequence_date_range.sequence_id
                WHERE ir_sequence.name = 'Job Card'
                  AND ir_sequence_date_range.date_from <= (date_trunc('month', CURRENT_DATE) + INTERVAL '1 month - 1 day')
                  AND ir_sequence_date_range.date_to >= date_trunc('month', CURRENT_DATE)
            ),
            pl_count AS (
                            SELECT 
                                project_task_id,
                                COUNT(*) AS det_count
                            FROM product_lines
                            GROUP BY project_task_id
                        )
            SELECT
                pt.id,
                invwh.inv_whouse,
                COALESCE(seq_data.location_code, '') AS location_code,
                COALESCE(seq_data.number_next, 0) AS number_next,
                COALESCE(pl_count.det_count, 0) AS inv_detrowscount,
                pt.work_center_id AS work_center_id,
                COALESCE(seq_data.location_code, '') ||
                COALESCE(sw.code, '') ||
                TO_CHAR(NOW(), 'YY') ||
                TO_CHAR(NOW(), 'MM') ||
                LPAD(COALESCE(seq_data.number_next::text, ''), 2, '0') AS inv_no,
                TO_CHAR(current_timestamp::date, 'YYYYMMDD')::int AS inv_date,
                '' AS inv_batch,
                (SELECT ru.user_code FROM res_users ru WHERE ru.id = pt.closed_jobcard_user_id LIMIT 1) AS inv_sman,
                CASE WHEN (pt.parts_grand_total_amount + pt.service_grand_total_amount) = 0 THEN '004' ELSE '009' END AS inv_xface,
                (
                    SELECT sw2.cst_no
                    FROM stock_warehouse sw2
                    JOIN project_task pt2 ON pt2.warehouse_id = sw2.id
                    WHERE pt2.job_card_state = 'Closed'
                      AND pt2.id = pt.id
                    LIMIT 1
                ) AS inv_cstno,
                pt.customer_name AS inv_cstname,
                jsonb_build_object(
                    'inv_cstadd',
                    to_jsonb(
                        COALESCE(pt.address_one, '') || ' ' ||
                        COALESCE(pt.phone, '') || ' ' ||
                        COALESCE((SELECT name::json ->> 'en_US' FROM res_city WHERE id = pt.customer_city_id), '')
                    )
                ) AS inv_cstadd,
                pt.name AS inv_cstref,
                '' AS inv_comm,
                2 AS inv_mop,
                '' AS inv_ccard,
                '' AS inv_ccardno,
                '' AS inv_ccardedt,
                0 AS inv_deposit,
                EXTRACT(MONTH FROM current_date) AS inv_period,
                'N' AS inv_status,
                999 AS user_id,
                TO_CHAR(current_date, 'yyyymmdd') AS user_lmd,
                0 AS inv_headdisc,
                0 AS inv_headdiscper,
                0 AS inv_cashamt,
                0 AS inv_creditamt,
                0 AS inv_ccardamt,
                '' AS inv_deladd,
                TO_CHAR(current_timestamp AT TIME ZONE 'Asia/Riyadh', 'HH24:MI') AS user_lmt,
                pt.name AS inv_manualinvno,
                'N' AS inv_print,
                (pt.parts_grand_total_amount + pt.service_grand_total_amount)::text AS inv_total,
                '' AS inv_discuserid,
                'N' AS inv_manualdoc,
                '' AS inv_franchise,
                '' AS inv_pickinglist,
                '' AS inv_ccmachine,
                '' AS inv_bankcode,
                0 AS inv_vatupdstatus,
                CASE 
                    WHEN pt.customer_identification_scheme = 'TIN' THEN pt.customer_identification_number
                    WHEN pt.customer_identification_scheme IN ('CRN', 'NAT', 'IQA') THEN rp.additional_identification_number
                END AS inv_cstvatreg,
                '' AS inv_reqapprove,
                '' AS inv_crtuserid,
                '' AS inv_crtuserlmd,
                '' AS inv_crtuserlmt,
                '' AS inv_apruserid,
                '' AS inv_apruserlmd,
                '' AS inv_apruserlmt,
                '' AS inv_aprcrlmtuserid,
                '' AS inv_aprcrlmtuserlmd,
                '' AS inv_aprcrlmtuserlmt,
                '' AS inv_onlineorderref,
                rp.ref AS inv_onlineprofileid,
                'Y' AS inv_smmodule,
                'N' AS inv_reqautocrnote,
                pt.customer_identification_scheme AS inv_cstidtype,
                pt.address_one AS inv_streetname,
                pt.building_number AS inv_buildno,
                pt.plot_identification AS inv_addno,
                pt.zip_code AS inv_pobox,
                (SELECT name FROM res_state_district WHERE id = pt.country_district_id) AS inv_district,
                (select work_center_group.name from work_center_group where  work_center_group_id=work_center_group.id) AS inv_region,
                '' AS inv_nearby,
                (SELECT name::json ->> 'en_US' FROM res_city WHERE id = pt.customer_city_id) AS inv_city,
                (SELECT code FROM res_country WHERE id = pt.country_id) AS inv_countrycode,
                (SELECT name::json ->> 'en_US' FROM res_country WHERE id = pt.country_id) AS inv_countryname,
                CASE 
                    WHEN pt.customer_identification_scheme = 'TIN' THEN pt.customer_identification_number
                    ELSE ''
                END AS inv_vatgroup,
                '' AS inv_uuid,
                CASE 
                    WHEN pt.customer_identification_scheme = 'TIN' THEN pt.customer_identification_number
                    ELSE ''
                END AS inv_cstid,
                pt.phone AS inv_cstmobile,
                rp.email AS inv_cstemail,
                rp.street2 AS inv_add2,
                CASE 
                    WHEN pt.customer_identification_scheme = 'TIN' THEN pt.customer_identification_number
                    ELSE ''
                END AS inv_idno
                ,pt.mode_of_payment
				,pt.mode_of_payment_balance_amount
				,0 as contract_id
                ,pt.inspection_charges_amount
                ,pt.balance_paid
                ,pt.final_balance_amount
            FROM project_task pt
            LEFT JOIN seq_data ON seq_data.work_center_id = pt.work_center_id
            LEFT JOIN stock_warehouse sw ON sw.id = pt.warehouse_id
            LEFT JOIN pl_count ON pl_count.project_task_id = pt.id
            LEFT JOIN res_partner rp ON rp.id = pt.partner_id
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
            WHERE  ((pt.job_card_state = 'Closed' AND pt.closed_datetime IS NOT NULL)
                    OR (pt.job_card_state = 'Cancelled' AND pt.inspection_charges_amount > 0)) AND pt.export_bool = false
            );
        """)
