from odoo import models, fields, tools

class TransactionDetails(models.Model):
    _inherit = 'transaction.details'

    trnd_promoref = fields.Char(string='Promotion Reference')
    trnd_regularpts = fields.Float(string='Regular Points')
    trnd_bonuspts = fields.Float(string='Bonus/Promo Points')

    def init(self):
        # Let base model build view first
        super(TransactionDetails, self).init()
        
        # Check if the SQL view vi_transaction_details exists
        self._cr.execute("SELECT 1 FROM information_schema.views WHERE table_name = 'vi_transaction_details';")
        if self._cr.fetchone():
            # If the view exists but does not contain our new fields, recreate it
            self._cr.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'vi_transaction_details' AND column_name = 'trnd_promoref';
            """)
            if not self._cr.fetchone():
                tools.drop_view_if_exists(self._cr, 'vi_transaction_details')
                self._cr.execute("""
                    CREATE OR REPLACE VIEW vi_transaction_details AS (
                        SELECT
                            row_number() OVER() AS id,
                            h.id AS header_id,
                            trnd_promoref,
                            trnd_regularpts,
                            trnd_bonuspts,
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
