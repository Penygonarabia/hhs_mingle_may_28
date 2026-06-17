from odoo import models, fields, tools, api, _
from odoo.exceptions import ValidationError,AccessError

class ViMonthlySalesTarget(models.Model):
    _name = 'vi.monthly.sales.target.dealer'
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
    showroom_id = fields.Many2one('dsales.showroom', string='Showroom', readonly=True)
    sale_dealer_id = fields.Many2one('res.users', string='Salesman', readonly=True)

    region_name = fields.Char(string='Region', readonly=True)
    city_name = fields.Char(string='City', readonly=True)

    dealer_latitude = fields.Float(string="Dealer Latitude", readonly=True)
    dealer_longitude = fields.Float(string="Dealer Longitude", readonly=True)
    showroom_latitude = fields.Float(string="Showroom Latitude", readonly=True)
    showroom_longitude = fields.Float(string="Showroom Longitude", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'vi_monthly_sales_target_dealer')
        self._cr.execute("""
            CREATE OR REPLACE VIEW vi_monthly_sales_target_dealer AS
            WITH target_data AS (
    SELECT
        dealer_id,
        dealer_showroom_id,
        sale_dealer_id,
        group_id,
        subgroup_id,
        franchise_id,
        region,
        city,
        year::int  AS year,
        month::int AS month,
        SUM(target_qty) AS target_qty,
        SUM(actual_qty) AS actual_qty
    FROM dealer_sales_target
    GROUP BY dealer_id, dealer_showroom_id, sale_dealer_id,
             group_id, subgroup_id, franchise_id,
             region, city, year, month
),

sales_data AS (
    SELECT
        dealer_id,
        dealer_showroom_id,
        user_id,
        group_id,
        subgroup_id,
        product_category_id,
        region_id,
        city_id,
        year,
        month,
        SUM(qty) AS sales_qty,
        MAX(current_latitude)  AS dealer_latitude,
        MAX(current_longitude) AS dealer_longitude
    FROM (
        -- Legacy Header Sales
        SELECT 
            dealer_id,
            dealer_showroom_id,
            user_id,
            group_id,
            subgroup_id,
            product_category_id,
            region_id,
            city_id,
            year,
            month,
            qty,
            current_latitude,
            current_longitude
        FROM dsales_showroom_sales
        WHERE qty IS NOT NULL AND qty != 0

        UNION ALL

        -- New Line Sales
        SELECT 
            h.dealer_id,
            h.dealer_showroom_id,
            h.user_id,
            l.product_group_id AS group_id,
            l.product_subgroup_id AS subgroup_id,
            l.product_category_id,
            h.region_id,
            h.city_id,
            h.year,
            h.month,
            l.qty,
            h.current_latitude,
            h.current_longitude
        FROM dsales_showroom_sales_line l
        JOIN dsales_showroom_sales h ON l.sales_id = h.id
        WHERE l.qty IS NOT NULL AND l.qty != 0 AND h.state = 'approved'
    ) combined_sales
    GROUP BY dealer_id, dealer_showroom_id, user_id,
             group_id, subgroup_id, product_category_id,
             region_id, city_id,
             year, month
)

SELECT
    row_number() OVER(
        ORDER BY COALESCE(t.year, s.year),
                 COALESCE(t.month, s.month)
    ) AS id,

    COALESCE(t.dealer_id, s.dealer_id) AS dealer_id,
    COALESCE(t.dealer_showroom_id, s.dealer_showroom_id) AS showroom_id,
    COALESCE(t.sale_dealer_id, s.user_id) AS sale_dealer_id,
    COALESCE(t.franchise_id, s.product_category_id) AS franchise_id,

    pc.name AS product_category_name,
    g.name  AS group_name,
    sg.name AS subgroup_name,

    COALESCE(r.name, t.region::text) AS region_name,
    COALESCE(c.name->>'en_US', t.city->>'en_US') AS city_name,

    COALESCE(t.year, s.year)   AS year,
    COALESCE(t.month, s.month) AS month,

    t.target_qty,
    t.actual_qty,
    s.sales_qty,

    /* Correct variance */
    COALESCE(s.sales_qty,0) - COALESCE(t.target_qty,0) AS variance,

    ROUND(
    (
        (COALESCE(s.sales_qty,0) - t.target_qty)::numeric
        / NULLIF(t.target_qty,0)
    ) * 100
, 2) AS variance_percent,

    s.dealer_latitude,
    s.dealer_longitude,
    sh.latitude  AS showroom_latitude,
    sh.longitude AS showroom_longitude

FROM target_data t
FULL OUTER JOIN sales_data s
    ON  t.dealer_id          = s.dealer_id
    AND t.dealer_showroom_id = s.dealer_showroom_id
    AND t.sale_dealer_id     = s.user_id
    AND t.group_id           = s.group_id
    AND t.subgroup_id        = s.subgroup_id
    AND t.year               = s.year
    AND t.month              = s.month
    AND t.franchise_id       = s.product_category_id

LEFT JOIN product_category pc 
    ON pc.id = COALESCE(t.franchise_id, s.product_category_id)

LEFT JOIN product_category g  
    ON g.id  = COALESCE(t.group_id, s.group_id)

LEFT JOIN product_category sg 
    ON sg.id = COALESCE(t.subgroup_id, s.subgroup_id)

LEFT JOIN res_region r        
    ON r.id  = s.region_id

LEFT JOIN res_city c          
    ON c.id  = s.city_id

LEFT JOIN dsales_showroom sh 
    ON sh.id = COALESCE(t.dealer_showroom_id, s.dealer_showroom_id)

ORDER BY year, month;
        """)

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        user = self.env.user

        # Check if user has BOTH backoffice AND readonly groups
        has_both_groups = (
                user.has_group('dealer.group_dealer_backoffice_user') and
                user.has_group('dealer.group_dealer_sales_readonly')
        )

        # If user has both groups, restrict write operations
        if has_both_groups and operation in ['write', 'create', 'unlink']:
            if raise_exception:
                raise AccessError(_("You have read-only access to sales records."))
            return False

        return super().check_access_rights(operation, raise_exception)