# -*- coding: utf-8 -*-
"""Direct-table query engine backing "PBI Dashboards > Service Dashboards".

Reproduces the SQL/logic of the three ``dbmodel.*.ct`` view models in
``service_dashboards_ct`` (see that module's ``models/dbmodel_*.py``)
against the underlying direct tables (``project_task``,
``machine_repair_support``, ``mail_message``/``mail_tracking_value``)
instead of depending on those views or on ``ks_dashboard_ninja``. Every
board/chart-item config in ``service_config.py`` is executed through the
generic runners at the bottom of this file — there is no per-board SQL.
"""
import itertools

from .service_config import ChartItemConfig, BoardConfig, GroupByConfig

# ---------------------------------------------------------------------
# param binder — every WHERE fragment below gets its own uniquely-named
# psycopg2 parameter (dashboard queries compose many small fragments from
# board scope + item domain + accumulated drill-path clauses, so plain
# %s positional params would drift the moment two fragments are combined
# in a different order than they were built).
# ---------------------------------------------------------------------
class ParamBinder:
    def __init__(self):
        self._counter = itertools.count()
        self.params = {}

    def bind(self, value):
        name = f"p{next(self._counter)}"
        self.params[name] = value
        return f"%({name})s"


# ---------------------------------------------------------------------
# jobcards CTE — ports service_dashboards_ct/models/dbmodel_jobcards_analysis.py's
# init() SQL (the dbmodel_jobcards_analysis_ct VIEW) against project_task
# directly, scoped to a date range up front so every downstream query only
# ever scans the rows it needs.
# ---------------------------------------------------------------------
_JOBCARDS_CTE_SQL = """
    jobcards AS (
        WITH user_role_map AS (
            SELECT
                u.id AS uid,
                STRING_AGG(DISTINCT
                    CASE
                        WHEN imd.name = 'group_parts_user' THEN 'Parts'
                        WHEN imd.name = 'group_technical_allocation_user' THEN 'Coordinator'
                        WHEN imd.name = 'group_call_center_user' THEN 'Call Center'
                        WHEN imd.name = 'group_job_card_mobile_user' THEN 'Technician'
                        ELSE NULL
                    END, ', '
                ) AS user_role
            FROM res_users u
            JOIN res_groups_users_rel rel ON rel.uid = u.id
            JOIN ir_model_data imd ON imd.res_id = rel.gid
            WHERE imd.module = 'machine_repair_management'
              AND imd.name IN (
                    'group_parts_user', 'group_technical_allocation_user',
                    'group_call_center_user', 'group_job_card_mobile_user'
                )
            GROUP BY u.id
        )
        SELECT
            pt.id AS task_id,
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
            COALESCE(CASE WHEN pt.onhold_hours::text LIKE '%%:%%' THEN (split_part(pt.onhold_hours::text, ':', 1)::float + split_part(pt.onhold_hours::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.onhold_hours::text, '')::float END, 0) AS onhold_hours,
            COALESCE(CASE WHEN pt.cstneedquote_hours::text LIKE '%%:%%' THEN (split_part(pt.cstneedquote_hours::text, ':', 1)::float + split_part(pt.cstneedquote_hours::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.cstneedquote_hours::text, '')::float END, 0) AS cstneedquote_hours,
            COALESCE(CASE WHEN pt.total_worked_hours::text LIKE '%%:%%' THEN (split_part(pt.total_worked_hours::text, ':', 1)::float + split_part(pt.total_worked_hours::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.total_worked_hours::text, '')::float END, 0) AS total_worked_hours,
            COALESCE(CASE WHEN pt.expected_completion_hours::text LIKE '%%:%%' THEN (split_part(pt.expected_completion_hours::text, ':', 1)::float + split_part(pt.expected_completion_hours::text, ':', 2)::float / 60.0) ELSE NULLIF(pt.expected_completion_hours::text, '')::float END, 0) AS expected_completion_hours,
            pt.service_created_datetime AS service_created_datetime,
            pt.active AS active
        FROM project_task pt

        LEFT JOIN (
            SELECT
                pl.project_task_id AS task_id,
                SUM(pl.qty) AS total_qty,
                SUM(pl.total) AS total_revenue,
                SUM(CASE WHEN (pp.default_code LIKE '%%SERVIC%%' OR pp.default_code LIKE '%%INSPECTION%%') THEN pl.total ELSE 0 END) AS labour_revenue,
                SUM(CASE WHEN (pp.default_code NOT LIKE '%%SERVIC%%' AND pp.default_code NOT LIKE '%%INSPECTION%%') THEN pl.total ELSE 0 END) AS parts_revenue,
                SUM(CASE WHEN ip.value_float > 0 THEN (pl.qty * ip.value_float) ELSE 0 END) AS warranty_spareparts_revenue
            FROM product_lines pl
            JOIN product_product pp ON pp.id = pl.product_id
            LEFT JOIN LATERAL (
                SELECT value_float FROM ir_property
                WHERE type = 'float' AND name = 'standard_price'
                  AND res_id = 'product.product,' || pl.product_id
                LIMIT 1
            ) ip ON pl.under_warranty_bool = true
            GROUP BY pl.project_task_id
        ) pa ON pa.task_id = pt.id

        LEFT JOIN (
            SELECT DISTINCT ON (work_center_location_id) work_center_location_id, res_users_id
            FROM res_users_work_center_location_rel
        ) um ON pt.work_center_id = um.work_center_location_id
        LEFT JOIN res_users ru ON ru.id = um.res_users_id

        LEFT JOIN user_role_map ug_tech ON ug_tech.uid = pt.technician_id
        LEFT JOIN user_role_map ug_ru ON ug_ru.uid = ru.id
        LEFT JOIN user_role_map ug_create ON ug_create.uid = pt.create_uid

        WHERE pt.active = true
          AND pt.service_created_datetime BETWEEN %(date_from)s AND %(date_to)s
    )
"""

# DBM-vocabulary field name -> real jobcards CTE column. 1:1 for everything
# except the two search-only booleans, which become callables producing a
# custom WHERE fragment (mirroring dbmodel_jobcards_analysis.py's
# _search_is_user_work_location/_search_is_my_user_group).
JOBCARDS_FIELD_MAP = {
    "task_id": "task_id", "user_id": "user_id", "default_work_location": "default_work_location",
    "service_warranty_id": "service_warranty_id", "work_center_group_id": "work_center_group_id",
    "work_center_id": "work_center_id", "technician_id": "technician_id", "scheduled_uid": "scheduled_uid",
    "closed_jobcard_user_id": "closed_jobcard_user_id", "job_card_status": "job_card_status",
    "action_status": "action_status", "service_created_datetime": "service_created_datetime",
    "total_worked_hours": "total_worked_hours",
}


