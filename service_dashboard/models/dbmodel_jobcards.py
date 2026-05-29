from odoo import api, models, fields, tools

class dbmodel_jobcards(models.Model):
    _name = 'dbmodel.jobcards'
    _description = 'dbm Job Cards'
    _auto = False

    user_id = fields.Many2one('res.users', string='User', readonly=True)
    default_work_location = fields.Many2one('work.center.location', string='Default Work Location', readonly=True)
    name = fields.Char(string='Name', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    service_warranty_id = fields.Many2one('service.warranty', string='Service Warranty', readonly=True)
    work_center_group_id = fields.Many2one('work.center.group', string='Work Center Group', readonly=True)
    work_center_id = fields.Many2one('work.center.location', string='Work Center', readonly=True)
    grand_total_amount = fields.Float(string='Grand Total Amount', readonly=True)
    service_grand_total_amount = fields.Float(string='Service Grand Total Amount', readonly=True)
    parts_grand_total_amount = fields.Float(string='Parts Grand Total Amount', readonly=True)
    rtat_hours = fields.Float(string='RTAT Hours', readonly=True)
    service_created_datetime = fields.Datetime(string='Service Created Datetime', readonly=True)
    job_card_state = fields.Char(string='Job Card State', readonly=True)
    active = fields.Boolean(string='Active', readonly=True)

    @api.model
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY pt.id, ru.id)::int AS id,
                    ru.id AS user_id,

                    ruwcll.work_center_location_id AS default_work_location,
                    pt.name AS name,
                    pt.company_id AS company_id,

                    pt.service_warranty_id AS service_warranty_id,
                    pt.work_center_group_id AS work_center_group_id,
                    pt.work_center_id AS work_center_id,

                    pt.grand_total AS grand_total_amount,
                    pt.service_grand_total_amount AS service_grand_total_amount,
                    pt.parts_grand_total_amount AS parts_grand_total_amount,

                    pt.rtat_hours AS rtat_hours,
                    pt.service_created_datetime AS service_created_datetime,
                    pt.job_card_state AS job_card_state,

                    pt.active AS active
                FROM
                    res_users ru

                    LEFT JOIN res_users_work_center_location_rel ruwcll 
                        ON ruwcll.res_users_id = ru.id
                    LEFT JOIN project_task pt 

                        ON pt.work_center_id = ruwcll.work_center_location_id
                WHERE 
                    pt.active = true

                ORDER BY
                    user_id
            )

        """ % self._table)
