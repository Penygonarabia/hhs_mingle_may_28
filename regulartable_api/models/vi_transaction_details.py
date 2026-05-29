from odoo import models, fields, tools

class TransactionDetails(models.Model):
    _name = 'transaction.details'
    _description = 'Transaction Details'

    trnd_type = fields.Char()
    trnd_whouse = fields.Char()
    trnd_no = fields.Char()
    trnd_slno = fields.Float()
    trnd_subslno = fields.Float()
    trnd_orcpno = fields.Char()
    trnd_pno = fields.Char()
    trnd_pact = fields.Char()
    trnd_nonstock = fields.Char()
    trnd_desc = fields.Char()
    trnd_group = fields.Char()
    trnd_stock = fields.Char()
    trnd_part = fields.Char()
    trnd_det1 = fields.Char()
    trnd_det2 = fields.Char()
    trnd_qtyreq = fields.Float()
    trnd_qtyiss = fields.Float()
    trnd_cost = fields.Float()
    trnd_price = fields.Float()
    trnd_disc = fields.Float()
    trnd_pdisc = fields.Float()
    trnd_vatcode = fields.Char()
    trnd_vat = fields.Float()
    trnd_ret = fields.Float()
    trnd_pidref = fields.Char()
    trnd_xface = fields.Char()
    trnd_fleetsale = fields.Char()
    trnd_trnslno = fields.Float()
    trnd_trnsubslno = fields.Float()
    trnd_subtrntype = fields.Char()
    trnd_subtrnref = fields.Char()
    trnd_cstorflag = fields.Char()
    trnd_sourcewh = fields.Char()
    trnd_discp = fields.Float()
    trnd_reqgroup = fields.Char()
    trnd_reqstock = fields.Char()
    trnd_reqpart = fields.Char()
    trnd_reqdesc = fields.Char()
    trnd_orgreqqty = fields.Float()
    trnd_cstpriceflg = fields.Char()
    trnd_isswhouse = fields.Char()
    trnd_export = fields.Char()
    trnd_wqty = fields.Float()
    trnd_dsiamt = fields.Float()
    trnd_salcat = fields.Char()
    trnd_vatexpt = fields.Char()
    trnd_promodisc = fields.Float()
    trnd_promomsg1 = fields.Char()
    trnd_promomsg2 = fields.Char()
    trnd_promomsg3 = fields.Char()
    trnd_campaign = fields.Float()
    trnd_campaignref = fields.Char()
    trnd_autocrnote = fields.Char()
    trnd_autocrnoteval = fields.Float()
    trnd_autocrnotestatus = fields.Char()
    trnd_lpoint = fields.Float()
    trnd_vatepttype = fields.Char()
    trnd_vateptcomm = fields.Char()
    trnd_cstspldisc = fields.Float()
    trnd_cashckproamt = fields.Float()
    trnd_cashbkproqty = fields.Float()
    trnd_cashbkprocstgroup = fields.Char()
    trnd_cashbkproref = fields.Char()
    trnd_cashbkproamt = fields.Float()
    trnd_lpunit = fields.Float()
    trnd_entrytime = fields.Datetime()
    trnd_line = fields.Char()
    trnd_nonstoc = fields.Char()
    trnd_nonstocksalacc = fields.Char()
    trnd_nonstockcashacc = fields.Char()
    trnd_nonstocksledgeracc = fields.Char()
    trnd_qtyres = fields.Float()
    trnd_cancelled = fields.Integer()
    trnd_dqty = fields.Float()
    trnd_onlineref = fields.Char()
    trnd_onlineprofileid = fields.Char()
    trnd_onlineorderpart = fields.Char()
    header_id = fields.Many2one(
        'transaction.header',
        string='Transaction Header',
        readonly=True
    )

    def init(self):
        tools.drop_view_if_exists(self._cr, 'vi_transaction_details')

        self._cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'transaction_details'")
        if not self._cr.fetchone():
            return

        self._cr.execute("""
            CREATE OR REPLACE VIEW vi_transaction_details AS (
                SELECT
                    row_number() OVER() AS id,
                    h.id AS header_id,
                    trnd_type,
                    trnd_whouse,
                    trnd_no,
                    trnd_slno,
                    trnd_subslno,
                    trnd_orcpno,
                    trnd_pno,
                    trnd_pact,
                    trnd_nonstock,
                    trnd_desc,
                    trnd_group,
                    trnd_stock,
                    trnd_part,
                    trnd_det1,
                    trnd_det2,
                    trnd_qtyreq,
                    trnd_qtyiss,
                    trnd_cost,
                    trnd_price,
                    trnd_disc,
                    trnd_pdisc,
                    trnd_vatcode,
                    trnd_vat,
                    trnd_ret,
                    trnd_pidref,
                    trnd_xface,
                    trnd_fleetsale,
                    trnd_trnslno,
                    trnd_trnsubslno,
                    trnd_subtrntype,
                    trnd_subtrnref,
                    trnd_cstorflag,
                    trnd_sourcewh,
                    trnd_discp,
                    trnd_reqgroup,
                    trnd_reqstock,
                    trnd_reqpart,
                    trnd_reqdesc,
                    trnd_orgreqqty,
                    trnd_cstpriceflg,
                    trnd_isswhouse,
                    trnd_export,
                    trnd_wqty,
                    trnd_dsiamt,
                    trnd_salcat,
                    trnd_vatexpt,
                    trnd_promodisc,
                    trnd_promomsg1,
                    trnd_promomsg2,
                    trnd_promomsg3,
                    trnd_campaign,
                    trnd_campaignref,
                    trnd_autocrnote,
                    trnd_autocrnoteval,
                    trnd_autocrnotestatus,
                    trnd_lpoint,
                    trnd_vatepttype,
                    trnd_vateptcomm,
                    trnd_cstspldisc,
                    trnd_cashckproamt,
                    trnd_cashbkproqty,
                    trnd_cashbkprocstgroup,
                    trnd_cashbkproref,
                    trnd_cashbkproamt,
                    trnd_lpunit,
                    trnd_entrytime,
                    trnd_line,
                    trnd_nonstoc,
                    trnd_nonstocksalacc,
                    trnd_nonstockcashacc,
                    trnd_nonstocksledgeracc,
                    trnd_qtyres,
                    trnd_cancelled,
                    trnd_dqty,
                    trnd_onlineref,
                    trnd_onlineprofileid,
                    trnd_onlineorderpart
                FROM transaction_details d
            LEFT JOIN vi_transaction_header h
                ON h.trnh_whouse = d.trnd_whouse
                AND h.trnh_no = d.trnd_no 
            )
        """)