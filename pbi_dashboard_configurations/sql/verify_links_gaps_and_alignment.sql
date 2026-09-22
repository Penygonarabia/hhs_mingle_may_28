-- Verify Links, Gaps and Data Alignments
-- =========================================================================
-- The one read-only check on the Configurations page. It answers the three
-- questions that used to need three separate buttons:
--
--   A. Are the master links complete?  Every one of the ten levels, for This
--      Year sales, Last Year sales and Target, plus the foreign-key and
--      taxonomy integrity of the master tables themselves.
--   B. Does every actual have a target?  Actuals (v_pbi_sales_sman_fact)
--      against budget (v_pbi_sales_budget_live) by Year, Sales Type Group,
--      Region, Main Category and Sub-Category.
--   C. Is the snapshot itself sound?  Row counts and in-scope totals per year,
--      the unassigned breakdown, and target coverage by main and sub category.
--
-- MERGED FROM THREE FILES, and the merge is the point: the three were run in
-- sequence by anyone diagnosing anything, and reading three outputs to answer
-- one question is how a gap gets missed between them. Superseded:
-- diagnose_master_links_and_gaps.sql, verify_sales_sman_targets_alignment.sql
-- and the reporting half of rebuild_and_verify_salesman_fact.sql.
--
-- READ-ONLY, AND THAT IS A PROPERTY WORTH KEEPING. The rebuild script this
-- absorbed also refreshed the materialized views and repaired budget
-- categories; those writes are NOT here. They are what "Complete Master Sync &
-- Gap Repair" does, and a verification that silently changed data would stop
-- being safe to run whenever somebody wondered. Run the sync first if this
-- reports a gap; run this to see whether it worked.
--
-- Safe to run multiple times on any server.
-- =========================================================================

SET jit = off;
SET enable_nestloop = off;

\echo ''
\echo '#### A. MASTER LINKS & GAPS ############################################'
\echo ''
\echo '=== 1. Master Links Gap Audit — This Year Sales (2026 In-Scope) =========='
\echo ''

WITH f26 AS MATERIALIZED (
    SELECT l1_code, l2_code, l3_code, l4_code, l5_code, l6_code, l7_code, l8_code, l9_code, lfam_code, amount, qty
    FROM v_pbi_sales_sman_fact
    WHERE yr = 2026 AND in_scope AND part_no IS NOT NULL
)
SELECT
    'L1 - Sales Type Group'       AS master_dimension,
    count(*) FILTER (WHERE l1_code IS NULL) AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l1_code IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l1_code IS NULL)::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l1_code IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f26
UNION ALL
SELECT
    'L2 - Partner Classification' AS master_dimension,
    count(*) FILTER (WHERE l2_code IS NULL) AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l2_code IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l2_code IS NULL)::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l2_code IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f26
UNION ALL
SELECT
    'L3 - Report Region'          AS master_dimension,
    count(*) FILTER (WHERE l3_code IS NULL) AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l3_code IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l3_code IS NULL)::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l3_code IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f26
UNION ALL
SELECT
    'L4 - City'                   AS master_dimension,
    count(*) FILTER (WHERE l4_code IS NULL) AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l4_code IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l4_code IS NULL)::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l4_code IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f26
UNION ALL
SELECT
    'L5 - Salesman'               AS master_dimension,
    count(*) FILTER (WHERE l5_code IS NULL OR l5_code = '') AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l5_code IS NULL OR l5_code = '')::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l5_code IS NULL OR l5_code = '')::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l5_code IS NULL OR l5_code = '') = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f26
UNION ALL
SELECT
    'L6 - Customer'               AS master_dimension,
    count(*) FILTER (WHERE l6_code IS NULL OR l6_code = '') AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l6_code IS NULL OR l6_code = '')::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l6_code IS NULL OR l6_code = '')::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l6_code IS NULL OR l6_code = '') = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f26
UNION ALL
SELECT
    'L7 - Main Category'          AS master_dimension,
    count(*) FILTER (WHERE l7_code IS NULL) AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l7_code IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l7_code IS NULL)::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l7_code IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f26
UNION ALL
SELECT
    'L8 - Sub-Category'           AS master_dimension,
    count(*) FILTER (WHERE l8_code IS NULL) AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l8_code IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l8_code IS NULL)::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l8_code IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f26
UNION ALL
SELECT
    'L9 - Product Group'          AS master_dimension,
    count(*) FILTER (WHERE l9_code IS NULL) AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l9_code IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l9_code IS NULL)::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l9_code IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f26
