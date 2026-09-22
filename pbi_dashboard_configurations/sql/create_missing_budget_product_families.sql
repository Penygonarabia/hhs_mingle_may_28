-- =============================================================================
-- Give every sub-group code the budget uses a family to land on.
--
--   psql -U odoo -d dbprod -f scripts/create_missing_budget_product_families.sql
--
-- WHAT IT DOES. Creates a product.family row for each erp_subgroup_code that
-- appears in sales_budget_line and matches no family today, naming it from
-- bidata where bidata knows the code. Idempotent -- it only ever inserts codes
-- that are missing, and never touches an existing row.
--
-- WHY. product.family was seeded from the codes that could be reached from a
-- PRODUCT -- catalog.cat_mainpartno -> bidata -> category. A code the BUDGET
-- uses but nothing sells under was therefore never created, and the target
-- captured against it had nowhere to go: it collapsed onto one nameless bar.
--
-- It is a 2026 problem and it is large. That year's file is coded against a
-- different range of sub-groups from 2025's and from what the products actually
-- sell under:
--
--     WTSG003   151,804,617   bidata calls it ELITE PLUS R22
--     WTSG021    36,954,936   AIR ECO
--     WTSG022    10,603,773   AIR PRO
--     WTSG023     9,771,213   AIR LUX
--     WTSG024     4,910,963   AIR MAX
--
-- After this those five draw as their own bars, carrying their own target and
-- no sales, which is what they are. Before it they were SAR 214m of target on a
-- bar with no name.
--
-- THIS DOES NOT DECIDE WHAT THEY MEAN, deliberately. If HHS confirms that the
-- 2026 file's WTSG003 is the same Elite the products sell as (WTSG006), that is
-- one field in Sales Type Groups > Product Family -- point WTSG003's "Report
-- Under" at ELITE R410 and the target moves to the Elite bar on the next
-- refresh. Guessing it here would move SAR 151.8m onto a bar on this script's
-- authority rather than on theirs.
--
-- WHAT IT STILL DOES NOT COVER, because no code names it: the '*' sentinel on
-- SAR 85,094,928 of 2026 Windows budget. The sentinel resolves only where its
-- product group has exactly one family (see the budget CTE in
-- pbi_sales_dashboards); ACWIN has six, so that money stays unassigned until
-- the file says which window range it belongs to.
--
-- AFTERWARDS rebuild the snapshot:
--     env['pbi.sales.sman.fact'].refresh_fact()
-- =============================================================================

\echo ''
\echo '=== Before: budget codes with no family =================================='
\echo ''

SELECT btrim(l.erp_subgroup_code) AS code, l.year,
       round(sum(l.val_01+l.val_02+l.val_03+l.val_04+l.val_05+l.val_06
                +l.val_07+l.val_08+l.val_09+l.val_10+l.val_11+l.val_12)) AS budget
  FROM sales_budget_line l
 WHERE COALESCE(btrim(l.erp_subgroup_code), '') NOT IN ('', '*')
   AND NOT EXISTS (SELECT 1 FROM product_family f
                    WHERE f.pfam_ref = btrim(l.erp_subgroup_code))
 GROUP BY 1, 2 ORDER BY 3 DESC;

\echo ''
\echo '=== Creating them ========================================================'
\echo ''

-- Named from bidata where it knows the code. Its psgroupname is sometimes just
-- the code echoed back, so a name that equals the code is treated as no name
-- and the code stands in -- a bar captioned WTSG021 is still findable, and is
-- honest about the fact that nothing has told us what it is.
INSERT INTO product_family (pfam_ref, pfam_name, pfam_name2, complete_name,
                            create_uid, create_date, write_uid, write_date)
SELECT c.code,
       COALESCE(n.name, c.code),
       n.name,
       '[' || c.code || ']-' || COALESCE(n.name, c.code),
       1, now(), 1, now()
  FROM (
      SELECT DISTINCT btrim(l.erp_subgroup_code) AS code
        FROM sales_budget_line l
       WHERE COALESCE(btrim(l.erp_subgroup_code), '') NOT IN ('', '*')
         AND NOT EXISTS (SELECT 1 FROM product_family f
                          WHERE f.pfam_ref = btrim(l.erp_subgroup_code))
         -- A code the single-family fallback already resolves must NOT get a
         -- family of its own. Creating one would MOVE the target rather than
         -- rescue it: the budget CTE prefers a direct match, so the row would
         -- leave the group's real family for a brand new empty one, and the
         -- 2026 Concealed, Package and Cassette bars would lose the target
         -- they have. Found the hard way, on the first run of this script.
         AND NOT EXISTS (
             SELECT 1
               FROM product_category gc
               JOIN product_family gf ON gf.id = gc.product_family
              WHERE gc.parent_id = l.product_group_id
              GROUP BY gc.parent_id
             HAVING count(DISTINCT COALESCE(gf.pfam_merged_into, gf.id)) = 1)
         -- And a code carrying no money needs no bar.
         AND (l.val_01+l.val_02+l.val_03+l.val_04+l.val_05+l.val_06
             +l.val_07+l.val_08+l.val_09+l.val_10+l.val_11+l.val_12) <> 0
  ) c
  LEFT JOIN LATERAL (
      SELECT btrim(b.bi_psgroupname) AS name
        FROM bidata b
       WHERE btrim(b.bi_psgroupcode) = c.code
         AND COALESCE(btrim(b.bi_psgroupname), '') NOT IN ('', c.code)
       GROUP BY 1 ORDER BY count(*) DESC LIMIT 1
  ) n ON true
ON CONFLICT (pfam_ref) DO NOTHING;

\echo ''
\echo '=== After: what was created =============================================='
\echo ''

SELECT pfam_ref, pfam_name,
       (SELECT count(*) FROM product_category c WHERE c.product_family = f.id) AS categories
  FROM product_family f
 WHERE NOT EXISTS (SELECT 1 FROM product_category c WHERE c.product_family = f.id)
 ORDER BY pfam_ref;

-- To revert (only removes families nothing points at, which is all this made):
--   DELETE FROM product_family f
--    WHERE NOT EXISTS (SELECT 1 FROM product_category c WHERE c.product_family = f.id)
--      AND NOT EXISTS (SELECT 1 FROM product_family m WHERE m.pfam_merged_into = f.id);
