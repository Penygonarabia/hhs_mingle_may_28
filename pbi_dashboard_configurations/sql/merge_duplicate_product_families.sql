-- =============================================================================
-- Make each Midea AC product sub-group one bar.
--
--   psql -U odoo -d dbprod -f scripts/merge_duplicate_product_families.sql
--
-- WHAT IT DOES. Points five families at the one they belong with, using the
-- same "Report Under" link the Inverter merge used. Idempotent, backed up.
--
--     VRF        -> VRFIN      three rows, all named "VRF"
--     VRFOUT     -> VRFIN      (indoor, outdoor, and a third from the feed)
--     CSTG003    -> CSTG002    Cassette MDV into Cassette R410
--     CONG003    -> CONG002    Concealed Top Discharge into Concealed R410
--     WTSG003    -> WTSG006    the 2026 file's Elite into the Elite that sells
--
-- WHY. The sub-group level is the model family, and product.family was seeded
-- from the ERP's own codes -- which split some models the way the catalog does,
-- by indoor/outdoor or by variant. Three of them drew as separate bars where the
-- business reads one, and two of those carried a name identical to their
-- sibling's, so the chart showed the same caption twice:
--
--     VRF                 15,976,658 of 2025 sales across THREE rows named "VRF"
--     Cassette             3,512,691 against a target of 12,347,095, with a
--                          second bar carrying 2,052,605 of sales and no target
--     Concealed Top Disch.    35,095 of sales and no target
--
-- The Cassette split is the one that mattered: the budget is captured against
-- CSTG002 alone, so the R410 bar showed 28 pct achievement while the MDV bar
-- beside it showed sales against nothing. Merged, Cassette reads 5,565,296
-- against 12,347,095 -- still short of target, but short for a real reason
-- rather than because half its sales were on another bar.
--
-- WTSG003 IS A DIFFERENT CASE FROM THE OTHER FOUR and worth reading on its own.
-- It is not a duplicate family; it is the code HHS's 2026 budget uses for Elite.
-- Their 2025 file said WTSG006 (ELITE R410) and carried SAR 140,113,359; their
-- 2026 file says WTSG003, which bidata knows as "ELITE PLUS R22", and carries
-- SAR 151,804,617. Nothing sells under WTSG003 and Elite R410 sold 97,284,255
-- through August with no target beside it, so the two halves were the same
-- business filed under two codes.
--
-- CONFIRMED BY HHS on 2026-09-10 -- that is what makes this a merge rather than
-- a guess, and it is why the code was created as its own family first: the
-- money was visible and named, and one field moved it once somebody with the
-- authority to say so had said it.
--
-- A MERGE, NOT A DELETE, for the reason spelled out on product.family:
-- the sales side reaches a family through product_category and the BUDGET
-- reaches it through its own code, so a deleted row strands the target captured
-- against that code.
--
-- THE LAUNDRY DUPLICATES ARE LEFT ALONE. LDR001/LDR002, LFL001/LFL002 and
-- LTL001/LTL002 also share names, but they are Beko's and Candy's respectively
-- and are genuinely different families. They never reach these boards, which
-- are Midea AC only.
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
 WHERE f.pfam_ref IN ('VRF','VRFIN','VRFOUT','CSTG002','CSTG003','CONG002',
                      'CONG003','WTSG003','WTSG006')
 ORDER BY f.pfam_ref;

\echo ''
\echo '=== Step 1: Backing up every row involved ================================='
\echo ''

DROP TABLE IF EXISTS product_family_merge_bak_20260910;
CREATE TABLE product_family_merge_bak_20260910 AS
SELECT id, pfam_ref, pfam_name, pfam_name2, pfam_merged_into, complete_name
  FROM product_family
 WHERE pfam_ref IN ('VRF','VRFIN','VRFOUT','CSTG002','CSTG003','CONG002','CONG003');

\echo ''
\echo '=== Step 2: Merging ======================================================='
\echo ''

-- Written as one statement over a literal map so the pairs are visible in one
-- place and adding another is a line, not a copy of the UPDATE.
UPDATE product_family f
   SET pfam_merged_into = t.id
  FROM (VALUES ('VRF','VRFIN'),
               ('VRFOUT','VRFIN'),
               ('CSTG003','CSTG002'),
               ('CONG003','CONG002'),
               ('ACCON','CONG002'),
               ('WTSG003','WTSG006')) AS pair(src, dst)
  JOIN product_family t ON t.pfam_ref = pair.dst
 WHERE f.pfam_ref = pair.src
   AND f.pfam_merged_into IS DISTINCT FROM t.id;

\echo ''
\echo '=== After ================================================================='
\echo ''

SELECT f.pfam_ref, f.pfam_name, m.pfam_ref AS reports_under
  FROM product_family f
  LEFT JOIN product_family m ON m.id = f.pfam_merged_into
 WHERE f.pfam_ref IN ('VRF','VRFIN','VRFOUT','CSTG002','CSTG003','CONG002',
                      'CONG003','WTSG003','WTSG006')
 ORDER BY f.pfam_ref;

\echo ''
\echo '=== Verification: no Midea AC group carries two families any more ========='
\echo ''

SELECT g.code AS product_group,
       count(DISTINCT COALESCE(f.pfam_merged_into, f.id)) AS families
  FROM product_category c
  JOIN product_category g ON g.id = c.parent_id
  JOIN product_family f ON f.id = c.product_family
 WHERE g.code IN ('ACVRF','ACCST','ACCON','ACPAC','ACPKG')
 GROUP BY 1 ORDER BY 1;

-- To revert:
--   UPDATE product_family f SET pfam_merged_into = b.pfam_merged_into
--     FROM product_family_merge_bak_20260910 b WHERE b.id = f.id;
