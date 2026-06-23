# -*- coding: utf-8 -*-
from odoo import models, fields, tools, api
from lxml import etree

class DbModelCallCenterAnalysis(models.Model):
    _name = "dbmodel.usergroup.analysis.ct"
    _description = "DBM User Group Wise Analysis (CT)"
    _table = "dbmodel_usergroup_analysis_ct"
    _auto = False

    # The 'id' field is automatically added by Odoo, mapped to our row_number() OVER () AS id

    request_id = fields.Many2one("machine.repair.support", string="Request ID", readonly=True)
    company_id = fields.Char(string="Company ID", readonly=True)
    user = fields.Many2one("res.users", string="User Name", readonly=True)
    user_login = fields.Char(string="User Login", readonly=True)
    user_group = fields.Char(string="User Group", readonly=True)
    task_id = fields.Char(string="Task ID", readonly=True)
    task_name = fields.Char(string="Task Name", readonly=True)
    
    service_request_state = fields.Char(string="Service Request State", readonly=True)
    team_id = fields.Char(string="Team ID", readonly=True)
    team_name = fields.Char(string="Team Name", readonly=True)
    service_type_id = fields.Many2one("service.nature", string="Service Type", readonly=True)
    work_center_group_id = fields.Many2one("work.center.group", string="Work Center Group", readonly=True)
    work_center_id = fields.Many2one("work.center.location", string="Work Location", readonly=True)
    request_date = fields.Datetime(string="Request Date", readonly=True)

    is_my_record = fields.Boolean(
        string="Is My Record",
        compute="_compute_is_my_record",
        search="_search_is_my_record"
    )

    @api.depends("user")
    def _compute_is_my_record(self):
        for rec in self:
            rec.is_my_record = (rec.user.id == self.env.uid) if rec.user else False

    def _search_is_my_record(self, operator, value):
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('user', '=', self.env.uid)]
        return [('user', '!=', self.env.uid)]

    # Canonical role -> field list, shared across every CT analysis model.
    # Fields absent on this model are dropped by the ``self._fields`` check.
    _DR_ROLE_FIELD_MAP = {
        'Parts': [
            'task_id', 'qty', 'parts_revenue',
            'warranty_spareparts_revenue', 'job_card_status', 'action_status',
        ],
        'Coordinator': [
            'task_id', 'user_id', 'job_card_status',
            'total_revenue', 'labour_revenue', 'parts_revenue',
            'rtat_hours', 'technician_travel_hours', 'onhold_hours',
            'total_worked_hours', 'action_status', 'service_created_datetime',
        ],
        'Call Center': [
            'task_id', 'job_card_status', 'action_status',
            'service_created_datetime', 'work_center_id', 'work_center_group_id',
        ],
        'Technician': [
            'task_id', 'job_card_status',
            'technician_travel_hours', 'total_worked_hours', 'action_status',
        ],
    }

    @api.model
    def _get_logged_user_role_groups(self):
        """Same role-detection as ``dbmodel.jobcards.analysis.ct`` /
        ``dbmodel.task.message.log.analysis.ct`` so this model can use the
        same role-keyed column map.
        """
        self.env.cr.execute(
            """
            SELECT DISTINCT
                CASE
                    WHEN imd.name = 'group_parts_user' THEN 'Parts'
                    WHEN imd.name = 'group_technical_allocation_user' THEN 'Coordinator'
                    WHEN imd.name = 'group_call_center_user' THEN 'Call Center'
                    WHEN imd.name = 'group_job_card_mobile_user' THEN 'Technician'
                END AS user_role
            FROM res_users u
            JOIN res_groups_users_rel rel ON rel.uid = u.id
            JOIN ir_model_data imd ON imd.res_id = rel.gid
            WHERE u.id = %s
              AND imd.module = 'machine_repair_management'
              AND imd.name IN (
                  'group_parts_user', 'group_technical_allocation_user',
                  'group_call_center_user', 'group_job_card_mobile_user'
              )
            """,
            (self.env.uid,),
        )
        return [row[0] for row in self.env.cr.fetchall() if row[0]]

    @api.model
    def _get_default_tree_view(self):
        # ``action=action_open_request_list type=object`` makes a row click
        # bypass the analysis-model form and jump straight to the underlying
        # ``machine.repair.support`` record.
        node = etree.Element(
            "tree",
            string=self._description,
            action="action_open_request_list",
            type="object",
            create="0",
            edit="0",
            delete="0",
        )
        roles = self._get_logged_user_role_groups()
        visible_fields = set()
        for role in roles:
            visible_fields.update(self._DR_ROLE_FIELD_MAP.get(role, []))

        exclude_fields = {
            'id', 'display_name', 'complete_name',
            'create_uid', 'create_date', 'write_uid', 'write_date',
            '__last_update', 'active',
        }
        if visible_fields:
            # Preserve the canonical (Coordinator) ordering so columns line up
            # across roles and models.
            render_fields = [
                f for f in self._DR_ROLE_FIELD_MAP['Coordinator']
                if f in visible_fields
                and f in self._fields
                and f not in exclude_fields
            ]
        else:
            render_fields = [
                f for f in self._fields if f not in exclude_fields
            ]

        for field_name in render_fields:
            field_node = etree.SubElement(node, "field", name=field_name)
            if self._fields[field_name].type == "many2one":
                field_node.set("options", "{'no_open': True}")
            if field_name.endswith("_hours"):
                field_node.set("widget", "float_time")
        return node

    def fields_view_get(self, view_id=None, view_type='tree', toolbar=False,
                         submenu=False):
        res = super().fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu,
        )
        if view_type == 'tree':
            node = self._get_default_tree_view()
            res['arch'] = etree.tostring(node, encoding='unicode')
        return res

    def action_open_request_list(self):
        """Open the underlying ``machine.repair.support`` form, preserving
        breadcrumbs, so the drill-down lands on the actual service request
        instead of the read-only analysis-model form.
        """
        self.ensure_one()
        if not self.request_id:
            return False
        action = self.env["ir.actions.actions"]._for_xml_id(
            "machine_repair_management.action_machine_repair_support"
        )
        form_view = self.env.ref(
            "machine_repair_management.machine_repair_support_form_view",
            raise_if_not_found=False,
        )
        action.update({
            'res_id': self.request_id.id,
            'view_mode': 'form',
            'views': [(form_view.id if form_view else False, 'form')],
            'target': 'current',
            'context': dict(self.env.context),
        })
        return action

    def get_formview_action(self, access_uid=None):
        """Direct form access (URL / breadcrumb back) should also bypass the
        intermediate analysis-model form and land on the source record.
        """
        self.ensure_one()
        action = self.action_open_request_list()
        if action:
            return action
        return super().get_formview_action(access_uid=access_uid)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    u.id AS user,
                    u.login AS user_login,

                    grp.user_group AS user_group,

                    mrs.task_id AS task_id,
                    mrs.name AS task_name,

                    mrs.id AS id, 
                    mrs.id AS request_id,
                    mrs.company_id AS company_id,
                    mrs.team_id AS team_id,
                    mst.name AS team_name,
                    mst.service_type_id AS service_type_id,
                    mrs.work_center_group_id AS work_center_group_id,
                    mst.work_center_id AS work_center_id,

                    mrs.service_request_state AS service_request_state,
                    mrs.request_date AS request_date
                FROM 
                    machine_repair_support mrs
                    LEFT JOIN machine_support_team mst ON mst.id = mrs.team_id
                    LEFT JOIN res_users u ON u.id = mrs.create_uid
                    LEFT JOIN (
                        SELECT 
                            u.id as uid, 
                            STRING_AGG(DISTINCT
                                case 
                                    when imd.name = 'group_parts_user' then 'parts'
                                    when imd.name = 'group_call_center_user' then 'call-center'
                                    when imd.name = 'group_technical_allocation_user' then 'co-ordinator'
                                    when imd.name = 'group_job_card_mobile_user' then 'mobile'
                                    else null
                                end, ', '
                            ) as user_group
                        FROM res_users u 
                        JOIN res_groups_users_rel rel ON rel.uid = u.id 
                        JOIN ir_model_data imd ON imd.res_id = rel.gid
                        WHERE imd.module = 'machine_repair_management' 
                        GROUP BY u.id
                    ) grp ON grp.uid = mrs.create_uid
                WHERE
                    grp.user_group IS NOT NULL
                    and mrs.task_id is not null
                ORDER BY
                    user_group,
                    user,
                    task_id
            )
        """
            % (self._table,)
        )
