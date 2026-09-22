-- Two dbprod data repairs applied 2026-09-03, both to make the AC monthly
-- measure resolve a product category for lines that carried none. Each closed a
-- month's value gap against the ERP's own sales report to the cent.
--
--   docker exec -i cloud-db-1 psql -U odoo -d dbprod -v ON_ERROR_STOP=1 \
--       -f - < scripts/dbprod_ac_scope_data_fixes.sql
--
-- IDEMPOTENT: both statements are guarded, so re-running reports 0 rows and
-- changes nothing. Verify afterwards with ./scripts/check_ac_sales_vs_erp.sh
--
-- NEITHER IS A CODE FIX. The dashboards were never changed; the measure was
-- always right and the master data was not. Both repairs are LOCAL TO dbprod --
-- the real defect is upstream in the ERP, which is what deleted the category and
-- omitted the group in the first place.

BEGIN;

-- 1. The ATOM product category (id 1193)
--
-- 10,941 transaction_details rows across 2024-2026 carry trnd_groupid = 1193,
-- but product_category held no such row -- ids stop at 1172. The ERP deleted the
-- category and left every line pointing at it. 7,854 of those lines still found
-- a category through the catalog chain (resolving as ACVRF / ACCON / ACCST, which
-- is the misfiling that had been noted against the Product Group chart); 4 found
-- nothing at all and fell out of scope entirely, costing July 2026 SAR 223,008.55.
--
-- Recreating the row fixes both: July gains exactly that value and no units (the
-- 4 lines are untagged), while the other 7,854 keep their totals and move to
-- ATOM for attribution, since COALESCE prefers pcg.code over the catalog chain.
-- Structural fields match its siblings ACVRF (249) and ACWTS (251); the business
-- flags (def_servicetypeid, allowed_group_bool, sub_category) are deliberately
-- left NULL rather than guessed -- set them in the UI if the category needs them.
INSERT INTO product_category
    (id, name, complete_name, code, parent_id, parent_path,
     create_uid, write_uid, create_date, write_date,
     packaging_reserve_method, warranty_period_combo)
SELECT 1193, 'ATOM', 'Midea / ATOM', 'ATOM', 5, '5/1193/',
       1, 1, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC',
       'partial', 'months'
WHERE NOT EXISTS (SELECT 1 FROM product_category WHERE id = 1193);

-- The sequence sat at 1173, below the id inserted above; without this the next
-- category created through the UI collides on the primary key.
SELECT setval('product_category_id_seq',
              GREATEST(1193, (SELECT last_value FROM product_category_id_seq)));

-- 2. The missing product group on IN10133375 (Jan 2026)
--
-- One line -- 224 units of MKH1-V700-R4-R, SAR 187,488.00 -- carried no
-- trnd_groupid, and the part has neither a catalog row nor a product_template,
-- so nothing could resolve its category and the line fell out of scope. The
-- ERP's own IN10133568 assigns 249 (ACVRF) to the same part five weeks later.
--
-- KNOWN TRADE-OFF, applied deliberately at the user's direction: this closes the
-- January VALUE gap exactly, and opens a QUANTITY one. The part is flagged '02',
-- so its 224 units now count and January reads 22,487 against the ERP report's
-- 22,263. The ERP includes this line's money but not its machines -- its unit
-- gate excludes the part, most plausibly for the missing catalog row -- which is
-- an inconsistency on that side. Reproducing it here would mean requiring
-- catalog membership in the unit gate globally, measured at a 45 pct loss of
-- 2026 units, so it was not done.
--
-- THIS ONE IS FRAGILE. It edits a transaction row, not master data. If the ERP
-- re-syncs IN10133375 the NULL returns and January silently reverts -- re-run
-- this script to reapply.
UPDATE transaction_details
SET trnd_groupid = 249
WHERE id = 474903
  AND trnd_groupid IS NULL
  AND UPPER(TRIM(trnd_part)) = 'MKH1-V700-R4-R';

COMMIT;

-- Rollback, should either need undoing:
--   DELETE FROM product_category WHERE id = 1193;
--   UPDATE transaction_details SET trnd_groupid = NULL WHERE id = 474903;