# ---------------------------------------------------------------------
# usergroup CTE — ports service_dashboards_ct/models/dbmodel_usergroup_analysis.py's
# init() SQL (the dbmodel_usergroup_analysis_ct VIEW) against
# machine_repair_support/machine_support_team directly. One row per
# machine.repair.support request created by a user in one of the 4
# tracked security groups (only "Service Analysis (CC)" uses this source).
# ---------------------------------------------------------------------
_USERGROUP_CTE_SQL = """
    usergroup AS (
        SELECT
            mrs.id AS request_id,
            u.id AS user_id,
            grp.user_group AS user_group,
            mrs.task_id AS task_id,
            mrs.team_id AS team_id,
            mst.service_type_id AS service_type_id,
            mrs.work_center_group_id AS work_center_group_id,
            mst.work_center_id AS work_center_id,
            mrs.service_request_state AS service_request_state,
            mrs.request_date AS request_date
        FROM machine_repair_support mrs
        LEFT JOIN machine_support_team mst ON mst.id = mrs.team_id
        LEFT JOIN res_users u ON u.id = mrs.create_uid
        LEFT JOIN (
            SELECT
                u.id AS uid,
                STRING_AGG(DISTINCT
                    CASE
                        WHEN imd.name = 'group_parts_user' THEN 'parts'
                        WHEN imd.name = 'group_call_center_user' THEN 'call-center'
                        WHEN imd.name = 'group_technical_allocation_user' THEN 'co-ordinator'
                        WHEN imd.name = 'group_job_card_mobile_user' THEN 'mobile'
                        ELSE NULL
                    END, ', '
                ) AS user_group
            FROM res_users u
            JOIN res_groups_users_rel rel ON rel.uid = u.id
            JOIN ir_model_data imd ON imd.res_id = rel.gid
            WHERE imd.module = 'machine_repair_management'
            GROUP BY u.id
        ) grp ON grp.uid = mrs.create_uid
        WHERE grp.user_group IS NOT NULL
          AND mrs.task_id IS NOT NULL
          AND mrs.request_date BETWEEN %(date_from)s AND %(date_to)s
    )
"""

USERGROUP_FIELD_MAP = {
    "user_id": "user_id", "user_group": "user_group", "task_id": "task_id",
    "team_id": "team_id", "service_type_id": "service_type_id",
    "work_center_group_id": "work_center_group_id", "work_center_id": "work_center_id",
    "service_request_state": "service_request_state", "request_date": "request_date",
}


# ---------------------------------------------------------------------
# message_log CTE — ports service_dashboards_ct/models/dbmodel_project_task_message_log.py's
# init() SQL (a MATERIALIZED VIEW there, for the 100k+-row mail_message/
# mail_tracking_value scan) against mail_message/mail_tracking_value
# directly, computed inline per-request instead of persisted — see
# service_config.py's module docstring / the plan: escalate to a real
# materialized-view model only if this proves too slow under real load.
# One row per status TRANSITION on a project.task (synthetic "New" row
# from its first mail_message, then one row per job_state change).
#
# Two source-vocabulary differences from the DBM view, both deliberate:
#   - user_role here is derived the SAME WAY jobcards' user_role is
#     (security-group membership of the message's AUTHOR), not via the
#     dbmodel_jobcards_analysis.py user_role_id -> "dashboard.user.rights"
#     path — that model has no table on this DB (added to
#     machine_repair_management's source after the last -u that would
#     have created it), so ks_dashboard_ninja's own `user_role in [6/7/8]`
#     numeric-id domains are meaningless to replicate literally. Board
#     configs here filter on the resolved role NAME instead (e.g.
#     ("user_role", "=", "Coordinator")).
#   - The hour-family columns (technician_travel_hours, onhold_hours,
#     etc.) are NOT ported — none of the 15 boards' chart configs read
#     them off this source (the boards that show hours read them off the
#     jobcards source instead, which already has service-provider
#     "hours per task" without the multiplication-across-transition-rows
#     problem message_log has).
# ---------------------------------------------------------------------
_MESSAGE_LOG_CTE_SQL = """
    message_log AS (
        WITH src AS (
            (SELECT DISTINCT ON (mm.res_id)
                mm.create_date AS ptml_date,
                mm.author_id AS ptml_author_id,
                NULL::text AS ptml_old_value,
                'New'::text AS ptml_new_value,
                mm.res_id AS ptml_res_id
            FROM mail_message mm
            WHERE mm.model = 'project.task'
              AND mm.create_date BETWEEN %(date_from)s AND %(date_to)s
            ORDER BY mm.res_id, mm.create_date ASC)
            UNION ALL
            SELECT
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
              AND log.create_date BETWEEN %(date_from)s AND %(date_to)s
              AND (COALESCE(log.old_value_char, log.old_value_text, log.old_value_datetime::text,
                            CAST(log.old_value_integer AS text), CAST(log.old_value_float AS text))
                   IS DISTINCT FROM
                   COALESCE(log.new_value_char, log.new_value_text, log.new_value_datetime::text,
                            CAST(log.new_value_integer AS text), CAST(log.new_value_float AS text)))
        ),
        role_map AS (
            SELECT
                u.id AS uid,
                STRING_AGG(DISTINCT
                    CASE
                        WHEN imd.name = 'group_parts_user' THEN 'Parts'
                        WHEN imd.name = 'group_technical_allocation_user' THEN 'Coordinator'
                        WHEN imd.name = 'group_call_center_user' THEN 'Call Center'
                        WHEN imd.name = 'group_job_card_mobile_user' THEN 'Technician'
                        ELSE NULL
                    END, ', '
                ) AS user_role
            FROM res_users u
            JOIN res_groups_users_rel rel ON rel.uid = u.id
            JOIN ir_model_data imd ON imd.res_id = rel.gid
            WHERE imd.module = 'machine_repair_management'
              AND imd.name IN ('group_parts_user', 'group_technical_allocation_user',
                                'group_call_center_user', 'group_job_card_mobile_user')
            GROUP BY u.id
        )
        SELECT
            ru.id AS user_id,
            rm.user_role AS user_role,
            wcr.work_center_group_id AS region,
            um.work_center_location_id AS city,
            src.ptml_res_id AS task_id,
            src.ptml_old_value AS ptml_initial_taskstatus,
            src.ptml_new_value AS ptml_final_taskstatus,
            src.ptml_date AS task_date,
            COALESCE(src.ptml_old_value || ' >> ' || src.ptml_new_value, src.ptml_new_value) AS status_transition
        FROM src
        INNER JOIN project_task pt ON pt.id = src.ptml_res_id AND pt.active = true
        LEFT JOIN res_partner rp ON rp.id = src.ptml_author_id
        LEFT JOIN res_users ru ON ru.partner_id = rp.id
        LEFT JOIN role_map rm ON rm.uid = ru.id
        LEFT JOIN (
            SELECT DISTINCT ON (user_id) work_center_group_id, user_id FROM user_work_center_group_rel
        ) wcr ON wcr.user_id = ru.id
        LEFT JOIN (
            SELECT DISTINCT ON (work_center_location_id) work_center_location_id, res_users_id
            FROM res_users_work_center_location_rel
        ) um ON pt.work_center_id = um.work_center_location_id
    )
"""

