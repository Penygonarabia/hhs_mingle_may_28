# -*- coding: utf-8 -*-
"""Direct-table query engine shared by all PBI dashboard sub-modules
(pbi_service_dashboards, pbi_contract_dashboards, pbi_promoter_dashboards).

Reproduces the SQL/logic of the three ``dbmodel.*.ct`` view models in
``service_dashboards_ct`` (see that module's ``models/dbmodel_*.py``)
against the underlying direct tables (``project_task``,
``machine_repair_support``, ``mail_message``/``mail_tracking_value``)
instead of depending on those views or on ``ks_dashboard_ninja``. Every
board/chart-item config in the per-module config files is executed through
the generic runners at the bottom of this file — there is no per-board SQL.
"""
import itertools
import logging

from .board_config import ChartItemConfig, BoardConfig, GroupByConfig, MONTHLY_WORKING_HOURS

_logger = logging.getLogger(__name__)

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
# job_state status vocabulary — display NAME (as recorded in
# mail_tracking_value.new_value_char at the time of the change) -> the
# project.task.type CODE it means.
#
# The tracking log stores the stage's display name, not its code, and
# those names have been renamed repeatedly over the years — matching a
# single current name silently drops most of the history. Every entry
# below is a name that actually occurs in the live tracking table:
# "Technician Reached" (96 rows) coexists with today's "Technician
# Reached - Job Started" (41), "Parts Ready" (38) with "Parts Ready &
# Reschedule" (14) and "Parts Ready & Rescheduled" (1), and so on.
#
# Only the codes the dashboards actually read are mapped; unmapped names
# (Quote Sent/Approved/Rejected, Warranty Verification, the project.task
# stages "Inbox"/"Today"/..., etc.) resolve to NULL and are ignored.
#
# "Parts Received" is the one genuinely ambiguous name: it is read as
# 123 (Spare Parts Handover to me), since code 205's own label spells
# out "Parts Received by Internal Technician".
# ---------------------------------------------------------------------
STATUS_ALIASES = {
    # 101 New
    "New": "101",
    # 102 Scheduled
    "Scheduled": "102",
    # 109 Technician Travel Started
    "Technician Travel Started": "109",
    "Technician Started": "109",
    # 110 Technician Reached - Job Started
    "Technician Reached - Job Started": "110",
    "Technician Reached": "110",
    # 121 On Hold -SP Req
    "On Hold -SP Req": "121",
    # 122 Parts Ready & Reschedule (+ the internal-technician variant,
    # code 207 — the same "the spare parts are ready" event, just routed
    # to an internal technician instead of a field one)
    "Parts Ready & Reschedule": "122",
    "Parts Ready & Rescheduled": "122",
    "Parts Ready": "122",
    "Parts Ready  & Reschedule with Internal  Technician": "122",
    # 123 Spare Parts Handover to me
    "Spare Parts Handover to me": "123",
    "Parts Received": "123",
    # 125 Ready to Invoice
    "Ready to Invoice": "125",
    # 126 Closed
    "Closed": "126",
    # 129 Customer Need Quote
    "Customer Need Quote": "129",
    # 131 Parts Added Req Service Charge
    "Parts Added Req Service Charge": "131",
    "Parts Added Req service": "131",
}


def _sql_str(value):
    """A single-quoted SQL string literal for a value that is baked into
    the CTE text itself rather than bound as a parameter (STATUS_ALIASES
    keys — module-level constants, never request input)."""
    return "'" + str(value).replace("'", "''") + "'"


def _status_code_case(col):
    """CASE expression mapping a tracked status NAME column to its
    project.task.type code, via STATUS_ALIASES. btrim'd because a few
    historic values carry trailing whitespace."""
    whens = " ".join(
        f"WHEN {_sql_str(name)} THEN {_sql_str(code)}"
        for name, code in STATUS_ALIASES.items()
    )
    return f"CASE btrim({col}) {whens} ELSE NULL END"


def _hours_between(start_expr, end_expr):
    """Elapsed hours between two timestamps, as a nullable float.

    NULL (not 0) whenever either endpoint is missing or the interval runs
    backwards — these columns are read by avg() measures, and a
    COALESCE(...,0) would silently drag every average down with rows that
    never reached the end state at all. The end >= start guard drops the
    handful of records whose stages were set out of order by a manual
    correction."""
    return (
        f"CASE WHEN {start_expr} IS NOT NULL AND {end_expr} IS NOT NULL "
        f"AND {end_expr} >= {start_expr} "
        f"THEN EXTRACT(EPOCH FROM ({end_expr} - {start_expr})) / 3600.0 END"
    )


def _first_author(code):
    """res_users id of the author of the EARLIEST transition into `code`
    — the user who actually performed that status change."""
    return (
        f"(array_agg(au.id ORDER BY mm.create_date ASC) "
        f"FILTER (WHERE sc.code = {_sql_str(code)} AND au.id IS NOT NULL))[1]"
    )


def _last_author(code):
    """res_users id of the author of the LATEST transition into `code` —
    used for Closed, where a re-opened-and-re-closed card should be
    attributed to whoever closed it last."""
    return (
        f"(array_agg(au.id ORDER BY mm.create_date DESC) "
        f"FILTER (WHERE sc.code = {_sql_str(code)} AND au.id IS NOT NULL))[1]"
    )


def _first_ts(code):
    return f"min(mm.create_date) FILTER (WHERE sc.code = {_sql_str(code)})"


def _last_ts(code):
    return f"max(mm.create_date) FILTER (WHERE sc.code = {_sql_str(code)})"


# ---------------------------------------------------------------------
# task_timeline — one row per project_task, pivoting its job_state
# transition log into "when did this card reach status X, and who put it
# there".
#
# Needed because the timestamps four of the service KPIs depend on are
# NOT recoverable from project_task's own columns (see
# machine_repair_management/models/job_card.py's state_date_map):
#   - Scheduled (102) writes scheduled_date, which is
#     default=fields.Datetime.now — stamped at CREATION, not when the
#     card was scheduled, so it cannot measure scheduling time.
#   - Parts Ready (122) and Spare Parts Handover (123) BOTH write
#     job_resume_date, so the handover overwrites the parts-ready value:
#     the "Parts Ready -> Hand Over" interval is unmeasurable from
#     stored fields, and "On Hold -> Parts Ready" computed off
#     job_resume_date (the stored onhold_hours field) actually measures
#     On Hold -> handover.
#   - Parts Added Req Service Charge (131) writes no datetime at all.
#
# Deliberately NOT date-scoped on the transition date: a card created in
# one month and closed in the next must keep its whole timeline, or its
# intervals are truncated at the period boundary. It is scoped to the
# same set of tasks the jobcards CTE itself selects (created within the
# dashboard's date range), which is what bounds the scan.
# ---------------------------------------------------------------------
_TASK_TIMELINE_CTE_SQL = f"""
        task_timeline AS (
            SELECT
                mm.res_id AS task_id,
                {_first_ts('102')} AS scheduled_ts,
                {_first_ts('109')} AS travel_started_ts,
                {_first_ts('110')} AS reached_ts,
                {_first_ts('121')} AS onhold_ts,
                {_first_ts('122')} AS parts_ready_ts,
                {_first_ts('123')} AS handover_ts,
                {_first_ts('125')} AS ready_to_invoice_ts,
                {_last_ts('126')} AS closed_ts,
                {_first_ts('129')} AS cst_need_quote_ts,
                {_first_ts('131')} AS parts_added_ts,
                {_first_author('102')} AS scheduled_by_uid,
                {_last_author('126')} AS closed_by_uid,
                -- The spare-parts coordinator who HANDLED the request:
                -- the earliest author, among the parts-flow transitions,
                -- who is actually a member of the Parts group. The
                -- request is raised by the technician (121/129), so the
                -- raising author is not the handler — a card no parts
                -- user has touched yet gets NULL here and drops out of
                -- the per-coordinator charts rather than being credited
                -- to the technician who raised it.
                (array_agg(au.id ORDER BY mm.create_date ASC) FILTER (
                    WHERE sc.code IN ('121', '122', '123', '129', '131')
                      AND au.id IS NOT NULL
                      AND pu.uid IS NOT NULL
                ))[1] AS parts_handler_uid
            FROM mail_tracking_value log
            JOIN mail_message mm ON mm.id = log.mail_message_id
            JOIN ir_model_fields ff ON ff.id = log.field_id
            CROSS JOIN LATERAL (
                SELECT {_status_code_case(
                    "COALESCE(log.new_value_char, log.new_value_text)"
                )} AS code
            ) sc
            LEFT JOIN res_partner rp ON rp.id = mm.author_id
            LEFT JOIN res_users au ON au.partner_id = rp.id
            LEFT JOIN parts_user_map pu ON pu.uid = au.id
            WHERE mm.model = 'project.task'
              AND ff.name = 'job_state'
              AND sc.code IS NOT NULL
              AND mm.res_id IN (
                    SELECT id FROM project_task
                    WHERE active = true
                      AND service_created_datetime BETWEEN %(date_from)s AND %(date_to)s
                )
            GROUP BY mm.res_id
        )
"""

