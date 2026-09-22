-- =============================================================================
-- Put the ATOM outdoor units back in Concealed, where the ERP already has them.
--
--   psql -U odoo -d dbprod -f scripts/fix_atom_outdoor_product_group.sql
--
-- WHAT IT DOES. Moves the ATOM system's outdoor units -- eleven catalog rows,
-- all MDV-V..W..(ATB) -- from ACVRF / VRFOUT to ACCON / CON004. Idempotent, and
-- it backs up every row it touches. Totals do not move: this changes which
-- Product Group and Product Sub-Group bar the money lands on, nothing else.
--
-- THE RULE IS THE ERP'S GROUP, NOT THE PART NUMBER. Rows are selected by
-- joining to what trnd_groupid says the part is, and only those the ERP calls
-- ATOM are moved. Matching on the (ATB) suffix alone looked equivalent and is
-- not: three (ATB) parts, MDV-V18WDHN1(ATB) among them, are filed under ACVRF
-- by the ERP itself, so a name-shaped rule drags real VRF parts into Concealed. Selecting on the disagreement itself also
-- makes the script self-limiting -- it can only ever move a row the ERP
-- already contradicts.
--
-- WHY. The boards resolve Product Group and Product Sub-Group through the
-- legacy `catalog` table (cat_pgroup / cat_psgroup), while the BUDGET is
-- captured against product_group_id, which is what transaction_details.
-- trnd_groupid states. Those two agree on every part that sells except these
-- eleven: the ERP calls them ATOM and the catalog calls them VRF. Nothing else
-- in the database calls them VRF --
--
--   * trnd_groupid says ATOM on all 5,294 lines they appear on;
--   * their own indoor partners are catalogued ACCON / CON003 (concealed
--     indoor R410) and ACCST / CST005, so the system they belong to is a
--     concealed/cassette one, not a VRF one;
--   * CON004 is the concealed OUTDOOR R410 sub-group that CON003 pairs with,
--     which is why that is the destination rather than a bare ACCON.
--
-- WHAT IT IS WORTH, Jan-Sep 2025 in scope: SAR 30,670,445 currently reported
-- as VRF. That one misfiling is the whole of the Product Group level's
-- target/actual disagreement:
--
--                       sales        target      before      after
--     VRF          15,985,536    19,350,623        241%        83%
--     Concealed    52,891,371    45,770,169         49%       116%
--
-- and it is what put VRF 2.7x over its target while Concealed sat at half of
-- one. Against the client's own September report, which reads VRF 17.2m and
-- Concealed 49.1m year to date, the corrected VRF figure is the ERP's own
-- ACVRF total to the riyal.
--
-- WHAT IT DOES NOT FIX. Cassette still reads SAR 5,565,296 against the client's
-- 9.5m. Some of these outdoor units pair with cassette indoor units rather than
-- concealed ones, and neither the catalog nor trnd_subgroupid says which --
-- every one of them carries a NULL trnd_subgroupid. Splitting them needs HHS to
-- say which model pairs with which; sending them all to Concealed is the
-- closest single answer the data supports, and it is right about VRF either
-- way.
--
-- RE-RUN IT AFTER A CATALOG RELOAD. `catalog` is an ERP feed table and a fresh
-- load restores the old classification, so this is wired into
-- sync_and_repair_all_masters.sql alongside the other catalog repairs. The real
-- fix is in the ERP's own catalog; until it lands, this stands in.
--
-- AFTERWARDS the snapshot must be rebuilt -- the boards read a materialized
-- view. `catalog` carries no refresh trigger (it is bulk-loaded, and reacting
-- to every write would rebuild continuously), so force it:
--     env['pbi.sales.sman.fact'].refresh_fact()
-- =============================================================================

\echo ''
\echo '=== Before ================================================================'
\echo ''

