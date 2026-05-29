# -*- coding: utf-8 -*-
from odoo import models, fields, tools, api
# pyrefly: ignore [missing-import]
from lxml import etree


class DbModelJobCards(models.Model):
    _name = "dbmodel.jobcards.analysis"
    _description = "DBM Job Cards Analysis"
    _auto = False

    # The 'id' field is automatically added by Odoo, mapped to our row_number() OVER () AS id

    row_no = fields.Integer(string="Row No", readonly=True)
    task_id = fields.Many2one("project.task", string="Task", readonly=True)
    task_name = fields.Char(string="Task Name", readonly=True)
    user_id = fields.Many2one("res.users", string="User", readonly=True)
    user_role = fields.Char(string="User Role", readonly=True)
    technician_id = fields.Many2one("res.users", string="Technician", readonly=True)
    scheduled_uid = fields.Many2one("res.users", string="Scheduled User", readonly=True)
    closed_jobcard_user_id = fields.Many2one("res.users", string="Closed Jobcard User", readonly=True)
    default_work_location = fields.Many2one(
        "work.center.location", string="Default Work Location", readonly=True
    )
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    service_warranty_id = fields.Many2one(
        "service.warranty", string="Service Warranty", readonly=True
    )
    work_center_group_id = fields.Many2one(
        "work.center.group", string="Work Center Group", readonly=True
    )
    work_center_id = fields.Many2one(
        "work.center.location", string="Work Center", readonly=True
    )

    # default_code = fields.Char(string="Default Code", readonly=True)
    # under_warranty_bool = fields.Boolean(string="Under Warranty", readonly=True)
    # service_product_price_edit_bool = fields.Boolean(
    #     string="Service Product Price Edit", readonly=True
    # )
    # product_id = fields.Many2one("product.product", string="Product", readonly=True)

    qty = fields.Float(string="Quantity", readonly=True)
    total_revenue = fields.Float(string="Total Revenue", readonly=True)
    # warranty_spareparts_cost = fields.Float(
    #     string="Warranty Spareparts Cost", readonly=True
    # )

    labour_revenue = fields.Float(string="Labour Revenue", readonly=True)
    parts_revenue = fields.Float(string="Parts Revenue", readonly=True)
    warranty_spareparts_revenue = fields.Float(
        string="Warranty Spareparts Revenue", readonly=True
    )

    rtat_hours = fields.Float(string="RTAT Hours", readonly=True)
    technician_travel_hours = fields.Float(string="Technician Travel Hours", readonly=True)
    technician_travel_hours_min = fields.Float(string="Technician Travel Hours (Min)", readonly=True)
    onhold_hours = fields.Float(string="Onhold Hours", readonly=True)
    onhold_hours_min = fields.Float(string="Onhold Hours (Min)", readonly=True)
    cstneedquote_hours = fields.Float(string="CST Need Quote Hours", readonly=True)
    cstneedquote_hours_min = fields.Float(string="CST Need Quote Hours (Min)", readonly=True)
    sv_worked_hours = fields.Float(string="SV Worked Hours", readonly=True)
    sv_worked_hours_min = fields.Float(string="SV Worked Hours (Min)", readonly=True)
    sv_worked_withhold_hours = fields.Float(string="SV Worked Withhold Hours", readonly=True)
    sv_worked_withhold_hours_min = fields.Float(string="SV Worked Withhold Hours (Min)", readonly=True)
    sv_worked_hours2 = fields.Float(string="SV Worked Hours 2", readonly=True)
    sv_worked_hours2_min = fields.Float(string="SV Worked Hours 2 (Min)", readonly=True)
    total_worked_hours = fields.Float(string="Total Worked Hours", readonly=True)
    total_worked_hours_min = fields.Float(string="Total Worked Hours (Min)", readonly=True)
    expected_completion_mins = fields.Float(string="Expected Completion Mins", readonly=True)
    expected_completion_hours = fields.Float(string="Expected Completion Hours", readonly=True)
    expected_completion_hours_min = fields.Float(string="Expected Completion Hours (Min)", readonly=True)
    job_card_status = fields.Char(string="Job Card Status", readonly=True)
    action_status = fields.Char(string="Action Status", readonly=True)
    service_created_datetime = fields.Datetime(
        string="Service Created Datetime", readonly=True
    )
    active = fields.Boolean(string="Active", readonly=True)

    is_user_work_location = fields.Boolean(
        string="Is My Work Location",
        compute="_compute_is_user_work_location",
        search="_search_is_user_work_location"
    )

    @api.model
    def _get_user_work_locations(self):
        self.env.cr.execute(
            "SELECT work_center_location_id FROM res_users_work_center_location_rel WHERE res_users_id = %s" % (self.env.uid,)
        )
        return [row[0] for row in self.env.cr.fetchall()]

    @api.depends("default_work_location")
    def _compute_is_user_work_location(self):
        allowed_locations = self._get_user_work_locations()
        for rec in self:
            rec.is_user_work_location = rec.default_work_location.id in allowed_locations

    def _search_is_user_work_location(self, operator, value):
        allowed_locations = self._get_user_work_locations()
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('default_work_location', 'in', allowed_locations)]
        else:
            return [('default_work_location', 'not in', allowed_locations)]

    is_my_user_group = fields.Boolean(
        string="Is My User Group",
        compute="_compute_is_my_user_group",
        search="_search_is_my_user_group"
    )

    @api.model
    def _get_logged_user_role_groups(self):
        self.env.cr.execute(
            """
            SELECT DISTINCT
                case 
                    when imd.name = 'group_parts_user' then 'Parts'
                    when imd.name = 'group_technical_allocation_user' then 'Coordinator'
                    when imd.name = 'group_call_center_user' then 'Call Center'
                    when imd.name = 'group_job_card_mobile_user' then 'Technician'
                end as user_role
            FROM res_users u
            JOIN res_groups_users_rel rel ON rel.uid = u.id
            JOIN ir_model_data imd ON imd.res_id = rel.gid
            WHERE u.id = %s
              AND imd.module = 'machine_repair_management'
              AND imd.name IN ('group_parts_user', 'group_technical_allocation_user', 'group_call_center_user', 'group_job_card_mobile_user')
            """ % (self.env.uid,)
        )
        return [row[0] for row in self.env.cr.fetchall() if row[0]]

    @api.depends("user_role")
    def _compute_is_my_user_group(self):
        my_groups = self._get_logged_user_role_groups()
        for rec in self:
            rec.is_my_user_group = False
            if rec.user_role and my_groups:
                if any(grp in rec.user_role for grp in my_groups):
                    rec.is_my_user_group = True

    def _search_is_my_user_group(self, operator, value):
        my_groups = self._get_logged_user_role_groups()
        if not my_groups:
            return [('id', '=', 0)] if (operator == '=' and value) else []

        domain = []
        for grp in my_groups:
            domain.append(('user_role', 'ilike', grp))
            
        if (operator == '=' and value) or (operator == '!=' and not value):
            if len(domain) > 1:
                return ['|'] * (len(domain) - 1) + domain
            return domain
        else:
            neg_domain = [('user_role', 'not ilike', grp) for grp in my_groups]
            if len(neg_domain) > 1:
                return ['&'] * (len(neg_domain) - 1) + neg_domain
            return neg_domain

    def fields_view_get(self, view_id=None, view_type='tree', toolbar=False, submenu=False):
        res = super(DbModelJobCards, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )
        if view_type == 'tree':
            node = self._get_default_tree_view()
            res['arch'] = etree.tostring(node, encoding='unicode')
        return res

    def action_open_task_list(self):
        """ Redirect row click to the actual project task form with breadcrumb support """
        self.ensure_one()
        if self.task_id:
            # Fetch the standard action to ensure breadcrumbs are maintained correctly
            action = self.env["ir.actions.actions"]._for_xml_id("project.action_view_task")
            action.update({
                'res_id': self.task_id.id,
                'view_mode': 'form',
                'views': [(self.env.ref('project.view_task_form2').id, 'form')],
                'target': 'current',
                'context': self.env.context,
            })
            return action

    @api.model
    def _get_default_tree_view(self):
        node = etree.Element("tree", string=self._description, action="action_open_task_list", type="object", create="0", edit="0", delete="0")
        
        # Get roles for current logged-in user
        roles = self._get_logged_user_role_groups()
        
        # Define specific field sets for each user group
        role_field_map = {
            'Parts': [
                'task_id', 'qty', 'parts_revenue', 
                'warranty_spareparts_revenue', 'job_card_status', 'action_status'
            ],
            'Coordinator': [
                'task_id', 'user_id', 'job_card_status', 
                'total_revenue', 'labour_revenue', 'parts_revenue', 
                'rtat_hours', 'technician_travel_hours', 'onhold_hours', 
                'total_worked_hours', 'action_status', 'service_created_datetime'
            ],
            'Call Center': [
                'task_id', 'job_card_status', 
                'action_status', 'service_created_datetime', 'work_center_id', 
                'work_center_group_id'
            ],
            'Technician': [
                'task_id', 'job_card_status', 
                'technician_travel_hours', 'total_worked_hours', 'action_status'
            ]
        }

        # Combine fields if user has multiple roles
        visible_fields = set()
        for role in roles:
            if role in role_field_map:
                visible_fields.update(role_field_map[role])

        exclude_fields = [
            "id", "row_no", "display_name", "complete_name", "create_uid", "create_date",
            "write_uid", "write_date", "__last_update", "active", "is_user_work_location", "is_my_user_group"
        ]

        # Determine which fields to actually render
        if visible_fields:
            # Filter fields to only those defined in visible_fields, ensuring they exist in the model
            render_fields = [f for f in self._fields if f in visible_fields and f not in exclude_fields]
        else:
            # Fallback to default behavior (all non-excluded fields) if no roles matched
            render_fields = [f for f in self._fields if f not in exclude_fields]

        for field_name in render_fields:
            field_node = etree.SubElement(node, "field", name=field_name)
            # Apply float_time widget for hour fields
            if field_name.endswith("_hours"):
                field_node.set("widget", "float_time")
            # Add no_open option for many2one fields
            field_node.set("options", "{'no_open': True}")
        
        # Add drilldown button at the end of the tree view
        etree.SubElement(node, "button", name="action_open_task_list", type="object", string="Drilldown", icon="fa-arrow-circle-right")
        
        return node

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
            /* Final query for custome module */
            SELECT
                pt.id AS id,
                row_number() OVER (ORDER BY pt.id) AS row_no,

                pt.id AS task_id,
                pt.name AS task_name,

                ru.id AS user_id,
                TRIM(BOTH ', ' FROM CONCAT_WS(', ', ug_tech.user_role, ug_ru.user_role, ug_create.user_role)) AS user_role,
                um.work_center_location_id AS default_work_location,

                pt.company_id AS company_id,
                pt.service_warranty_id AS service_warranty_id,
                pt.work_center_group_id AS work_center_group_id,
                pt.work_center_id AS work_center_id,
                pt.technician_id AS technician_id,
                pt.scheduled_uid AS scheduled_uid, 
                pt.closed_jobcard_user_id AS closed_jobcard_user_id,

                COALESCE(pa.total_qty, 0) AS qty,
                COALESCE(pa.total_revenue, 0) AS total_revenue,
                COALESCE(pa.labour_revenue, 0) AS labour_revenue,
                COALESCE(pa.parts_revenue, 0) AS parts_revenue,
                COALESCE(pa.warranty_spareparts_revenue, 0) AS warranty_spareparts_revenue,

                pt.job_card_state AS job_card_status,
                pt.action_status AS action_status,
                COALESCE(CASE WHEN pt.rtat_hours::text LIKE '%%:%%' THEN (split_part(pt.rtat_hours::text, ':', 1)::float + split_part(pt.rtat_hours::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.rtat_hours::text, '')::float END, 0) AS rtat_hours,
                COALESCE(CASE WHEN pt.technician_travel_hours::text LIKE '%%:%%' THEN (split_part(pt.technician_travel_hours::text, ':', 1)::float + split_part(pt.technician_travel_hours::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.technician_travel_hours::text, '')::float END, 0) AS technician_travel_hours,
                COALESCE(CASE WHEN pt.technician_travel_hours_min::text LIKE '%%:%%' THEN (split_part(pt.technician_travel_hours_min::text, ':', 1)::float + split_part(pt.technician_travel_hours_min::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.technician_travel_hours_min::text, '')::float END, 0) AS technician_travel_hours_min,
                COALESCE(CASE WHEN pt.onhold_hours::text LIKE '%%:%%' THEN (split_part(pt.onhold_hours::text, ':', 1)::float + split_part(pt.onhold_hours::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.onhold_hours::text, '')::float END, 0) AS onhold_hours,
                COALESCE(CASE WHEN pt.onhold_hours_min::text LIKE '%%:%%' THEN (split_part(pt.onhold_hours_min::text, ':', 1)::float + split_part(pt.onhold_hours_min::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.onhold_hours_min::text, '')::float END, 0) AS onhold_hours_min,
                COALESCE(CASE WHEN pt.cstneedquote_hours::text LIKE '%%:%%' THEN (split_part(pt.cstneedquote_hours::text, ':', 1)::float + split_part(pt.cstneedquote_hours::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.cstneedquote_hours::text, '')::float END, 0) AS cstneedquote_hours,
                COALESCE(CASE WHEN pt.cstneedquote_hours_min::text LIKE '%%:%%' THEN (split_part(pt.cstneedquote_hours_min::text, ':', 1)::float + split_part(pt.cstneedquote_hours_min::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.cstneedquote_hours_min::text, '')::float END, 0) AS cstneedquote_hours_min,
                COALESCE(CASE WHEN pt.sv_worked_hours::text LIKE '%%:%%' THEN (split_part(pt.sv_worked_hours::text, ':', 1)::float + split_part(pt.sv_worked_hours::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.sv_worked_hours::text, '')::float END, 0) AS sv_worked_hours,
                COALESCE(CASE WHEN pt.sv_worked_hours_min::text LIKE '%%:%%' THEN (split_part(pt.sv_worked_hours_min::text, ':', 1)::float + split_part(pt.sv_worked_hours_min::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.sv_worked_hours_min::text, '')::float END, 0) AS sv_worked_hours_min,
                COALESCE(CASE WHEN pt.sv_worked_withhold_hours::text LIKE '%%:%%' THEN (split_part(pt.sv_worked_withhold_hours::text, ':', 1)::float + split_part(pt.sv_worked_withhold_hours::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.sv_worked_withhold_hours::text, '')::float END, 0) AS sv_worked_withhold_hours,
                COALESCE(CASE WHEN pt.sv_worked_withhold_hours_min::text LIKE '%%:%%' THEN (split_part(pt.sv_worked_withhold_hours_min::text, ':', 1)::float + split_part(pt.sv_worked_withhold_hours_min::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.sv_worked_withhold_hours_min::text, '')::float END, 0) AS sv_worked_withhold_hours_min,
                COALESCE(CASE WHEN pt.sv_worked_hours2::text LIKE '%%:%%' THEN (split_part(pt.sv_worked_hours2::text, ':', 1)::float + split_part(pt.sv_worked_hours2::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.sv_worked_hours2::text, '')::float END, 0) AS sv_worked_hours2,
                COALESCE(CASE WHEN pt.sv_worked_hours2_min::text LIKE '%%:%%' THEN (split_part(pt.sv_worked_hours2_min::text, ':', 1)::float + split_part(pt.sv_worked_hours2_min::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.sv_worked_hours2_min::text, '')::float END, 0) AS sv_worked_hours2_min,
                COALESCE(CASE WHEN pt.total_worked_hours::text LIKE '%%:%%' THEN (split_part(pt.total_worked_hours::text, ':', 1)::float + split_part(pt.total_worked_hours::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.total_worked_hours::text, '')::float END, 0) AS total_worked_hours,
                COALESCE(CASE WHEN pt.total_worked_hours_min::text LIKE '%%:%%' THEN (split_part(pt.total_worked_hours_min::text, ':', 1)::float + split_part(pt.total_worked_hours_min::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.total_worked_hours_min::text, '')::float END, 0) AS total_worked_hours_min,
                COALESCE(CASE WHEN pt.expected_completion_mins::text LIKE '%%:%%' THEN (split_part(pt.expected_completion_mins::text, ':', 1)::float + split_part(pt.expected_completion_mins::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.expected_completion_mins::text, '')::float END, 0) AS expected_completion_mins,
                COALESCE(CASE WHEN pt.expected_completion_hours::text LIKE '%%:%%' THEN (split_part(pt.expected_completion_hours::text, ':', 1)::float + split_part(pt.expected_completion_hours::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.expected_completion_hours::text, '')::float END, 0) AS expected_completion_hours,
                COALESCE(CASE WHEN pt.expected_completion_hours_min::text LIKE '%%:%%' THEN (split_part(pt.expected_completion_hours_min::text, ':', 1)::float + split_part(pt.expected_completion_hours_min::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.expected_completion_hours_min::text, '')::float END, 0) AS expected_completion_hours_min,
                pt.service_created_datetime AS service_created_datetime,
                pt.active AS active

            FROM project_task pt

            /* Aggregated product lines (NO duplication) */
            LEFT JOIN (
                SELECT
                    pl.project_task_id AS task_id,

                    SUM(pl.qty) AS total_qty,
                    SUM(pl.total) AS total_revenue,

                    SUM(
                        CASE 
                            WHEN (pp.default_code LIKE '%%SERVIC%%' OR pp.default_code LIKE '%%INSPECTION%%')
                            THEN pl.total ELSE 0 
                        END
                    ) AS labour_revenue,

                    SUM(
                        CASE 
                            WHEN (pp.default_code NOT LIKE '%%SERVIC%%' AND pp.default_code NOT LIKE '%%INSPECTION%%')
                            THEN pl.total ELSE 0 
                        END
                    ) AS parts_revenue,

                    SUM(
                        CASE 
                            WHEN ip.value_float > 0 
                            THEN (pl.qty * ip.value_float)
                            ELSE 0 
                        END
                    ) AS warranty_spareparts_revenue

                FROM product_lines pl
                JOIN product_product pp 
                    ON pp.id = pl.product_id

                LEFT JOIN (
                    
                    SELECT DISTINCT ON (split_part(res_id, ',', 2))
                        split_part(res_id, ',', 2)::int AS product_id,
                        value_float
                    FROM ir_property
                    WHERE type = 'float'
                      AND name = 'standard_price'
                ) ip 
                    ON ip.product_id = pl.product_id and pl.under_warranty_bool = true

                GROUP BY pl.project_task_id

            ) pa ON pa.task_id = pt.id


            /* User mapping (NO duplication) */
            LEFT JOIN (
                SELECT DISTINCT ON (work_center_location_id)
                    work_center_location_id,
                    res_users_id
                FROM res_users_work_center_location_rel
            ) um 
                ON pt.work_center_id = um.work_center_location_id

            LEFT JOIN res_users ru 
                ON ru.id = um.res_users_id

            /* Ultra-fast Subquery matches for all logical user pathways! */
            LEFT JOIN (
                SELECT u.id as uid, STRING_AGG(DISTINCT
                    case when imd.name = 'group_parts_user' then 'Parts'
                         when imd.name = 'group_technical_allocation_user' then 'Coordinator'
                         when imd.name = 'group_call_center_user' then 'Call Center'
                         when imd.name = 'group_job_card_mobile_user' then 'Technician' else null
                    end, ', ') as user_role
                FROM res_users u JOIN res_groups_users_rel rel ON rel.uid = u.id JOIN ir_model_data imd ON imd.res_id = rel.gid
                WHERE imd.module = 'machine_repair_management' GROUP BY u.id
            ) ug_tech ON ug_tech.uid = pt.technician_id

            LEFT JOIN (
                SELECT u.id as uid, STRING_AGG(DISTINCT
                    case when imd.name = 'group_parts_user' then 'Parts'
                         when imd.name = 'group_technical_allocation_user' then 'Coordinator'
                         when imd.name = 'group_call_center_user' then 'Call Center'
                         when imd.name = 'group_job_card_mobile_user' then 'Technician' else null
                    end, ', ') as user_role
                FROM res_users u JOIN res_groups_users_rel rel ON rel.uid = u.id JOIN ir_model_data imd ON imd.res_id = rel.gid
                WHERE imd.module = 'machine_repair_management' GROUP BY u.id
            ) ug_ru ON ug_ru.uid = ru.id

            LEFT JOIN (
                SELECT u.id as uid, STRING_AGG(DISTINCT
                    case when imd.name = 'group_parts_user' then 'Parts'
                         when imd.name = 'group_technical_allocation_user' then 'Coordinator'
                         when imd.name = 'group_call_center_user' then 'Call Center'
                         when imd.name = 'group_job_card_mobile_user' then 'Technician' else null
                    end, ', ') as user_role
                FROM res_users u JOIN res_groups_users_rel rel ON rel.uid = u.id JOIN ir_model_data imd ON imd.res_id = rel.gid
                WHERE imd.module = 'machine_repair_management' GROUP BY u.id
            ) ug_create ON ug_create.uid = pt.create_uid

            WHERE
                pt.active = true
                
            ORDER BY pt.id
            )
        """
            % (self._table,)
        )
