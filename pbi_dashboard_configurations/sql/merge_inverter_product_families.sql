-- =============================================================================
-- Report the two Inverter families as one bar.
--
--   psql -U odoo -d dbprod -f scripts/merge_inverter_product_families.sql
--
-- WHAT IT DOES. Points WTSG009 Mission Inverter at WTSG016, and renames WTSG016
-- to "Inverter". Idempotent, and it takes a backup of both rows.
--
-- WHY. The client's monthly report shows a single INVERTER bar on its split
-- sub-group page; the ERP carries two families and the boards drew two. The
-- total was never wrong -- SAR 11,532,391 of Jan-Sep 2025 against the report's
-- ~11m -- it was split across two bars where the reader expects one.
--
-- A MERGE, NOT A DELETE, and it has to be. The sales side reaches a family
-- through product_category, but the budget reaches it through its own code
-- (sales_budget_line.erp_subgroup_code -> pfam_ref). Deleting WTSG009 would
-- strand the SAR 5,478,312 of target captured against that code. Both rows stay
-- and one reports under the other; the resolution happens where the family is
-- read, so the two figures are SUMMED into one family before anything
-- de-duplicates them.
--
-- THE NAME MOVES TO THE CLIENT'S. WTSG016 keeps its ERP reference and its
-- original spelling in Name 2, so the trail back is intact.
--
-- THIS IS MASTER DATA, and after this it needs no script: Sales Type Groups ->
-- Product Family carries a "Report Under" field, so any two families can be
-- merged from the UI and the boards follow on the next refresh.
--
-- AFTERWARDS rebuild the snapshot -- product_family carries a refresh trigger,
-- so it queues within a minute, or force it with:
--     env['pbi.sales.sman.fact'].refresh_fact()
-- =============================================================================

\echo ''
\echo '=== Before ================================================================'
\echo ''

SELECT f.pfam_ref, f.pfam_name, m.pfam_ref AS reports_under,
       (SELECT count(*) FROM product_category c WHERE c.product_family = f.id) AS categories
  FROM product_family f
  LEFT JOIN product_family m ON m.id = f.pfam_merged_into
 WHERE f.pfam_ref IN ('WTSG009', 'WTSG016')
 ORDER BY f.pfam_ref;

\echo ''
\echo '=== Step 1: Backing up both rows =========================================='
\echo ''

DROP TABLE IF EXISTS product_family_inverter_bak_20260910;
CREATE TABLE product_family_inverter_bak_20260910 AS
SELECT id, pfam_ref, pfam_name, pfam_name2, pfam_merged_into, complete_name
  FROM product_family
 WHERE pfam_ref IN ('WTSG009', 'WTSG016');

\echo ''
\echo '=== Step 2: Merging ======================================================='
\echo ''

UPDATE product_family f
   SET pfam_merged_into = t.id
  FROM product_family t
 WHERE t.pfam_ref = 'WTSG016'
   AND f.pfam_ref = 'WTSG009'
   AND f.pfam_merged_into IS DISTINCT FROM t.id;

-- The surviving row takes the label the client's report uses, keeping its own
-- spelling in Name 2. COALESCE so a re-run does not overwrite Name 2 with the
-- new name once the first run has already moved it.
UPDATE product_family
   SET pfam_name2    = COALESCE(NULLIF(pfam_name2, ''), pfam_name),
       pfam_name     = 'Inverter',
       complete_name = '[' || pfam_ref || ']-Inverter'
 WHERE pfam_ref = 'WTSG016'
   AND pfam_name <> 'Inverter';

\echo ''
\echo '=== After ================================================================='
\echo ''

SELECT f.pfam_ref, f.pfam_name, f.pfam_name2, m.pfam_ref AS reports_under
  FROM product_family f
  LEFT JOIN product_family m ON m.id = f.pfam_merged_into
 WHERE f.pfam_ref IN ('WTSG009', 'WTSG016')
 ORDER BY f.pfam_ref;

-- To revert:
--   UPDATE product_family f
--      SET pfam_name = b.pfam_name, pfam_name2 = b.pfam_name2,
--          pfam_merged_into = b.pfam_merged_into,
--          complete_name = b.complete_name
--     FROM product_family_inverter_bak_20260910 b
--    WHERE b.id = f.id;