MESSAGE_LOG_FIELD_MAP = {
    "task_id": "task_id", "user_id": "user_id", "region": "region", "city": "city",
    "ptml_final_taskstatus": "ptml_final_taskstatus", "ptml_initial_taskstatus": "ptml_initial_taskstatus",
    "task_date": "task_date", "status_transition": "status_transition", "user_role": "user_role",
    # Alias, not a distinct column: the jobcards/usergroup vocabulary name
    # for the same region concept ("region" here) — lets a board-level
    # region-filterable scope clause (service_main.py's _effective_board,
    # written once in jobcards vocabulary) apply uniformly to boards that
    # mix a message_log-source item in with jobcards-source items (CRD,
    # Parts), instead of erroring "unknown domain field".
    "work_center_group_id": "region",
}


# ---------------------------------------------------------------------
# promoter_showrooms CTE — backs "PBI Dashboards > Promoter Dashboards >
# Promoters"' "Employees Count By Region, City & Showroom" tile. One row
# per promoter.showroom (master-data table, not date-scoped — the CTE
# alias is "promoter_showrooms", plural, to avoid colliding with the real
# promoter_showroom table it selects from).
# ---------------------------------------------------------------------
_PROMOTER_SHOWROOMS_CTE_SQL = """
    promoter_showrooms AS (
        SELECT
            ps.id AS showroom_pk,
            ps.region_id AS region_id,
            ps.city AS city_id,
            ps.dealer_id AS dealer_id,
            ps.promoter_required AS promoter_required
        FROM promoter_showroom ps
    )
"""

PROMOTER_SHOWROOMS_FIELD_MAP = {
    "showroom_pk": "showroom_pk", "region_id": "region_id", "city_id": "city_id",
    "dealer_id": "dealer_id", "promoter_required": "promoter_required",
}


# ---------------------------------------------------------------------
# promoter_sales CTE — backs "Promoters"' 2 "Sales (Qty)" tiles. One row
# per promoter.showroom.sales entry, scoped to the dashboard's date range
# on date_time (region_id/city_id are already computed+stored columns on
# that model itself, no join needed).
# ---------------------------------------------------------------------
_PROMOTER_SALES_CTE_SQL = """
    promoter_sales AS (
        SELECT
            pss.id AS sales_id,
            pss.region_id AS region_id,
            pss.city_id AS city_id,
            pss.showroom AS showroom_id,
            pss.group_id AS group_id,
            pss.subgroup_id AS subgroup_id,
            pss.product_category_id AS franchise_id,
            pss.dealer_id AS dealer_id,
            pss.qty AS qty,
            pss.date_time AS date_time
        FROM promoter_showroom_sales pss
        WHERE pss.date_time BETWEEN %(date_from)s AND %(date_to)s
    )
"""

PROMOTER_SALES_FIELD_MAP = {
    "sales_id": "sales_id", "region_id": "region_id", "city_id": "city_id",
    "showroom_id": "showroom_id", "group_id": "group_id", "subgroup_id": "subgroup_id",
    "franchise_id": "franchise_id", "dealer_id": "dealer_id", "qty": "qty", "date_time": "date_time",
}


# ---------------------------------------------------------------------
# sales_comparison CTE — backs "Promoter - Sales Comparison". One row per
# sales.target record; target_qty/actual_qty already live side by side on
# that same model (promoter.showroom.sales.create/write/unlink keeps
# actual_qty in lockstep — see promoter/models/promoter_showroom_sales.py),
# so no join to promoter_showroom_sales is needed here. region/city are
# already plain, human-readable Char columns (related+stored off
# showroom_id), so no label-lookup join is needed for those two either.
# Scoped to the dashboard's date range by comparing the "YYYY-MM" period
# string lexicographically, which sorts chronologically since year is
# 4-digit and month is zero-padded.
# ---------------------------------------------------------------------
_SALES_COMPARISON_CTE_SQL = """
    sales_comparison AS (
        SELECT
            st.id AS target_id,
            st.region AS region,
            st.city AS city,
            (st.year || '-' || st.month) AS period,
            st.dealer_id AS dealer_id,
            st.showroom_id AS showroom_id,
            st.promoter_id AS promoter_id,
            st.target_qty AS target_qty,
            st.actual_qty AS actual_qty
        FROM sales_target st
        WHERE (st.year || '-' || st.month) BETWEEN
            to_char(%(date_from)s::date, 'YYYY-MM') AND to_char(%(date_to)s::date, 'YYYY-MM')
    )
"""

SALES_COMPARISON_FIELD_MAP = {
    "target_id": "target_id",
    # "sc_"-prefixed, not the bare "region"/"city" the message_log field
    # map above already uses as DBM-vocabulary keys (aliasing
    # work_center_group/work_center_location, a completely different
    # lookup) — _LABEL_LOOKUP is one shared dict keyed by field NAME
    # across every source, so reusing "region"/"city" here would silently
    # inherit that unrelated join instead of rendering these already-plain-
    # text columns as-is.
    "sc_region": "region", "sc_city": "city",
    "period": "period",
    "dealer_id": "dealer_id", "showroom_id": "showroom_id", "promoter_id": "promoter_id",
    "target_qty": "target_qty", "actual_qty": "actual_qty",
}