SELECT trim(cat_pgroup) AS product_group, trim(cat_psgroup) AS sub_group, count(*) AS parts
  FROM catalog
 WHERE trim(cat_grp) = 'MDA'
   AND upper(trim(cat_part)) LIKE 'MDV-V%(ATB)%'
 GROUP BY 1, 2
 ORDER BY 1, 2;

\echo ''
\echo '=== Step 1: Selecting the rows the ERP contradicts ========================'
\echo ''

-- Catalog rows filed under VRF that trnd_groupid calls ATOM. A temp view, so
-- the backup and the UPDATE below cannot pick different rows -- and so the
-- UPDATE re-reads it AFTER the backup has been taken, which is why it is a
-- view over live data rather than a snapshot.
CREATE TEMP VIEW atom_outdoor_rows AS
WITH erp AS (
    SELECT DISTINCT ON (upper(trim(d.trnd_part)))
           upper(trim(d.trnd_part)) AS part, pc.code AS grp
      FROM transaction_details d
      JOIN product_category pc ON pc.id = d.trnd_groupid
     WHERE trim(d.trnd_group) = 'MDA'
     GROUP BY 1, pc.code
     ORDER BY 1, count(*) DESC
)
SELECT c.id, c.cat_part
  FROM catalog c
  JOIN erp e ON e.part = upper(trim(c.cat_part))
 WHERE trim(c.cat_grp) = 'MDA'
   AND trim(c.cat_pgroup) = 'ACVRF'
   AND e.grp = 'ATOM';

SELECT count(*) AS rows_to_move FROM atom_outdoor_rows;

\echo ''
\echo '=== Step 2: Backing them up =============================================='
\echo ''

DROP TABLE IF EXISTS catalog_atom_outdoor_bak_20260910;
CREATE TABLE catalog_atom_outdoor_bak_20260910 AS
SELECT id, cat_part, cat_grp, cat_pgroup, cat_psgroup
  FROM catalog
 WHERE id IN (SELECT id FROM atom_outdoor_rows);

\echo ''
\echo '=== Step 3: Re-pointing them at Concealed ================================='
\echo ''

UPDATE catalog
   SET cat_pgroup  = 'ACCON',
       cat_psgroup = 'CON004'
 WHERE id IN (SELECT id FROM atom_outdoor_rows);

\echo ''
\echo '=== After ================================================================='
\echo ''

SELECT trim(cat_pgroup) AS product_group, trim(cat_psgroup) AS sub_group, count(*) AS parts
  FROM catalog
 WHERE trim(cat_grp) = 'MDA'
   AND upper(trim(cat_part)) LIKE 'MDV-V%(ATB)%'
 GROUP BY 1, 2
 ORDER BY 1, 2;

\echo ''
\echo '=== Verification: catalog now agrees with the ERP on every part that sells '
\echo ''

-- Should return only rows the ERP itself disagrees on for another reason.
-- Before this script it also returned the ATOM outdoor units.
WITH erp AS (
    SELECT DISTINCT ON (upper(trim(d.trnd_part)))
           upper(trim(d.trnd_part)) AS part, pc.code AS grp
      FROM transaction_details d
      JOIN product_category pc ON pc.id = d.trnd_groupid
     WHERE trim(d.trnd_group) = 'MDA'
     GROUP BY 1, pc.code
     ORDER BY 1, count(*) DESC
)
SELECT c.cat_part, trim(c.cat_pgroup) AS catalog_group, e.grp AS erp_group
  FROM catalog c
  JOIN erp e ON e.part = upper(trim(c.cat_part))
 WHERE trim(c.cat_grp) = 'MDA'
   AND trim(c.cat_pgroup) <> e.grp
   AND e.grp <> 'ATOM'          -- the ATOM indoor units are correctly filed
 ORDER BY 1;                    -- under Concealed/Cassette and stay there

-- To revert:
--   UPDATE catalog c
--      SET cat_pgroup  = b.cat_pgroup,
--          cat_psgroup = b.cat_psgroup
--     FROM catalog_atom_outdoor_bak_20260910 b
--    WHERE b.id = c.id;
