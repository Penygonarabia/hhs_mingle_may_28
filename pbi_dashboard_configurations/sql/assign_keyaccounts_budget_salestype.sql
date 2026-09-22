-- =============================================================================
-- Give the Key Accounts sales type group a target.
--
--   psql -U odoo -d dbprod -f scripts/assign_keyaccounts_budget_salestype.sql
--
-- WHAT IT DOES. Points the sales_budget_line rows captured against partner
-- classifications 004 Modern Trade and 007 Wholeseller at sales type group
-- '03' Key Accounts, for 2025 and 2026. Idempotent: re-running it changes
-- nothing, and it takes a backup of every row it is about to touch.
--
-- WHY IT IS NEEDED. Sale types 101 Modern Trade and 102 Wholesale were created
-- under Key Accounts in September 2026 and the ERP books invoices under them,
-- so the actuals side of the Sales Type Group level has a Key Accounts bar --
-- SAR 12,857,724 in September 2025 alone. The budget side had nothing to put
-- beside it: no sales_budget_line in any year has ever carried a group other
-- than '01' Dealers and '02' Projects, so the bar drew sales against a flat
-- zero target and read as an infinite over-achievement.
--
-- The budget carries no sale type of its own -- the client's file states the
-- customer, not how the invoice would be booked -- so the classification is
-- the only thing in it that identifies this business. 004 and 007 are exactly
-- the classifications whose invoices carry 101 and 102: every one of the 1,509
-- headers on sale type 101 belongs to an 004 customer and every one of the
-- 1,323 on 102 to an 007 customer, with no exceptions in either direction.
--
-- HOW WELL THE TWO SIDES WILL AGREE, measured on dbprod 2026-09-10 over
-- in-scope sales, as the share of each classification's money that is actually
-- booked under its own new sale type:
--
--             2024            2025                    2026
--     004     0.0%     60.2% (24,363,495 under  58.3% (12,422,355 under
--                             Dealers)                Dealers)
--     007     0.0%    100.0%                  100.0%
--
-- SO WHOLESALE IS EXACT AND MODERN TRADE IS NOT. 007's whole target lands on
-- Key Accounts and so does every riyal of its sales. 004's whole target lands
-- there too, while about 40 percent of its sales stay under Dealers, because
-- the ERP still raises roughly two Modern Trade invoices in five under sale
-- type 001 FG Direct Sales rather than 101. That overstates the Key Accounts
-- target and understates the Dealers one, at the SALES TYPE GROUP level only.
--
-- That residue is an ERP booking gap and the fix belongs there, not here:
-- splitting 004's budget to match the mix would be inventing a capture that
-- does not exist, and would move every time the mix moved. Until those
-- invoices are raised under 101, read Key Accounts achievement as indicative
-- and the DEPARTMENT level -- which is cut by the customer and is exact on
-- both sides -- as the number of record.
--
-- 2024 IS DELIBERATELY EXCLUDED. The first invoice on either sale type is
-- dated 2025-01-01, so 2024 has no Key Accounts sales at all; giving it a Key
-- Accounts target would put a bar on the chart with nothing beside it and
-- would break the year-on-year comparison the boards draw. 2024 stays on
-- Dealers, which is where its sales are.
--
-- AFTERWARDS the snapshot must be refreshed for the boards to see this. The
-- trigger in pbi_sales_dashboards queues that within a minute of this
-- committing (sales_budget_line is one of the master tables it watches), or
-- force it with:
--     env['pbi.sales.sman.fact'].refresh_fact()
-- The TARGET itself is read live and is on the chart immediately; it is the
-- actuals-side snapshot that waits.
-- =============================================================================

\echo ''
\echo '=== Before ================================================================'
\echo ''

SELECT year, partner_classification_code, salestype_group_code,
       salestype_group_name, count(*) AS lines
  FROM sales_budget_line
 WHERE partner_classification_code IN ('004', '007')
 GROUP BY 1, 2, 3, 4
 ORDER BY 1, 2;

\echo ''
\echo '=== Step 1: Backing up the rows about to change ==========================='
\echo ''

-- One backup table per run, named for the day, so an earlier run's copy is
-- never overwritten. Carries the id and the three columns this touches, which
-- is all a revert needs.
DROP TABLE IF EXISTS sales_budget_line_salestype_bak_keyacct_20260910;
CREATE TABLE sales_budget_line_salestype_bak_keyacct_20260910 AS
SELECT id, year, partner_classification_code,
       salestype_group_code, salestype_group_name, salestype_is_placeholder
  FROM sales_budget_line
 WHERE year IN (2025, 2026)
   AND partner_classification_code IN ('004', '007')
   AND salestype_group_code IS DISTINCT FROM '03';

\echo ''
\echo '=== Step 2: Assigning Key Accounts ======================================='
\echo ''

-- The group's own spelling wins, read from the master rather than typed here,
-- so renaming it in Sales > Configuration and re-running this keeps the
-- denormalized name in step. If the group is absent the UPDATE matches nothing
-- and the script is a no-op rather than writing a name for a group that does
-- not exist.
UPDATE sales_budget_line l
   SET salestype_group_code = g.salgrp_ref,
       salestype_group_name = g.salgrp_name,
       -- Set deliberately, so the import's backfill can never overwrite it.
       salestype_is_placeholder = false
  FROM salestypes_group g
 WHERE g.salgrp_ref = '03'
   AND l.year IN (2025, 2026)
   AND l.partner_classification_code IN ('004', '007')
   AND l.salestype_group_code IS DISTINCT FROM g.salgrp_ref;

\echo ''
\echo '=== After ================================================================'
\echo ''

SELECT year, partner_classification_code, salestype_group_code,
       salestype_group_name, count(*) AS lines
  FROM sales_budget_line
 WHERE partner_classification_code IN ('004', '007')
 GROUP BY 1, 2, 3, 4
 ORDER BY 1, 2;

\echo ''
\echo '=== Verification: target now carried per sales type group ================='
\echo ''

SELECT year, salestype_group_code, salestype_group_name,
       round(sum(budget_amount)) AS budget_value,
       round(sum(budget_qty))    AS budget_qty
  FROM v_sales_budget_month
 GROUP BY 1, 2, 3
 ORDER BY 1, 2;

-- To revert:
--   UPDATE sales_budget_line l
--      SET salestype_group_code     = b.salestype_group_code,
--          salestype_group_name     = b.salestype_group_name,
--          salestype_is_placeholder = b.salestype_is_placeholder
--     FROM sales_budget_line_salestype_bak_keyacct_20260910 b
--    WHERE b.id = l.id;
