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
            "SELECT work_center_location_id FROM res_users_work_center_location_rel WHERE res_users_id = %s",
            (self.env.uid,)
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
            """,
            (self.env.uid,)
        )
        return [row[0] for row in self.env.cr.fetchall() if row[0]]

    @api.model
    def _get_default_tree_view(self):
        node = etree.Element("tree", string=self._description, action="action_open_task_list", type="object", create="0", edit="0", delete="0")
        roles = self._get_logged_user_role_groups()
        role_field_map = {
            'Parts': ['task_id', 'task_date', 'status_transition'],
            'Coordinator': [
                'task_id', 'user_id', 'task_date', 'user_role', 'region', 'city',
                'status_transition', 'rtat_hours', 'technician_travel_hours',
                'onhold_hours', 'total_worked_hours'
            ],
            'Call Center': ['task_id', 'task_date', 'region', 'city', 'status_transition'],
            'Technician': ['task_id', 'task_date', 'status_transition', 'technician_travel_hours', 'total_worked_hours'],
        }
        visible_fields = set()
        for role in roles:
            if role in role_field_map:
                visible_fields.update(role_field_map[role])
        if not visible_fields:
            render_fields = [
                "task_id", "user_id", "task_date", "user_role", "region", "city",
                "status_transition", "rtat_hours"
            ]
        else:
            all_possible_fields = [
                "task_id", "user_id", "task_date", "user_role", "region", "city",
                "status_transition", "rtat_hours", "technician_travel_hours",
                "onhold_hours", "total_worked_hours"
            ]
            render_fields = [f for f in all_possible_fields if f in visible_fields]
        if not render_fields:
            render_fields = [
                "task_id", "user_id", "task_date", "user_role", "region", "city",
                "status_transition", "rtat_hours"
            ]
        render_fields.extend(['task_count', 'on_hold_task_count'])
        for field_name in render_fields:
            if field_name in self._fields:
                field_node = etree.SubElement(node, "field", name=field_name)
                if field_name != "task_id" and self._fields[field_name].type == "many2one":
                    field_node.set("options", "{'no_open': True, 'no_create': True}")
                if field_name.endswith("_hours"):
                    field_node.set("widget", "float_time")
                if field_name in ['task_count', 'on_hold_task_count']:
                    field_node.set("sum", "Total")
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

    @api.model
    def refresh_materialized(self):
        """Refresh the materialized view. Called by an ir.cron on a schedule."""
        self.env.cr.execute(
            "REFRESH MATERIALIZED VIEW CONCURRENTLY dbmodel_task_message_log_analysis"
        )

    def init(self):
        cr = self.env.cr
        # The view is a MATERIALIZED VIEW so dashboard queries hit indexed storage
        # instead of recomputing 100k+ rows from mail_message and mail_tracking_value
        # on every chart load. An ir.cron refreshes it on a schedule.
        # Drop in either form — relkind may be 'v' (first install) or 'm' (re-run)
        cr.execute("""
            DO $$
            DECLARE r record;
            BEGIN
                SELECT relkind INTO r FROM pg_class WHERE relname = 'dbmodel_task_message_log_analysis';
                IF FOUND THEN
                    IF r.relkind = 'm' THEN
                        EXECUTE 'DROP MATERIALIZED VIEW dbmodel_task_message_log_analysis CASCADE';
                    ELSE
                        EXECUTE 'DROP VIEW dbmodel_task_message_log_analysis CASCADE';
                    END IF;
                END IF;
            END $$;
        """)

        cr.execute("""
            CREATE OR REPLACE FUNCTION _safe_hours(v anyelement) RETURNS float
            LANGUAGE plpgsql IMMUTABLE AS $func$
            DECLARE
                s text := v::text;
            BEGIN
                IF s IS NULL OR s = '' THEN RETURN 0; END IF;
                IF s ~ '^[0-9]+ days, [0-9]+:[0-9]+' THEN
                    RETURN split_part(s, ' days, ', 1)::float * 24
                         + split_part(split_part(s, ' days, ', 2), ':', 1)::float
                         + split_part(split_part(s, ' days, ', 2), ':', 2)::float / 60.0;
                END IF;
                IF s ~ '^-?[0-9]+:[0-9]+$' THEN
                    RETURN split_part(s, ':', 1)::float
                         + split_part(s, ':', 2)::float / 60.0;
                END IF;
                IF s ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN
                    RETURN s::float;
                END IF;
                RETURN 0;
            EXCEPTION WHEN others THEN
                RETURN 0;
            END;
            $func$
        """)

        cr.execute("""
            CREATE MATERIALIZED VIEW dbmodel_task_message_log_analysis AS
            WITH src AS (
                (SELECT DISTINCT ON (mm.res_id)
                    (mm.id * 2) AS ptml_id,
                    mm.create_date AS ptml_date,
                    mm.author_id AS ptml_author_id,
                    NULL::text AS ptml_old_value,
                    'New'::text AS ptml_new_value,
                    mm.res_id AS ptml_res_id
                FROM mail_message mm
                WHERE mm.model = 'project.task'
                ORDER BY mm.res_id, mm.create_date ASC)
                UNION ALL
                SELECT
                    (log.id * 2 + 1) AS ptml_id,
                    log.create_date AS ptml_date,
                    mm.author_id AS ptml_author_id,
                    COALESCE(log.old_value_char, log.old_value_text, log.old_value_datetime::text,
                             CAST(log.old_value_integer AS text), CAST(log.old_value_float AS text)) AS ptml_old_value,
                    COALESCE(log.new_value_char, log.new_value_text, log.new_value_datetime::text,
                             CAST(log.new_value_integer AS text), CAST(log.new_value_float AS text)) AS ptml_new_value,
                    mm.res_id AS ptml_res_id
                FROM mail_tracking_value log
                JOIN mail_message mm ON mm.id = log.mail_message_id
                JOIN ir_model_fields ff ON ff.id = log.field_id
                WHERE mm.model = 'project.task'
                  AND ff.name = 'job_state'
                  AND (COALESCE(log.old_value_char, log.old_value_text, log.old_value_datetime::text,
                                CAST(log.old_value_integer AS text), CAST(log.old_value_float AS text))
                       IS DISTINCT FROM
                       COALESCE(log.new_value_char, log.new_value_text, log.new_value_datetime::text,
                                CAST(log.new_value_integer AS text), CAST(log.new_value_float AS text)))
            )
            SELECT
                src.ptml_id AS id,
                ru.id as user_id,
                src.ptml_author_id as partner_id,
                rp.name as user_name,
                ur.dashboard_rights_id as user_role,
                ru.dashboard_type_selection as dashboard_type,
                pt.active as active,
                wcr.work_center_group_id as region,
                um.work_center_location_id as city,
                src.ptml_res_id as task_id,
                pt.name as task_description,
                pt.write_uid as write_uid,
                LPAD(FLOOR(COALESCE(pt.rtat_hours, 0) / 3600)::text, 2, '0') || ':' ||
                LPAD(FLOOR(MOD(COALESCE(pt.rtat_hours, 0)::numeric, 3600) / 60)::text, 2, '0') as rtat_hours,
                src.ptml_old_value as ptml_initial_taskstatus,
                src.ptml_new_value as ptml_final_taskstatus,
                src.ptml_date as task_date,
                COALESCE(src.ptml_old_value || ' >> ' || src.ptml_new_value, src.ptml_new_value) as status_transition,
                _safe_hours(pt.technician_travel_hours) AS technician_travel_hours,
                _safe_hours(pt.technician_travel_hours_min) AS technician_travel_hours_min,
                _safe_hours(pt.onhold_hours) AS onhold_hours,
                _safe_hours(pt.onhold_hours_min) AS onhold_hours_min,
                _safe_hours(pt.cstneedquote_hours) AS cstneedquote_hours,
                _safe_hours(pt.cstneedquote_hours_min) AS cstneedquote_hours_min,
                _safe_hours(pt.sv_worked_hours) AS sv_worked_hours,
                _safe_hours(pt.sv_worked_hours_min) AS sv_worked_hours_min,
                _safe_hours(pt.sv_worked_withhold_hours) AS sv_worked_withhold_hours,
                _safe_hours(pt.sv_worked_withhold_hours_min) AS sv_worked_withhold_hours_min,
                _safe_hours(pt.sv_worked_hours2) AS sv_worked_hours2,
                _safe_hours(pt.sv_worked_hours2_min) AS sv_worked_hours2_min,
                _safe_hours(pt.total_worked_hours) AS total_worked_hours,
                _safe_hours(pt.total_worked_hours_min) AS total_worked_hours_min,
                _safe_hours(pt.expected_completion_mins) AS expected_completion_mins,
                _safe_hours(pt.expected_completion_hours) AS expected_completion_hours,
                _safe_hours(pt.expected_completion_hours_min) AS expected_completion_hours_min,
                1 AS task_count,
                CASE WHEN src.ptml_new_value ILIKE '%%hold%%' THEN 1 ELSE 0 END AS on_hold_task_count
            FROM src
            INNER JOIN project_task pt ON pt.id = src.ptml_res_id AND pt.active = true
            LEFT JOIN res_partner rp ON rp.id = src.ptml_author_id
            LEFT JOIN res_users ru ON ru.partner_id = rp.id
            LEFT JOIN (SELECT DISTINCT ON (user_id) dashboard_rights_id, user_id FROM user_dashboard_rights_rel) ur ON ur.user_id = ru.id
            LEFT JOIN (SELECT DISTINCT ON (user_id) work_center_group_id, user_id FROM user_work_center_group_rel) wcr ON wcr.user_id = ru.id
            LEFT JOIN (SELECT DISTINCT ON (work_center_location_id) work_center_location_id, res_users_id FROM res_users_work_center_location_rel) um ON pt.work_center_id = um.work_center_location_id
            WITH DATA
        """)

        cr.execute("CREATE UNIQUE INDEX IF NOT EXISTS dbmodel_tml_analysis_id_idx ON dbmodel_task_message_log_analysis (id)")
        cr.execute("CREATE INDEX IF NOT EXISTS dbmodel_tml_analysis_user_id_idx ON dbmodel_task_message_log_analysis (user_id)")
        cr.execute("CREATE INDEX IF NOT EXISTS dbmodel_tml_analysis_status_idx ON dbmodel_task_message_log_analysis (ptml_final_taskstatus)")
        cr.execute("CREATE INDEX IF NOT EXISTS dbmodel_tml_analysis_user_status_idx ON dbmodel_task_message_log_analysis (user_id, ptml_final_taskstatus)")
        cr.execute("CREATE INDEX IF NOT EXISTS dbmodel_tml_analysis_task_id_idx ON dbmodel_task_message_log_analysis (task_id)")
        cr.execute("CREATE INDEX IF NOT EXISTS dbmodel_tml_analysis_task_date_idx ON dbmodel_task_message_log_analysis (task_date)")
        cr.execute("ANALYZE dbmodel_task_message_log_analysis")
