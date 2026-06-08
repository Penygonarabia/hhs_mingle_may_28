from odoo import models, fields, api, tools


class LoyaltyAuditView(models.Model):
    _name = 'loyalty.audit.view'
    _description = 'Loyalty Audit View'
    _auto = False
    #_log_access = False
    #_rec_name = 'customer_name'
    #_order = 'transaction_date desc'

    # Customer Information
    region_id = fields.Many2one('res.country.state', string='Region', readonly=True)
    work_center_group_id = fields.Many2one('work.center.group', string='Region', readonly=True,compute='_compute_work_center_name')
    work_center_group_name = fields.Char(string='Region', readonly=True)
    city = fields.Char(string='City', readonly=True)
    salesman_id = fields.Many2one('res.partner', string='Salesman', readonly=True)
    partner_id = fields.Many2one('res.partner', string='partner', readonly=True)
    salesman_code=fields.Char(string='Salesman Code', readonly=True)
    customer_name = fields.Char(string='Customer Name', readonly=True)
    salesman_name=fields.Char(string='Salesman Name',readonly=True)
    customer_code = fields.Char(string='Customer Code', readonly=True)
    customer_name = fields.Char(string='Customer Name', readonly=True)
    mobile = fields.Char(string='Mobile #', readonly=True)
    tier_name = fields.Char(string='Tier Name', readonly=True)

    # Transaction Information
    transaction_type = fields.Char( string='Transaction Type', readonly=True)
    warehouse = fields.Integer(string='Warehouse', readonly=True)
    transaction_no = fields.Char(string='Transaction No', readonly=True)
    transaction_date = fields.Datetime(string='Transaction Date', readonly=True)

    # Points Information
    regular_points = fields.Integer(string='Regular', readonly=True)
    bonus_points = fields.Integer(string='Bonus', readonly=True)
    total_points = fields.Integer(string='Total Points', readonly=True)
    redemption_points = fields.Integer(string='Redemption', readonly=True)
    expired_points = fields.Integer(string='Expired', readonly=True)
    net_total_points = fields.Integer(string='Total', readonly=True)

    # Adjustment Information
    reason_type = fields.Char(string='Reason Type', readonly=True)
    reason_name=fields.Char(string='Reason Name', readonly=True,compute='_compute_reason_name',store=False)
    adjustment_type = fields.Char(string='Adjustment Type', readonly=True)

    # Status Information
    status = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True)
    remarks = fields.Text(string='Remarks', readonly=True)

    # Audit Fields
    created_by = fields.Many2one('res.users', string='Created By', readonly=True)
    created_date = fields.Datetime(string='Created Date', readonly=True)
    modified_by = fields.Many2one('res.users', string='Modified By', readonly=True)
    modified_date = fields.Datetime(string='Modified Date', readonly=True)

    @api.depends('reason_type')
    def _compute_reason_name(self):
        for rec in self:
            rec.reason_name=False
            reason_type = self.env['manual.promotion.reason.types'].search([('reason_code','=',rec.reason_type)])
            for reason in reason_type:
                rec.reason_name=reason.reason_name


    @api.depends('partner_id')
    def _compute_work_center_name(self):
        for records in self:
            records.work_center_group_id = False
            print("1111111111111111111111111",'1',records.partner_id,records)
            if records.partner_id.customer_city_id:
                records.work_center_group_id = records.partner_id.customer_city_id.def_work_center_id.work_center_group_id.id or False
                print("workcenterrrrrrrrrrrrrrrrrrrrrrrrrr",records.work_center_group_id)

    # def _adjustment_type(self):
    #     for rec in self:
    #         adjustment_type_search = self.env['customer.loyalty.points.history'].search([])
    #         for adjustment in adjustment_type_search:
    #             print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",adjustment.clph_adjtype,type(adjustment.clph_adjtype))
    #             if adjustment.clph_adjtype== '+':
    #                 rec.adjustment_type='Addition'
    #             if adjustment.clph_adjtype == '-':
    #                 rec.adjustment_type='Deduction'

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    CAST(row_number() OVER () AS integer) AS id,
                    p.id AS partner_id,
                    wcg.name AS work_center_group_name,
                    p.state_id AS region_id,
                    p.city AS city,
                    u.partner_id AS salesman_id,
                    p.salesman_name AS salesman_name,
                    p.ref AS customer_code,
                    p.salesman_code AS salesman_code,
                    p.name AS customer_name,
                    p.mobile AS mobile,
                    p.tier_name AS tier_name,
            
                    CASE
                        WHEN h.clph_doctype = '99' THEN 'adjustment'
                        WHEN h.clph_doctype = '98' THEN 'redeem'
                        WHEN h.clph_doctype = '97' THEN 'expired'
                        WHEN h.clph_doctype = '01' THEN 'invoice'
                        WHEN h.clph_doctype = '02' THEN 'credit note'
                        ELSE 'regular'
                    END AS transaction_type,
            
                    CASE
                        WHEN h.clph_whouse ~ '^[0-9]+$' THEN h.clph_whouse::integer
                        ELSE NULL
                    END AS warehouse,
            
                    h.clph_docnumber AS transaction_no,
                    h.clph_datetime AS transaction_date,
            
                    -- Regular Points
                    CASE
                        WHEN h.clph_doctype = '02'
                            THEN -COALESCE(h.clph_regpoints, 0)
                        ELSE
                            COALESCE(h.clph_regpoints, 0)
                    END AS regular_points,
            
                    -- Bonus Points
                    CASE
                        WHEN h.clph_doctype = '02'
                            THEN -COALESCE(h.clph_bonuspoints, 0)
                        ELSE
                            COALESCE(h.clph_bonuspoints, 0)
                    END AS bonus_points,
            
                    -- Total Points
                    CASE
                        WHEN h.clph_doctype = '02'
                            THEN -(COALESCE(h.clph_regpoints, 0) + COALESCE(h.clph_bonuspoints, 0))
                        ELSE
                            COALESCE(h.clph_regpoints, 0) + COALESCE(h.clph_bonuspoints, 0)
                    END AS total_points,
            
                    -- Redemption
                    CASE
                        WHEN h.clph_doctype = '98'
                            THEN COALESCE(h.clph_regpoints, 0)
                        ELSE 0
                    END AS redemption_points,
            
                    -- Expired
                    CASE
                        WHEN h.clph_doctype = '97'
                            THEN COALESCE(h.clph_regpoints, 0)
                        ELSE 0
                    END AS expired_points,
            
                    -- Net Balance Impact
                    CASE
                        WHEN h.clph_doctype = '01' THEN
                            COALESCE(h.clph_regpoints, 0) +
                            COALESCE(h.clph_bonuspoints, 0)
            
                        WHEN h.clph_doctype = '02' THEN
                            -(
                                COALESCE(h.clph_regpoints, 0) +
                                COALESCE(h.clph_bonuspoints, 0)
                            )
            
                        WHEN h.clph_doctype = '98' THEN
                            -COALESCE(h.clph_regpoints, 0)
            
                        WHEN h.clph_doctype = '97' THEN
                            -COALESCE(h.clph_regpoints, 0)
            
                        WHEN h.clph_doctype = '99' THEN
                            CASE
                                WHEN h.clph_adjtype = '+'
                                    THEN COALESCE(h.clph_regpoints, 0) +
                                         COALESCE(h.clph_bonuspoints, 0)
                                ELSE
                                    -(
                                        COALESCE(h.clph_regpoints, 0) +
                                        COALESCE(h.clph_bonuspoints, 0)
                                    )
                            END
            
                        ELSE
                            COALESCE(h.clph_regpoints, 0) +
                            COALESCE(h.clph_bonuspoints, 0)
                    END AS net_total_points,
            
                    h.clph_reasoncode AS reason_type,
            
                    CASE
                        WHEN h.clph_adjtype = '+' THEN 'Addition'
                        ELSE 'Deduction'
                    END AS adjustment_type,
            
                    'approved'::varchar AS status,
            
                    h.clph_note AS remarks,
                    h.create_uid AS created_by,
                    h.create_date AS created_date,
                    h.write_uid AS modified_by,
                    h.write_date AS modified_date
            
                FROM customer_loyalty_points_history h
                LEFT JOIN res_partner p
                    ON p.id = h.clph_cstid
                LEFT JOIN res_users u
                    ON u.partner_id = p.id
                LEFT JOIN res_city ccm
                    ON ccm.id = p.customer_city_id
                LEFT JOIN work_center_location wcl
                    ON wcl.id = ccm.def_work_center_id
                LEFT JOIN work_center_group wcg
                    ON wcg.id = wcl.work_center_group_id
            
                WHERE p.activate_loyalty_feature = TRUE
            
                ORDER BY h.clph_datetime DESC
            )
        """ % self._table)
        # self.env.cr.execute("""
        #     CREATE OR REPLACE VIEW %s AS (
        #         SELECT
        #             CAST(row_number() OVER () AS integer) AS id,
        #             p.id AS partner_id,
        #             wcg.name AS work_center_group_name,
        #             p.state_id AS region_id,
        #             p.city AS city,
        #             u.partner_id AS salesman_id,
        #             p.salesman_name As salesman_name,
        #             p.ref AS customer_code,
        #             p.salesman_code As salesman_code,
        #             p.name AS customer_name,
        #             p.mobile AS mobile,
        #             p.tier_name AS tier_name,
        #             CASE
        #                 WHEN h.clph_doctype = '99' THEN 'adjustment'
        #                 WHEN h.clph_doctype = '98' THEN 'redeem'
        #                 WHEN h.clph_doctype = '97' THEN 'expired'
        #                 WHEN h.clph_doctype = '01' THEN 'invoice'
        #                 WHEN h.clph_doctype = '02' THEN 'credit note'
        #                 ELSE 'regular'
        #             END AS transaction_type,
        #             CASE
        #                 WHEN h.clph_whouse ~ '^[0-9]+$' THEN h.clph_whouse::integer
        #                 ELSE NULL
        #             END AS warehouse,
        #             h.clph_docnumber AS transaction_no,
        #             h.clph_datetime AS transaction_date,
        #             COALESCE(h.clph_regpoints, 0) AS regular_points,
        #             COALESCE(h.clph_bonuspoints, 0) AS bonus_points,
        #             COALESCE(h.clph_regpoints, 0) + COALESCE(h.clph_bonuspoints, 0) AS total_points,
        #             CASE
        #                 WHEN h.clph_doctype = '98' THEN COALESCE(h.clph_regpoints, 0)
        #                 ELSE 0
        #             END AS redemption_points,
        #             CASE
        #                 WHEN h.clph_doctype = '97' THEN COALESCE(h.clph_regpoints, 0)
        #                 ELSE 0
        #             END AS expired_points,
        #             (
        #                 COALESCE(h.clph_regpoints, 0) + COALESCE(h.clph_bonuspoints, 0) -
        #                 (CASE WHEN h.clph_doctype = '98' THEN COALESCE(h.clph_regpoints, 0) ELSE 0 END) -
        #                 (CASE WHEN h.clph_doctype = '97' THEN COALESCE(h.clph_regpoints, 0) ELSE 0 END)
        #             ) AS net_total_points,
        #             h.clph_reasoncode AS reason_type,
        #             CASE
        #                 WHEN h.clph_adjtype = '+' THEN 'Addition'
        #                 ELSE 'Deduction'
        #             END AS adjustment_type,
        #             'approved'::varchar AS status,
        #             h.clph_note AS remarks,
        #             h.create_uid AS created_by,
        #             h.create_date AS created_date,
        #             h.write_uid AS modified_by,
        #             h.write_date AS modified_date
        #         FROM customer_loyalty_points_history h
        #         LEFT JOIN res_partner p ON p.id = h.clph_cstid
        #         LEFT JOIN res_users u ON u.partner_id = p.id
        #         LEFT JOIN res_city ccm
        #             ON ccm.id = p.customer_city_id
        #         LEFT JOIN work_center_location wcl
        #             ON wcl.id = ccm.def_work_center_id
        #         LEFT JOIN work_center_group wcg
        #             ON wcg.id = wcl.work_center_group_id
        #         WHERE p.activate_loyalty_feature = True
        #         ORDER BY h.clph_datetime DESC
        #     )
        # """ % self._table)
