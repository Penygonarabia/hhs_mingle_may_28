# from odoo import models, fields, tools

# class DbmJobcardsDetailed(models.Model):
#     _name = 'dbm.jobcards.detailed'
#     _description = 'DBM Jobcards'
#     _auto = False
#     _rec_name = 'task_name'

#     # --- Fields ---
#     row_no = fields.Integer(string='Row No')

#     task_id = fields.Many2one('project.task', string='Task')
#     task_name = fields.Char(string='Task Reference')

#     user_id = fields.Many2one('res.users', string='User')
#     default_work_location = fields.Many2one('stock.warehouse', string='Work Location')

#     company_id = fields.Many2one('res.company', string='Company')
#     service_warranty = fields.Many2one('service.warranty', string='Warranty')

#     work_center_group_id = fields.Many2one('mrp.workcenter.group', string='Work Center Group')
#     work_center_id = fields.Many2one('mrp.workcenter', string='Work Center')

#     default_code = fields.Char(string='Product Code')
#     product_id = fields.Many2one('product.product', string='Product')

#     under_warranty_bool = fields.Boolean(string='Under Warranty')
#     service_product_price_edit_bool = fields.Boolean(string='Service Price Editable')

#     total_revenue = fields.Float(string='Total Revenue')
#     labour_revenue = fields.Float(string='Labour Revenue')
#     parts_revenue = fields.Float(string='Parts Revenue')
#     warranty_spareparts_revenue = fields.Float(string='Warranty Spare Parts Revenue')

#     rtat_hours = fields.Float(string='RTAT Hours')

#     job_card_status = fields.Char(string='Job Card Status')
#     service_created_datetime = fields.Datetime(string='Service Created On')

#     # --- SQL View ---
#     def init(self):
#         tools.drop_view_if_exists(self._cr, self._table)
#         self._cr.execute(f"""
#             CREATE OR REPLACE VIEW {self._table} AS (

#                 WITH masters AS (
#                     SELECT
#                         pt.id AS task_id,
#                         pt.name AS task_reference,
#                         ru.id AS user_id,
#                         ruwcll.work_center_location_id AS default_work_location,
#                         pt.company_id,
#                         pt.service_warranty_id,
#                         pt.work_center_group_id,
#                         pt.work_center_id,
#                         pt.job_card_state,
#                         pt.service_created_datetime,
#                         pt.rtat_hours
#                     FROM project_task pt
#                     JOIN res_users_work_center_location_rel ruwcll
#                         ON pt.work_center_id = ruwcll.work_center_location_id
#                     JOIN res_users ru
#                         ON ru.id = ruwcll.res_users_id
#                 ),

#                 revenues AS (
#                     SELECT
#                         pl.project_task_id AS task_id,
#                         pt.name AS task_name,
#                         pp.default_code,
#                         pl.under_warranty_bool,
#                         pp.service_product_price_edit_bool,
#                         pl.total AS value,
#                         pl.product_id
#                     FROM project_task pt
#                     JOIN product_lines pl
#                         ON pl.project_task_id = pt.id
#                     JOIN product_product pp
#                         ON pp.id = pl.product_id
#                 ),

#                 uw_sparts_revenue AS (
#                     SELECT
#                         pl.project_task_id AS task_id,
#                         pl.product_id,
#                         COALESCE(ip.value_float, 0) AS value
#                     FROM product_lines pl
#                     LEFT JOIN ir_property ip
#                         ON split_part(ip.res_id, ',', 2)::int = pl.product_id
#                         AND ip.type = 'float'
#                         AND ip.name = 'standard_price'
#                     WHERE pl.under_warranty_bool = true
#                 )

#                 SELECT
#                     -- Unique ID for Odoo
#                     row_number() OVER () AS id,

#                     -- Row number (based on your ordering)
#                     row_number() OVER (ORDER BY mst.user_id, mst.task_id) AS row_no,

#                     mst.task_id,
#                     mst.task_reference AS task_name,
#                     mst.user_id,
#                     mst.default_work_location,
#                     mst.company_id,
#                     mst.service_warranty_id AS service_warranty,
#                     mst.work_center_group_id,
#                     mst.work_center_id,

#                     rev.default_code,
#                     rev.under_warranty_bool,
#                     rev.service_product_price_edit_bool,

#                     uwspr.product_id,

#                     rev.value AS total_revenue,

#                     CASE
#                         WHEN (rev.default_code LIKE '%SERVICE%' OR rev.default_code LIKE '%INSPECTION%')
#                         THEN rev.value ELSE 0
#                     END AS labour_revenue,

#                     CASE
#                         WHEN (rev.default_code NOT LIKE '%SERVICE%' AND rev.default_code NOT LIKE '%INSPECTION%')
#                         THEN rev.value ELSE 0
#                     END AS parts_revenue,

#                     uwspr.value AS warranty_spareparts_revenue,

#                     mst.rtat_hours,
#                     mst.job_card_state AS job_card_status,
#                     mst.service_created_datetime

#                 FROM masters mst

#                 LEFT JOIN revenues rev
#                     ON rev.task_id = mst.task_id

#                 LEFT JOIN uw_sparts_revenue uwspr
#                     ON uwspr.task_id = mst.task_id
#                    AND uwspr.product_id = rev.product_id

#             )
#         """)
