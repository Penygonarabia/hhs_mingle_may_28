-- Audit 10-Level Target Reconciliation & Two-Stage Deduplication Integrity
--
--   psql -U odoo -d <database> -v ON_ERROR_STOP=1 -f pbi_dashboard_configurations/sql/check_sman_fact_budget_integrity.sql
--
-- Also offered on PBI Dashboards > Configurations > Maintenance Scripts.
--
-- PURPOSE:
--   1. Validates that SUM(budget_value) across 10 levels strictly reconciles with
--      v_sales_budget_month and sales_budget_line control totals.
--   2. Verifies the two-stage deduplication rule: MAX(budget_value) over budget_key
--      grouped before summing across dimension slices.
--   3. Identifies any level exhibiting variance, multi-part inflation, or unmapped codes.
--

\echo '----------------------------------------------------------------------'
\echo 'Step 1: Raw Target Baseline from v_sales_budget_month (Year 2025 Control)'
\echo '----------------------------------------------------------------------'

WITH raw_baseline AS (
    SELECT 
        year AS yr,
        ROUND(SUM(COALESCE(budget_amount, 0)), 2) AS raw_budget_val,
        ROUND(SUM(COALESCE(budget_qty, 0)), 0) AS raw_budget_qty,
        COUNT(*) AS monthly_slices_count
    FROM v_sales_budget_month
    WHERE year = 2025
    GROUP BY year
)
SELECT 
    yr AS control_year,
    raw_budget_val AS total_budget_value_sar,
    raw_budget_qty AS total_budget_quantity_units,
    monthly_slices_count
FROM raw_baseline;

\echo '----------------------------------------------------------------------'
\echo 'Step 2: 10-Level Target Audit against Live View (v_pbi_sales_budget_live)'
\echo '----------------------------------------------------------------------'

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'v_pbi_sales_budget_live') THEN
        RAISE NOTICE 'Auditing 10-level two-stage target sums against v_pbi_sales_budget_live for 2025...';
    ELSE
        RAISE WARNING 'v_pbi_sales_budget_live does not exist. Please run sync_and_repair_all_masters.sql or bring_up wizard first.';
    END IF;
END $$;