# ---------------------------------------------------------------------
# contracts CTE — backs "PBI Dashboards > Contract Dashboards > Contract
# Analysis", porting contract_dashboards/data/contracts_analysis_dashboard_data.xml's
# "Contract Analysis" ks_dashboard_ninja.board against subscription_contracts
# directly (no ks_dashboard_ninja or contract_dashboards module dependency).
# One row per subscription.contracts record, scoped to the dashboard's date
# range on date_start (the only ks_date_filter_field any of that board's 7
# items use). contract_amount/service_amount and the 6 preventive/
# corrective visit columns mirror contract_dashboards' own related=/
# compute=+store=True fields (amount_total/untaxed_amount and the
# entitlement_*/actual_*_count/balance_* fields already on
# sales_contract_and_recurring_invoices' subscription.contracts) — computed
# here directly instead of depending on contract_dashboards' mirror columns
# existing on this DB.
# ---------------------------------------------------------------------
_CONTRACTS_CTE_SQL = """
    contracts AS (
        SELECT
            sc.id AS contract_id,
            sc.name AS name,
            sc.partner_id AS partner_id,
            sc.work_center_group_id AS work_center_group_id,
            sc.work_center_id AS work_center_id,
            sc.sales_person_user_id AS sales_person_user_id,
            sc.contract_type AS contract_type,
            sc.state AS state,
            sc.date_start AS date_start,
            sc.company_id AS company_id,
            COALESCE(sc.amount_total, 0) AS contract_amount,
            COALESCE(sc.untaxed_amount, 0) AS service_amount,
            COALESCE(sc.entitlement_prevent, 0) AS preventive_estimated,
            COALESCE(sc.actual_prevent_count, 0) AS preventive_actual,
            COALESCE(sc.balance_prevent, 0) AS preventive_balance,
            COALESCE(sc.entitlement_correct, 0) AS corrective_estimated,
            COALESCE(sc.actual_correct_count, 0) AS corrective_actual,
            COALESCE(sc.balance_correct, 0) AS corrective_balance
        FROM subscription_contracts sc
        WHERE sc.date_start BETWEEN %(date_from)s AND %(date_to)s
    )
"""

CONTRACTS_FIELD_MAP = {
    "contract_id": "contract_id", "name": "name", "partner_id": "partner_id",
    "work_center_group_id": "work_center_group_id", "work_center_id": "work_center_id",
    "sales_person_user_id": "sales_person_user_id", "contract_type": "contract_type",
    "state": "state", "date_start": "date_start", "company_id": "company_id",
    "contract_amount": "contract_amount", "service_amount": "service_amount",
    "preventive_estimated": "preventive_estimated", "preventive_actual": "preventive_actual",
    "preventive_balance": "preventive_balance", "corrective_estimated": "corrective_estimated",
    "corrective_actual": "corrective_actual", "corrective_balance": "corrective_balance",
}


_SOURCE_CTE = {
    "jobcards": (_JOBCARDS_CTE_SQL, JOBCARDS_FIELD_MAP, "jobcards"),
    "usergroup": (_USERGROUP_CTE_SQL, USERGROUP_FIELD_MAP, "usergroup"),
    "message_log": (_MESSAGE_LOG_CTE_SQL, MESSAGE_LOG_FIELD_MAP, "message_log"),
    "promoter_showrooms": (_PROMOTER_SHOWROOMS_CTE_SQL, PROMOTER_SHOWROOMS_FIELD_MAP, "promoter_showrooms"),
    "promoter_sales": (_PROMOTER_SALES_CTE_SQL, PROMOTER_SALES_FIELD_MAP, "promoter_sales"),
    "sales_comparison": (_SALES_COMPARISON_CTE_SQL, SALES_COMPARISON_FIELD_MAP, "sales_comparison"),
    "contracts": (_CONTRACTS_CTE_SQL, CONTRACTS_FIELD_MAP, "contracts"),
}

# Terminal drill target's id column, by source — defaults to "task_id"
# (right for jobcards/message_log). Extend here, never with an if/elif
# chain at the call site, when adding a source whose CTE's own row
# identity isn't task_id.
_TERMINAL_ID_COL = {
    "usergroup": "request_id",
    "promoter_showrooms": "showroom_pk",
    "promoter_sales": "sales_id",
    "sales_comparison": "target_id",
    "contracts": "contract_id",
}


# ---------------------------------------------------------------------
# role / region / work-location resolvers — by NAME, never by hardcoded
# id: the CT boards hardcode work_center_group_id in [7]/[6]/[5] and
# dashboard_user_rights ids like [6]/[7]/[8], both of which are specific
# to the DB they were authored against and are not safe to copy here.
#
# A board renders 10-15 items, each independently compiling its own
# domain/scope through compile_domain()/_technician_guard_clause() — so
# without caching, these 3 lookups each re-run once per item (sometimes
# twice, once for the item's own domain and once for the shared board
# scope) even though the result is identical every time within a single
# board_data()/chart_data() request. Memoized on env.cr (fresh per HTTP
# request, discarded after — never persists or leaks across requests)
# rather than functools.lru_cache, which would need explicit keying/
# invalidation to avoid holding stale entries once a cursor is GC'd.
# ---------------------------------------------------------------------
def _request_cache(env):
    cache = getattr(env.cr, "_pbi_dashboards_cache", None)
    if cache is None:
        cache = {}
        env.cr._pbi_dashboards_cache = cache
    return cache


