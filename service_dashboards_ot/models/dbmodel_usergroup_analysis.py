# -*- coding: utf-8 -*-
from odoo import models, fields, tools, api
from lxml import etree

class DbModelCallCenterAnalysis(models.Model):
    _name = "dbmodel.usergroup.analysis"
    _description = "DBM User Group Wise Analysis"
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

    @api.model
    def _get_default_tree_view(self):
        node = etree.Element("tree", string=self._description)
        exclude_fields = [
            "display_name",
            "complete_name",
            "create_uid",
            "create_date",
            "write_uid",
            "write_date",
            "__last_update",
        ]
        for field_name in self._fields:
            if field_name not in exclude_fields:
                field_node = etree.SubElement(node, "field", name=field_name)
                if self._fields[field_name].type == "many2one":
                    field_node.set("options", "{'no_open': True}")
        return node

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
