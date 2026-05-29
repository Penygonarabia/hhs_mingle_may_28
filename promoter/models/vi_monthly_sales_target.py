from odoo import models, fields, tools, api
from odoo.exceptions import ValidationError,AccessError

class ViMonthlySalesTarget(models.Model):
    _name = 'vi.monthly.sales.target'
    _description = 'Monthly Sales Target Comparison'
    _auto = False

    id = fields.Integer(string='ID', readonly=True)
    franchise_id = fields.Many2one('product.category', string='Franchise', readonly=True)
    product_category_name = fields.Char(string='Category Name', readonly=True)
    group_name = fields.Char(string='Group Name', readonly=True)
    subgroup_name = fields.Char(string='Subgroup Name', readonly=True)

    year = fields.Char(string='Year', readonly=True)
    month = fields.Integer(string='Month', readonly=True)

    sales_qty = fields.Integer(string='Sales Qty', readonly=True)
    target_qty = fields.Integer(string='Target Qty', readonly=True)
    actual_qty = fields.Integer(string='Actual Qty', readonly=True)  
    variance = fields.Float(string='Variance', readonly=True)
    variance_percent = fields.Float(string='Variance %', readonly=True)

    dealer_id = fields.Many2one('res.partner', string='Dealer', domain=[('is_dealer', '=', True)], readonly=True)
    showroom_id = fields.Many2one('promoter.showroom', string='Showroom', readonly=True)
    promoter_id = fields.Many2one('res.users', string='Promoter', readonly=True)

    region_name = fields.Char(string='Region', readonly=True)
    city_name = fields.Char(string='City', readonly=True)

    promoter_latitude = fields.Float(string="Promoter Latitude", readonly=True)
    promoter_longitude = fields.Float(string="Promoter Longitude", readonly=True)
    showroom_latitude = fields.Float(string="Showroom Latitude", readonly=True)
    showroom_longitude = fields.Float(string="Showroom Longitude", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'vi_monthly_sales_target')
        self._cr.execute("""
            CREATE OR REPLACE VIEW vi_monthly_sales_target AS
            SELECT
                row_number() OVER() AS id,

                COALESCE(t.dealer_id, s.dealer_id) AS dealer_id,
                COALESCE(t.showroom_id, s.showroom) AS showroom_id,
                COALESCE(t.promoter_id, s.user_id) AS promoter_id,
                COALESCE(t.franchise_id, s.product_category_id) AS franchise_id,

                pc.name AS product_category_name,
                g.name  AS group_name,
                sg.name AS subgroup_name,

                COALESCE(r.name::text, t.region::text) AS region_name,
                COALESCE(c.name->>'en_US', t.city::text) AS city_name,

                COALESCE(t.year::int, s.year)   AS year,
                COALESCE(t.month::int, s.month) AS month,

                COALESCE(SUM(t.target_qty), 0) AS target_qty,
                COALESCE(SUM(t.actual_qty), 0) AS actual_qty,
                COALESCE(SUM(s.qty), 0) AS sales_qty,

                COALESCE(SUM(s.qty), 0) - COALESCE(SUM(t.actual_qty), 0) AS variance,

                CASE
                    WHEN COALESCE(SUM(t.actual_qty), 0) = 0 THEN 0
                    ELSE ROUND(
                        (
                            (COALESCE(SUM(s.qty), 0) - COALESCE(SUM(t.actual_qty), 0))
                            / NULLIF(SUM(t.actual_qty), 0)
                        )::numeric,
                        2
                    )
                END AS variance_percent,

                MAX(s.current_latitude)  AS promoter_latitude,
                MAX(s.current_longitude) AS promoter_longitude,
                MAX(sh.latitude)         AS showroom_latitude,
                MAX(sh.longitude)        AS showroom_longitude

            FROM sales_target t

            FULL OUTER JOIN promoter_showroom_sales s
                ON  t.dealer_id    = s.dealer_id
                AND t.showroom_id  = s.showroom
                AND t.promoter_id  = s.user_id
                AND t.group_id     = s.group_id
                AND t.subgroup_id  = s.subgroup_id
                AND t.year::int    = s.year
                AND t.month::int   = s.month
                AND t.franchise_id = s.product_category_id

            LEFT JOIN product_category pc
                ON pc.id = COALESCE(t.franchise_id, s.product_category_id)

            LEFT JOIN product_category g
                ON g.id = COALESCE(t.group_id, s.group_id)

            LEFT JOIN product_category sg
                ON sg.id = COALESCE(t.subgroup_id, s.subgroup_id)

            LEFT JOIN res_region r
                ON r.id = s.region_id

            LEFT JOIN res_city c
                ON c.id = s.city_id

            LEFT JOIN promoter_showroom sh
                ON sh.id = s.showroom

            GROUP BY
                COALESCE(t.dealer_id, s.dealer_id),
                COALESCE(t.showroom_id, s.showroom),
                COALESCE(t.promoter_id, s.user_id),
                COALESCE(t.franchise_id, s.product_category_id),

                pc.name,
                g.name,
                sg.name,

                COALESCE(r.name::text, t.region::text),
                COALESCE(c.name->>'en_US', t.city::text),

                COALESCE(t.year::int, s.year),
                COALESCE(t.month::int, s.month)
        """)
    # def init(self):
    #     tools.drop_view_if_exists(self._cr, 'vi_monthly_sales_target')
    #     self._cr.execute("""
    #         CREATE OR REPLACE VIEW vi_monthly_sales_target AS
    #         SELECT
    #             row_number() OVER() AS id,
    #             COALESCE(t.dealer_id, s.dealer_id) AS dealer_id,
    #             COALESCE(t.showroom_id, s.showroom) AS showroom_id,
    #             COALESCE(t.promoter_id, s.user_id) AS promoter_id,
    #             COALESCE(t.franchise_id, s.product_category_id) AS franchise_id,
    #             pc.name AS product_category_name,
    #             g.name  AS group_name,
    #             sg.name AS subgroup_name,
    #             COALESCE(r.name::text, t.region::text) AS region_name,
    #             COALESCE(c.name->>'en_US', t.city->>'en_US') AS city_name,
    #             COALESCE(t.year::int, s.year)   AS year,
    #             COALESCE(t.month::int, s.month) AS month,

    #             COALESCE(SUM(t.target_qty), 0) AS target_qty,
    #             COALESCE(SUM(t.actual_qty), 0) AS actual_qty, 
    #             COALESCE(SUM(s.qty), 0) AS sales_qty,

    #             COALESCE(SUM(s.qty), 0) - COALESCE(SUM(t.actual_qty), 0) AS variance,
    #             CASE
    #                 WHEN COALESCE(SUM(t.actual_qty), 0) = 0 THEN 0
    #                 ELSE ROUND(((COALESCE(SUM(s.qty), 0) - COALESCE(SUM(t.actual_qty), 0))
    #                             / NULLIF(SUM(t.actual_qty), 0))::numeric, 2)
    #             END AS variance_percent,

    #             MAX(s.current_latitude) AS promoter_latitude,
    #             MAX(s.current_longitude) AS promoter_longitude,
    #             MAX(sh.latitude) AS showroom_latitude,
    #             MAX(sh.longitude) AS showroom_longitude

    #         FROM sales_target t
    #         FULL OUTER JOIN promoter_showroom_sales s 
    #             ON  t.dealer_id   = s.dealer_id
    #             AND t.showroom_id = s.showroom
    #             AND t.promoter_id = s.user_id
    #             AND t.group_id    = s.group_id
    #             AND t.subgroup_id = s.subgroup_id
    #             AND t.year::int   = s.year
    #             AND t.month::int  = s.month
    #             AND t.franchise_id = s.product_category_id

    #         LEFT JOIN product_category pc ON pc.id = COALESCE(t.franchise_id, s.product_category_id)
    #         LEFT JOIN product_category g  ON g.id  = COALESCE(t.group_id, s.group_id)
    #         LEFT JOIN product_category sg ON sg.id = COALESCE(t.subgroup_id, s.subgroup_id)
    #         LEFT JOIN res_region r        ON r.id  = s.region_id
    #         LEFT JOIN res_city c          ON c.id  = s.city_id
    #         LEFT JOIN promoter_showroom sh ON sh.id = s.showroom

    #         GROUP BY 
    #             COALESCE(t.dealer_id, s.dealer_id),
    #             COALESCE(t.showroom_id, s.showroom),
    #             COALESCE(t.promoter_id, s.user_id),
    #             COALESCE(t.franchise_id, s.product_category_id),
    #             pc.name,
    #             g.name,
    #             sg.name,
    #             COALESCE(t.group_id, s.group_id),
    #             COALESCE(t.subgroup_id, s.subgroup_id),
    #             COALESCE(r.name, t.region::text),
    #             COALESCE(c.name->>'en_US', t.city->>'en_US'),
    #             COALESCE(t.year::int, s.year),
    #             COALESCE(t.month::int, s.month)
    #         ORDER BY year, month;
    #     """)

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        user = self.env.user

        # Check if user has BOTH backoffice AND readonly groups
        has_both_groups = (
                user.has_group('promoter.group_promoter_backoffice_user') and
                user.has_group('promoter.group_promoter_sales_readonly')
        )

        # If user has both groups, restrict write operations
        if has_both_groups and operation in ['write', 'create', 'unlink']:
            if raise_exception:
                raise AccessError(_("You have read-only access to sales records."))
            return False

        return super().check_access_rights(operation, raise_exception)