# The timeline-derived columns exposed on the jobcards CTE. Each interval
# prefers the timeline timestamp and falls back to project_task's own
# stored column where one exists and is trustworthy (110/125 write
# technician_reached_date/closed_datetime from the same write() that logs
# the transition, so they agree — the fallback only matters for cards
# whose tracking rows predate the current job_state tracking config).
_TIMELINE_DERIVED_COLUMNS = f"""
            tl.scheduled_ts AS scheduled_ts,
            tl.travel_started_ts AS travel_started_ts,
            tl.reached_ts AS reached_ts,
            tl.onhold_ts AS onhold_ts,
            tl.parts_ready_ts AS parts_ready_ts,
            tl.handover_ts AS handover_ts,
            tl.ready_to_invoice_ts AS ready_to_invoice_ts,
            tl.closed_ts AS closed_ts,
            tl.cst_need_quote_ts AS cst_need_quote_ts,
            tl.parts_added_ts AS parts_added_ts,
            tl.scheduled_by_uid AS scheduled_by_uid,
            tl.closed_by_uid AS closed_by_uid,
            tl.parts_handler_uid AS parts_handler_uid,
            COALESCE(tl.reached_ts, pt.technician_reached_date) AS reached_ts_eff,
            COALESCE(tl.ready_to_invoice_ts, pt.closed_datetime) AS ready_to_invoice_ts_eff,
            -- The remaining "_eff" pairs. Each repeats, verbatim, the
            -- COALESCE an hour column below is built from, so a Formula &
            -- Details table can show the exact endpoints that produced the
            -- number rather than the bare tracking-log column (NULL on any
            -- card whose transition predates job_state tracking, which
            -- would make the table fail to reconcile with its own bar).
            COALESCE(tl.travel_started_ts, pt.technician_started_date) AS travel_started_ts_eff,
            COALESCE(tl.closed_ts, pt.job_card_completed_time) AS closed_ts_eff,
            COALESCE(tl.onhold_ts, pt.job_hold_date) AS onhold_ts_eff,
            COALESCE(tl.cst_need_quote_ts, pt.cstneedquote_date) AS cst_need_quote_ts_eff,
            {_hours_between(
                "COALESCE(tl.reached_ts, pt.technician_reached_date)",
                "COALESCE(tl.ready_to_invoice_ts, pt.closed_datetime)",
            )} AS labor_hours,
            {_hours_between(
                "COALESCE(tl.travel_started_ts, pt.technician_started_date)",
                "COALESCE(tl.reached_ts, pt.technician_reached_date)",
            )} AS travel_time_hours,
            {_hours_between("pt.service_created_datetime", "tl.scheduled_ts")} AS scheduling_hours,
            {_hours_between(
                "COALESCE(tl.ready_to_invoice_ts, pt.closed_datetime)",
                "COALESCE(tl.closed_ts, pt.job_card_completed_time)",
            )} AS job_closing_hours,
            {_hours_between(
                "COALESCE(tl.onhold_ts, pt.job_hold_date)",
                "tl.parts_ready_ts",
            )} AS onhold_to_ready_hours,
            {_hours_between("tl.parts_ready_ts", "tl.handover_ts")} AS ready_to_handover_hours,
            -- "was this card ever a spare-part request", for the Parts
            -- boards' request COUNT. job_card_status alone answers "is it
            -- one RIGHT NOW", which silently drops every request that has
            -- since progressed to Parts Ready / Closed — i.e. exactly the
            -- ones the coordinator finished handling. The status check is
            -- kept as a fallback for cards whose transition predates
            -- job_state tracking.
            (
                tl.onhold_ts IS NOT NULL
                OR tl.cst_need_quote_ts IS NOT NULL
                OR pt.job_hold_date IS NOT NULL
                OR pt.cstneedquote_date IS NOT NULL
                OR pt.job_card_state IN ('On Hold -SP Req', 'Customer Need Quote')
            ) AS is_spare_part_request,
            {_hours_between(
                "COALESCE(tl.cst_need_quote_ts, pt.cstneedquote_date)",
                "tl.parts_added_ts",
            )} AS quote_to_parts_added_hours,
"""


# ---------------------------------------------------------------------
# jobcards CTE — ports service_dashboards_ct/models/dbmodel_jobcards_analysis.py's
# init() SQL (the dbmodel_jobcards_analysis_ct VIEW) against project_task
# directly, scoped to a date range up front so every downstream query only
# ever scans the rows it needs.
# ---------------------------------------------------------------------
_JOBCARDS_CTE_SQL = f"""
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
        ),
        -- Members of the Parts group, for task_timeline's
        -- parts_handler_uid — a separate, single-group lookup rather than
        -- an ILIKE against user_role_map's STRING_AGG'd text, since this
        -- one is a join key, not a display value.
        parts_user_map AS (
            SELECT DISTINCT u.id AS uid
            FROM res_users u
            JOIN res_groups_users_rel rel ON rel.uid = u.id
            JOIN ir_model_data imd ON imd.res_id = rel.gid
            WHERE imd.module = 'machine_repair_management'
              AND imd.name = 'group_parts_user'
        ),
        -- THE TECHNICIAN'S OWN REGION, for job cards that carry none.
        --
        -- 6,863 of the 15,979 active job cards on dbprod have no
        -- work_center_group_id, so every region chart on the Service boards
        -- drew 43 pct of its jobs in one "No Region" bar. Those cards have no
        -- work_center_id either, so there is no city to climb from -- the
        -- technician is the only thing on them that knows where the work was.
        --
        -- LEARNED FROM THE JOB CARDS THEMSELVES, not from the technician's
        -- assigned locations, and the difference is measurable. Against the
        -- 7,084 cards that carry BOTH a region and a technician:
        --
        --     res_users_work_center_location_rel   92.0 pct agreement
        --     the technician's own dominant region 98.4 pct
        --
        -- The assignment table stays as a backup for a technician who has
        -- never closed a regioned card, which is what takes coverage up to the
        -- full 1,376 -- every regionless card that has a technician at all.
        --
        -- THE OTHER 5,487 STAY UNASSIGNED, and no join can rescue them: they
        -- carry no technician, no city, no scheduler, no closer and no
        -- company. The partner is the only other field on them, and the
        -- partner's own work centre agrees with the job card's region on just
        -- 53 of 177 -- worse than a coin toss, so it is deliberately not used.
        --
        -- Deliberately NOT date-scoped: the history is what makes the estimate
        -- good, and re-deriving it from a narrow window would make a one-month
        -- view guess worse than a one-year view for the very same job card.
        tech_region_hist AS (
            SELECT technician_id AS uid, work_center_group_id AS grp
            FROM (
                SELECT technician_id, work_center_group_id,
                       ROW_NUMBER() OVER (PARTITION BY technician_id
                                          ORDER BY count(*) DESC, work_center_group_id) AS rn
                FROM project_task
                WHERE active AND technician_id IS NOT NULL
                  AND work_center_group_id IS NOT NULL
                GROUP BY 1, 2
            ) ranked WHERE rn = 1
        ),
        tech_region_assigned AS (
            SELECT r.res_users_id AS uid, MIN(l.work_center_group_id) AS grp
            FROM res_users_work_center_location_rel r
            JOIN work_center_location l ON l.id = r.work_center_location_id
            WHERE l.work_center_group_id IS NOT NULL
            GROUP BY 1
        ),
{_TASK_TIMELINE_CTE_SQL}
        SELECT
            pt.id AS task_id,
            pt.name AS name,
            ru.id AS user_id,
            TRIM(BOTH ', ' FROM CONCAT_WS(', ', ug_tech.user_role, ug_ru.user_role, ug_create.user_role)) AS user_role,
            um.work_center_location_id AS default_work_location,
            pt.company_id AS company_id,
            pt.service_warranty_id AS service_warranty_id,
            -- The FRANCHISE the job card belongs to: machine_repair_management
            -- keeps the brand on project_task.product_category_id, a top-level
            -- product.category (Midea / Beko / Candy / ...) -- the same column
            -- promoter_showroom_sales exposes as franchise_id, named the same
            -- way here so one filter reads identically on every board.
            pt.product_category_id AS franchise_id,
            -- The card's own region first; the technician's only where it has
            -- none. See tech_region_hist above for why, and for what is still
            -- beyond reach.
            COALESCE(pt.work_center_group_id, trh.grp, tra.grp) AS work_center_group_id,
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
{_TIMELINE_DERIVED_COLUMNS}            pt.active AS active
        FROM project_task pt

        LEFT JOIN task_timeline tl ON tl.task_id = pt.id

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

        -- One row per technician in each, so neither can fan a job card out.
        LEFT JOIN tech_region_hist trh ON trh.uid = pt.technician_id
        LEFT JOIN tech_region_assigned tra ON tra.uid = pt.technician_id

        WHERE pt.active = true
          AND pt.service_created_datetime BETWEEN %(date_from)s AND %(date_to)s
    )
"""