def get_user_role_codes(env, uid):
    """Ports dbmodel_jobcards_analysis.py::_get_logged_user_role_groups()."""
    cache = _request_cache(env)
    key = ("user_role_codes", uid)
    if key in cache:
        return cache[key]
    env.cr.execute(
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
        WHERE u.id = %(uid)s
          AND imd.module = 'machine_repair_management'
          AND imd.name IN ('group_parts_user', 'group_technical_allocation_user',
                            'group_call_center_user', 'group_job_card_mobile_user')
        """,
        {"uid": uid},
    )
    result = [row[0] for row in env.cr.fetchall() if row[0]]
    cache[key] = result
    return result


def get_user_work_location_ids(env, uid):
    """Ports dbmodel_jobcards_analysis.py::_get_user_work_locations()."""
    cache = _request_cache(env)
    key = ("user_work_location_ids", uid)
    if key in cache:
        return cache[key]
    env.cr.execute(
        "SELECT work_center_location_id FROM res_users_work_center_location_rel WHERE res_users_id = %(uid)s",
        {"uid": uid},
    )
    result = [row[0] for row in env.cr.fetchall()]
    cache[key] = result
    return result


def region_id_by_name(env, name):
    cache = _request_cache(env)
    key = ("region_id_by_name", name)
    if key in cache:
        return cache[key]
    rec = env["work.center.group"].sudo().search([("name", "=", name)], limit=1)
    result = rec.id if rec else None
    cache[key] = result
    return result


def _is_user_work_location_clause(op, value, binder, uid, env):
    """Field-map callable for the jobcards source's "is_user_work_location"
    DBM-vocabulary field — mirrors dbmodel_jobcards_analysis.py's
    _search_is_user_work_location (default_work_location IN the current
    user's own res_users_work_center_location_rel set)."""
    allowed = get_user_work_location_ids(env, uid)
    negate = not ((op == "=" and value) or (op == "!=" and not value))
    p = binder.bind(allowed or [0])
    return f"NOT (default_work_location = ANY({p}))" if negate else f"default_work_location = ANY({p})"


JOBCARDS_FIELD_MAP["is_user_work_location"] = _is_user_work_location_clause


def _is_my_user_group_clause(op, value, binder, uid, env):
    """Field-map callable for the jobcards source's "is_my_user_group"
    DBM-vocabulary field — mirrors dbmodel_jobcards_analysis.py's
    _search_is_my_user_group (task's user_role overlaps one of the
    current user's own roles, via a per-role ILIKE against the
    STRING_AGG'd user_role text column, since one task can carry more
    than one role name — e.g. "Coordinator, Technician")."""
    roles = get_user_role_codes(env, uid)
    negate = not ((op == "=" and value) or (op == "!=" and not value))
    if not roles:
        return "1=0" if not negate else "1=1"
    ors = " OR ".join(f"user_role ILIKE {binder.bind('%' + r + '%')}" for r in roles)
    return f"NOT ({ors})" if negate else f"({ors})"


JOBCARDS_FIELD_MAP["is_my_user_group"] = _is_my_user_group_clause


_PROMOTER_SOURCES = ("promoter_showrooms", "promoter_sales", "sales_comparison")


def _promoter_guard_clause(env, uid, binder, source):
    """Reproduces the promoter module's own search_fetch scoping (see
    promoter/models/promoter_showroom.py, promoter_showroom_sales.py,
    sales_target.py) — raw SQL bypasses those ORM-level overrides
    entirely, so equivalent scoping must be reapplied here for every
    promoter-family source, regardless of which board is being viewed:
      - group_promoter_sales_donotshow: hides every row (matches
        search_fetch's unconditional ``return self.browse([])``).
      - group_promoter_user (the mobile field promoter): sees only their
        own dealer_id/showroom (matches search_fetch's domain addition).
    Back-office/admin users get no extra restriction here, matching the
    ORM's own default (no matching group -> unrestricted search_fetch)."""
    if source not in _PROMOTER_SOURCES:
        return None
    user = env.user
    if user.has_group("promoter.group_promoter_sales_donotshow"):
        return "1=0"
    if user.has_group("promoter.group_promoter_user"):
        dealer_id = user.dealer_id.id if user.dealer_id else 0
        showroom_id = user.showroom_id.id if user.showroom_id else 0
        showroom_col = "showroom_pk" if source == "promoter_showrooms" else "showroom_id"
        return (
            f"(dealer_id = {binder.bind(dealer_id)} AND "
            f"{showroom_col} = {binder.bind(showroom_id)})"
        )
    return None


# ---------------------------------------------------------------------
# domain compiler
# ---------------------------------------------------------------------
def _substitute_symbol(value, uid, env):
    """Resolves the two symbolic value conventions BoardConfig/ChartItemConfig
    domains use instead of hardcoded, DB-specific ids:
      - "%UID"           -> the current user's id (ks_dashboard_ninja's own
                             domain-substitution convention, kept identical
                             here for the 4 "_users" boards).
      - "@region:<name>" -> work.center.group id resolved by NAME (the CT
                             boards hardcode work_center_group_id in
                             [7]/[6]/[5] for Central/East/West, which are
                             specific to the DB they were authored against).
    """
    if value == "%UID":
        return uid
    if isinstance(value, str) and value.startswith("@region:"):
        return region_id_by_name(env, value[len("@region:"):])
    return value


def compile_domain(domain, field_map, binder, uid, env=None):
    """domain: list of (field, operator, value) using DBM-vocabulary field
    names, operator in {'=', '!=', 'in', 'not in'}."""
    clauses = []
    for entry in domain or []:
        f, op, value = entry
        mapped = field_map.get(f)
        if mapped is None:
            raise ValueError(f"Unknown domain field {f!r} for this source")
        if callable(mapped):
            clauses.append(mapped(op, value, binder, uid, env))
            continue
        if isinstance(value, (list, tuple)):
            value = [_substitute_symbol(v, uid, env) for v in value]
        else:
            value = _substitute_symbol(value, uid, env)
        # Odoo domain convention: ("field", "=" / "!=", False) means IS
        # (NOT) NULL, regardless of the field's real type — every
        # DBM-vocabulary field here maps to an integer/text CTE column, so
        # binding Python False as a SQL boolean literal (e.g. "technician_id
        # != false") is a type-mismatch error, not just semantically wrong.
        if op == "=" and value is False:
            clauses.append(f"{mapped} IS NULL")
        elif op == "!=" and value is False:
            clauses.append(f"{mapped} IS NOT NULL")
        elif op == "=":
            clauses.append(f"{mapped} = {binder.bind(value)}")
        elif op == "!=":
            clauses.append(f"{mapped} != {binder.bind(value)}")
        elif op == "in":
            clauses.append(f"{mapped} = ANY({binder.bind(list(value))})")
        elif op == "not in":
            clauses.append(f"NOT ({mapped} = ANY({binder.bind(list(value))}))")
        else:
            raise ValueError(f"Unsupported domain operator {op!r}")
    return clauses


def _technician_guard_clause(env, uid, binder, source="jobcards"):
    """Reproduces service_dashboards_ct/security/service_dashboard_rules.xml's
    rule_jobcards_analysis_ct_technician ir.rule — raw SQL bypasses ir.rule
    entirely, so this must be applied unconditionally to every jobcards-
    source query whenever the current user is a Technician, regardless of
    which board is being viewed. technician_id/scheduled_uid/
    closed_jobcard_user_id only exist on the jobcards CTE — usergroup and
    message_log carry no equivalent columns, so the guard is a no-op for
    those sources (their own row-shape is already user/author-scoped
    differently, not a job-card ownership check)."""
    if source != "jobcards":
        return None
    if "Technician" not in get_user_role_codes(env, uid):
        return None
    p = binder.bind(uid)
    return f"(technician_id = {p} OR scheduled_uid = {p} OR closed_jobcard_user_id = {p})"


# ---------------------------------------------------------------------
# groupby / date-interval SQL
# ---------------------------------------------------------------------
# Many2one DBM-vocabulary fields whose raw id needs a display-name lookup
# for the chart's label — the id itself stays the "code" so drill-path
# WHERE clauses keep filtering on the real column, only the label shown
# to the user is resolved. res_users has no physical "name" column on this
# DB (it's a related field onto res_partner.name, not stored) — those two
# fields get the special res_users_partner_name marker instead of a plain
# (table, name_col) pair.
_LABEL_LOOKUP = {
    "work_center_group_id": ("work_center_group", "name"),
    "work_center_id": ("work_center_location", "name"),
    "service_warranty_id": ("service_warranty", "name"),
    "technician_id": "res_users_partner_name",
    "default_work_location": ("work_center_location", "name"),
    "user_id": "res_users_partner_name",
    "region": ("work_center_group", "name"),
    "city": ("work_center_location", "name"),
    # promoter_showrooms / promoter_sales — region_id/city_id are
    # promoter.showroom's own res.region/res.city columns (distinct from
    # jobcards' "region"/"city" aliases above, which point at
    # work_center_group/work_center_location instead).
    "region_id": ("res_region", "name"),
    # res_city.name is translate=True (stored as jsonb {"en_US": ..., "ar_001": ...}),
    # unlike every other lookup table here (plain varchar) — the 3rd tuple
    # element marks it so _groupby_sql reads name->>'<lang>' instead of a
    # bare column (COALESCE can't mix jsonb and text).
    "city_id": ("res_city", "name", "jsonb"),
    "showroom_pk": ("promoter_showroom", "name"),
    "showroom_id": ("promoter_showroom", "name"),
    "group_id": ("product_category", "name"),
    "subgroup_id": ("product_category", "name"),
    # sales_comparison — "period" is the synthetic (year || '-' || month)
    # column computed in the CTE itself, not a plain id needing a join;
    # see _groupby_sql's "period_month_label" branch below.
    "period": "period_month_label",
    # sales.target.city is a related Char to showroom_id.city.name (itself
    # translate=True) — Odoo mirrors the source field's jsonb storage onto
    # the related column too, even though the Python side declares plain
    # Char. sales.target.region has no such issue (related to
    # showroom_id.region_id.name, which is plain varchar) so "sc_region"
    # is deliberately NOT in this dict — it needs no lookup at all.
    "sc_city": "jsonb_inline",
    # contracts — salesman (res.users, delegated to res.partner.name: res_users
    # itself has no physical "name" column, see _RES_USERS_NAME_EXPR) and
    # customer (res.partner.name, plain varchar, not translate=True).
    "sales_person_user_id": "res_users_partner_name",
    "partner_id": ("res_partner", "name"),
}

_RES_USERS_NAME_EXPR = (
    "(SELECT rp.name FROM res_users ru2 JOIN res_partner rp ON rp.id = ru2.partner_id WHERE ru2.id = {col})"
)


def _lang_for(env):
    """Current session's language code (e.g. 'en_US', 'ar_001'), for
    reading translate=True jsonb columns (res_city.name) in the viewer's
    own language rather than a hardcoded one — same field the ORM itself
    would use (record.name resolves via env.context['lang'])."""
    return env.context.get("lang") or env.user.lang or "en_US"


def _groupby_sql(field_map, groupby, env=None):
    # "week" is NOT handled here — see run_breakdown's week branch /
    # _resolve_week_bucket below: it needs a relative rank over the
    # filtered result set's distinct real calendar weeks, which can't be
    # expressed as a single SELECT-able column expression the way
    # month_year/plain fields can.
    field = groupby.field
    col = field_map[field]
    if groupby.interval == "month_year":
        return f"to_char({col}, 'YYYY-MM')", f"to_char({col}, 'Mon YYYY')"
    if field in _LABEL_LOOKUP:
        spec = _LABEL_LOOKUP[field]
        if spec == "jsonb_inline":
            # The DBM-vocabulary field IS itself a translate=True column
            # stored as jsonb (e.g. sales.target.city, a related Char to
            # res.city.name — Odoo mirrors the source field's jsonb
            # storage even though the Python side declares plain Char) —
            # unlike the id-lookup markers below, there's no separate id
            # column to keep as "code": GROUP BY/drill-compare must use
            # the SAME resolved-text expression as the label, or comparing
            # jsonb to a text code later raises "operator does not exist".
            lang = _lang_for(env) if env is not None else "en_US"
            text_expr = f"COALESCE({col}->>'{lang}', {col}->>'en_US')"
            return text_expr, text_expr
        if spec == "res_users_partner_name":
            label_expr = _RES_USERS_NAME_EXPR.format(col=col)
        elif spec == "period_month_label":
            # col is already "(year || '-' || month)" (YYYY-MM) — render
            # as "Mon YYYY" for display while code stays the sortable
            # YYYY-MM string.
            label_expr = f"to_char(to_date({col}, 'YYYY-MM'), 'Mon YYYY')"
        elif len(spec) == 3:
            # translate=True column stored as jsonb — read the current
            # session's language key, falling back to en_US if that
            # translation is missing (e.g. Arabic name never entered).
            table, name_col, _marker = spec
            lang = _lang_for(env) if env is not None else "en_US"
            label_expr = (
                f"(SELECT COALESCE({name_col}->>'{lang}', {name_col}->>'en_US') "
                f"FROM {table} WHERE id = {col})"
            )
        else:
            table, name_col = spec
            label_expr = f"(SELECT {name_col} FROM {table} WHERE id = {col})"
        return col, f"COALESCE({label_expr}, {col}::text)"
    return col, col


def _measure_sql(measure):
    if measure is None:
        return "count(*)"
    agg = {"sum": "sum", "avg": "avg", "count": "count"}[measure.agg]
    return f"{agg}({measure.field})"


def _base_where(env, uid, board: BoardConfig, item: ChartItemConfig, field_map, binder, extra_domain=None):
    clauses = []
    clauses += compile_domain(board.scope, field_map, binder, uid, env)
    clauses += compile_domain(item.domain, field_map, binder, uid, env)
    if extra_domain:
        clauses += compile_domain(extra_domain, field_map, binder, uid, env)
    guard = _technician_guard_clause(env, uid, binder, item.source)
    if guard:
        clauses.append(guard)
    promoter_guard = _promoter_guard_clause(env, uid, binder, item.source)
    if promoter_guard:
        clauses.append(promoter_guard)
    return clauses


def _run_query(env, sql, params):
    env.cr.execute(sql, params)
    cols = [d[0] for d in env.cr.description]
    return [dict(zip(cols, row)) for row in env.cr.fetchall()]


# ---------------------------------------------------------------------
# generic runners — dispatch on item.source, drive every board/chart item
# from its ChartItemConfig instead of per-board Python.
# ---------------------------------------------------------------------
def _source_ctx(item: ChartItemConfig):
    cte_sql, field_map, cte_name = _SOURCE_CTE[item.source]
    return cte_sql, field_map, cte_name


def run_kpi(env, uid, board: BoardConfig, item: ChartItemConfig, date_from, date_to):
    cte_sql, field_map, cte_name = _source_ctx(item)

    def _count_or_measure(domain, measure):
        binder = ParamBinder()
        binder.params["date_from"] = date_from
        binder.params["date_to"] = date_to
        clauses = []
        clauses += compile_domain(board.scope, field_map, binder, uid, env)
        clauses += compile_domain(domain, field_map, binder, uid, env)
        guard = _technician_guard_clause(env, uid, binder, item.source)
        if guard:
            clauses.append(guard)
        promoter_guard = _promoter_guard_clause(env, uid, binder, item.source)
        if promoter_guard:
            clauses.append(promoter_guard)
        where = (" AND " + " AND ".join(clauses)) if clauses else ""
        sql = f"WITH {cte_sql} SELECT {_measure_sql(measure)} AS v FROM {cte_name} WHERE 1=1{where}"
        rows = _run_query(env, sql, binder.params)
        return rows[0]["v"] if rows else None

    if item.type == "kpi_dual":
        value = _count_or_measure(item.domain, item.measure)
        value2 = _count_or_measure(item.domain_2 or [], item.measure_2)
        return {"value": float(value or 0), "value2": float(value2 or 0)}
    value = _count_or_measure(item.domain, item.measure)
    return {"value": float(value or 0)}


def _fields_shown(item: ChartItemConfig):
    return [item.groupby.field] + [s.field for s in item.drill]


def _level_groupby_config(field, item, idx):
    """The field displayed at drill level idx carries a date interval when
    either the top-level groupby (idx 0) or the drill step itself (idx > 0,
    DrillStep.interval) declares one — e.g. Contract Analysis's Region ->
    City -> Salesman -> Month chain, where "Month" is drill level 3, not
    the top-level groupby."""
    interval = item.groupby.interval if idx == 0 else item.drill[idx - 1].interval
    return GroupByConfig(field, interval)


def _resolve_week_bucket(env, cte_sql, cte_name, raw_col, base_clauses, params, week_label):
    """Reverses a "Week-N" label back into the real date_trunc('week', ...)
    value it refers to. "Week-N" is a RELATIVE rank — the Nth distinct real
    (Monday-start) calendar week present in the filtered result set, in
    chronological order — not an absolute week-of-year number or a
    day-of-month bucket (verified against the live source: 3 records in
    ISO week 13 + 2 in ISO week 21 of the same filtered set render as
    "Week-1"=3, "Week-2"=2). So resolving it back requires re-running the
    same distinct-week enumeration with the SAME pre-drill filters that
    produced the original level-0 breakdown."""
    try:
        n = int(str(week_label).split("-")[1])
    except (ValueError, IndexError):
        return None
    where = (" WHERE " + " AND ".join(base_clauses)) if base_clauses else ""
    sql = f"""
        WITH {cte_sql}
        SELECT DISTINCT date_trunc('week', {raw_col}) AS week_start
        FROM {cte_name}{where}
        ORDER BY week_start
        OFFSET %(_week_offset)s LIMIT 1
    """
    p = dict(params)
    p["_week_offset"] = n - 1
    env.cr.execute(sql, p)
    row = env.cr.fetchone()
    return row[0] if row else None


def _drill_filter_clause(env, cte_sql, cte_name, field_map, item, idx, code, base_clauses, binder):
    """The WHERE fragment that filters rows down to an already-clicked
    bucket at drill level `idx`. A "week" level 0 needs the reverse-lookup
    above; month_year/plain fields translate directly via the same
    bucketing expression their breakdown was computed with (comparing the
    raw column straight to the label, e.g. "2026-03", is a Postgres type
    error, not just wrong results)."""
    fields_shown = _fields_shown(item)
    level_cfg = _level_groupby_config(fields_shown[idx], item, idx)
    if level_cfg.interval == "week":
        raw_col = field_map[fields_shown[idx]]
        week_start = _resolve_week_bucket(env, cte_sql, cte_name, raw_col, base_clauses, binder.params, code)
        if week_start is None:
            return f"date_trunc('week', {raw_col}) IS NULL"
        return f"date_trunc('week', {raw_col}) = {binder.bind(week_start)}"
    code_col, _label_col = _groupby_sql(field_map, level_cfg, env)
    # A "None" bucket (label for an actual NULL groupby value, e.g. an
    # untagged action_status) has code=None — "col = NULL" is never true
    # in SQL regardless of the column's actual value, it has to be "col IS
    # NULL" to match those rows back on drill-down.
    if code is None:
        return f"{code_col} IS NULL"
    return f"{code_col} = {binder.bind(code)}"


def run_breakdown(env, uid, board: BoardConfig, item: ChartItemConfig, date_from, date_to, drill_path):
    """drill_path: list of {"code": ...} already clicked, one per level of
    _fields_shown(item) in order. Returns the breakdown for the NEXT level,
    or None once past the item's configured drill chain (caller should
    treat that as terminal — see run_terminal_domain)."""
    cte_sql, field_map, cte_name = _source_ctx(item)
    fields_shown = _fields_shown(item)
    idx = len(drill_path or [])
    if idx >= len(fields_shown):
        return None

    binder = ParamBinder()
    binder.params["date_from"] = date_from
    binder.params["date_to"] = date_to
    clauses = _base_where(env, uid, board, item, field_map, binder)
    base_clauses_snapshot = list(clauses)  # pre-drill filters, needed to resolve any "Week-N" entry consistently
    for i, entry in enumerate(drill_path or []):
        clauses.append(_drill_filter_clause(env, cte_sql, cte_name, field_map, item, i, entry["code"], base_clauses_snapshot, binder))
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    level_cfg = _level_groupby_config(fields_shown[idx], item, idx)
    measure_sql = _measure_sql(item.measure)
    # measure_2 is an optional second series on plain bar items (e.g.
    # "Employee Performance Analysis - Estimated vs Actual Hours" —
    # expected_completion_hours vs total_worked_hours per region) — the
    # drill/click behaviour is unchanged, it just renders a 2nd bar per
    # category (see service_dashboard.js renderChart).
    measure2_sql = f", {_measure_sql(item.measure_2)} AS value2" if item.measure_2 else ""

    if level_cfg.interval == "week":
        raw_col = field_map[fields_shown[idx]]
        sql = f"""
            WITH {cte_sql}
            SELECT 'Week-' || ROW_NUMBER() OVER (ORDER BY week_start) AS code,
                   'Week-' || ROW_NUMBER() OVER (ORDER BY week_start) AS label,
                   value{', value2' if item.measure_2 else ''}
            FROM (
                SELECT date_trunc('week', {raw_col}) AS week_start, {measure_sql} AS value{measure2_sql}
                FROM {cte_name}{where}
                GROUP BY 1
            ) _wb
            ORDER BY week_start ASC
            LIMIT {item.limit}
        """
    else:
        code_col, label_col = _groupby_sql(field_map, level_cfg, env)
        if item.sort and idx == 0:
            order_field, order_dir = item.sort
        elif level_cfg.interval:
            # "Month wise" charts read chronologically, not sorted by
            # whichever month happens to have the most records.
            order_field, order_dir = "code", "ASC"
        else:
            order_field, order_dir = "value", "DESC"
        order_expr = "value" if order_field == "value" else code_col
        sql = (
            f"WITH {cte_sql} SELECT {code_col} AS code, {label_col} AS label, {measure_sql} AS value{measure2_sql} "
            f"FROM {cte_name}{where} GROUP BY 1, 2 ORDER BY {order_expr} {order_dir} LIMIT {item.limit}"
        )
    rows = _run_query(env, sql, binder.params)
    if item.measure_2:
        return [{"code": r["code"], "label": str(r["label"]), "value": float(r["value"] or 0),
                  "value2": float(r["value2"] or 0)} for r in rows]
    return [{"code": r["code"], "label": str(r["label"]), "value": float(r["value"] or 0)} for r in rows]


def run_table(env, uid, board: BoardConfig, item: ChartItemConfig, date_from, date_to):
    """'table' item type — a flat, ungrouped row listing (e.g. Contract
    Analysis's "Visits Comparison" list-view mirror: one row per contract,
    not a groupby aggregate). Each item.table_columns entry is resolved the
    SAME way a bar/pie groupby label is (_groupby_sql), so an id-lookup
    column (region/city/salesman/customer) renders its display name while
    a plain numeric/text column passes through unchanged — no separate
    "table" label-resolution path to keep in sync with _LABEL_LOOKUP."""
    cte_sql, field_map, cte_name = _source_ctx(item)
    binder = ParamBinder()
    binder.params["date_from"] = date_from
    binder.params["date_to"] = date_to
    clauses = _base_where(env, uid, board, item, field_map, binder)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    id_col = _TERMINAL_ID_COL.get(item.source, "task_id")

    select_parts = [f"{id_col} AS row_id"]
    for i, col in enumerate(item.table_columns):
        _code_col, label_col = _groupby_sql(field_map, GroupByConfig(col.field), env)
        select_parts.append(f"{label_col} AS col{i}")

    if item.sort:
        order_field, order_dir = item.sort
        order_expr = field_map.get(order_field, order_field)
    else:
        order_expr, order_dir = id_col, "DESC"

    sql = (
        f"WITH {cte_sql} SELECT {', '.join(select_parts)} "
        f"FROM {cte_name}{where} ORDER BY {order_expr} {order_dir} LIMIT {item.limit}"
    )
    rows = _run_query(env, sql, binder.params)
    result = []
    for r in rows:
        row = {"id": r["row_id"]}
        for i, col in enumerate(item.table_columns):
            v = r[f"col{i}"]
            row[col.field] = (float(v) if v is not None else 0.0) if col.numeric else ("" if v is None else str(v))
        result.append(row)
    return result


def run_terminal_domain(env, uid, board: BoardConfig, item: ChartItemConfig, drill_path, date_from, date_to):
    """Once a chart's configured drill chain is exhausted, resolve the
    accumulated filters into a plain Odoo domain on item.record_model so
    the client can open a native list+form view — including the same
    date-range scope every breakdown query was computed under, so the
    list matches exactly what was drilled into rather than all-time data."""
    fields_shown = _fields_shown(item)

    # jobcards -> project.task: every DBM-vocabulary field used in
    # board.scope/item.domain (task_id/work_center_id/job_card_status/etc.)
    # is either a real project.task column or renamed 1:1 (job_card_status
    # -> job_card_state), so the domain translates directly without an
    # extra query. Exception: "is_my_user_group" has no real project.task
    # equivalent (it's derived from the CTE's STRING_AGG'd user_role,
    # itself built from technician_id/scheduled_uid/closed_jobcard_user_id
    # role memberships — not a single column to rename) — those items fall
    # through to the id-lookup path below instead, same as message_log/
    # usergroup sources.
    uses_is_my_user_group = any(f == "is_my_user_group" for f, _op, _v in list(board.scope) + list(item.domain))
    # A "week" bucket (day-of-month based) repeats every month, so it's not
    # one contiguous date range — and even "month_year" would need extra
    # month-boundary math to become a real range — so any item whose level
    # 0 groupby carries a date interval falls through to the id-lookup path
    # below instead of trying to build an ORM domain entry directly on the
    # bucket label (that path already handles jobcards fine: id_col is
    # "task_id" for any non-usergroup source, and jobcards' CTE has it).
    uses_date_interval = item.groupby is not None and item.groupby.interval is not None
    if item.source == "jobcards" and item.record_model == "project.task" and not uses_is_my_user_group and not uses_date_interval:
        domain = list(board.scope) + list(item.domain)
        for i, entry in enumerate(drill_path or []):
            domain.append((fields_shown[i], "=", entry["code"]))
        domain = [
            (f, op, [_substitute_symbol(v, uid, env) for v in val] if isinstance(val, (list, tuple))
             else _substitute_symbol(val, uid, env))
            for f, op, val in domain
        ]
        translated = []
        for f, op, v in domain:
            if f == "job_card_status":
                f = "job_card_state"
            elif f == "is_user_work_location":
                # Not a real project.task column (it's a search-only
                # computed field on the jobcards CTE/DBM view) — translate
                # to the same real-column check the callable itself uses:
                # the task's own work_center_id is one of the current
                # user's assigned work locations.
                allowed = get_user_work_location_ids(env, uid)
                negate = not ((op == "=" and v) or (op == "!=" and not v))
                f, op, v = "work_center_id", ("not in" if negate else "in"), (allowed or [0])
            translated.append((f, op, v))
        translated.append(("service_created_datetime", ">=", date_from))
        translated.append(("service_created_datetime", "<=", date_to))
        return item.record_model, translated

    # message_log -> project.task, usergroup -> machine.repair.support:
    # several DBM-vocabulary fields on these two sources (message_log's
    # status/role/region-and-city-of-AUTHOR; usergroup's computed
    # user_group aggregate) have no real column of the same name/meaning
    # on the target model, so a literal field-rename translation isn't
    # possible. Instead, re-run the same accumulated filters as a plain
    # id lookup against the source CTE (every row carries the target
    # record's real id straight through: task_id for message_log,
    # request_id for usergroup) and hand back an ("id", "in", [...])
    # domain — exactly as faithful as the field-translation path, just
    # computed via one extra query instead of a rename table.
    cte_sql, field_map, cte_name = _source_ctx(item)
    binder = ParamBinder()
    binder.params["date_from"] = date_from
    binder.params["date_to"] = date_to
    clauses = _base_where(env, uid, board, item, field_map, binder)
    base_clauses_snapshot = list(clauses)
    for i, entry in enumerate(drill_path or []):
        clauses.append(_drill_filter_clause(env, cte_sql, cte_name, field_map, item, i, entry["code"], base_clauses_snapshot, binder))
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    id_col = _TERMINAL_ID_COL.get(item.source, "task_id")
    sql = f"WITH {cte_sql} SELECT DISTINCT {id_col} FROM {cte_name}{where}"
    rows = _run_query(env, sql, binder.params)
    ids = [r[id_col] for r in rows if r[id_col]]
    return item.record_model, [("id", "in", ids or [0])]
