from odoo import models, fields, tools

class TransactionHeader(models.Model):
    _inherit = 'transaction.header'

    trnh_processed = fields.Char(
        string='Processed',
        size=1,
        default='N'
    )

    def init(self):
        # Let base model build view first
        super(TransactionHeader, self).init()
        
        # Check if the SQL view vi_transaction_header exists
        self._cr.execute("SELECT 1 FROM information_schema.views WHERE table_name = 'vi_transaction_header';")
        if self._cr.fetchone():
            # If the view exists but does not contain trnh_processed, recreate the view
            self._cr.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'vi_transaction_header' AND column_name = 'trnh_processed';
            """)
            if not self._cr.fetchone():
                tools.drop_view_if_exists(self._cr, 'vi_transaction_header')
                self._cr.execute("""
                    CREATE OR REPLACE VIEW vi_transaction_header AS (
                        SELECT
                            row_number() OVER() AS id,
                            trnh_processed,
                            trnh_type,
                            trnh_whouse,
                            trnh_no,
                            trnh_date,
                            trnh_batch,
                            trnh_sman,
                            trnh_referenceno,
                            trnh_xface,
                            trnh_cstno,
                            trnh_cstname,
                            trnh_cstadd,
                            trnh_cstref,
                            trnh_comm,
                            trnh_mop,
                            trnh_ccard,
                            trnh_ccardno,
                            trnh_ccardedt,
                            trnh_deposit,
                            trnh_period,
                            trnh_status,
                            trnh_user_id,
                            trnh_user_lmd,
                            trnh_headdisc,
                            trnh_headdiscper,
                            trnh_cashamt,
                            trnh_creditamt,
                            trnh_ccardamt,
                            trnh_deladd,
                            trnh_user_lmt,
                            trnh_manualinvno,
                            trnh_print,
                            trnh_total,
                            trnh_discuserid,
                            trnh_manualdoc,
                            trnh_franchise,
                            trnh_pickinglist,
                            trnh_ccmachine,
                            trnh_bankcode,
                            trnh_vatupdstatus,
                            trnh_cstvatreg,
                            trnh_reqapprove,
                            trnh_crtuserid,
                            trnh_crtuserlmd,
                            trnh_crtuserlmt,
                            trnh_apruserid,
                            trnh_apruserlmd,
                            trnh_apruserlmt,
                            trnh_aprcrlmtuserid,
                            trnh_aprcrlmtuserlmd,
                            trnh_aprcrlmtuserlmt,
                            trnh_onlineorderref,
                            trnh_onlineprofileid,
                            trnh_reqautocrnote,
                            trnh_autocrnoteref,
                            trnh_smmodule,
                            trnh_expdate,
                            trnh_time,
                            trnh_idno,
                            trnh_add2,
                            trnh_streetname,
                            trnh_buildno,
                            trnh_addno,
                            trnh_pobox,
                            trnh_district,
                            trnh_region,
                            trnh_nearby,
                            trnh_city,
                            trnh_countrycode,
                            trnh_vatgroup,
                            trnh_signatureid,
                            trnh_signaturetype,
                            trnh_signaturevalue,
                            trnh_certificate,
                            trnh_certificatedate,
                            trnh_certificatetime,
                            trnh_certificateno,
                            trnh_certificatebycn,
                            trnh_certificatebyo,
                            trnh_certificatebyl,
                            trnh_certificatebyst,
                            trnh_certificateslno,
                            trnh_uuid,
                            trnh_prvdocno,
                            trnh_prvxmlhas,
                            trnh_xmlhas,
                            trnh_qrcodehas,
                            trnh_prvxmlhasb64,
                            trnh_xmlhasb64,
                            trnh_xfacetype,
                            trnh_invlcsymbol,
                            trnh_invfcsymbol,
                            trnh_seleridtype,
                            trnh_selerid,
                            trnh_cstidtype,
                            trnh_cstid,
                            trnh_moptype,
                            trnh_cstmobile,
                            trnh_cstemail,
                            trnh_certificatebyc,
                            trnh_pdffilename,
                            trnh_zatcastatus,
                            trnh_entrytime,
                            trnh_recordid,
                            trnh_version,
                            trnh_mop2,
                            trnh_mop2amount,
                            trnh_postissue,
                            trnh_postissuemsg,
                            trnh_detrowscount,
                            trnh_reason,
                            trnh_onlineordertime,
                            trnh_aprcrprduserid,
                            trnh_aprcrprduserlmd,
                            trnh_aprcrprduserlmt,
                            trnh_source,
                            trnh_export,
                            trnh_arraiveddt,
                            trnh_by
                        FROM transaction_header
                    )
                """)