# DBM-vocabulary field name -> real jobcards CTE column. 1:1 for everything
# except the two search-only booleans, which become callables producing a
# custom WHERE fragment (mirroring dbmodel_jobcards_analysis.py's
# _search_is_user_work_location/_search_is_my_user_group).
JOBCARDS_FIELD_MAP = {
    "task_id": "task_id", "name": "name", "user_id": "user_id", "default_work_location": "default_work_location",
    "service_warranty_id": "service_warranty_id", "work_center_group_id": "work_center_group_id",
    "work_center_id": "work_center_id", "technician_id": "technician_id", "scheduled_uid": "scheduled_uid",
    "closed_jobcard_user_id": "closed_jobcard_user_id", "job_card_status": "job_card_status",
    "action_status": "action_status", "service_created_datetime": "service_created_datetime",
    "total_worked_hours": "total_worked_hours",
    # machine_repair_management's own working-hours-aware RTAT compute.
    # Used as a measure by several boards; named here too so it can also
    # be read per record by the Formula & Details engine.
    "rtat_hours": "rtat_hours",
    # timeline-derived (see _TASK_TIMELINE_CTE_SQL) — status timestamps,
    # the intervals between them, and who performed each transition.
    "scheduled_ts": "scheduled_ts", "travel_started_ts": "travel_started_ts",
    "reached_ts": "reached_ts", "onhold_ts": "onhold_ts",
    "parts_ready_ts": "parts_ready_ts", "handover_ts": "handover_ts",
    "ready_to_invoice_ts": "ready_to_invoice_ts", "closed_ts": "closed_ts",
    "cst_need_quote_ts": "cst_need_quote_ts", "parts_added_ts": "parts_added_ts",
    "labor_hours": "labor_hours", "travel_time_hours": "travel_time_hours",
    "scheduling_hours": "scheduling_hours", "job_closing_hours": "job_closing_hours",
    "onhold_to_ready_hours": "onhold_to_ready_hours",
    "ready_to_handover_hours": "ready_to_handover_hours",
    "quote_to_parts_added_hours": "quote_to_parts_added_hours",
    "scheduled_by_uid": "scheduled_by_uid", "closed_by_uid": "closed_by_uid",
    "parts_handler_uid": "parts_handler_uid",
    "reached_ts_eff": "reached_ts_eff", "ready_to_invoice_ts_eff": "ready_to_invoice_ts_eff",
    "travel_started_ts_eff": "travel_started_ts_eff", "closed_ts_eff": "closed_ts_eff",
    "onhold_ts_eff": "onhold_ts_eff", "cst_need_quote_ts_eff": "cst_need_quote_ts_eff",
    "is_spare_part_request": "is_spare_part_request",
    # brand/franchise the card was raised against (project_task.product_category_id)
    "franchise_id": "franchise_id",
}

# The subset of JOBCARDS_FIELD_MAP above that exists only on the CTE (it
# is derived from the job_state tracking log), with no project.task column
# of the same name — see run_terminal_domain's uses_timeline_field.
_TIMELINE_FIELDS = frozenset([
    "scheduled_ts", "travel_started_ts", "reached_ts", "onhold_ts", "parts_ready_ts",
    "handover_ts", "ready_to_invoice_ts", "closed_ts", "cst_need_quote_ts", "parts_added_ts",
    "labor_hours", "travel_time_hours", "scheduling_hours", "job_closing_hours",
    "onhold_to_ready_hours", "ready_to_handover_hours", "quote_to_parts_added_hours",
    "scheduled_by_uid", "closed_by_uid", "parts_handler_uid", "is_spare_part_request",
    "reached_ts_eff", "ready_to_invoice_ts_eff", "travel_started_ts_eff", "closed_ts_eff",
    "onhold_ts_eff", "cst_need_quote_ts_eff",
])


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
            mrs.request_date AS request_date,
            -- The franchise of the job card the request hangs off, so the
            -- board-level franchise filter reaches this source too (the CTE
            -- is already restricted to requests that carry a task_id, and a
            -- task is unique, so the join cannot fan a request out).
            pt.product_category_id AS franchise_id
        FROM machine_repair_support mrs
        LEFT JOIN project_task pt ON pt.id = mrs.task_id
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
    "user_id": "user_id", "task_id": "task_id",
    "team_id": "team_id", "service_type_id": "service_type_id",
    "work_center_group_id": "work_center_group_id", "work_center_id": "work_center_id",
    "service_request_state": "service_request_state", "request_date": "request_date",
    "franchise_id": "franchise_id",
}


def _user_group_clause(op, value, binder, uid, env):
    """Field-map callable for the usergroup source's "user_group" — a
    MEMBERSHIP test against the CTE's comma-separated group list, not
    string equality.

    ``user_group`` is a STRING_AGG over every machine_repair_management
    group the request's creator belongs to, so an operator who is in the
    Call Center group AND any other one carries
    "call-center, co-ordinator, mobile, parts", not "call-center". The
    board configs (and the ks_dashboard_ninja items they were ported
    from) all say ``("user_group", "=", "call-center")``, which under
    plain equality matches only the operators who hold exactly one group
    — every request raised by a multi-group Call Center operator was
    silently dropped from "Service Analysis (CC)", under-counting the
    board against the underlying request list.

    Same problem, same shape, and the same fix as the jobcards source's
    ``is_my_user_group`` (see _is_my_user_group_clause): match the token
    inside the aggregate rather than the aggregate as a whole. Delimiter-
    padded on both sides so "parts" cannot match "spare-parts" and
    "co-ordinator" cannot match a longer name containing it."""
    values = list(value) if isinstance(value, (list, tuple)) else [value]
    ors = " OR ".join(
        f"(', ' || user_group || ', ') LIKE {binder.bind('%, ' + str(v) + ', %')}"
        for v in values
    )
    negate = op in ("!=", "not in")
    return f"NOT ({ors})" if negate else f"({ors})"


USERGROUP_FIELD_MAP["user_group"] = _user_group_clause


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
            -- The TASK's own region, not the transition author's.
            --
            -- The DBM view read this from a user_work_center_group_rel
            -- m2m, which does not exist on this database and never will:
            -- it is declared on machine_repair_management's
            -- project.task.message.log model, which is _auto = False, so
            -- Odoo never creates its relation table. Selecting from it
            -- raised UndefinedTable, which aborted the whole request
            -- transaction — taking down every board carrying a
            -- message_log item, not just that one chart.
            --
            -- Reading the region off project_task also makes the
            -- region-filterable boards (CRD, Parts) consistent: their
            -- jobcards-source items filter on the JOB's region, so their
            -- message_log items now do too, instead of on whichever
            -- region the acting user happened to be assigned to.
            pt.work_center_group_id AS region,
            -- The TASK's franchise, for the same reason its region is read
            -- off the task rather than off the transition's author.
            pt.product_category_id AS franchise_id,
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
    # region-filterable scope clause (board_engine.py's _effective_board,
    # written once in jobcards vocabulary) apply uniformly to boards that
    # mix a message_log-source item in with jobcards-source items (CRD,
    # Parts), instead of erroring "unknown domain field".
    "work_center_group_id": "region",
    "franchise_id": "franchise_id",
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
            -- REGION AND CITY FALL BACK TO THE CUSTOMER'S OWN WORK CENTRE.
            --
            -- 124 of the 146 contracts on dbprod carry neither, so "Contract
            -- Analysis" drew 68.7 pct of its amount and 84.9 pct of its count
            -- in a single "No Region" bar. The partner names a work centre,
            -- and a work centre names its group -- the same taxonomy the
            -- contract's own column uses, not a mapping invented here -- which
            -- fills 107 of the 124.
            --
            -- The contract still wins wherever it has a value, so this can only
            -- fill a gap. That ordering is doing more work than usual here:
            -- exactly ONE contract carries both, so there is no sample to
            -- measure the fallback's agreement against the way the salesman
            -- board's city fallback was measured (13,810 of 13,872). It is the
            -- customer's own service region, which is the right answer for a
            -- service contract far more often than "No Region" is, but it is
            -- inference rather than record -- if contracts start being created
            -- with their region filled in, this quietly stops firing.
            --
            -- Both levels move together on purpose: chart 1 drills Region ->
            -- City, so a contract given a region and no city would drill into
            -- nothing.
            COALESCE(sc.work_center_group_id, pwc.work_center_group_id) AS work_center_group_id,
            COALESCE(sc.work_center_id, p.work_center_id) AS work_center_id,
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
        -- Both are primary-key lookups, so neither can fan a contract out.
        LEFT JOIN res_partner p ON p.id = sc.partner_id
        LEFT JOIN work_center_location pwc ON pwc.id = p.work_center_id
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