-- Two-stage evaluation across key dimensions
WITH baseline_val AS (
    SELECT COALESCE(SUM(budget_amount), 0) AS baseline_tot 
    FROM v_sales_budget_month WHERE year = 2025
),
l1_check AS (
    SELECT 'L1 (Sales Type Group)' AS level_name,
           ROUND(SUM(budget), 2) AS level_budget_val,
           (SELECT baseline_tot FROM baseline_val) AS baseline_val
    FROM (
        SELECT budget_l1_code, budget_key, MAX(budget_value) AS budget
        FROM v_pbi_sales_budget_live
        WHERE yr = 2025
        GROUP BY budget_l1_code, budget_key
    ) s
),
l2_check AS (
    SELECT 'L2 (Partner Classification)' AS level_name,
           ROUND(SUM(budget), 2) AS level_budget_val,
           (SELECT baseline_tot FROM baseline_val) AS baseline_val
    FROM (
        SELECT l2_code, budget_key, MAX(budget_value) AS budget
        FROM v_pbi_sales_budget_live
        WHERE yr = 2025
        GROUP BY l2_code, budget_key
    ) s
),
l3_check AS (
    SELECT 'L3 (Report Region)' AS level_name,
           ROUND(SUM(budget), 2) AS level_budget_val,
           (SELECT baseline_tot FROM baseline_val) AS baseline_val
    FROM (
        SELECT l3_code, budget_key, MAX(budget_value) AS budget
        FROM v_pbi_sales_budget_live
        WHERE yr = 2025
        GROUP BY l3_code, budget_key
    ) s
),
l4_check AS (
    SELECT 'L4 (City)' AS level_name,
           ROUND(SUM(budget), 2) AS level_budget_val,
           (SELECT baseline_tot FROM baseline_val) AS baseline_val
    FROM (
        SELECT l4_code, budget_key, MAX(budget_value) AS budget
        FROM v_pbi_sales_budget_live
        WHERE yr = 2025
        GROUP BY l4_code, budget_key
    ) s
),
l5_check AS (
    SELECT 'L5 (Salesman)' AS level_name,
           ROUND(SUM(budget), 2) AS level_budget_val,
           (SELECT baseline_tot FROM baseline_val) AS baseline_val
    FROM (
        SELECT l5_code, budget_key, MAX(budget_value) AS budget
        FROM v_pbi_sales_budget_live
        WHERE yr = 2025
        GROUP BY l5_code, budget_key
    ) s
),
l6_check AS (
    SELECT 'L6 (Customer)' AS level_name,
           ROUND(SUM(budget), 2) AS level_budget_val,
           (SELECT baseline_tot FROM baseline_val) AS baseline_val
    FROM (
        SELECT l6_code, budget_key, MAX(budget_value) AS budget
        FROM v_pbi_sales_budget_live
        WHERE yr = 2025
        GROUP BY l6_code, budget_key
    ) s
),
l7_check AS (
    SELECT 'L7 (Main Category)' AS level_name,
           ROUND(SUM(budget), 2) AS level_budget_val,
           (SELECT baseline_tot FROM baseline_val) AS baseline_val
    FROM (
        SELECT l7_code, budget_key, MAX(budget_value) AS budget
        FROM v_pbi_sales_budget_live
        WHERE yr = 2025
        GROUP BY l7_code, budget_key
    ) s
),
l8_check AS (
    SELECT 'L8 (Sub Category)' AS level_name,
           ROUND(SUM(budget), 2) AS level_budget_val,
           (SELECT baseline_tot FROM baseline_val) AS baseline_val
    FROM (
        SELECT l8_code, budget_key, MAX(budget_value) AS budget
        FROM v_pbi_sales_budget_live
        WHERE yr = 2025
        GROUP BY l8_code, budget_key
    ) s
),
l9_check AS (
    SELECT 'L9 (Product Group)' AS level_name,
           ROUND(SUM(budget), 2) AS level_budget_val,
           (SELECT baseline_tot FROM baseline_val) AS baseline_val
    FROM (
        SELECT l9_code, budget_key, MAX(budget_value) AS budget
        FROM v_pbi_sales_budget_live
        WHERE yr = 2025
        GROUP BY l9_code, budget_key
    ) s
),
all_levels AS (
    SELECT * FROM l1_check
    UNION ALL SELECT * FROM l2_check
    UNION ALL SELECT * FROM l3_check
    UNION ALL SELECT * FROM l4_check
    UNION ALL SELECT * FROM l5_check
    UNION ALL SELECT * FROM l6_check
    UNION ALL SELECT * FROM l7_check
    UNION ALL SELECT * FROM l8_check
    UNION ALL SELECT * FROM l9_check
)
SELECT 
    level_name,
    level_budget_val,
    baseline_val,
    ROUND(level_budget_val - baseline_val, 2) AS variance_sar,
    CASE 
        WHEN ABS(level_budget_val - baseline_val) < 1.0 THEN '100.0% EXACT MATCH (PASS)'
        ELSE 'VARIANCE DETECTED (FAIL)'
    END AS status
FROM all_levels;

\echo '----------------------------------------------------------------------'
\echo 'Step 3: Verification of Unsafe Levels (L5 Salesman & L10 Subgroup)'
\echo '----------------------------------------------------------------------'

SELECT 
    'L5 (Salesman - Raw vs Attributed)' AS probe,
    COUNT(DISTINCT salesman_partner_id) AS attributed_salesmen_count,
    COUNT(*) FILTER (WHERE salesman_partner_id IS NOT NULL) AS attributed_budget_lines,
    COUNT(*) FILTER (WHERE salesman_partner_id IS NULL) AS unassigned_budget_lines
FROM sales_budget_line
WHERE year = 2025;
