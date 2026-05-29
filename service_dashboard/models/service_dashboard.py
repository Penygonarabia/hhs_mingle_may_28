from odoo import models, fields, tools


class ServiceDashboard(models.Model):
    _name = 'service.dashboard'
    _description = 'Service Dashboard View'
    _auto = False

    name = fields.Char(string='Name', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    service_warranty_id = fields.Many2one('service.warranty', string='Service Warranty', readonly=True)
    warranty_name = fields.Char(string='Warranty Name', readonly=True)
    work_center_group_id = fields.Many2one('work.center.group', string='Work Center Group', readonly=True)
    region = fields.Char(string='Region', readonly=True)
    work_center_id = fields.Many2one('work.center.location', string='Work Center', readonly=True)
    work_location = fields.Char(string='Work Location', readonly=True)
    grand_total_amount = fields.Float(string='Grand Total Amount', readonly=True)
    service_grand_total_amount = fields.Float(string='Service Grand Total Amount', readonly=True)
    parts_grand_total_amount = fields.Float(string='Parts Grand Total Amount', readonly=True)
    warranty_spareparts_value = fields.Float(string='Warranty Spare Parts Value', readonly=True)
    rtat_hours = fields.Float(string='RTAT Hours', readonly=True)
    service_created_datetime = fields.Datetime(string='Service Created Datetime', readonly=True)
    job_card_state = fields.Char(string='Job Card State', readonly=True)
    active = fields.Boolean(string='Active', readonly=True)

    def init(self):
        # We drop the view first and then recreate it
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH aggregated_properties AS (
                    -- Get the first property value per task to avoid duplication from multiple product lines
                    SELECT DISTINCT ON (pl.project_task_id)
                        pl.project_task_id,
                        ip.value_float
                    FROM product_lines pl
                    JOIN ir_property ip ON (
                        ip.res_id = 'product.product,' || pl.product_id
                    )
                    ORDER BY pl.project_task_id, pl.id DESC
                )
                SELECT
                    pt.id AS id,
                    pt.name AS name,
                    pt.company_id AS company_id,
                    pt.service_warranty_id AS service_warranty_id,
                    sw.name AS warranty_name,
                    pt.work_center_group_id AS work_center_group_id,
                    wcg.name AS region,
                    pt.work_center_id AS work_center_id,
                    wcl.name AS work_location,
                    pt.grand_total AS grand_total_amount,
                    pt.service_grand_total_amount AS service_grand_total_amount,
                    pt.parts_grand_total_amount AS parts_grand_total_amount,
                    ap.value_float AS warranty_spareparts_value,
                    pt.rtat_hours AS rtat_hours,
                    pt.service_created_datetime AS service_created_datetime,
                    pt.job_card_state AS job_card_state,
                    pt.active AS active
                FROM
                    project_task pt
                    LEFT JOIN service_warranty sw ON sw.id = pt.service_warranty_id
                    LEFT JOIN work_center_location wcl ON wcl.id = pt.work_center_id
                    LEFT JOIN work_center_group wcg ON wcg.id = pt.work_center_group_id
                    LEFT JOIN aggregated_properties ap ON ap.project_task_id = pt.id
                WHERE pt.active = true
            )
        """ % self._table)
