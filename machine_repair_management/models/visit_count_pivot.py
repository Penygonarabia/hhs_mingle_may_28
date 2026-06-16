from odoo import models, fields, tools, api


class VisitCountReport(models.Model):
    _name = 'visit.count.report'
    _description = 'Visit Count Report'
    _auto = False

    contract_id = fields.Many2one(
        'subscription.contracts',
        string='Contract'
    )
    sales_person_user_id = fields.Many2one('res.users', string  = "SalesPerson")

    project_id = fields.Many2one(
        'project.project',
        string='Project'
    )
    # city=fields.Char(string='City')
    city=fields.Many2one('res.city',string='City')

    #customer_city_id = fields.Many2one('res.city', string='City')
    #citys=fields.Char(string='City')

    work_center_group_id = fields.Many2one(
        'work.center.group',
        string='Region',
        # compute='_compute_work_center_name'
    )
    # region=fields.Char(string='Region')



    partner_id = fields.Many2one(
        'res.partner',
        string='Customer'
    )

    entitlement_prevent = fields.Integer(string='Estimated Preventive Total')
    actual_prevent_count = fields.Integer(string='Preventive Actual')
    balance_prevent = fields.Integer(string='Preventive Balance')

    entitlement_correct = fields.Integer(string='Estimated Corrective Total')
    actual_correct_count = fields.Integer(string='Corrective Actual')
    balance_correct = fields.Integer(string='Corrective Balance')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW visit_count_report AS (
                SELECT
                    sc.id AS id,
                    sc.id AS contract_id,
                    sc.project_id,
                    COALESCE(sc.work_center_group_id, wcg.id) AS work_center_group_id,
                    sc.partner_id,
                    COALESCE(rp.user_id, cp.user_id) AS sales_person_user_id,
                
                    COALESCE(rp.customer_city_id, cp.customer_city_id) AS city,
                    
                  
                
                    COALESCE(sc.entitlement_prevent, 0) AS entitlement_prevent,
                    COALESCE(sc.actual_prevent_count, 0) AS actual_prevent_count,
                    COALESCE(sc.balance_prevent, 0) AS balance_prevent,
                
                    COALESCE(sc.entitlement_correct, 0) AS entitlement_correct,
                    COALESCE(sc.actual_correct_count, 0) AS actual_correct_count,
                    COALESCE(sc.balance_correct, 0) AS balance_correct
                
                FROM subscription_contracts sc
                LEFT JOIN res_partner rp
                    ON rp.id = sc.partner_id
                LEFT JOIN res_partner cp
                    ON cp.id = rp.commercial_partner_id
                LEFT JOIN res_city ccm
                    ON ccm.id = COALESCE(rp.customer_city_id, cp.customer_city_id)
                LEFT JOIN work_center_location wcl
                    ON wcl.id = ccm.def_work_center_id
                LEFT JOIN work_center_group wcg
                    ON wcg.id = wcl.work_center_group_id
            )
        """)

        # self.env.cr.execute("""
        #     CREATE OR REPLACE VIEW visit_count_report AS (
        #         SELECT
        #             sc.id AS id,
        #             sc.id AS contract_id,
        #             sc.project_id,
        #             COALESCE(sc.work_center_group_id, wcg.id) AS work_center_group_id,
        #             sc.partner_id,
        #             COALESCE(sc.sales_person_user_id, rp.user_id) AS sales_person_user_id,
        #             ccm.name AS city,
        #             COALESCE(sc.region, wcg.name) AS region,
        #
        #             COALESCE(sc.entitlement_prevent, 0) AS entitlement_prevent,
        #             COALESCE(sc.actual_prevent_count, 0) AS actual_prevent_count,
        #             COALESCE(sc.balance_prevent, 0) AS balance_prevent,
        #
        #             COALESCE(sc.entitlement_correct, 0) AS entitlement_correct,
        #             COALESCE(sc.actual_correct_count, 0) AS actual_correct_count,
        #             COALESCE(sc.balance_correct, 0) AS balance_correct
        #
        #         FROM subscription_contracts sc
        #         LEFT JOIN res_partner rp
        #          ON rp.id = sc.partner_id
        #         LEFT JOIN res_partner cp
        #          ON cp.id = rp.commercial_partner_id
        #         LEFT JOIN res_city ccm
        #             ON ccm.id = COALESCE(sc.city, rp.customer_city_id, cp.customer_city_id)
        #         LEFT JOIN work_center_location wcl
        #             ON wcl.id = ccm.def_work_center_id
        #         LEFT JOIN work_center_group wcg
        #             ON wcg.id = wcl.work_center_group_id
        #     )
        # """)
