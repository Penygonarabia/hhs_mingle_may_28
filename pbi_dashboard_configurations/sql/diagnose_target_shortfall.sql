-- ============================================================================
-- WHY IS THE TARGET DIFFERENT ON THIS SERVER?
-- ============================================================================
--
-- READ ONLY. Nothing here writes.
--
--   psql -U odoo -d <database> -v ON_ERROR_STOP=1 -f \
--     pbi_dashboard_configurations/sql/diagnose_target_shortfall.sql
--
-- RUN IT ON BOTH DATABASES AND DIFF THE OUTPUT. Every block is a single row of
-- numbers for 2025 through September, so the two runs line up side by side and
-- the first block whose numbers differ is the answer.
--
-- The tiles' target is not one number with one source. It is the budget file,
-- narrowed twice and then de-duplicated, and each of those stages can lose
-- money for a different reason:
--
--   Block 1  did the new code reach this server at all
--   Block 2  the budget file itself          -- differs => the DATA differs
--   Block 3  the product-group whitelist     -- differs => scope drops rows
--   Block 4  the two-stage de-duplication    -- differs => keys collapse
--   Block 5  what the tile actually shows
--   Block 6  the salesman split that block 4 turns on
--
-- Block 5 is the tile. Blocks 2 to 4 say which stage lost the difference
-- between block 2 and block 5, and each names its own fix.
-- ============================================================================

\echo ''
\echo '=== 1. Is the l5 fix on this server? ====================================='
\echo '    rows_sharing_a_key = 0 means the key matches the grain (fix present).'
\echo ''

-- The budget CTE emits one row per grain tuple. With every grain column in
-- budget_key, each row keys uniquely; rows_sharing_a_key is then 0. Any other
-- number means the key is still coarser than the grain -- the fix did not
-- reach this server (run -u pbi_sales_dashboards), or a second grain column is
-- missing from it. This is the same question a viewdef text search asks, but
-- answered from behaviour rather than from matching a rendered expression.
SELECT count(*)                                   AS live_rows,
       count(DISTINCT budget_key)                 AS distinct_keys,
       count(*) - count(DISTINCT budget_key)      AS rows_sharing_a_key
  FROM v_pbi_sales_budget_live
 WHERE yr = 2025 AND budget_key IS NOT NULL;

\echo ''
\echo '=== 2. The budget file itself (the control total) ========================'
\echo '    If these differ between servers, no code change can help: the two'
\echo '    databases hold different budget rows. Import the missing ones.'
\echo ''

SELECT round(sum(budget_amount) FILTER (WHERE month <= 9), 2) AS ytd_sep_source,
       round(sum(budget_amount) FILTER (WHERE month  = 9), 2) AS mtd_sep_source,
       round(sum(budget_amount), 2)                           AS full_year_source,
       count(*)                                               AS rows_2025,
       count(DISTINCT product_group_id)                       AS product_groups
  FROM v_sales_budget_month
 WHERE year = 2025;

\echo ''
\echo '=== 3. What the product-group whitelist drops ============================'
\echo '    The budget is scoped to groups that HAVE in-scope sales. A group the'
\echo '    feed never sold on this server takes its whole target with it.'
\echo ''

SELECT round(COALESCE(sum(b.budget_amount) FILTER (WHERE b.month <= 9), 0), 2)
         AS ytd_sep_dropped_by_scope,
       round(COALESCE(sum(b.budget_amount) FILTER (WHERE b.month  = 9), 0), 2)
         AS mtd_sep_dropped_by_scope,
       count(DISTINCT b.product_group_id) AS groups_dropped
  FROM v_sales_budget_month b
 WHERE b.year = 2025
   AND NOT EXISTS (SELECT 1 FROM v_pbi_sales_sman_fact f
                    WHERE f.l9_code::text = b.product_group_id::text AND f.in_scope);

\echo ''
\echo '    ...and which groups they are:'
\echo ''

SELECT b.product_group_id, pc.code AS group_code, pc.name AS group_name,
       round(sum(b.budget_amount), 2) AS budget_2025
  FROM v_sales_budget_month b
  LEFT JOIN product_category pc ON pc.id = b.product_group_id
 WHERE b.year = 2025
   AND NOT EXISTS (SELECT 1 FROM v_pbi_sales_sman_fact f
                    WHERE f.l9_code::text = b.product_group_id::text AND f.in_scope)
 GROUP BY 1, 2, 3
 ORDER BY 4 DESC;

\echo ''
\echo '=== 4. What the two-stage de-duplication drops ==========================='
\echo '    all_rows is every budget row summed; two_stage is max() per'
\echo '    budget_key, which is what every chart and tile does. A gap means the'
\echo '    key is COARSER than the rows -- the l5 bug, or another grain column'
\echo '    missing from the key. Zero means the key and the grain agree.'
\echo ''

WITH bl AS (
    SELECT budget_key, mth, budget_value
      FROM v_pbi_sales_budget_live
     WHERE yr = 2025 AND budget_key IS NOT NULL
),
staged AS (
    SELECT budget_key, mth, max(budget_value) AS bv
      FROM bl GROUP BY budget_key, mth
)
SELECT round((SELECT sum(budget_value) FROM bl    WHERE mth <= 9), 2) AS ytd_all_rows,
       round((SELECT sum(bv)           FROM staged WHERE mth <= 9), 2) AS ytd_two_stage,
       round((SELECT sum(budget_value) FROM bl    WHERE mth <= 9), 2)
         - round((SELECT sum(bv)       FROM staged WHERE mth <= 9), 2) AS ytd_lost_to_collapse,
       round((SELECT sum(budget_value) FROM bl    WHERE mth  = 9), 2) AS mtd_all_rows,
       round((SELECT sum(bv)           FROM staged WHERE mth  = 9), 2) AS mtd_two_stage;

\echo ''
\echo '=== 5. What the tile shows ==============================================='
\echo '    This is the number on screen. Compare against block 2.'
\echo ''

SELECT round((SELECT sum(bv) FROM (SELECT budget_key, max(budget_value) AS bv
                                     FROM v_pbi_sales_budget_live
                                    WHERE yr = 2025 AND mth <= 9
                                      AND budget_key IS NOT NULL
                                    GROUP BY budget_key) t), 2) AS ytd_sep_tile,
       round((SELECT sum(bv) FROM (SELECT budget_key, max(budget_value) AS bv
                                     FROM v_pbi_sales_budget_live
                                    WHERE yr = 2025 AND mth = 9
                                      AND budget_key IS NOT NULL
                                    GROUP BY budget_key) t), 2) AS mtd_sep_tile;

\echo ''
\echo '=== 6. The salesman split block 4 turns on ==============================='
\echo '    Where the budget names no salesman, every row keys alike and the l5'
\echo '    bug was invisible. A server with attribution is where it bit.'
\echo ''

SELECT count(*)                                                    AS rows_2025,
       count(salesman_partner_id)                                  AS with_salesman_id,
       count(DISTINCT salesman_partner_id)                         AS distinct_salesmen,
       count(*) FILTER (WHERE btrim(COALESCE(salesman_code,'')) IN ('','*'))
                                                                   AS salesman_code_blank_or_star
  FROM v_sales_budget_month
 WHERE year = 2025;