# ---------------------------------------------------------------------
# budget_compare CTE — backs "PBI Dashboards > Budget Dashboards > Budget
# Analysis". One row per budget cell per month, carrying OUR budget and
# BIDATA's budget as two separate measures so a single chart can draw both
# series (the same shape sales_comparison uses for target vs actual).
#
# UNION ALL rather than a join between the two views. Joining them on the
# dimension tuple would need every one of a dozen nullable columns to
# match, and a row that failed to pair would vanish silently from BOTH
# series — which is the one failure a reconciliation screen must not have.
# Unioning, each side contributes its own measure and zero for the other,
# so SUM() per dimension gives both totals and nothing can be dropped.
#
# budget_line_id is the terminal drill target (sales.budget.line). BIDATA
# rows have no Odoo record behind them and carry 0, an id that matches
# nothing — so drilling to the bottom lands on our budget lines, which are
# the only records there are to open.
#
# Scoped by MONTH, not by day: budget has no dates, only (year, month), so
# the period string is compared the way sales_comparison compares its own.
# ---------------------------------------------------------------------
_BUDGET_COMPARE_CTE_SQL = """
    budget_compare AS (
        SELECT
            COALESCE(b.budget_line_id, 0)      AS budget_line_id,
            b.year                             AS year,
            (b.year || '-' || b.month)         AS period,
            brreg.id                           AS region_id,
            b.city_id                          AS city_id,
            bpcl.id                            AS partner_classification_id,
            bsg.id                             AS salestype_group_id,
            bmc.id                             AS main_category_id,
            bsc.id                             AS sub_category_id,
            b.product_group_id                 AS group_id,
            b.product_subgroup_id              AS subgroup_id,
            b.franchise_code                   AS franchise_code,
            b.customer_code                    AS customer_code,
            b.salesman_code                    AS salesman_code,
            COALESCE(b.budget_qty, 0)          AS budget_qty,
            COALESCE(b.budget_amount, 0)       AS budget_amount,
            0::double precision                AS bidata_qty,
            0::double precision                AS bidata_amount
        FROM v_sales_budget_month_edit b
        -- Resolved from the budget's CODES, not from ids it stores, so the
        -- budget module can drop those links entirely. The ids are identical --
        -- the codes were computed from them and every master's code is unique
        -- and non-blank, so each join matches one row or none -- which keeps
        -- this CTE's value space, and therefore every filter, drill and label
        -- on the board above it, exactly as it was. BIDATA's side of the UNION
        -- keeps its own ids: that view resolves them itself, and lives in this
        -- layer now.
        LEFT JOIN partner_classification bpcl ON bpcl.pc_code    = b.partner_classification_code
        LEFT JOIN res_region             brreg ON brreg.code     = b.region_code
        LEFT JOIN salestypes_group       bsg  ON bsg.salgrp_ref  = b.salestype_group_code
        LEFT JOIN main_category          bmc  ON bmc.maincat_ref = b.main_category_code
        LEFT JOIN sub_category           bsc  ON bsc.subcat_ref  = b.sub_category_code
        WHERE (b.year || '-' || b.month) BETWEEN
            to_char(%(date_from)s::date, 'YYYY-MM') AND to_char(%(date_to)s::date, 'YYYY-MM')
        UNION ALL
        SELECT
            0                                  AS budget_line_id,
            d.year                             AS year,
            (d.year || '-' || d.month)         AS period,
            d.region_id, d.city_id, d.partner_classification_id, d.salestype_group_id,
            d.main_category_id, d.sub_category_id,
            d.product_group_id                 AS group_id,
            d.product_subgroup_id              AS subgroup_id,
            d.franchise_code, d.customer_code, d.salesman_code,
            0::double precision                AS budget_qty,
            0::double precision                AS budget_amount,
            COALESCE(d.budget_qty, 0)          AS bidata_qty,
            COALESCE(d.budget_amount, 0)       AS bidata_amount
        FROM v_bidata_budget_month d
        WHERE (d.year || '-' || d.month) BETWEEN
            to_char(%(date_from)s::date, 'YYYY-MM') AND to_char(%(date_to)s::date, 'YYYY-MM')
    )
"""

BUDGET_COMPARE_FIELD_MAP = {
    "budget_line_id": "budget_line_id",
    "year": "year", "period": "period",
    # region_id / city_id / group_id / subgroup_id are named to match the
    # keys _LABEL_LOOKUP already carries (res_region, res_city, and
    # product_category twice), so they render their names with no new
    # lookup entry.
    "region_id": "region_id", "city_id": "city_id",
    "group_id": "group_id", "subgroup_id": "subgroup_id",
    "partner_classification_id": "partner_classification_id",
    "salestype_group_id": "salestype_group_id",
    "main_category_id": "main_category_id",
    "sub_category_id": "sub_category_id",
    "franchise_code": "franchise_code",
    "customer_code": "customer_code", "salesman_code": "salesman_code",
    "budget_qty": "budget_qty", "budget_amount": "budget_amount",
    "bidata_qty": "bidata_qty", "bidata_amount": "bidata_amount",
}


