# models/vi_account_move.py

from odoo import models, fields, tools


class ViAccountMove(models.Model):
    _name = 'vi.account.move'
    _description = 'VI Account Move'
    _auto = False
    _rec_name = 'inv_no'


    inv_whouse = fields.Char(string='Warehouse')
    inv_no = fields.Char(string='Invoice No')
    inv_date = fields.Date(string='Invoice Date')
    inv_batch = fields.Char(string='Batch')
    inv_sman = fields.Char(string='Salesman')
    inv_xface = fields.Integer(string='XFace')
    inv_cstno = fields.Char(string='Customer No')
    inv_cstname = fields.Char(string='Customer Name')
    inv_cstadd = fields.Char(string='Customer Address')
    inv_cstref = fields.Char(string='Customer Ref')
    inv_comm = fields.Text(string='Comment')
    inv_mop = fields.Integer(string='MOP')
    inv_ccard = fields.Char(string='CCard')
    inv_ccardno = fields.Char(string='CCard No')
    inv_ccardedt = fields.Char(string='CCard EDT')
    inv_deposit = fields.Float(string='Deposit')
    inv_period = fields.Char(string='Period')
    inv_status = fields.Char(string='Status')
    user_id = fields.Integer(string='User ID')
    user_lmd = fields.Char(string='Last Modified Date')
    inv_headdisc = fields.Float(string='Head Discount')
    inv_headdiscper = fields.Float(string='Head Discount %')
    inv_cashamt = fields.Float(string='Cash Amount')
    inv_creditamt = fields.Float(string='Credit Amount')
    inv_ccardamt = fields.Float(string='Card Amount')
    inv_deladd = fields.Char(string='Delivery Address')
    user_lmt = fields.Char(string='Last Modified Time')
    inv_manualinvno = fields.Char(string='Manual Invoice No')
    inv_print = fields.Char(string='Print')
    inv_total = fields.Float(string='Total')
    inv_discuserid = fields.Char(string='Discount User')
    inv_manualdoc = fields.Char(string='Manual Doc')
    inv_franchise = fields.Char(string='Franchise')
    inv_pickinglist = fields.Char(string='Picking List')
    inv_ccmachine = fields.Char(string='CC Machine')
    inv_bankcode = fields.Char(string='Bank Code')
    inv_vatupdstatus = fields.Integer(string='VAT Update Status')
    inv_cstvatreg = fields.Char(string='VAT Reg')
    inv_reqapprove = fields.Char(string='Request Approve')
    inv_crtuserid = fields.Char(string='Create User')
    inv_crtuserlmd = fields.Char(string='Create User LMD')
    inv_crtuserlmt = fields.Char(string='Create User LMT')
    inv_apruserid = fields.Char(string='Approve User')
    inv_apruserlmd = fields.Char(string='Approve User LMD')
    inv_apruserlmt = fields.Char(string='Approve User LMT')
    inv_aprcrlmtuserid = fields.Char(string='APR CRLMT User')
    inv_aprcrlmtuserlmd = fields.Char(string='APR CRLMT User LMD')
    inv_aprcrlmtuserlmt = fields.Char(string='APR CRLMT User LMT')
    inv_onlineorderref = fields.Char(string='Online Order Ref')
    inv_onlineprofileid = fields.Char(string='Online Profile ID')
    inv_smmodule = fields.Char(string='SM Module')
    inv_reqautocrnote = fields.Char(string='Req Auto CR Note')
    inv_cstidtype = fields.Char(string='Customer ID Type')
    inv_streetname = fields.Char(string='Street')
    inv_buildno = fields.Char(string='Building No')
    inv_addno = fields.Char(string='Additional No')
    inv_pobox = fields.Char(string='PO Box')
    inv_district = fields.Char(string='District')
    inv_region = fields.Char(string='Region')
    inv_nearby = fields.Char(string='Nearby')
    inv_city = fields.Char(string='City')
    inv_countrycode = fields.Char(string='Country Code')
    inv_countryname = fields.Char(string='Country Name')
    inv_vatgroup = fields.Char(string='VAT Group')
    inv_cstid = fields.Char(string='Customer ID')
    inv_cstmobile = fields.Char(string='Mobile')
    inv_cstemail = fields.Char(string='Email')
    inv_add1 = fields.Char(string='Address 1')
    inv_add2 = fields.Char(string='Address 2')
    inv_idno = fields.Char(string='ID No')


    def init(self):
        tools.drop_view_if_exists(self._cr, 'vi_account_move')

        self._cr.execute("""
            CREATE OR REPLACE VIEW vi_account_move AS (

                 SELECT
                    am.id AS id,

                    sw.code AS inv_whouse,
                    am.name AS inv_no,
                    am.invoice_date AS inv_date,
                    NULL AS inv_batch,
                    (SELECT ru.user_code FROM res_users ru WHERE ru.id = am.write_uid LIMIT 1) AS inv_sman,
                    777 AS inv_xface,
                   am.customer_code AS inv_cstno,

                    rp.name AS inv_cstname,

                    CONCAT(
                        COALESCE(rp.street, ''),
                        ' ',
                        COALESCE(rp.mobile, ''),
                        ' ',
                        COALESCE(rp.city, '')
                    ) AS inv_cstadd,

                    am.name AS inv_cstref,

                    '' AS inv_comm,

                    2 AS inv_mop,

                    '' AS inv_ccard,
                    '' AS inv_ccardno,
                    '' AS inv_ccardedt,

                    0 AS inv_deposit,

                    TO_CHAR(am.invoice_date, 'MM') AS inv_period,

                   'N' AS inv_status,

                    am.create_uid AS user_id,

                    TO_CHAR(am.write_date, 'YYYYMMDD') AS user_lmd,

                    0 AS inv_headdisc,
                    0 AS inv_headdiscper,
                    0 AS inv_cashamt,
                    0 AS inv_creditamt,
                    0 AS inv_ccardamt,

                    '' AS inv_deladd,

                    TO_CHAR(am.write_date, 'HH24:MI') AS user_lmt,

                    am.name AS inv_manualinvno,

                    'N' AS inv_print,

                    am.grand_total_amount AS inv_total,

                    '' AS inv_discuserid,
                    'N' AS inv_manualdoc,
                    '' AS inv_franchise,
                    '' AS inv_pickinglist,
                    '' AS inv_ccmachine,
                    '' AS inv_bankcode,

                    0 AS inv_vatupdstatus,

                    rp.vat AS inv_cstvatreg,

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

                    rp.additional_identification_scheme AS inv_cstidtype,

                    rp.street AS inv_streetname,

                    rp.building_number AS inv_buildno,
                    rp.plot_identification AS inv_addno,

                    rp.zip AS inv_pobox,

                    '' AS inv_district,
                    '' AS inv_region,
                    '' AS inv_nearby,

                    rp.city AS inv_city,

                    (select code from res_country where id=rp.country_id) AS inv_countrycode,
                    (select name from res_country where id=rp.country_id) AS inv_countryname,

                    '' AS inv_vatgroup,

                     CASE 
                        WHEN rp.additional_identification_scheme = 'TIN' THEN rp.vat 
                        ELSE ''  
                    END AS inv_cstid,
					
					rp.mobile AS inv_cstmobile,
                    rp.email AS inv_cstemail,
                    rp.street2 AS inv_add1,
                    rp.street2 AS inv_add2,
					 CASE 
                        WHEN rp.additional_identification_scheme = 'TIN' THEN rp.vat 
                        ELSE ''  
                    END AS inv_idno                    

                FROM account_move am

                LEFT JOIN res_partner rp
                    ON am.partner_id = rp.id

                LEFT JOIN res_country rc
                    ON rp.country_id = rc.id

                LEFT JOIN res_users ru
                    ON am.invoice_user_id = ru.id

                LEFT JOIN res_partner rup
                    ON ru.partner_id = rup.id

                LEFT JOIN stock_warehouse sw
                    ON sw.id = am.warehouse_id

                WHERE am.move_type = 'out_invoice'
                AND am.state in ('posted')

            )
        """)