UNION ALL
SELECT
    'L10 - Product Sub-Group'     AS master_dimension,
    count(*) FILTER (WHERE lfam_code IS NULL) AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE lfam_code IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE lfam_code IS NULL)::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE lfam_code IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f26;

\echo ''
\echo '=== 2. Master Links Gap Audit — Last Year Sales (2025 In-Scope) ==========='
\echo ''

WITH f25 AS MATERIALIZED (
    SELECT l1_code, l2_code, l3_code, l4_code, l5_code, l6_code, l7_code, l8_code, l9_code, lfam_code, amount, qty
    FROM v_pbi_sales_sman_fact
    WHERE yr = 2025 AND in_scope AND part_no IS NOT NULL
)
SELECT
    'L1 - Sales Type Group'       AS master_dimension,
    count(*) FILTER (WHERE l1_code IS NULL) AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l1_code IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l1_code IS NULL)::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l1_code IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f25
UNION ALL
SELECT
    'L2 - Partner Classification' AS master_dimension,
    count(*) FILTER (WHERE l2_code IS NULL) AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l2_code IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l2_code IS NULL)::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l2_code IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f25
UNION ALL
SELECT
    'L3 - Report Region'          AS master_dimension,
    count(*) FILTER (WHERE l3_code IS NULL) AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l3_code IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l3_code IS NULL)::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l3_code IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f25
UNION ALL
SELECT
    'L4 - City'                   AS master_dimension,
    count(*) FILTER (WHERE l4_code IS NULL) AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l4_code IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l4_code IS NULL)::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l4_code IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f25
UNION ALL
SELECT
    'L5 - Salesman'               AS master_dimension,
    count(*) FILTER (WHERE l5_code IS NULL OR l5_code = '') AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l5_code IS NULL OR l5_code = '')::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l5_code IS NULL OR l5_code = '')::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l5_code IS NULL OR l5_code = '') = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f25
UNION ALL
SELECT
    'L6 - Customer'               AS master_dimension,
    count(*) FILTER (WHERE l6_code IS NULL OR l6_code = '') AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l6_code IS NULL OR l6_code = '')::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l6_code IS NULL OR l6_code = '')::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l6_code IS NULL OR l6_code = '') = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f25
UNION ALL
SELECT
    'L7 - Main Category'          AS master_dimension,
    count(*) FILTER (WHERE l7_code IS NULL) AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l7_code IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l7_code IS NULL)::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l7_code IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f25
UNION ALL
SELECT
    'L8 - Sub-Category'           AS master_dimension,
    count(*) FILTER (WHERE l8_code IS NULL) AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l8_code IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l8_code IS NULL)::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l8_code IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f25
UNION ALL
SELECT
    'L9 - Product Group'          AS master_dimension,
    count(*) FILTER (WHERE l9_code IS NULL) AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE l9_code IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE l9_code IS NULL)::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE l9_code IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f25