_SOURCE_CTE = {
    "jobcards": (_JOBCARDS_CTE_SQL, JOBCARDS_FIELD_MAP, "jobcards"),
    "usergroup": (_USERGROUP_CTE_SQL, USERGROUP_FIELD_MAP, "usergroup"),
    "message_log": (_MESSAGE_LOG_CTE_SQL, MESSAGE_LOG_FIELD_MAP, "message_log"),
    "promoter_showrooms": (_PROMOTER_SHOWROOMS_CTE_SQL, PROMOTER_SHOWROOMS_FIELD_MAP, "promoter_showrooms"),
    "promoter_sales": (_PROMOTER_SALES_CTE_SQL, PROMOTER_SALES_FIELD_MAP, "promoter_sales"),
    "sales_comparison": (_SALES_COMPARISON_CTE_SQL, SALES_COMPARISON_FIELD_MAP, "sales_comparison"),
    "contracts": (_CONTRACTS_CTE_SQL, CONTRACTS_FIELD_MAP, "contracts"),
    "budget_compare": (_BUDGET_COMPARE_CTE_SQL, BUDGET_COMPARE_FIELD_MAP, "budget_compare"),
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
    "budget_compare": "budget_line_id",
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
    # Raw lookup rather than search([("name", "=", name)]): the ORM reads a
    # field the way the MODEL declares it — for a translate=True Char it
    # emits "name"->>'lang' — so an ORM search here fails on any database
    # whose column and declaration disagree, which is exactly the state a
    # half-deployed module leaves behind. Reading the column directly, and
    # through the same shape-agnostic expression the labels use, keeps this
    # working whichever way another module declares its own field. The board
    # configs name a region in English, so en_US is the key to match.
    expr = _translated_text_expr("name", "en_US")
    env.cr.execute(
        f"SELECT id FROM work_center_group WHERE {expr} = %s LIMIT 1", (name,))
    row = env.cr.fetchone()
    result = row[0] if row else None
    cache[key] = result
    return result


def franchise_id_by_name(env, name):
    """product.category id for a franchise NAME (Midea / Beko / Candy / ...).

    Same shape and the same reasoning as region_id_by_name above: the
    filter travels as a name rather than an id because ids differ between
    the databases these boards run on. product_category.name is a plain
    Char in core, but it is read through the same shape-agnostic
    expression anyway so a module that makes it translatable on some
    server does not break the lookup here.
    """
    cache = _request_cache(env)
    key = ("franchise_id_by_name", name)
    if key in cache:
        return cache[key]
    expr = _translated_text_expr("name", "en_US")
    env.cr.execute(
        f"SELECT id FROM product_category WHERE {expr} = %s ORDER BY id LIMIT 1", (name,))
    row = env.cr.fetchone()
    result = row[0] if row else None
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


def _user(env, uid):
    """The res.users record these guards are about — resolved from the uid
    they were passed, not from env.user.

    In an HTTP request the two are the same user, so this changes no
    behaviour there. But every other function here is keyed on uid, and
    reading env.user instead meant the promoter guards silently answered
    for whoever owned the environment: under an admin/superuser env they
    reported "not restricted" for a uid that is restricted, which is a
    guard that cannot be tested and would quietly follow the wrong user if
    these were ever called with an env that is not the viewer's."""
    return env["res.users"].browse(uid).sudo()


def promoter_list_view_blocked(env, uid, source):
    """Whether this user may not drill a promoter chart through to a native
    list view.

    "Promoter Sales Donot Show ListView"
    (promoter.group_promoter_sales_donotshow) is a LIST-VIEW restriction:
    the promoter module implements it by overriding search_fetch on
    promoter.showroom / promoter.showroom.sales / sales.target to return
    an empty recordset, so members see no rows in any list of those
    models. It is not a restriction on the aggregate figures — the whole
    point of giving someone the dashboard is that they see the totals.

    So the guard belongs on the drill-through, not on the numbers: the
    charts and KPIs are computed for these users like anyone else, and
    clicking past the last drill level is refused with a message instead
    of opening a list that search_fetch would render empty anyway (which
    read as "the dashboard is broken", not "you may not see this")."""
    return source in _PROMOTER_SOURCES and \
        _user(env, uid).has_group("promoter.group_promoter_sales_donotshow")


def _promoter_guard_clause(env, uid, binder, source):
    """Reproduces the promoter module's own ROW-SCOPING for the raw-SQL
    path (see promoter/models/promoter_showroom_sales.py's search_fetch) —
    raw SQL bypasses that ORM-level override entirely, so equivalent
    scoping must be reapplied here for every promoter-family source,
    regardless of which board is being viewed:
      - group_promoter_user (the mobile field promoter): sees only their
        own dealer_id/showroom (matches search_fetch's domain addition).
    Back-office/admin users get no extra restriction here, matching the
    ORM's own default (no matching group -> unrestricted search_fetch).

    group_promoter_sales_donotshow is deliberately NOT handled here — it
    restricts the list view, not the aggregates; see
    promoter_list_view_blocked()."""
    if source not in _PROMOTER_SOURCES:
        return None
    user = _user(env, uid)
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
      - "@franchise:<name>" -> product.category id resolved by NAME, for the
                             franchise filter the boards' filter bar sends
                             (same by-name-not-by-id reasoning as @region).
    """
    if value == "%UID":
        return uid
    if isinstance(value, str) and value.startswith("@region:"):
        return region_id_by_name(env, value[len("@region:"):])
    if isinstance(value, str) and value.startswith("@franchise:"):
        return franchise_id_by_name(env, value[len("@franchise:"):])
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
    # Plain 2-tuple, and staying that way: work_center_group.name is a
    # plain varchar. It was made translate=True on 2026-08-28 purely so
    # these boards could show an Arabic Region caption, which retyped the
    # column, cascade-dropped three views and broke every Region chart on
    # the server that had this code without that upgrade. A dashboard does
    # not get to change another module's schema — see the note on
    # work.center.group.name in machine_repair_management.
    "work_center_group_id": ("work_center_group", "name"),
    "work_center_id": ("work_center_location", "name"),
    "service_warranty_id": ("service_warranty", "name"),
    "technician_id": "res_users_partner_name",
    "default_work_location": ("work_center_location", "name"),
    "user_id": "res_users_partner_name",
    # timeline attribution columns — the user who performed a given
    # status transition (see _TASK_TIMELINE_CTE_SQL)
    "scheduled_by_uid": "res_users_partner_name",
    "closed_by_uid": "res_users_partner_name",
    "parts_handler_uid": "res_users_partner_name",
    # work_center_group.name again (jobcards' region alias) — plain
    # varchar, see work_center_group_id above.
    "region": ("work_center_group", "name"),
    "city": ("work_center_location", "name"),
    # franchise/brand — a top-level product.category, on all three service
    # sources (jobcards / usergroup / message_log)
    "franchise_id": ("product_category", "name"),
    # promoter_showrooms / promoter_sales — region_id/city_id are
    # promoter.showroom's own res.region/res.city columns (distinct from
    # jobcards' "region"/"city" aliases above, which point at
    # work_center_group/work_center_location instead).
    # The optional 3rd element is documentation, not a switch: it records
    # that this column is translate=True SOMEWHERE (res_region.name became
    # jsonb the first time base_territory was upgraded; res_city.name is
    # jsonb in core). _groupby_sql reads every lookup the same way, so a
    # column that is jsonb here and varchar on another server works either
    # way and neither needs a marker to be added or removed.
    "region_id": ("res_region", "name", "jsonb"),
    "city_id": ("res_city", "name", "jsonb"),
    "showroom_pk": ("promoter_showroom", "name"),
    "showroom_id": ("promoter_showroom", "name"),
    "group_id": ("product_category", "name"),
    "subgroup_id": ("product_category", "name"),
    # sales_comparison — "period" is the synthetic (year || '-' || month)
    # column computed in the CTE itself, not a plain id needing a join;
    # see _groupby_sql's "period_month_label" branch below.
    "period": "period_month_label",
    # sales.target.city and .region are related Chars to
    # showroom_id.city.name / showroom_id.region_id.name, both
    # translate=True — Odoo mirrors the source field's jsonb storage onto
    # the related column too, even though the Python side declares plain
    # Char. Verified against information_schema: sales_target.city AND
    # sales_target.region are both jsonb.
    #
    # region used to be exempt (res_region.name was plain varchar when this
    # dict was written) and the exemption outlived the reason: once
    # res_region.name was made translatable, "Sales (Actual vs Target) -
    # Region wise" started handing psycopg2 a dict as the drill code and
    # raised "can't adapt type 'dict'" the moment a bar was clicked. Only a
    # drill hit it, which is why every level-0 board sweep stayed green.
    "sc_city": "jsonb_inline",
    "sc_region": "jsonb_inline",
    # contracts — salesman (res.users, delegated to res.partner.name: res_users
    # itself has no physical "name" column, see _RES_USERS_NAME_EXPR) and
    # customer (res.partner.name, plain varchar, not translate=True).
    "sales_person_user_id": "res_users_partner_name",
    "partner_id": ("res_partner", "name"),
    # budget_compare — the four dimension masters dashboard_groups owns.
    "partner_classification_id": ("partner_classification", "complete_name"),
    "salestype_group_id": ("salestypes_group", "salgrp_name"),
    "main_category_id": ("main_category", "maincat_name"),
    "sub_category_id": ("sub_category", "subcat_name"),
}

# Deliberately nested rather than the more obvious single
# "FROM res_users ru2 JOIN res_partner rp ON rp.id = ru2.partner_id
#  WHERE ru2.id = {col}":
#
# {col} is a bare column name from the enclosing source CTE, and
# res_partner has a column of its own called user_id (the customer's
# salesperson). So in the joined form, a groupby on the "user_id" field
# resolved "WHERE ru2.id = user_id" against res_partner's user_id — the
# innermost scope wins — instead of the outer CTE's, and the lookup
# returned NULL. Charts grouped by user then fell back to
# COALESCE(..., col::text) and rendered raw database ids ("2", "161")
# where the user's name belongs.
#
# Here res_partner is reached from a SIBLING subquery instead, so it is
# never in an enclosing scope of the {col} reference: the only scopes
# above that reference are res_users (which has no user_id column) and
# the source CTE itself. Simply nesting the other way round is not
# enough — res_partner would still enclose the reference and capture it
# exactly the same way.
_RES_USERS_NAME_EXPR = (
    "(SELECT (SELECT rp.name FROM res_partner rp WHERE rp.id = ru2.partner_id) "
    "FROM res_users ru2 WHERE ru2.id = {col})"
)


# Display label for a bucket whose groupby value is NULL, by
# DBM-vocabulary field name. Only the LABEL is substituted: the bucket's
# CODE stays NULL, so clicking one still takes _drill_filter_clause's
# "IS NULL" branch and filters exactly the rows that have no value —
# baking the text into the code instead would compare a column against
# the literal 'No Region' and match nothing.
#
# Applied only where the column is genuinely absent, never where a lookup
# merely failed: COALESCE tries the display name first, then the raw id,
# and only then this. Fields with no entry here keep rendering their NULL
# bucket as "None", which is what every board showed before.
_NULL_LABEL = {
    # the work.center.group region, under each name the sources give it
    # (jobcards/usergroup's work_center_group_id, message_log's "region")
    "work_center_group_id": "No Region",
    "region": "No Region",
    # promoter's own res.region — a different table, same words
    "region_id": "No Region",
    # sales.target.region: plain text, no id lookup (see _LABEL_LOOKUP)
    "sc_region": "No Region",
    "franchise_id": "No Franchise",
}


# These labels are the engine's own words, not database values, so unlike
# every other bucket label they are ours to translate — and they have to be
# translated HERE. pbi_i18n.js is documented as touching static chrome only
# ("never call t() on a value that came out of a database row"), and by the
# time a bucket label reaches the client it is indistinguishable from the
# real region names sitting beside it in the same array.
_NULL_LABEL_AR = {
    "No Region": "بدون منطقة",
    "No Franchise": "بدون وكالة",
}


def _lang_for(env):
    """Current session's language code (e.g. 'en_US', 'ar_001'), for
    reading translate=True jsonb columns (res_city.name) in the viewer's
    own language rather than a hardcoded one — same field the ORM itself
    would use (record.name resolves via env.context['lang'])."""
    return env.context.get("lang") or env.user.lang or "en_US"


def _translated_text_expr(col, lang):
    """Read a translate=True Char column as plain text, whether the live
    column is jsonb or varchar.

    The storage type is not ours to assume. Several modules declare the
    same models these labels come from (three declare res.region alone),
    and the column's type is decided by whichever of them was upgraded
    LAST — so the two servers this code runs on have drifted apart on
    exactly that before: a still-varchar res_region.name met a literal
    name->>'en_US' and every board grouped by region died with "operator
    does not exist: character varying ->> unknown".

    to_jsonb() normalises both shapes. A jsonb translation dict passes
    through untouched; a varchar becomes a jsonb *string*, whose ->>'key'
    is NULL rather than an error. The CASE tail therefore supplies the raw
    text for exactly the varchar case, and still leaves a genuine
    translation dict that carries neither key NULL, as before.
    """
    return (f"COALESCE(to_jsonb({col})->>'{lang}', to_jsonb({col})->>'en_US', "
            f"CASE WHEN jsonb_typeof(to_jsonb({col})) = 'string' "
            f"THEN {col}::text END)")


def _null_label_for(field, env):
    """The display text for `field`'s NULL bucket, in the viewer's own
    language — same session language the jsonb label lookups above read.
    None for a field that has no NULL label, which keeps its previous
    rendering."""
    label = _NULL_LABEL.get(field)
    if not label:
        return None
    lang = _lang_for(env) if env is not None else "en_US"
    if lang.lower().startswith("ar"):
        return _NULL_LABEL_AR.get(label, label)
    return label


def _groupby_sql(field_map, groupby, env=None):
    # "week" is NOT handled here — see run_breakdown's week branch: a week
    # level is a LEFT JOIN onto the period's full week series (empty weeks
    # included), not a column expression the way month_year/plain fields
    # are.
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
            text_expr = _translated_text_expr(col, lang)
            null_label = _null_label_for(field, env)
            if null_label:
                # Safe to fold into the code as well as the label here, and
                # only here: this branch's code and label are the SAME
                # expression, so _drill_filter_clause rebuilds it verbatim
                # and "= 'No Region'" matches exactly the rows whose jsonb
                # is absent. (In the id-lookup branches the code is the raw
                # id, where a text literal would match nothing.)
                text_expr = f"COALESCE({text_expr}, {_sql_str(null_label)})"
            return text_expr, text_expr
        if spec == "res_users_partner_name":
            label_expr = _RES_USERS_NAME_EXPR.format(col=col)
        elif spec == "period_month_label":
            # col is already "(year || '-' || month)" (YYYY-MM) — render
            # as "Mon YYYY" for display while code stays the sortable
            # YYYY-MM string.
            label_expr = f"to_char(to_date({col}, 'YYYY-MM'), 'Mon YYYY')"
        else:
            # One expression for every id lookup, 2-tuple and 3-tuple alike.
            # The third element now only DOCUMENTS that a column is known to
            # be translated somewhere; it no longer selects a different
            # reader, because none of these columns belongs to us. Whether
            # any of them is jsonb or varchar is the declaring module's
            # decision (and, for the ones several modules declare, a
            # decision that changes with upgrade order), so reading them
            # through _translated_text_expr is what keeps a dashboard from
            # breaking — or from needing another module changed on its
            # behalf. A translation is shown when the column carries one.
            table, name_col = spec[0], spec[1]
            lang = _lang_for(env) if env is not None else "en_US"
            label_expr = (
                f"(SELECT {_translated_text_expr(name_col, lang)} "
                f"FROM {table} WHERE id = {col})"
            )
        null_label = _null_label_for(field, env)
        if null_label:
            return col, f"COALESCE({label_expr}, {col}::text, {_sql_str(null_label)})"
        return col, f"COALESCE({label_expr}, {col}::text)"
    null_label = _null_label_for(field, env)
    if null_label:
        # A plain (non-lookup) column — its own value is the label, so the
        # fallback is the only thing wrapped around it.
        return col, f"COALESCE({col}::text, {_sql_str(null_label)})"
    return col, col


# What "count" means on a source whose rows are NOT the records the board
# is talking about. message_log holds one row per status TRANSITION on a
# project.task, so count(*) there answers "how many status changes", while
# every item reading it is named for the job cards / tasks themselves
# ("Job Cards - Users wise", "Tasks - Month wise", "Closed Tasks") — a
# coordinator who scheduled, put on hold and closed the same card was
# counted three times. The drill-through that bar opens is a DISTINCT
# task_id lookup (see run_terminal_domain), so the list always came back
# shorter than the number that opened it — reported on "Service Analysis
# (CRD)" as the per-coordinator bars disagreeing with their own list view.
#
# Counting distinct task_ids makes the bar and the list it opens the same
# number by construction, and makes every message_log item count the thing
# its own name promises. Sources whose rows already ARE the records (one
# row per task/request/contract) keep plain count(*) and are unaffected.
_SOURCE_COUNT_EXPR = {
    "message_log": "count(DISTINCT task_id)",
}


def _measure_sql(measure, period_months=1, source=None):
    """The SELECT-list aggregate for a chart item's measure. period_months
    is only consulted by 'expr' measures that reference it (currently
    technician utilization, whose 176-hour denominator scales with the
    period the viewer selected). source picks the row-identity-aware count
    expression for a measure-less item (see _SOURCE_COUNT_EXPR)."""
    if measure is None:
        return _SOURCE_COUNT_EXPR.get(source, "count(*)")
    if measure.agg == "expr":
        return measure.expr.format(period_months=float(period_months or 1))
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
def ensure_database_indexes(env):
    """Ensures critical indexes exist on tables backing PBI dashboards."""
    cache = _request_cache(env)
    if cache.get("db_indexes_checked"):
        return
    cr = env.cr
    try:
        cr.execute("SELECT to_regclass('project_task')")
        if cr.fetchone()[0]:
            cr.execute("CREATE INDEX IF NOT EXISTS idx_project_task_service_dt ON project_task (active, service_created_datetime)")
        cr.execute("SELECT to_regclass('mail_message')")
        if cr.fetchone()[0]:
            cr.execute("CREATE INDEX IF NOT EXISTS idx_mail_message_model_res ON mail_message (model, res_id)")
        cr.execute("SELECT to_regclass('mail_tracking_value')")
        if cr.fetchone()[0]:
            cr.execute("CREATE INDEX IF NOT EXISTS idx_mail_tracking_msg_field ON mail_tracking_value (mail_message_id, field_id)")
        cr.execute("SELECT to_regclass('product_lines')")
        if cr.fetchone()[0]:
            cr.execute("CREATE INDEX IF NOT EXISTS idx_product_lines_task_id ON product_lines (project_task_id)")
    except Exception:
        pass
    cache["db_indexes_checked"] = True


# Columns worth an index on a materialized source table — the ones every
# board over that source filters or groups by. Sources absent from here are
# small enough to scan.
_SOURCE_TABLE_INDEXES = {
    "jobcards": (
        "work_center_group_id",
        "work_center_id",
        "technician_id",
        "job_card_status",
        "action_status",
        "service_created_datetime",
        "franchise_id",
    ),
}


def _ensure_source_table(env, source, date_from, date_to):
    """Materializes a source CTE once per request transaction into a temp table.

    A dashboard page runs 10-18 queries for the same (source, date_from, date_to).
    Re-evaluating a heavy multi-table CTE (such as jobcards, which scans tracking
    logs and aggregates lines) on every single query causes massive cumulative
    latency (15 x 3s = 45s).

    Materializing the date-scoped slice once into an indexed TEMP TABLE on the
    request's transaction turns every subsequent query into an indexed sub-millisecond
    lookup, cutting page load time by 90-95%.
    """
    ensure_database_indexes(env)
    cache = _request_cache(env)
    key = ("source_table", source, str(date_from), str(date_to))
    if key in cache:
        return cache[key]

    cte_sql, field_map, cte_name = _SOURCE_CTE[source]
    temp_tbl = f"pbi_tmp_{source}"
    binder = ParamBinder()
    binder.params["date_from"] = date_from
    binder.params["date_to"] = date_to
    # A SAVEPOINT, not a bare try: a statement that fails here poisons the
    # whole request transaction, so every later query dies with "current
    # transaction is aborted" and the fallback below can never actually run.
    # Rolling back to a savepoint taken here leaves the SET LOCAL planner
    # hints set before it in place.
    try:
        with env.cr.savepoint(flush=False):
            env.cr.execute(f"DROP TABLE IF EXISTS {temp_tbl}")
            env.cr.execute(
                f"CREATE TEMP TABLE {temp_tbl} ON COMMIT DROP AS "
                f"WITH {cte_sql} SELECT * FROM {cte_name}",
                binder.params
            )
            for col in _SOURCE_TABLE_INDEXES.get(source, ()):
                # No IF NOT EXISTS, and no index name: Postgres rejects the
                # two together (an unnamed index cannot be looked up), and
                # neither is needed — the DROP above takes the previous
                # table's indexes with it, and a TEMP table's indexes live in
                # this session's own schema, so the generated name is private
                # to it and cannot collide with a concurrent request.
                env.cr.execute(f"CREATE INDEX ON {temp_tbl} ({col})")
            env.cr.execute(f"ANALYZE {temp_tbl}")
        res = (temp_tbl, field_map, temp_tbl, True)
    except Exception:
        _logger.warning("board_sql: temp table for source %s failed, falling back to the inline CTE", source, exc_info=True)
        res = (cte_sql, field_map, cte_name, False)

    cache[key] = res
    return res


def _source_ctx(item: ChartItemConfig):
    cte_sql, field_map, cte_name = _SOURCE_CTE[item.source]
    return cte_sql, field_map, cte_name


def run_kpi(env, uid, board: BoardConfig, item: ChartItemConfig, date_from, date_to, period_months=1):
    cte_sql, field_map, table_name, is_temp = _ensure_source_table(env, item.source, date_from, date_to)

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
        with_prefix = f"WITH {cte_sql} " if not is_temp else ""
        sql = (f"{with_prefix}SELECT {_measure_sql(measure, period_months, item.source)} AS v "
               f"FROM {table_name} WHERE 1=1{where}")
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


# The bucket series every "week" level is built on: one row per calendar
# (Monday-start) week the SELECTED period touches, from the week holding
# date_from through the week holding date_to. Deliberately derived from the
# period alone, never from the data — a week with no records is still a
# week of that month, and dropping it silently renumbered the following
# week as "Week-1" (August 2026 starts on a Saturday: its real first week
# was empty, so "Week-1" showed the 3-9 Aug week's numbers). Both the
# breakdown and the drill-down reverse lookup read this same definition,
# so a "Week-N" label always names the same week in both.
_WEEK_SERIES_SQL = """
        SELECT generate_series(
            date_trunc('week', %(date_from)s::timestamp),
            date_trunc('week', %(date_to)s::timestamp),
            interval '7 days'
        ) AS week_start
"""


def _resolve_week_bucket(env, params, week_label):
    """Reverses a "Week-N" label back into the real date_trunc('week', ...)
    value it names — the Nth week of _WEEK_SERIES_SQL, counted from the
    week containing date_from. Reads the period, not the result set, so an
    empty week in the middle never shifts what the later labels mean."""
    try:
        n = int(str(week_label).split("-")[1])
    except (ValueError, IndexError):
        return None
    if n < 1:
        return None
    sql = f"SELECT week_start FROM ({_WEEK_SERIES_SQL}) _w ORDER BY week_start OFFSET %(_week_offset)s LIMIT 1"
    p = dict(params)
    p["_week_offset"] = n - 1
    env.cr.execute(sql, p)
    row = env.cr.fetchone()
    return row[0] if row else None


def _drill_filter_clause(env, field_map, item, idx, code, binder):
    """The WHERE fragment that filters rows down to an already-clicked
    bucket at drill level `idx`. A "week" level needs the reverse-lookup
    above; month_year/plain fields translate directly via the same
    bucketing expression their breakdown was computed with (comparing the
    raw column straight to the label, e.g. "2026-03", is a Postgres type
    error, not just wrong results)."""
    fields_shown = _fields_shown(item)
    level_cfg = _level_groupby_config(fields_shown[idx], item, idx)
    if level_cfg.interval == "week":
        raw_col = field_map[fields_shown[idx]]
        week_start = _resolve_week_bucket(env, binder.params, code)
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


def run_breakdown(env, uid, board: BoardConfig, item: ChartItemConfig, date_from, date_to, drill_path,
                  period_months=1):
    """drill_path: list of {"code": ...} already clicked, one per level of
    _fields_shown(item) in order. Returns the breakdown for the NEXT level,
    or None once past the item's configured drill chain (caller should
    treat that as terminal — see run_terminal_domain)."""
    cte_sql, field_map, table_name, is_temp = _ensure_source_table(env, item.source, date_from, date_to)
    fields_shown = _fields_shown(item)
    idx = len(drill_path or [])
    if idx >= len(fields_shown):
        return None

    binder = ParamBinder()
    binder.params["date_from"] = date_from
    binder.params["date_to"] = date_to
    clauses = _base_where(env, uid, board, item, field_map, binder)
    for i, entry in enumerate(drill_path or []):
        clauses.append(_drill_filter_clause(env, field_map, item, i, entry["code"], binder))
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    level_cfg = _level_groupby_config(fields_shown[idx], item, idx)
    measure_sql = _measure_sql(item.measure, period_months, item.source)
    # measure_2 is an optional second series on plain bar items (e.g.
    # "Employee Performance Analysis - Estimated vs Actual Hours" —
    # expected_completion_hours vs total_worked_hours per region) — the
    # drill/click behaviour is unchanged, it just renders a 2nd bar per
    # category (see service_dashboard.js renderChart).
    measure2_sql = f", {_measure_sql(item.measure_2, period_months, item.source)} AS value2" if item.measure_2 else ""

    if level_cfg.interval == "week":
        raw_col = field_map[fields_shown[idx]]
        # LEFT JOIN onto the full week series (see _WEEK_SERIES_SQL), so a
        # week of the selected period that holds no records still reports a
        # bucket, with 0, instead of vanishing and renumbering its
        # successors. The join is on the real week start, so the numbering
        # is positional — Week-1 is always the week containing date_from.
        value2_select = ", COALESCE(_agg.value2, 0) AS value2" if item.measure_2 else ""
        with_cte = f"{cte_sql}, " if not is_temp else ""
        sql = f"""
            WITH {with_cte}_weeks AS ({_WEEK_SERIES_SQL}),
            _agg AS (
                SELECT date_trunc('week', {raw_col}) AS week_start, {measure_sql} AS value{measure2_sql}
                FROM {table_name}{where}
                GROUP BY 1
            )
            SELECT 'Week-' || ROW_NUMBER() OVER (ORDER BY _weeks.week_start) AS code,
                   'Week-' || ROW_NUMBER() OVER (ORDER BY _weeks.week_start) AS label,
                   COALESCE(_agg.value, 0) AS value{value2_select}
            FROM _weeks LEFT JOIN _agg ON _agg.week_start = _weeks.week_start
            ORDER BY _weeks.week_start ASC
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
        with_prefix = f"WITH {cte_sql} " if not is_temp else ""
        sql = (
            f"{with_prefix}SELECT {code_col} AS code, {label_col} AS label, {measure_sql} AS value{measure2_sql} "
            # NULLS LAST: Postgres sorts NULLs FIRST on a DESC order, so a
            # measure that can aggregate to NULL — every timeline-derived
            # interval, which is deliberately NULL rather than 0 for cards
            # that never reached the end state — would fill the top of the
            # chart with empty categories and push the real values past
            # the item's LIMIT, off the visible axis entirely.
            f"FROM {table_name}{where} GROUP BY 1, 2 "
            f"ORDER BY {order_expr} {order_dir} NULLS LAST LIMIT {item.limit}"
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
    cte_sql, field_map, table_name, is_temp = _ensure_source_table(env, item.source, date_from, date_to)
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

    with_prefix = f"WITH {cte_sql} " if not is_temp else ""
    sql = (
        f"{with_prefix}SELECT {', '.join(select_parts)} "
        f"FROM {table_name}{where} ORDER BY {order_expr} {order_dir} LIMIT {item.limit}"
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


# The two rewrites _translate_jobcards_domain performs when turning a
# DBM-vocabulary domain into a real project.task one: a straight rename, and
# a search-only field expanded into the real column it stands for.
_JOBCARDS_DOMAIN_RENAMES = {"job_card_status": "job_card_state",
                            "franchise_id": "product_category_id"}
_JOBCARDS_DOMAIN_EXPANDED = frozenset(["is_user_work_location"])


def _jobcards_domain_translatable(env, model, fields_used):
    """Whether every DBM-vocabulary field in fields_used has a real
    counterpart on `model` once those rewrites are applied.

    Several jobcards columns exist only inside the CTE and have no field
    behind them — default_work_location, for one, is joined from the
    *user's* work-location map rather than stored on the task — so a domain
    naming one is not a domain Odoo can execute ("ValueError: Invalid field
    project.task.default_work_location in leaf"). Checked against the real
    model rather than a hand-kept list, so a config that starts grouping on
    a new CTE-only column degrades to the id-lookup path instead of raising.
    """
    model_fields = env[model]._fields
    for f in fields_used:
        if f in _JOBCARDS_DOMAIN_EXPANDED:
            continue
        if _JOBCARDS_DOMAIN_RENAMES.get(f, f) not in model_fields:
            return False
    return True


def _has_row_guard(env, uid, source):
    """Whether a row-level guard clause (technician scoping, promoter
    scoping) applies to the current user for this source — i.e. whether
    the raw-SQL path is restricting rows in a way no ORM domain built from
    the config alone would reproduce."""
    binder = ParamBinder()
    return bool(_technician_guard_clause(env, uid, binder, source)) or \
        bool(_promoter_guard_clause(env, uid, binder, source))


def _translate_jobcards_domain(env, uid, domain):
    """A DBM-vocabulary domain (board scope + item domain + drill entries)
    rewritten as a real project.task ORM domain: "%UID"/"@region:<name>"
    symbols resolved, job_card_status renamed to its real column, and
    is_user_work_location — a search-only computed field with no column
    behind it — expanded into the same work_center_id check the callable
    itself performs."""
    domain = [
        (f, op, [_substitute_symbol(v, uid, env) for v in val] if isinstance(val, (list, tuple))
         else _substitute_symbol(val, uid, env))
        for f, op, val in domain
    ]
    translated = []
    for f, op, v in domain:
        if f in _JOBCARDS_DOMAIN_RENAMES:
            f = _JOBCARDS_DOMAIN_RENAMES[f]
        elif f == "is_user_work_location":
            allowed = get_user_work_location_ids(env, uid)
            negate = not ((op == "=" and v) or (op == "!=" and not v))
            f, op, v = "work_center_id", ("not in" if negate else "in"), (allowed or [0])
        translated.append((f, op, v))
    return translated


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
    # Timeline-derived fields (status timestamps, the intervals between
    # them, and the transition-author attribution columns) are computed in
    # the CTE from mail_tracking_value — none of them is a project.task
    # column, so an item that groups, drills or filters on one cannot take
    # the field-rename fast path and falls through to the id-lookup path
    # below (which re-runs the very same CTE and hands back ("id", "in",
    # [...]), so the drilled list still matches the chart exactly).
    uses_timeline_field = (
        any(f in _TIMELINE_FIELDS for f, _op, _v in list(board.scope) + list(item.domain))
        or any(f in _TIMELINE_FIELDS for f in fields_shown)
    )
    # A row-level guard (technician / promoter) is a SQL clause with no
    # project.task-domain equivalent, so an item under one can never take
    # the ORM fast path — it would hand back a domain that shows the whole
    # company's cards. Those fall through to the id-lookup path below,
    # which applies the guard like every other query here does.
    fields_used = [f for f, _op, _v in list(board.scope) + list(item.domain)] + fields_shown
    if (item.source == "jobcards" and item.record_model == "project.task"
            and not uses_is_my_user_group and not uses_date_interval and not uses_timeline_field
            and not _has_row_guard(env, uid, item.source)
            and _jobcards_domain_translatable(env, item.record_model, fields_used)):
        domain = list(board.scope) + list(item.domain)
        for i, entry in enumerate(drill_path or []):
            domain.append((fields_shown[i], "=", entry["code"]))
        translated = _translate_jobcards_domain(env, uid, domain)
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
    cte_sql, field_map, table_name, is_temp = _ensure_source_table(env, item.source, date_from, date_to)
    binder = ParamBinder()
    binder.params["date_from"] = date_from
    binder.params["date_to"] = date_to
    clauses = _base_where(env, uid, board, item, field_map, binder)
    for i, entry in enumerate(drill_path or []):
        clauses.append(_drill_filter_clause(env, field_map, item, i, entry["code"], binder))
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    id_col = _TERMINAL_ID_COL.get(item.source, "task_id")
    with_prefix = f"WITH {cte_sql} " if not is_temp else ""
    sql = f"{with_prefix}SELECT DISTINCT {id_col} FROM {table_name}{where}"
    rows = _run_query(env, sql, binder.params)
    ids = [r[id_col] for r in rows if r[id_col]]
    return item.record_model, [("id", "in", ids or [0])]




# ---------------------------------------------------------------------
# "Formula & Details" — the record-level audit behind a chart's bars.
#
# A bar says "this technician logged 96 hours"; this returns the job cards
# that made up the 96, each with the timestamps the formula read and the
# value it produced, so the figure can be recomputed by hand. Which
# columns and which formula text comes entirely from the item's
# DetailConfig (board_config.py) — there is no per-chart SQL here.
#
# Only 'jobcards'-sourced items are supported: it is the one source with
# one row per record (message_log has one row per transition, so a record
# would appear many times and its hours would multiply).
# ---------------------------------------------------------------------
_DETAIL_SUPPORTED_SOURCES = ("jobcards",)


def _fmt_detail_hours(hours):
    """Float hours -> "H:MM". Matches the client-side formatter."""
    if hours is None:
        return "-"
    neg = hours < 0
    hours = abs(hours)
    h_int = int(hours)
    m_int = int(round((hours - h_int) * 60))
    if m_int >= 60:
        h_int += 1
        m_int = 0
    return "%s%d:%02d" % ("-" if neg else "", h_int, m_int)


def _detail_cell(value, kind):
    """One row value, rendered for display. Returns (raw, formatted)."""
    if value is None:
        return None, "-"
    if kind == "datetime":
        return value.strftime("%Y-%m-%d %H:%M:%S"), value.strftime("%Y-%m-%d %H:%M:%S")
    if kind == "hours":
        return round(float(value), 2), _fmt_detail_hours(float(value))
    if kind == "number":
        return round(float(value), 2), f"{float(value):,.2f}"
    # A whole-number column — a 1/0 denominator contribution, a count —
    # where "number"'s two decimals would read as noise ("1.00").
    if kind == "integer":
        return int(value), f"{int(value):,}"
    return value, str(value)


def _entity_id_list(entity_id):
    """The modal's entity picker is multi-select, so what arrives here is
    "all"/None (no restriction), a single id, a list of ids, or the
    comma-separated string the export URL carries. Normalised to a list of
    ints; anything unparseable is dropped rather than raising, so a stale
    bookmark degrades to "no restriction" instead of a 500."""
    if entity_id in (None, "", "all", []):
        return []
    if isinstance(entity_id, str):
        parts = [p for p in entity_id.split(",") if p.strip() and p.strip() != "all"]
    elif isinstance(entity_id, (list, tuple, set)):
        parts = list(entity_id)
    else:
        parts = [entity_id]
    out = []
    for p in parts:
        try:
            out.append(int(p))
        except (ValueError, TypeError):
            continue
    return out


def run_chart_detail(env, uid, board: BoardConfig, item: ChartItemConfig, date_from, date_to,
                     entity_id=None, period_months=1.0):
    """Records, formula metadata and summary figures behind one chart item.

    ``entity_id`` narrows to one or more technicians/coordinators (the
    modal's multi-select pushes its selection down here rather than
    filtering in the browser, so the export and the on-screen table
    agree). Accepts a single id, a list of ids, or a comma-separated
    string; "all"/None means every entity.
    """
    detail = getattr(item, "detail", None)
    if not detail:
        raise ValueError(f"Chart {item.key!r} has no Formula & Details configuration.")
    if item.source not in _DETAIL_SUPPORTED_SOURCES:
        raise ValueError(f"Formula & Details is not available for {item.source!r} charts.")

    cte_sql, field_map, table_name, is_temp = _ensure_source_table(env, item.source, date_from, date_to)

    def col(name):
        """Config-declared column -> its real CTE column, or a clear error.

        Every name here comes from board_config, never from the request,
        but resolving through field_map keeps a config typo a startup-time
        error message instead of a raw SQL syntax failure.
        """
        real = field_map.get(name)
        if not isinstance(real, str):
            raise ValueError(f"Unknown detail column {name!r} for source {item.source!r}.")
        return real

    binder = ParamBinder()
    binder.params["date_from"] = date_from
    binder.params["date_to"] = date_to

    entity_col = col(detail.entity_col)
    clauses = _base_where(env, uid, board, item, field_map, binder)
    entity_ids = _entity_id_list(entity_id)
    if entity_ids:
        clauses.append(f"{entity_col} = ANY({binder.bind(entity_ids)})")

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with_prefix = f"WITH {cte_sql}, " if not is_temp else "WITH "

    def detail_select(c):
        # A derived column (DetailColumn.expr) carries its own SQL over the
        # jc alias — the row's contribution to a denominator, say — and so
        # never goes through col()/field_map, which only knows real columns.
        if getattr(c, "expr", None):
            return f"({c.expr}) AS {c.key}"
        return f"jc.{col(c.col)} AS {c.key}"

    extra_selects = ", ".join(detail_select(c) for c in detail.columns)
    extra_selects = (extra_selects + ",\n            ") if extra_selects else ""

    if detail.value_expr:
        value_sql = detail.value_expr
    elif detail.value_col:
        value_sql = f"jc.{col(detail.value_col)}"
    else:
        value_sql = "NULL::float"

    sql = f"""
        {with_prefix}_filtered_detail AS (
            SELECT * FROM {table_name}{where}
        )
        SELECT
            jc.task_id AS task_id,
            COALESCE(jc.name, 'JC-' || jc.task_id) AS name,
            jc.{entity_col} AS entity_id,
            COALESCE(ent_partner.name, 'Unassigned') AS entity_name,
            COALESCE(wcl.name, '-') AS work_center_name,
            COALESCE(wcg.name, '-') AS region_name,
            COALESCE(jc.job_card_status, '-') AS status,
            {extra_selects}({value_sql}) AS value
        FROM _filtered_detail jc
        LEFT JOIN res_users ent_user ON ent_user.id = jc.{entity_col}
        LEFT JOIN res_partner ent_partner ON ent_partner.id = ent_user.partner_id
        LEFT JOIN work_center_location wcl ON wcl.id = jc.work_center_id
        LEFT JOIN work_center_group wcg ON wcg.id = jc.work_center_group_id
        ORDER BY ent_partner.name ASC, ({value_sql}) DESC NULLS LAST, jc.name ASC
    """

    rows = _run_query(env, sql, binder.params)

    is_count = detail.agg == "count"
    records = []
    entity_map = {}
    total_value = 0.0
    counted = 0

    for r in rows:
        raw_value = r.get("value")
        has_value = raw_value is not None
        value = float(raw_value) if has_value else None
        if has_value:
            total_value += value
            counted += 1

        e_id = r.get("entity_id")
        e_name = r.get("entity_name")
        if e_id:
            bucket = entity_map.setdefault(e_id, {"id": e_id, "name": e_name, "count": 0, "value": 0.0})
            bucket["count"] += 1
            if has_value:
                bucket["value"] += value

        record = {
            "task_id": r.get("task_id"),
            "name": r.get("name"),
            "entity_id": e_id,
            "entity_name": e_name,
            "work_center": r.get("work_center_name"),
            "region": r.get("region_name"),
            "status": r.get("status"),
            # A row whose interval never completed contributes nothing to
            # an average — showing it greyed rather than hiding it is the
            # whole point of an audit table.
            "counted": bool(is_count or has_value),
            "value": None if value is None else round(value, 2),
            "value_formatted": (_fmt_detail_hours(value) if detail.value_kind == "hours"
                                else ("-" if value is None else f"{value:,.2f}")) if not is_count else "",
        }
        for c in detail.columns:
            raw, formatted = _detail_cell(r.get(c.key), c.kind)
            record[c.key] = formatted
            record[c.key + "_raw"] = raw
        records.append(record)

    total_records = len(records)
    avg_value = (total_value / counted) if counted else 0.0

    def as_pair(v):
        if detail.value_kind == "hours":
            return round(v, 2), _fmt_detail_hours(v)
        return round(v, 2), f"{v:,.2f}"

    total_num, total_fmt = as_pair(total_value)
    avg_num, avg_fmt = as_pair(avg_value)

    entities = sorted(entity_map.values(), key=lambda x: str(x["name"]).lower())
    for e in entities:
        e_num, e_fmt = as_pair(e["value"])
        e["value"] = e_num
        e["value_formatted"] = e_fmt if not is_count else str(e["count"])

    summary = {
        "agg": detail.agg,
        "entity_label": detail.entity_label,
        "record_label": detail.record_label,
        "value_label": detail.value_label,
        "value_kind": detail.value_kind,
        "total_records": total_records,
        "counted_records": total_records if is_count else counted,
        "total_value": total_num,
        "total_value_formatted": total_fmt,
        "avg_value": avg_num,
        "avg_value_formatted": avg_fmt,
        "entities": entities,
    }

    if detail.agg == "utilization":
        # The divisor the chart itself uses — MONTHLY_WORKING_HOURS scaled
        # by the months the viewer's date filter spans, so "This Year"
        # divides by 176 * 12 rather than reporting ~1200%.
        months = float(period_months or 1.0) if detail.period_scaled else 1.0
        divisor = months * MONTHLY_WORKING_HOURS
        summary["divisor"] = round(divisor, 2)
        summary["divisor_label"] = (
            f"{months:g} month(s) x {MONTHLY_WORKING_HOURS:g} working hours = {divisor:,.2f}"
        )
        summary["utilization_pct"] = round((total_value / divisor * 100.0) if divisor else 0.0, 2)
        for e in entities:
            e["utilization_pct"] = round((e["value"] / divisor * 100.0) if divisor else 0.0, 2)

    formula = {
        "title": f"{item.name} — Calculation Formula",
        "expression": detail.expression,
        "terms": [{"label": label, "definition": definition} for label, definition in detail.terms],
        "scope": detail.scope,
        "unit": ("Hours (shown as H:MM)" if detail.value_kind == "hours"
                 else ("Job Card count" if is_count else "Value")),
    }

    return {
        "formula": formula,
        "summary": summary,
        "columns": [{"key": c.key, "label": c.label, "kind": c.kind,
                     "total": bool(getattr(c, "total", False))}
                    for c in detail.columns],
        "valueColumn": {"label": detail.value_label, "kind": detail.value_kind, "shown": not is_count},
        "records": records,
    }


def run_labor_hours_detail(env, uid, board: BoardConfig, item: ChartItemConfig, date_from, date_to,
                           technician_id=None, period_months=1.0):
    """Back-compat alias for the pre-generalisation entry point (callers in
    older pbi_service_dashboards builds, and cached .pyc imports)."""
    return run_chart_detail(env, uid, board, item, date_from, date_to,
                            entity_id=technician_id, period_months=period_months)
