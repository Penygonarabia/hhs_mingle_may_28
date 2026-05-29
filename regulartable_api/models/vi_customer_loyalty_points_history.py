from odoo import models, fields, tools


class CustomerLoyaltyPointsHistory(models.Model):
    _name = 'vi.customer.loyalty.points.history'
    _description = 'Customer Loyalty Points History'
    _auto = False  # PostgreSQL View

    id = fields.Integer(string='ID')
    clph_cstid = fields.Integer(string='Customer ID')
    clph_cstcode = fields.Char(string='Customer Code')
    clph_date = fields.Date(string='Date')
    clph_doctype = fields.Char(string='Document Type')
    clph_docnumber = fields.Char(string='Document Number')
    clph_type = fields.Char(string='Type')
    clph_whouse = fields.Char(string='Warehouse')
    clph_regpoints = fields.Float(string='Regular Points')
    clph_bonuspoints = fields.Float(string='Bonus Points')
    clph_totalpoints = fields.Float(string='Total Points')
    clph_note = fields.Text(string='Note')
    clph_uid = fields.Char(string='User ID')
    clph_datetime = fields.Datetime(string='Date Time')
    clph_adjtype = fields.Char(string='Adjustment Type')
    clph_reasoncode = fields.Char(string='Reason Code')
    clph_promoref = fields.Char(string='Promo Reference')
    clph_lmd = fields.Datetime(string='Last Modified')
    clph_export = fields.Char(string='Export')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    clph_cstid,
                    clph_cstcode,
                    clph_date,
                    clph_doctype,
                    clph_docnumber,
                    clph_type,
                    clph_whouse,
                    clph_regpoints,
                    clph_bonuspoints,
                    clph_totalpoints,
                    clph_note,
                    clph_uid,
                    clph_datetime,
                    clph_adjtype,
                    clph_reasoncode,
                    clph_promoref,
                    clph_lmd,
                    clph_export
                FROM customer_loyalty_points_history where clph_export='N'
            )
        """)