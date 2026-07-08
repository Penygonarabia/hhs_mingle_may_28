from odoo import models, fields, tools

class LoyaltyPromotionParticipation(models.Model):
    _name = 'loyalty.promotion.participation'
    _description = 'Promotion Participation'
    _auto = False

    promotion_reference = fields.Char(string='Promotion #', readonly=True)
    promotion_name = fields.Char(string='Promotion Name', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    tier_id = fields.Many2one('customer.tier', string='Tier', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    no_of_active_customers = fields.Integer(string='No of active Customer', readonly=True)
    utilized_customers = fields.Integer(string='Utilized Customers', readonly=True)
    utilized_transactions = fields.Integer(string='Utilized Transactions', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER ()::integer AS id,
                    sub.promotion_reference,
                    sub.promotion_name,
                    sub.partner_id,
                    sub.tier_id,
                    sub.date,
                    sub.no_of_active_customers,
                    sub.utilized_customers,
                    sub.utilized_transactions
                FROM (
                    -- 1. Active/eligible customer lines
                    SELECT
                        p.promotion_reference,
                        p.promotion_name,
                        rp.id AS partner_id,
                        rp.customer_tier_id AS tier_id,
                        NULL::date AS date,
                        1::integer AS no_of_active_customers,
                        0::integer AS utilized_customers,
                        0::integer AS utilized_transactions
                    FROM lp_setup_promotions p
                    CROSS JOIN res_partner rp
                    WHERE rp.activate_loyalty_feature = true
                      AND (
                          p.select_all_customers = true
                          OR EXISTS (
                              SELECT 1 FROM lp_setup_promotions_tiers t
                              WHERE t.promotion_id = p.id AND t.tier_id = rp.customer_tier_id
                          )
                          OR EXISTS (
                              SELECT 1 FROM lp_setup_promotions_customers c
                              WHERE c.promotion_id = p.id AND c.customer_id = rp.id
                          )
                      )
                    
                    UNION ALL
                    
                    -- 2. Utilized customer lines
                    SELECT
                        p.promotion_reference,
                        p.promotion_name,
                        rp.id AS partner_id,
                        rp.customer_tier_id AS tier_id,
                        TO_DATE(th.trnh_date, 'YYYYMMDD') AS date,
                        0::integer AS no_of_active_customers,
                        1::integer AS utilized_customers,
                        COUNT(DISTINCT th.trnh_no)::integer AS utilized_transactions
                    FROM lp_setup_promotions p
                    JOIN transaction_details td ON td.trnd_promoref = p.promotion_reference
                    JOIN transaction_header th ON th.trnh_no = td.trnd_no AND th.trnh_whouse = td.trnd_whouse
                    JOIN res_partner rp ON rp.ref = th.trnh_cstno
                    GROUP BY p.promotion_reference, p.promotion_name, rp.id, rp.customer_tier_id, th.trnh_date
                ) sub
            )
        """ % self._table)


class LoyaltySalesmanPromotionParticipation(models.Model):
    _name = 'loyalty.salesman.promotion.participation'
    _description = 'Salesman Wise Promotion Participation'
    _auto = False

    promotion_reference = fields.Char(string='Promotion #', readonly=True)
    promotion_name = fields.Char(string='Promotion Name', readonly=True)
    salesman_code = fields.Char(string='Salesman Code', readonly=True)
    salesman_name = fields.Char(string='Salesman Name', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    tier_id = fields.Many2one('customer.tier', string='Tier', readonly=True)
    region_id = fields.Many2one('res.country.state', string='Region', readonly=True)
    city = fields.Char(string='City', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    no_of_active_customers = fields.Integer(string='No of active Customer', readonly=True)
    utilized_customers = fields.Integer(string='Utilized Customers', readonly=True)
    utilized_transactions = fields.Integer(string='Utilized Transactions', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER ()::integer AS id,
                    sub.promotion_reference,
                    sub.promotion_name,
                    sub.salesman_code,
                    sub.salesman_name,
                    sub.partner_id,
                    sub.tier_id,
                    sub.region_id,
                    sub.city,
                    sub.date,
                    sub.no_of_active_customers,
                    sub.utilized_customers,
                    sub.utilized_transactions
                FROM (
                    -- 1. Active/eligible customer lines
                    SELECT
                        p.promotion_reference,
                        p.promotion_name,
                        COALESCE(rp.salesman_code, '') AS salesman_code,
                        CASE
                            WHEN COALESCE(rp.salesman_code, '') = '' THEN 'No Salesman'
                            ELSE COALESCE(sm.sm_name, rp.salesman_name, rp.salesman_code)
                        END AS salesman_name,
                        rp.id AS partner_id,
                        rp.customer_tier_id AS tier_id,
                        rp.state_id AS region_id,
                        rp.city AS city,
                        NULL::date AS date,
                        1::integer AS no_of_active_customers,
                        0::integer AS utilized_customers,
                        0::integer AS utilized_transactions
                    FROM lp_setup_promotions p
                    CROSS JOIN res_partner rp
                    LEFT JOIN sl_salesman sm ON sm.sm_code = rp.salesman_code
                    WHERE rp.activate_loyalty_feature = true
                      AND (
                          p.select_all_customers = true
                          OR EXISTS (
                              SELECT 1 FROM lp_setup_promotions_tiers t
                              WHERE t.promotion_id = p.id AND t.tier_id = rp.customer_tier_id
                          )
                          OR EXISTS (
                              SELECT 1 FROM lp_setup_promotions_customers c
                              WHERE c.promotion_id = p.id AND c.customer_id = rp.id
                          )
                      )
                    
                    UNION ALL
                    
                    -- 2. Utilized customer lines
                    SELECT
                        p.promotion_reference,
                        p.promotion_name,
                        COALESCE(th.trnh_sman, '') AS salesman_code,
                        CASE
                            WHEN COALESCE(th.trnh_sman, '') = '' THEN 'No Salesman'
                            ELSE COALESCE(sm.sm_name, rp_sman.salesman_name, th.trnh_sman)
                        END AS salesman_name,
                        rp.id AS partner_id,
                        rp.customer_tier_id AS tier_id,
                        rp.state_id AS region_id,
                        rp.city AS city,
                        TO_DATE(th.trnh_date, 'YYYYMMDD') AS date,
                        0::integer AS no_of_active_customers,
                        1::integer AS utilized_customers,
                        COUNT(DISTINCT th.trnh_no)::integer AS utilized_transactions
                    FROM lp_setup_promotions p
                    JOIN transaction_details td ON td.trnd_promoref = p.promotion_reference
                    JOIN transaction_header th ON th.trnh_no = td.trnd_no AND th.trnh_whouse = td.trnd_whouse
                    JOIN res_partner rp ON rp.ref = th.trnh_cstno
                    LEFT JOIN sl_salesman sm ON sm.sm_code = th.trnh_sman
                    LEFT JOIN (
                        SELECT DISTINCT salesman_code, salesman_name
                        FROM res_partner
                        WHERE salesman_code IS NOT NULL
                    ) rp_sman ON rp_sman.salesman_code = th.trnh_sman
                    GROUP BY p.promotion_reference, p.promotion_name, th.trnh_sman, sm.sm_name, rp_sman.salesman_name, rp.id, rp.customer_tier_id, rp.state_id, rp.city, th.trnh_date
                ) sub
            )
        """ % self._table)
