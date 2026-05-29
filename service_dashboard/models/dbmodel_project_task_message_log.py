# -*- coding: utf-8 -*-
from odoo import models, fields, tools, api
from lxml import etree

class DbModelTaskMessageLogAnalysis(models.Model):
    _name = "dbmodel.task.message.log.analysis"
    _description = "DBM Task Message Log Analysis"
    _auto = False

    user_id = fields.Many2one("res.users", string="User", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Partner", readonly=True)
    user_name = fields.Char(string="User Name", readonly=True)
    user_role = fields.Many2one("dashboard.user.rights", string="User Role", readonly=True)
    dashboard_type = fields.Char(string="Dashboard Type", readonly=True)

    active = fields.Boolean(string="Active", readonly=True)
    region = fields.Many2one("work.center.group", string="Region", readonly=True)
    city = fields.Many2one("work.center.location", string="City", readonly=True)

    task_id = fields.Many2one("project.task", string="Task", readonly=True)
    task_description = fields.Char(string="Task Description", readonly=True)
    write_uid = fields.Many2one("res.users", string="Write User", readonly=True)
    ptml_initial_taskstatus = fields.Char(string="Initial Task Status", readonly=True)
    ptml_final_taskstatus = fields.Char(string="Final Task Status", readonly=True)
    task_date = fields.Datetime(string="Task Date", readonly=True)
    rtat_hours = fields.Char(string="RTAT", readonly=True)

    status_transition = fields.Char(string="Status Transition", readonly=True)
    technician_travel_hours = fields.Float(string="Technician Travel Hours", readonly=True)
    technician_travel_hours_min = fields.Float(string="Technician Travel Hours Min", readonly=True)
    onhold_hours = fields.Float(string="On Hold Hours", readonly=True)
    onhold_hours_min = fields.Float(string="On Hold Hours Min", readonly=True)
    cstneedquote_hours = fields.Float(string="CST Need Quote Hours", readonly=True)
    cstneedquote_hours_min = fields.Float(string="CST Need Quote Hours Min", readonly=True)
    sv_worked_hours = fields.Float(string="SV Worked Hours", readonly=True)
    sv_worked_hours_min = fields.Float(string="SV Worked Hours Min", readonly=True)
    sv_worked_withhold_hours = fields.Float(string="SV Worked Withhold Hours", readonly=True)
    sv_worked_withhold_hours_min = fields.Float(string="SV Worked Withhold Hours Min", readonly=True)
    sv_worked_hours2 = fields.Float(string="SV Worked Hours 2", readonly=True)
    sv_worked_hours2_min = fields.Float(string="SV Worked Hours 2 Min", readonly=True)
    total_worked_hours = fields.Float(string="Total Worked Hours", readonly=True)
    total_worked_hours_min = fields.Float(string="Total Worked Hours Min", readonly=True)
    expected_completion_mins = fields.Float(string="Expected Completion Mins", readonly=True)
    expected_completion_hours = fields.Float(string="Expected Completion Hours", readonly=True)
    expected_completion_hours_min = fields.Float(string="Expected Completion Hours Min", readonly=True)
    task_count = fields.Integer(string="Total Tasks", readonly=True)
    on_hold_task_count = fields.Integer(string="On Hold Tasks", readonly=True)

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

    @api.depends("city")
    def _compute_is_user_work_location(self):
        allowed_locations = self._get_user_work_locations()
        for rec in self:
            rec.is_user_work_location = rec.city.id in allowed_locations

    def _search_is_user_work_location(self, operator, value):
        allowed_locations = self._get_user_work_locations()
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('city', 'in', allowed_locations)]
        else:
            return [('city', 'not in', allowed_locations)]

    is_my_user_group = fields.Boolean(
        string="Is My User Group",
        compute="_compute_is_my_user_group",
        search="_search_is_my_user_group"
    )

    @api.depends("user_role")
    def _compute_is_my_user_group(self):
        my_groups = self._get_logged_user_role_groups()
        for rec in self:
            rec.is_my_user_group = False
            if rec.user_role.name and my_groups:
                if any(grp in rec.user_role.name for grp in my_groups):
                    rec.is_my_user_group = True

    def _search_is_my_user_group(self, operator, value):
        my_groups = self._get_logged_user_role_groups()
        if not my_groups:
            return [('id', '=', 0)] if (operator == '=' and value) else []

        domain = []
        for grp in my_groups:
            domain.append(('user_role.name', 'ilike', grp))
            
        if (operator == '=' and value) or (operator == '!=' and not value):
            if len(domain) > 1:
                return ['|'] * (len(domain) - 1) + domain
            return domain
        else:
            neg_domain = [('user_role.name', 'not ilike', grp) for grp in my_groups]
            if len(neg_domain) > 1:
                return ['&'] * (len(neg_domain) - 1) + neg_domain
            return neg_domain

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

    @api.model
    def _get_default_tree_view(self):
        node = etree.Element("tree", string=self._description, action="action_open_task_list", type="object", create="0", edit="0", delete="0")
        
        # Get roles for current logged-in user
        roles = self._get_logged_user_role_groups()
        
        # Define specific field sets for each user group
        role_field_map = {
            'Parts': [
                'task_id', 'task_date', 'status_transition'
            ],
            'Coordinator': [
                'task_id', 'user_id', 'task_date', 'user_role', 'region', 'city', 
                'status_transition', 'rtat_hours', 'technician_travel_hours', 
                'onhold_hours', 'total_worked_hours'
            ],
            'Call Center': [
                'task_id', 'task_date', 'region', 'city', 'status_transition'
            ],
            'Technician': [
                'task_id', 'task_date', 'status_transition', 'technician_travel_hours', 'total_worked_hours'
            ]
        }

        # Combine fields if user has multiple roles
        visible_fields = set()
        for role in roles:
            if role in role_field_map:
                visible_fields.update(role_field_map[role])

        # Default fallback if no roles matched
        if not visible_fields:
            render_fields = [
                "task_id", "user_id", "task_date", "user_role", "region", "city", 
                "status_transition", "rtat_hours"
            ]
        else:
            # Maintain a specific order if possible, or just use the set
            # For better UX, we can define a priority order or just use the model order
            all_possible_fields = [
                "task_id", "user_id", "task_date", "user_role", "region", "city", 
                "status_transition", "rtat_hours", "technician_travel_hours", 
                "onhold_hours", "total_worked_hours"
            ]
            render_fields = [f for f in all_possible_fields if f in visible_fields]
        
        # Always append task_count and on_hold_task_count at the end of render_fields
        if not render_fields:
            render_fields = [
                "task_id", "user_id", "task_date", "user_role", "region", "city", 
                "status_transition", "rtat_hours"
            ]
        render_fields.extend(['task_count', 'on_hold_task_count'])

        for field_name in render_fields:
            if field_name in self._fields:
                field_node = etree.SubElement(node, "field", name=field_name)
                # Disable hyperlink for all many2one except task_id
                if field_name != "task_id" and self._fields[field_name].type == "many2one":
                    field_node.set("options", "{'no_open': True, 'no_create': True}")
                # Apply float_time widget for hour fields
                if field_name.endswith("_hours"):
                    field_node.set("widget", "float_time")
                # Apply sum to task_count and on_hold_task_count
                if field_name in ['task_count', 'on_hold_task_count']:
                    field_node.set("sum", "Total")
        
        # Add drilldown button at the end of the tree view
        etree.SubElement(node, "button", name="action_open_task_list", type="object", string="Drilldown", icon="fa-arrow-circle-right")
        
        return node

    @api.model
    def fields_view_get(self, view_id=None, view_type='tree', toolbar=False, submenu=False):
        res = super(DbModelTaskMessageLogAnalysis, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'tree':
            node = self._get_default_tree_view()
            res['arch'] = etree.tostring(node, encoding='unicode')
        return res

    def action_open_task_list(self):
        self.ensure_one()
        if self.task_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'project.task',
                'res_id': self.task_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    row_number() OVER () AS id,
                    /* user details */
                    ru.id as user_id,
                    ptml.author_id as partner_id,
                    rp.name as user_name,
                    ur.dashboard_rights_id as user_role,
                    ru.dashboard_type_selection as dashboard_type,

                    /* other master details */
                    pt.active as active,
                    wcr.work_center_group_id as region,
                    um.work_center_location_id as city,

                    /* task details */
                    ptml.res_id as task_id,
                    pt.name as task_description,
                    pt.write_uid as write_uid,
                    LPAD(FLOOR(COALESCE(pt.rtat_hours, 0) / 3600)::text, 2, '0') || ':' || LPAD(FLOOR(MOD(COALESCE(pt.rtat_hours, 0)::numeric, 3600) / 60)::text, 2, '0') as rtat_hours,
                    ptml.old_value as ptml_initial_taskstatus,
                    ptml.new_value as ptml_final_taskstatus,
                    ptml.date as task_date,


                    /* new analysis */
                    COALESCE(ptml.old_value || ' >> ' || ptml.new_value, ptml.new_value) as status_transition,

                    /* Safe Float Casting Helper Logic */
                    COALESCE(CASE WHEN pt.technician_travel_hours::text ~ ':' THEN (NULLIF(split_part(pt.technician_travel_hours::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.technician_travel_hours::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.technician_travel_hours::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS technician_travel_hours,
                    COALESCE(CASE WHEN pt.technician_travel_hours_min::text ~ ':' THEN (NULLIF(split_part(pt.technician_travel_hours_min::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.technician_travel_hours_min::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.technician_travel_hours_min::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS technician_travel_hours_min,
                    COALESCE(CASE WHEN pt.onhold_hours::text ~ ':' THEN (NULLIF(split_part(pt.onhold_hours::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.onhold_hours::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.onhold_hours::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS onhold_hours,
                    COALESCE(CASE WHEN pt.onhold_hours_min::text ~ ':' THEN (NULLIF(split_part(pt.onhold_hours_min::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.onhold_hours_min::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.onhold_hours_min::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS onhold_hours_min,
                    COALESCE(CASE WHEN pt.cstneedquote_hours::text ~ ':' THEN (NULLIF(split_part(pt.cstneedquote_hours::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.cstneedquote_hours::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.cstneedquote_hours::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS cstneedquote_hours,
                    COALESCE(CASE WHEN pt.cstneedquote_hours_min::text ~ ':' THEN (NULLIF(split_part(pt.cstneedquote_hours_min::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.cstneedquote_hours_min::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.cstneedquote_hours_min::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS cstneedquote_hours_min,
                    COALESCE(CASE WHEN pt.sv_worked_hours::text ~ ':' THEN (NULLIF(split_part(pt.sv_worked_hours::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.sv_worked_hours::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.sv_worked_hours::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS sv_worked_hours,
                    COALESCE(CASE WHEN pt.sv_worked_hours_min::text ~ ':' THEN (NULLIF(split_part(pt.sv_worked_hours_min::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.sv_worked_hours_min::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.sv_worked_hours_min::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS sv_worked_hours_min,
                    COALESCE(CASE WHEN pt.sv_worked_withhold_hours::text ~ ':' THEN (NULLIF(split_part(pt.sv_worked_withhold_hours::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.sv_worked_withhold_hours::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.sv_worked_withhold_hours::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS sv_worked_withhold_hours,
                    COALESCE(CASE WHEN pt.sv_worked_withhold_hours_min::text ~ ':' THEN (NULLIF(split_part(pt.sv_worked_withhold_hours_min::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.sv_worked_withhold_hours_min::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.sv_worked_withhold_hours_min::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS sv_worked_withhold_hours_min,
                    COALESCE(CASE WHEN pt.sv_worked_hours2::text ~ ':' THEN (NULLIF(split_part(pt.sv_worked_hours2::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.sv_worked_hours2::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.sv_worked_hours2::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS sv_worked_hours2,
                    COALESCE(CASE WHEN pt.sv_worked_hours2_min::text ~ ':' THEN (NULLIF(split_part(pt.sv_worked_hours2_min::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.sv_worked_hours2_min::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.sv_worked_hours2_min::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS sv_worked_hours2_min,
                    COALESCE(CASE WHEN pt.total_worked_hours::text ~ ':' THEN (NULLIF(split_part(pt.total_worked_hours::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.total_worked_hours::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.total_worked_hours::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS total_worked_hours,
                    COALESCE(CASE WHEN pt.total_worked_hours_min::text ~ ':' THEN (NULLIF(split_part(pt.total_worked_hours_min::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.total_worked_hours_min::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.total_worked_hours_min::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS total_worked_hours_min,
                    COALESCE(CASE WHEN pt.expected_completion_mins::text ~ ':' THEN (NULLIF(split_part(pt.expected_completion_mins::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.expected_completion_mins::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.expected_completion_mins::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS expected_completion_mins,
                    COALESCE(CASE WHEN pt.expected_completion_hours::text ~ ':' THEN (NULLIF(split_part(pt.expected_completion_hours::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.expected_completion_hours::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.expected_completion_hours::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS expected_completion_hours,
                    COALESCE(CASE WHEN pt.expected_completion_hours_min::text ~ ':' THEN (NULLIF(split_part(pt.expected_completion_hours_min::text, ':', 1), '')::numeric + COALESCE(NULLIF(split_part(pt.expected_completion_hours_min::text, ':', 2), ''), '0')::numeric / 60.0)::float ELSE NULLIF(REGEXP_REPLACE(pt.expected_completion_hours_min::text, '[^0-9.]', '', 'g'), '')::float END, 0) AS expected_completion_hours_min,
                    1 AS task_count,
                    CASE WHEN ptml.new_value ILIKE '%%hold%%' OR ptml.new_value ILIKE '%%Hold%%' THEN 1 ELSE 0 END AS on_hold_task_count
                FROM 
                    project_task_message_log ptml
                    INNER JOIN project_task pt
                        ON pt.id = ptml.res_id
                        AND pt.active = true
                    LEFT JOIN res_partner rp
                        ON rp.id = ptml.author_id
                    LEFT JOIN res_users ru
                        ON ru.partner_id = rp.id

                    /* User Roles (NO duplication) */
                    LEFT JOIN (
                        SELECT DISTINCT ON (user_id)
                            dashboard_rights_id,
                            user_id
                        FROM user_dashboard_rights_rel
                    ) ur ON ur.user_id = ru.id
					
                    /* Region mapping (NO duplication) */
                    LEFT JOIN (
                        SELECT DISTINCT ON (user_id)
                            work_center_group_id,
                            user_id
                        FROM user_work_center_group_rel
                    ) wcr ON wcr.user_id = ru.id
 
 					/* City mapping (NO duplication) */
                    LEFT JOIN (
                        SELECT DISTINCT ON (work_center_location_id)
                            work_center_location_id,
                            res_users_id
                        FROM res_users_work_center_location_rel
                    ) um 
                        ON pt.work_center_id = um.work_center_location_id
                ORDER BY
                    ptml.res_id,
                    ptml.date
            )
            """
            % (self._table,)
        )