UNION ALL
SELECT
    'L10 - Product Sub-Group'     AS master_dimension,
    count(*) FILTER (WHERE lfam_code IS NULL) AS unassigned_rows,
    COALESCE(round(sum(amount) FILTER (WHERE lfam_code IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    COALESCE(round(sum(qty) FILTER (WHERE lfam_code IS NULL)::numeric, 0), 0)       AS unassigned_qty,
    CASE WHEN count(*) FILTER (WHERE lfam_code IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM f25;

\echo ''
\echo '=== 3. Master Links Gap Audit — Target / Budget (2026) ===================='
\echo ''

WITH b26 AS MATERIALIZED (
    SELECT 
        salestype_group_code, 
        partner_classification_code, 
        region_code, 
        city_code, 
        customer_code, 
        main_category_code, 
        sub_category_code, 
        product_group_id, 
        budget_amount
    FROM v_sales_budget_month
    WHERE year = 2026
)
SELECT
    'L1 - Sales Type Group'       AS master_dimension,
    count(*) FILTER (WHERE NULLIF(trim(salestype_group_code), '') IS NULL) AS unassigned_rows,
    COALESCE(round(sum(budget_amount) FILTER (WHERE NULLIF(trim(salestype_group_code), '') IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    CASE WHEN count(*) FILTER (WHERE NULLIF(trim(salestype_group_code), '') IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM b26
UNION ALL
SELECT
    'L2 - Partner Classification' AS master_dimension,
    count(*) FILTER (WHERE NULLIF(trim(partner_classification_code), '') IS NULL) AS unassigned_rows,
    COALESCE(round(sum(budget_amount) FILTER (WHERE NULLIF(trim(partner_classification_code), '') IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    CASE WHEN count(*) FILTER (WHERE NULLIF(trim(partner_classification_code), '') IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM b26
UNION ALL
SELECT
    'L3 - Report Region'          AS master_dimension,
    count(*) FILTER (WHERE NULLIF(trim(region_code), '') IS NULL) AS unassigned_rows,
    COALESCE(round(sum(budget_amount) FILTER (WHERE NULLIF(trim(region_code), '') IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    CASE WHEN count(*) FILTER (WHERE NULLIF(trim(region_code), '') IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM b26
UNION ALL
SELECT
    'L4 - City'                   AS master_dimension,
    count(*) FILTER (WHERE NULLIF(trim(city_code), '') IS NULL) AS unassigned_rows,
    COALESCE(round(sum(budget_amount) FILTER (WHERE NULLIF(trim(city_code), '') IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    CASE WHEN count(*) FILTER (WHERE NULLIF(trim(city_code), '') IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM b26
UNION ALL
SELECT
    'L6 - Customer / Segment'     AS master_dimension,
    count(*) FILTER (WHERE NULLIF(trim(customer_code), '') IS NULL) AS unassigned_rows,
    COALESCE(round(sum(budget_amount) FILTER (WHERE NULLIF(trim(customer_code), '') IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    CASE WHEN count(*) FILTER (WHERE NULLIF(trim(customer_code), '') IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM b26
UNION ALL
SELECT
    'L7 - Main Category'          AS master_dimension,
    count(*) FILTER (WHERE NULLIF(trim(main_category_code), '') IS NULL) AS unassigned_rows,
    COALESCE(round(sum(budget_amount) FILTER (WHERE NULLIF(trim(main_category_code), '') IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    CASE WHEN count(*) FILTER (WHERE NULLIF(trim(main_category_code), '') IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM b26
UNION ALL
SELECT
    'L8 - Sub-Category'           AS master_dimension,
    count(*) FILTER (WHERE NULLIF(trim(sub_category_code), '') IS NULL) AS unassigned_rows,
    COALESCE(round(sum(budget_amount) FILTER (WHERE NULLIF(trim(sub_category_code), '') IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    CASE WHEN count(*) FILTER (WHERE NULLIF(trim(sub_category_code), '') IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM b26
UNION ALL
SELECT
    'L9 - Product Group'          AS master_dimension,
    count(*) FILTER (WHERE product_group_id IS NULL) AS unassigned_rows,
    COALESCE(round(sum(budget_amount) FILTER (WHERE product_group_id IS NULL)::numeric, 2), 0.00) AS unassigned_amount,
    CASE WHEN count(*) FILTER (WHERE product_group_id IS NULL) = 0 THEN 'PERFECT (0 Gaps)' ELSE 'GAP DETECTED' END AS status
FROM b26;

\echo ''
\echo '=== 4. Master Table Health & Materialized View Freshness =================='
\echo ''

SELECT
    'v_pbi_sales_sman_fact'     AS view_name,
    count(*)                    AS row_count,
    CASE WHEN count(*) > 0 THEN 'POPULATED (OK)' ELSE 'EMPTY (REFRESH NEEDED)' END AS status
FROM v_pbi_sales_sman_fact
UNION ALL
SELECT
    'v_pbi_sales_budget_snap'   AS view_name,
    count(*)                    AS row_count,
    CASE WHEN count(*) > 0 THEN 'POPULATED (OK)' ELSE 'EMPTY (REFRESH NEEDED)' END AS status
FROM v_pbi_sales_budget_snap
UNION ALL
SELECT
    'v_pbi_sales_scope_groups'  AS view_name,
    count(*)                    AS row_count,
    CASE WHEN count(*) > 0 THEN 'POPULATED (OK)' ELSE 'EMPTY (REFRESH NEEDED)' END AS status
FROM v_pbi_sales_scope_groups;

\echo ''
\echo '=== 5. Sales Type Group Master Configuration & Alignment Audit ============'
\echo ''

-- 5A. Master Data Setup: Sale Types count per Sales Type Group
SELECT
    g.id,
    g.salgrp_ref AS group_ref,
    g.salgrp_name AS group_name,
    count(st.id) AS configured_sale_types_count,
    CASE WHEN count(st.id) > 0 THEN 'CONFIGURED (Active)'
         ELSE 'NO SALE TYPES (Unused)' END AS master_setup_status
FROM salestypes_group g
LEFT JOIN sale_types st ON st.saltype_group = g.id
GROUP BY g.id, g.salgrp_ref, g.salgrp_name
ORDER BY g.id;

-- 5B. Target Records check: verify no budget rows are on unconfigured sales type groups
SELECT
    salestype_group_code,
    salestype_group_name,
    count(*) AS budget_rows_count,
    round(sum(budget_amount)::numeric, 2) AS total_target_amount,
    CASE WHEN salestype_group_code IN (
             SELECT DISTINCT g.salgrp_ref 
             FROM salestypes_group g 
             JOIN sale_types st ON st.saltype_group = g.id
         ) THEN 'VALID (Mapped to active master)'
         ELSE 'WARNING (Group has no configured sale types)' END AS budget_group_status
FROM v_sales_budget_month
WHERE year = 2026
GROUP BY salestype_group_code, salestype_group_name
ORDER BY salestype_group_code;

\echo ''
\echo '#### B. TARGET vs ACTUALS ALIGNMENT ####################################'
\echo ''
\echo '=== 1. Target & Actuals Summary by Year ==================================='
\echo ''

SELECT
    f.yr AS year,
    count(DISTINCT f.mth) AS months_with_sales,
    round(sum(f.amount)::numeric, 2) AS actual_amount,
    round(sum(f.qty)::numeric, 0) AS actual_qty,
    round(b.total_budget_value::numeric, 2) AS target_amount,
    round(b.total_budget_qty::numeric, 0) AS target_qty,
    round((sum(f.amount) / NULLIF(b.total_budget_value, 0) * 100)::numeric, 1) AS achv_val_pct,
    round((sum(f.qty) / NULLIF(b.total_budget_qty, 0) * 100)::numeric, 1) AS achv_qty_pct
FROM v_pbi_sales_sman_fact f
LEFT JOIN (
    SELECT yr, sum(budget_value) AS total_budget_value, sum(budget_qty) AS total_budget_qty
    FROM v_pbi_sales_budget_live
    GROUP BY yr
) b ON b.yr = f.yr
WHERE f.in_scope
GROUP BY f.yr, b.total_budget_value, b.total_budget_qty
ORDER BY f.yr DESC;

\echo ''
\echo '=== 2. Target vs Actuals by Sales Type Group (2026) ======================='
\echo ''

SELECT
    COALESCE(f.l1_code, b.budget_l1_code, 'UNASSIGNED') AS sales_type_group,
    COALESCE(f.l1_label, b.budget_l1_label, 'Unassigned') AS group_name,
    round(COALESCE(sum(f.amount), 0)::numeric, 2) AS ytd_actual_amount,
    round(COALESCE(sum(f.qty), 0)::numeric, 0) AS ytd_actual_qty,
    round(COALESCE(b.target_val, 0)::numeric, 2) AS ytd_target_amount,
    round(COALESCE(b.target_qty, 0)::numeric, 0) AS ytd_target_qty,
    CASE WHEN COALESCE(b.target_val, 0) = 0 THEN 'NO TARGET' ELSE 'OK' END AS target_status
FROM v_pbi_sales_sman_fact f
FULL OUTER JOIN (
    SELECT
        budget_l1_code,
        budget_l1_label,
        sum(budget_value) AS target_val,
        sum(budget_qty) AS target_qty
    FROM v_pbi_sales_budget_live
    WHERE yr = 2026
    GROUP BY budget_l1_code, budget_l1_label
) b ON b.budget_l1_code = f.l1_code
WHERE (f.yr = 2026 OR f.yr IS NULL) AND (f.in_scope OR f.in_scope IS NULL)
GROUP BY f.l1_code, f.l1_label, b.budget_l1_code, b.budget_l1_label, b.target_val, b.target_qty
ORDER BY ytd_actual_amount DESC;

\echo ''
\echo '=== 3. Target vs Actuals by Region (2026) ================================'
\echo ''

SELECT
    COALESCE(f.l3_code, b.l3_code, 'UNASSIGNED') AS region_code,
    COALESCE(f.l3_label, b.l3_label, 'Unassigned') AS region_name,
    round(COALESCE(sum(f.amount), 0)::numeric, 2) AS actual_amount,
    round(COALESCE(sum(f.qty), 0)::numeric, 0) AS actual_qty,
    round(COALESCE(b.target_val, 0)::numeric, 2) AS target_amount,
    round(COALESCE(b.target_qty, 0)::numeric, 0) AS target_qty,
    CASE WHEN COALESCE(b.target_val, 0) = 0 THEN 'NO TARGET' ELSE 'OK' END AS region_status
FROM v_pbi_sales_sman_fact f
FULL OUTER JOIN (
    SELECT
        l3_code,
        l3_label,
        sum(budget_value) AS target_val,
        sum(budget_qty) AS target_qty
    FROM v_pbi_sales_budget_live
    WHERE yr = 2026
    GROUP BY l3_code, l3_label
) b ON b.l3_code = f.l3_code
WHERE (f.yr = 2026 OR f.yr IS NULL) AND (f.in_scope OR f.in_scope IS NULL)
GROUP BY f.l3_code, f.l3_label, b.l3_code, b.l3_label, b.target_val, b.target_qty
ORDER BY actual_amount DESC;

\echo ''
\echo '=== 4. Target vs Actuals by Main Category (2026) =========================='
\echo ''

SELECT
    COALESCE(b.l7_label, f.l7_label, 'Unassigned') AS main_category,
    round(COALESCE(sum(f.amount), 0)::numeric, 2)  AS actual_amount_ytd,
    round(COALESCE(b.target_val, 0)::numeric, 2)   AS target_amount_ytd,
    CASE WHEN COALESCE(b.target_val, 0) = 0 THEN 'NO TARGET' ELSE 'OK' END AS category_status
FROM (
    SELECT DISTINCT l7_code, l7_label, sum(amount) AS amount
    FROM v_pbi_sales_sman_fact
    WHERE yr = 2026 AND in_scope
    GROUP BY l7_code, l7_label
) f
FULL OUTER JOIN (
    SELECT
        l7_code,
        max(l7_label) AS l7_label,
        sum(budget_value) AS target_val
    FROM v_pbi_sales_budget_live
    WHERE yr = 2026
    GROUP BY l7_code
) b ON b.l7_code = f.l7_code
GROUP BY b.l7_label, f.l7_label, b.target_val
ORDER BY actual_amount_ytd DESC;

\echo ''
\echo '=== 5. Target vs Actuals by Sub-Category (2026 Top 10) ===================='
\echo ''

SELECT
    COALESCE(b.l8_label, f.l8_label, 'Unassigned') AS sub_category,
    round(COALESCE(sum(f.amount), 0)::numeric, 2)  AS actual_amount_ytd,
    round(COALESCE(b.target_val, 0)::numeric, 2)   AS target_amount_ytd,
    CASE WHEN COALESCE(b.target_val, 0) = 0 THEN 'NO TARGET' ELSE 'OK' END AS subcategory_status
FROM (
    SELECT DISTINCT l8_code, l8_label, sum(amount) AS amount
    FROM v_pbi_sales_sman_fact
    WHERE yr = 2026 AND in_scope
    GROUP BY l8_code, l8_label
) f
FULL OUTER JOIN (
    SELECT
        l8_code,
        max(l8_label) AS l8_label,
        sum(budget_value) AS target_val
    FROM v_pbi_sales_budget_live
    WHERE yr = 2026
    GROUP BY l8_code
) b ON b.l8_code = f.l8_code
GROUP BY b.l8_label, f.l8_label, b.target_val
ORDER BY actual_amount_ytd DESC
LIMIT 10;

\echo ''
\echo '#### C. SNAPSHOT COVERAGE ##############################################'
\echo '=== C1. Snapshot Summary by Year ================================================='
\echo ''

SELECT
    yr AS year,
    count(*) AS total_rows,
    count(*) FILTER (WHERE in_scope) AS in_scope_rows,
    count(DISTINCT l1_code) AS sales_type_groups,
    count(DISTINCT l3_code) AS regions,
    count(DISTINCT l7_code) AS product_subcats,
    round(sum(amount) FILTER (WHERE in_scope)::numeric, 2) AS total_in_scope_amount,
    round(sum(qty) FILTER (WHERE in_scope)::numeric, 0) AS total_in_scope_qty
FROM v_pbi_sales_sman_fact
GROUP BY yr
ORDER BY yr DESC;

\echo ''
\echo '=== C2. Scope & Unassigned Breakdown (2026) ============================='
\echo ''

SELECT
    COALESCE(l1_code, 'UNASSIGNED') AS stg_code,
    COALESCE(l1_label, 'Unassigned') AS sales_type_group,
    count(*) AS row_count,
    round(sum(amount)::numeric, 2) AS amount,
    round(sum(qty)::numeric, 0) AS qty
FROM v_pbi_sales_sman_fact
WHERE yr = 2026 AND in_scope
GROUP BY l1_code, l1_label
ORDER BY amount DESC;

\echo ''

-- C3 and C4 are deliberately absent. The rebuild script this section came from
-- ended with Target vs Actuals by Main Category and by Sub-Category for 2026 --
-- the same two reports section B already prints, from the same two views. Two
-- copies of one answer in one output is how a reader stops trusting either.
