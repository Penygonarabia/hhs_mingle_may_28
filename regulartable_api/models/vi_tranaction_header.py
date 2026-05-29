from odoo import models, fields, tools

class TransactionHeader(models.Model):
    _name = 'transaction.header'
    _description = 'Transaction Header'
    _rec_name = 'trnh_no'
    

    trnh_type = fields.Char()
    trnh_whouse = fields.Char()
    trnh_no = fields.Char()
    trnh_date = fields.Char()
    formatted_invoice_date = fields.Char(string='Invoice Date', compute='_compute_formatted_invoice_date')

    def _compute_formatted_invoice_date(self):
        for rec in self:
            if rec.trnh_date and len(rec.trnh_date) == 8:
                rec.formatted_invoice_date = f"{rec.trnh_date[6:8]}-{rec.trnh_date[4:6]}-{rec.trnh_date[0:4]}"
            else:
                rec.formatted_invoice_date = rec.trnh_date

    trnh_batch = fields.Char()
    trnh_sman = fields.Char()
    trnh_referenceno = fields.Char()
    trnh_xface = fields.Char()
    trnh_cstno = fields.Char()
    trnh_cstname = fields.Char()
    trnh_cstadd = fields.Char()
    trnh_cstref = fields.Char()
    trnh_comm = fields.Char()
    trnh_mop = fields.Char()
    trnh_ccard = fields.Char()
    trnh_ccardno = fields.Char()
    trnh_ccardedt = fields.Char()
    trnh_deposit = fields.Float()
    trnh_period = fields.Float()
    trnh_status = fields.Char()
    trnh_user_id = fields.Char()
    trnh_user_lmd = fields.Char()
    trnh_headdisc = fields.Float()
    trnh_headdiscper = fields.Float()
    trnh_cashamt = fields.Float()
    trnh_creditamt = fields.Float()
    trnh_ccardamt = fields.Float()
    trnh_deladd = fields.Char()
    trnh_user_lmt = fields.Char()
    trnh_manualinvno = fields.Char()
    trnh_print = fields.Char()
    trnh_total = fields.Float()
    trnh_discuserid = fields.Char()
    trnh_manualdoc = fields.Char()
    trnh_franchise = fields.Char()
    trnh_pickinglist = fields.Char()
    trnh_ccmachine = fields.Char()
    trnh_bankcode = fields.Char()
    trnh_vatupdstatus = fields.Integer()
    trnh_cstvatreg = fields.Char()
    trnh_reqapprove = fields.Char()
    trnh_crtuserid = fields.Char()
    trnh_crtuserlmd = fields.Char()
    trnh_crtuserlmt = fields.Char()
    trnh_apruserid = fields.Char()
    trnh_apruserlmd = fields.Char()
    trnh_apruserlmt = fields.Char()
    trnh_aprcrlmtuserid = fields.Char()
    trnh_aprcrlmtuserlmd = fields.Char()
    trnh_aprcrlmtuserlmt = fields.Char()
    trnh_onlineorderref = fields.Char()
    trnh_onlineprofileid = fields.Char()
    trnh_reqautocrnote = fields.Char()
    trnh_autocrnoteref = fields.Char()
    trnh_smmodule = fields.Char()
    trnh_expdate = fields.Char()
    trnh_time = fields.Char()
    trnh_idno = fields.Char()
    trnh_add2 = fields.Char()
    trnh_streetname = fields.Char()
    trnh_buildno = fields.Char()
    trnh_addno = fields.Char()
    trnh_pobox = fields.Char()
    trnh_district = fields.Char()
    trnh_region = fields.Char()
    trnh_nearby = fields.Char()
    trnh_city = fields.Char()
    trnh_countrycode = fields.Char()
    trnh_vatgroup = fields.Char()
    trnh_signatureid = fields.Char()
    trnh_signaturetype = fields.Char()
    trnh_signaturevalue = fields.Char()
    trnh_certificate = fields.Char()
    trnh_certificatedate = fields.Char()
    trnh_certificatetime = fields.Char()
    trnh_certificateno = fields.Char()
    trnh_certificatebycn = fields.Char()
    trnh_certificatebyo = fields.Char()
    trnh_certificatebyl = fields.Char()
    trnh_certificatebyst = fields.Char()
    trnh_certificateslno = fields.Char()
    trnh_uuid = fields.Char()
    trnh_prvdocno = fields.Char()
    trnh_prvxmlhas = fields.Char()
    trnh_xmlhas = fields.Char()
    trnh_qrcodehas = fields.Text()
    trnh_prvxmlhasb64 = fields.Char()
    trnh_xmlhasb64 = fields.Char()
    trnh_xfacetype = fields.Char()
    trnh_invlcsymbol = fields.Char()
    trnh_invfcsymbol = fields.Char()
    trnh_seleridtype = fields.Char()
    trnh_selerid = fields.Char()
    trnh_cstidtype = fields.Char()
    trnh_cstid = fields.Char()
    trnh_moptype = fields.Char()
    trnh_cstmobile = fields.Char()
    trnh_cstemail = fields.Char()
    trnh_certificatebyc = fields.Char()
    trnh_pdffilename = fields.Char()
    trnh_zatcastatus = fields.Char()
    trnh_entrytime = fields.Datetime()
    trnh_recordid = fields.Integer()
    trnh_version = fields.Char()
    trnh_mop2 = fields.Char()
    trnh_mop2amount = fields.Float()
    trnh_postissue = fields.Char()
    trnh_postissuemsg = fields.Char()
    trnh_detrowscount = fields.Integer()
    trnh_reason = fields.Char()
    trnh_onlineordertime = fields.Char()
    trnh_aprcrprduserid = fields.Char()
    trnh_aprcrprduserlmd = fields.Char()
    trnh_aprcrprduserlmt = fields.Char()
    trnh_source = fields.Char()
    trnh_export = fields.Char()
    trnh_arraiveddt = fields.Datetime()
    trnh_by = fields.Char()


    def init(self):
        tools.drop_view_if_exists(self._cr, 'vi_transaction_header')

        self._cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'transaction_header'")
        if not self._cr.fetchone():
            return

        self._cr.execute("""
            CREATE OR REPLACE VIEW vi_transaction_header AS (
                SELECT
                    row_number() OVER() AS id,
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