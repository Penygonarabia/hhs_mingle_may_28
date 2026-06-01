# models/project_task_message_log.py
from odoo import models, fields, tools, api
from odoo.tools import drop_view_if_exists

class ProjectTaskMessageLog(models.Model):
    _name = 'project.task.message.log'
    _description = 'Project Task Message Log'
    _auto = False  # use SQL view, not a real table

    date = fields.Datetime('Date')
    author = fields.Char('Author')
    serial_no = fields.Char('Serial No')
    # field_id = fields.Many2one('ir.model.fields', 'Field', deprecated=False)
    author_id = fields.Many2one('res.partner', 'Author Partner')
    old_value = fields.Char('Old Value')
    new_value = fields.Char('Status')
    model = fields.Char('Model')
    res_id = fields.Integer('Resource ID')
    user_id = fields.Many2one('res.users',string = "User")
    # In project.task.message.log model
    # These resolve automatically via user_id — no extra SQL needed for ORM
    work_center_group_ids = fields.Many2many(
        'work.center.group',
        'user_work_center_group_rel',
        'user_id',
        'work_center_group_id',
        string="Work Center Group"
    )
    user_rights_roles_ids = fields.Many2many(
        'dashboard.user.rights',
        'user_dashboard_rights_rel',
        'user_id',
        'dashboard_rights_id',
        string="User Selection"
    )
    dashboard_type_selection = fields.Selection([
        ('individual', 'Individual'),
        ('manager', 'Manager')
    ], string="User Roles")
        
        

    #### working code commented on April 27 2026 commented by Vijaya Bhaskar because they need New State in the status
    # def init(self):
    #     drop_view_if_exists(self.env.cr, 'project_task_message_log')
    #     self.env.cr.execute("""
    #         CREATE OR REPLACE VIEW project_task_message_log AS
    #         SELECT
    #             -- Best option: Simple unique sequential ID (no overflow/collision risk)
    #             ROW_NUMBER() OVER (ORDER BY mm.res_id ASC, log.create_date ASC, log.id ASC) AS id,
    #
    #             -- Alternative composite if you prefer (ultra-safe):
    #             -- (mm.res_id::bigint * 1000000000000 + log.id) AS id,
    #
    #             ROW_NUMBER() OVER (
    #                 PARTITION BY mm.res_id
    #                 ORDER BY log.create_date ASC, log.id ASC
    #             )::text AS serial_no,
    #
    #             log.create_date AS date,
    #             rp.name AS author,
    #             mm.author_id AS author_id,
    #             ru.id AS user_id,
    #
    #             COALESCE(
    #                 log.old_value_char,
    #                 log.old_value_text,
    #                 log.old_value_datetime::text,
    #                 CAST(log.old_value_integer AS text),
    #                 CAST(log.old_value_float AS text)
    #             ) AS old_value,
    #
    #             COALESCE(
    #                 log.new_value_char,
    #                 log.new_value_text,
    #                 log.new_value_datetime::text,
    #                 CAST(log.new_value_integer AS text),
    #                 CAST(log.new_value_float AS text)
    #             ) AS new_value,
    #
    #             ff.name AS field_name,
    #             mm.model AS model,
    #             mm.res_id AS res_id
    #
    #         FROM mail_tracking_value log
    #         JOIN mail_message mm ON mm.id = log.mail_message_id
    #         LEFT JOIN res_partner rp ON rp.id = mm.author_id
    #         LEFT JOIN res_users ru ON ru.partner_id = rp.id
    #         LEFT JOIN ir_model_fields ff ON ff.id = log.field_id
    #
    #         WHERE mm.model = 'project.task'
    #           AND ff.name = 'job_state'
    #
    #           -- Filter out non-changes and empty values
    #           AND (
    #               COALESCE(log.old_value_char, log.old_value_text, log.old_value_datetime::text,
    #                        CAST(log.old_value_integer AS text), CAST(log.old_value_float AS text))
    #               IS DISTINCT FROM
    #               COALESCE(log.new_value_char, log.new_value_text, log.new_value_datetime::text,
    #                        CAST(log.new_value_integer AS text), CAST(log.new_value_float AS text))
    #           )
    #     """)
        
    # def init(self):
    #     drop_view_if_exists(self.env.cr, 'project_task_message_log')
    #
    #     self.env.cr.execute("""
    #         CREATE OR REPLACE VIEW project_task_message_log AS (
    #
    #             SELECT
    #                 ROW_NUMBER() OVER (ORDER BY combined.res_id, combined.date) AS id,
    #
    #                 ROW_NUMBER() OVER (
    #                     PARTITION BY combined.res_id
    #                     ORDER BY combined.date
    #                 )::text AS serial_no,
    #
    #                 combined.date,
    #                 combined.author,
    #                 combined.author_id,
    #                 combined.user_id,
    #                 combined.old_value,
    #                 combined.new_value,
    #                 combined.model,
    #                 combined.res_id
    #
    #             FROM (
    #
    #                 -- ✅ FIXED: ONLY ONE TASK CREATED (wrapped properly)
    #                 SELECT *
    #                 FROM (
    #                     SELECT DISTINCT ON (mm.res_id)
    #                         mm.create_date AS date,
    #                         rp.name AS author,
    #                         mm.author_id AS author_id,
    #                         ru.id AS user_id,
    #
    #                         NULL AS old_value,
    #                         'New' AS new_value,
    #
    #                         mm.model,
    #                         mm.res_id
    #
    #                     FROM mail_message mm
    #                     LEFT JOIN res_partner rp ON rp.id = mm.author_id
    #                     LEFT JOIN res_users ru ON ru.partner_id = rp.id
    #
    #                     WHERE mm.model = 'project.task'
    #
    #                     ORDER BY mm.res_id, mm.create_date ASC
    #                 ) created_logs
    #
    #
    #                 UNION ALL
    #
    #
    #                 -- ✅ STATUS TRACKING
    #                 SELECT
    #                     log.create_date AS date,
    #                     rp.name AS author,
    #                     mm.author_id AS author_id,
    #                     ru.id AS user_id,
    #
    #                     COALESCE(
    #                         log.old_value_char,
    #                         log.old_value_text,
    #                         log.old_value_datetime::text,
    #                         CAST(log.old_value_integer AS text),
    #                         CAST(log.old_value_float AS text)
    #                     ) AS old_value,
    #
    #                     COALESCE(
    #                         log.new_value_char,
    #                         log.new_value_text,
    #                         log.new_value_datetime::text,
    #                         CAST(log.new_value_integer AS text),
    #                         CAST(log.new_value_float AS text)
    #                     ) AS new_value,
    #
    #                     mm.model,
    #                     mm.res_id
    #
    #                 FROM mail_tracking_value log
    #                 JOIN mail_message mm ON mm.id = log.mail_message_id
    #                 LEFT JOIN res_partner rp ON rp.id = mm.author_id
    #                 LEFT JOIN res_users ru ON ru.partner_id = rp.id
    #                 LEFT JOIN ir_model_fields ff ON ff.id = log.field_id
    #
    #                 WHERE mm.model = 'project.task'
    #                 AND ff.name = 'job_state'
    #
    #                 AND (
    #                     COALESCE(log.old_value_char, log.old_value_text, log.old_value_datetime::text,
    #                              CAST(log.old_value_integer AS text), CAST(log.old_value_float AS text))
    #                     IS DISTINCT FROM
    #                     COALESCE(log.new_value_char, log.new_value_text, log.new_value_datetime::text,
    #                              CAST(log.new_value_integer AS text), CAST(log.new_value_float AS text))
    #                 )
    #
    #             ) AS combined
    #
    #             ORDER BY combined.res_id, combined.date
    #         )
    #     """)
    
    def init(self):
        drop_view_if_exists(self.env.cr, 'project_task_message_log')

        # Check if the relation tables and fields added by dashboard_user_rights_roles exist in the database.
        # This is necessary because machine_repair_management is loaded before dashboard_user_rights_roles,
        # so during installation these tables do not yet exist, which would otherwise crash with an UndefinedTable error.
        self.env.cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'user_work_center_group_rel'
            ) AND EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'user_dashboard_rights_rel'
            ) AND EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'res_users' AND column_name = 'dashboard_type_selection'
            )
        """)
        has_relations = self.env.cr.fetchone()[0]

        if has_relations:
            self.env.cr.execute("""
                CREATE OR REPLACE VIEW project_task_message_log AS (

                    SELECT
                        combined.id AS id,

                        ROW_NUMBER() OVER (
                            PARTITION BY combined.res_id
                            ORDER BY combined.date
                        )::text AS serial_no,

                        combined.date,
                        combined.author,
                        combined.author_id,
                        combined.user_id,
                        combined.old_value,
                        combined.new_value,
                        combined.model,
                        combined.res_id,

                        ru_full.dashboard_type_selection,

                        COALESCE(wcg.work_center_group_ids, ARRAY[]::integer[]) AS work_center_group_ids,
                        COALESCE(urr.user_rights_roles_ids, ARRAY[]::integer[]) AS user_rights_roles_ids

                    FROM (

                        -- TASK CREATED LOG (id = mm.id * 2)
                        SELECT *
                        FROM (
                            SELECT DISTINCT ON (mm.res_id)
                                (mm.id * 2)     AS id,
                                mm.create_date  AS date,
                                rp.name         AS author,
                                mm.author_id    AS author_id,
                                ru.id           AS user_id,
                                NULL            AS old_value,
                                'New'           AS new_value,
                                mm.model,
                                mm.res_id

                            FROM mail_message mm
                            LEFT JOIN res_partner rp ON rp.id = mm.author_id
                            LEFT JOIN res_users ru   ON ru.partner_id = rp.id

                            WHERE mm.model = 'project.task'
                            ORDER BY mm.res_id, mm.create_date ASC
                        ) created_logs

                        UNION ALL

                        -- STATUS TRACKING LOG (id = log.id * 2 + 1)
                        SELECT
                            (log.id * 2 + 1) AS id,
                            log.create_date  AS date,
                            rp.name          AS author,
                            mm.author_id     AS author_id,
                            ru.id            AS user_id,

                            COALESCE(
                                log.old_value_char,
                                log.old_value_text,
                                log.old_value_datetime::text,
                                CAST(log.old_value_integer AS text),
                                CAST(log.old_value_float AS text)
                            ) AS old_value,

                            COALESCE(
                                log.new_value_char,
                                log.new_value_text,
                                log.new_value_datetime::text,
                                CAST(log.new_value_integer AS text),
                                CAST(log.new_value_float AS text)
                            ) AS new_value,

                            mm.model,
                            mm.res_id

                        FROM mail_tracking_value log
                        JOIN mail_message mm         ON mm.id = log.mail_message_id
                        LEFT JOIN res_partner rp     ON rp.id = mm.author_id
                        LEFT JOIN res_users ru       ON ru.partner_id = rp.id
                        LEFT JOIN ir_model_fields ff ON ff.id = log.field_id

                        WHERE mm.model = 'project.task'
                        AND ff.name = 'job_state'
                        AND (
                            COALESCE(log.old_value_char, log.old_value_text, log.old_value_datetime::text,
                                     CAST(log.old_value_integer AS text), CAST(log.old_value_float AS text))
                            IS DISTINCT FROM
                            COALESCE(log.new_value_char, log.new_value_text, log.new_value_datetime::text,
                                     CAST(log.new_value_integer AS text), CAST(log.new_value_float AS text))
                        )

                    ) AS combined

                    LEFT JOIN res_users ru_full
                        ON ru_full.id = combined.user_id

                    LEFT JOIN (
                        SELECT
                            user_id,
                            ARRAY_AGG(work_center_group_id) AS work_center_group_ids
                        FROM user_work_center_group_rel
                        GROUP BY user_id
                    ) wcg ON wcg.user_id = combined.user_id

                    LEFT JOIN (
                        SELECT
                            user_id,
                            ARRAY_AGG(dashboard_rights_id) AS user_rights_roles_ids
                        FROM user_dashboard_rights_rel
                        GROUP BY user_id
                    ) urr ON urr.user_id = combined.user_id
                )
            """)
        else:
            self.env.cr.execute("""
                CREATE OR REPLACE VIEW project_task_message_log AS (

                    SELECT
                        combined.id AS id,

                        ROW_NUMBER() OVER (
                            PARTITION BY combined.res_id
                            ORDER BY combined.date
                        )::text AS serial_no,

                        combined.date,
                        combined.author,
                        combined.author_id,
                        combined.user_id,
                        combined.old_value,
                        combined.new_value,
                        combined.model,
                        combined.res_id,

                        NULL::varchar AS dashboard_type_selection,
                        ARRAY[]::integer[] AS work_center_group_ids,
                        ARRAY[]::integer[] AS user_rights_roles_ids

                    FROM (

                        -- TASK CREATED LOG (id = mm.id * 2)
                        SELECT *
                        FROM (
                            SELECT DISTINCT ON (mm.res_id)
                                (mm.id * 2)     AS id,
                                mm.create_date  AS date,
                                rp.name         AS author,
                                mm.author_id    AS author_id,
                                ru.id           AS user_id,
                                NULL            AS old_value,
                                'New'           AS new_value,
                                mm.model,
                                mm.res_id

                            FROM mail_message mm
                            LEFT JOIN res_partner rp ON rp.id = mm.author_id
                            LEFT JOIN res_users ru   ON ru.partner_id = rp.id

                            WHERE mm.model = 'project.task'
                            ORDER BY mm.res_id, mm.create_date ASC
                        ) created_logs

                        UNION ALL

                        -- STATUS TRACKING LOG (id = log.id * 2 + 1)
                        SELECT
                            (log.id * 2 + 1) AS id,
                            log.create_date  AS date,
                            rp.name          AS author,
                            mm.author_id     AS author_id,
                            ru.id            AS user_id,

                            COALESCE(
                                log.old_value_char,
                                log.old_value_text,
                                log.old_value_datetime::text,
                                CAST(log.old_value_integer AS text),
                                CAST(log.old_value_float AS text)
                            ) AS old_value,

                            COALESCE(
                                log.new_value_char,
                                log.new_value_text,
                                log.new_value_datetime::text,
                                CAST(log.new_value_integer AS text),
                                CAST(log.new_value_float AS text)
                            ) AS new_value,

                            mm.model,
                            mm.res_id

                        FROM mail_tracking_value log
                        JOIN mail_message mm         ON mm.id = log.mail_message_id
                        LEFT JOIN res_partner rp     ON rp.id = mm.author_id
                        LEFT JOIN res_users ru       ON ru.partner_id = rp.id
                        LEFT JOIN ir_model_fields ff ON ff.id = log.field_id

                        WHERE mm.model = 'project.task'
                        AND ff.name = 'job_state'
                        AND (
                            COALESCE(log.old_value_char, log.old_value_text, log.old_value_datetime::text,
                                     CAST(log.old_value_integer AS text), CAST(log.old_value_float AS text))
                            IS DISTINCT FROM
                            COALESCE(log.new_value_char, log.new_value_text, log.new_value_datetime::text,
                                     CAST(log.new_value_integer AS text), CAST(log.new_value_float AS text))
                        )

                    ) AS combined
                )
            """)
       
    # def init(self):
    #     """Create SQL view showing only job_state changes with serial numbers starting from 1 for each project.task"""
    #     tools.drop_view_if_exists(self._cr, 'project_task_message_log')
    #     self._cr.execute("""
    #         CREATE OR REPLACE VIEW project_task_message_log AS
    #         SELECT
    #             -- Unique and stable id across all tasks
    #             CONCAT(mm.res_id, '_', log.id) AS id,
    #             -- Serial number restarts per task
    #             ROW_NUMBER() OVER (
    #                 PARTITION BY mm.res_id
    #                 ORDER BY log.create_date ASC, log.id ASC
    #             )::text AS serial_no,
    #             log.create_date AS date,
    #             rp.name AS author,
    #             mm.author_id AS author_id,
    #             COALESCE(log.old_value_char, log.old_value_text, CAST(log.old_value_integer AS TEXT)) AS old_value,
    #             COALESCE(log.new_value_char, log.new_value_text, CAST(log.new_value_integer AS TEXT)) AS new_value,
    #             ff.name AS field_name,
    #             mm.model AS model,
    #             mm.res_id AS res_id
    #         FROM mail_tracking_value log
    #         JOIN mail_message mm ON mm.id = log.mail_message_id
    #         LEFT JOIN res_partner rp ON rp.id = mm.author_id
    #         LEFT JOIN ir_model_fields ff ON ff.id = log.field_id
    #         WHERE mm.model = 'project.task'
    #           -- ✅ Only show logs related to the job_state field
    #           AND ff.name = 'job_state'
    #           -- ✅ Only include actual changes where old and new values differ and are not null
    #           AND (
    #               COALESCE(log.old_value_char, log.old_value_text, CAST(log.old_value_integer AS TEXT)) IS NOT NULL
    #               OR COALESCE(log.new_value_char, log.new_value_text, CAST(log.new_value_integer AS TEXT)) IS NOT NULL
    #           )
    #           AND (
    #               COALESCE(log.old_value_char, log.old_value_text, CAST(log.old_value_integer AS TEXT))
    #               IS DISTINCT FROM
    #               COALESCE(log.new_value_char, log.new_value_text, CAST(log.new_value_integer AS TEXT))
    #           )
    #         ORDER BY mm.res_id, log.create_date ASC, log.id ASC
    #     """)

    # @api.model
    def get_message_logs(self):
        """Return serial-numbered message logs for a specific task"""
        return self.search([('res_id', '=', self.id)]).read([
            'serial_no',
            'date',
            'author',
            'author_id',
            'old_value',
            'new_value',
            'model',
            'res_id'
        ])
