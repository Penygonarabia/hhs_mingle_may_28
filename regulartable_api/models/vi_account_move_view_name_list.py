from odoo import models, fields, tools


class ViAccountMoveNameList(models.Model):
    _name = 'vi.account.move.namelist'
    _description = 'Account Move Name List'
    _auto = False
    _rec_name = 'inv_manualinvno'

    id = fields.Integer(string='ID', readonly=True)
    inv_whouse = fields.Char(string='Warehouse', readonly=True)
    inv_manualinvno = fields.Char(string='Invoice Number', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'vi_account_move_namelist')

        self._cr.execute("""
            CREATE OR REPLACE VIEW vi_account_move_namelist AS (

                SELECT
                    am.id AS id,
                    sw.code AS inv_whouse,
                    am.name AS inv_manualinvno

                FROM account_move am
                LEFT JOIN stock_warehouse sw
                    ON sw.id = am.warehouse_id

                WHERE am.state = 'posted'
                    AND am.move_type = 'out_invoice'
                    AND am.export_bool = FALSE
                    AND am.invoice_date IS NOT NULL

                    AND EXISTS (
                        SELECT 1
                        FROM account_move_line aml

                        JOIN product_product pp
                            ON pp.id = aml.product_id

                        WHERE aml.move_id = am.id

                            AND NOT (
                                aml.price_unit = 0
                                AND pp.default_code = 'INSPECTION'
                            )

                        GROUP BY aml.move_id

                        HAVING

                            MAX(
                                CASE
                                    WHEN aml.price_unit > 0
                                    THEN 1
                                    ELSE 0
                                END
                            ) = 1

                            OR

                            MAX(
                                CASE
                                    WHEN pp.default_code NOT IN (
                                        'INSPECTION',
                                        'SERVICBEKO',
                                        'SERVICE',
                                        'SERVICEASK',
                                        'SERVICECANDY'
                                    )
                                    THEN 1
                                    ELSE 0
                                END
                            ) = 1
                    )

            )
        """)