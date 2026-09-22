-- Portable form of the two AC-scope data repairs, for a database OTHER than the
-- one they were first applied to.
--
--   psql -U odoo -d <database> -v ON_ERROR_STOP=1 -f scripts/ac_scope_data_fixes_portable.sql
--
-- Read scripts/dbprod_ac_scope_data_fixes.sql first for WHY these exist. That
-- file is the dbprod record and hardcodes dbprod's surrogate keys -- product
-- category id 5 as the Midea root, 1193 as the deleted ATOM group, detail row
-- 474903 as the January line. NONE of those ids can be assumed on another
-- database: id 5 there may be an entirely different category, and attaching a
-- new group under it would put ATOM in the wrong place. This version looks
-- everything up by code and document number instead, and refuses to act when a
-- lookup is ambiguous.
--
-- SAFE TO RUN TWICE. Every statement is guarded; a second run reports the same
-- diagnosis and changes nothing.
--
-- NOT NEEDED HERE: the lower-case part numbers (defect 01 of the ERP report).
-- The dashboards upper-case both sides of every part-number join already, so no
-- database-side repair makes any difference to them -- that one is fixed in the
-- ERP or not at all.

\echo ''
\echo '=== 1. DIAGNOSIS (read-only) ================================================'
\echo ''

-- Does this database even have the ERP feed these repairs act on?
SELECT to_regclass('transaction_details') IS NOT NULL AS has_transaction_details,
       to_regclass('product_category')    IS NOT NULL AS has_product_category,
       to_regclass('catalogflags')        IS NOT NULL AS has_catalogflags;

\echo ''
\echo '-- Product-group ids referenced by invoice lines that do NOT exist as categories.'
\echo '-- On dbprod this was a single row: id 1193, the deleted ATOM group.'
SELECT d.trnd_groupid            AS dangling_id,
       count(*)                  AS invoice_lines,
       count(DISTINCT upper(trim(d.trnd_part))) AS distinct_parts,
       min(substring(h.trnh_date,1,6)) AS first_period,
       max(substring(h.trnh_date,1,6)) AS last_period
FROM transaction_details d
JOIN transaction_header h ON h.id = d.header_id
WHERE d.trnd_groupid IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM product_category c WHERE c.id = d.trnd_groupid)
GROUP BY 1 ORDER BY 2 DESC;

\echo ''
\echo '-- The Midea root category this script would attach a restored group under.'
\echo '-- Exactly one row must come back, or the repair below declines to run.'
SELECT id, code, name, parent_id
FROM product_category
WHERE trim(code) = 'MDA' AND parent_id IS NULL;

\echo ''
\echo '-- Invoice lines in AC scope carrying NO product group at all.'
SELECT trim(h.trnh_no) AS doc_no, h.trnh_date,
       upper(trim(d.trnd_part)) AS part,
       coalesce(d.trnd_qtyiss,0) AS qty
FROM transaction_details d
JOIN transaction_header h ON h.id = d.header_id
WHERE d.trnd_groupid IS NULL
  AND trim(d.trnd_group) = 'MDA'
  AND lpad(trim(h.trnh_type),2,'0') IN ('01','02')
  AND trim(h.trnh_status) IN ('C','P')
  AND trim(h.trnh_cstno) NOT LIKE 'V%'
  AND coalesce(d.trnd_qtyiss,0) + coalesce(d.trnd_ret,0) > 0
ORDER BY h.trnh_date
LIMIT 50;

\echo ''
\echo '=== 2. REPAIR (guarded, idempotent) ========================================='
\echo ''

BEGIN;

-- 2a. Restore the ATOM product group, if this database shows the same defect.
--
-- Only acts when ALL of the following hold, and says so when they do not:
--   * a single Midea root category exists (looked up by code, never by id)
--   * invoice lines actually reference a category id that does not exist
--   * no category with code ATOM exists already
--
-- The id is reused deliberately: it is the ERP's own category id arriving
-- through the feed, so recreating the row AT that id is what makes the existing
-- references resolve. Creating ATOM at a fresh id would leave every line still
-- dangling.
DO $$
DECLARE
    v_parent   integer;
    v_dangling integer;
    v_lines    bigint;
BEGIN
    SELECT id INTO v_parent
    FROM product_category
    WHERE trim(code) = 'MDA' AND parent_id IS NULL;

    IF v_parent IS NULL THEN
        RAISE NOTICE 'SKIPPED (ATOM): no single Midea root category with code MDA -- resolve by hand.';
        RETURN;
    END IF;

    IF EXISTS (SELECT 1 FROM product_category WHERE trim(code) = 'ATOM') THEN
        RAISE NOTICE 'SKIPPED (ATOM): a category with code ATOM already exists. Nothing to do.';
        RETURN;
    END IF;

    -- The most-referenced dangling id, and how many lines hang off it.
    SELECT d.trnd_groupid, count(*) INTO v_dangling, v_lines
    FROM transaction_details d
    WHERE d.trnd_groupid IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM product_category c WHERE c.id = d.trnd_groupid)
    GROUP BY d.trnd_groupid
    ORDER BY count(*) DESC
    LIMIT 1;

    IF v_dangling IS NULL THEN
        RAISE NOTICE 'SKIPPED (ATOM): no dangling product-group references. This database does not have the defect.';
        RETURN;
    END IF;

    INSERT INTO product_category
        (id, name, complete_name, code, parent_id, parent_path,
         create_uid, write_uid, create_date, write_date,
         packaging_reserve_method, warranty_period_combo)
    VALUES
        (v_dangling, 'ATOM', 'Midea / ATOM', 'ATOM', v_parent,
         v_parent || '/' || v_dangling || '/',
         1, 1, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC',
         'partial', 'months');

    -- The sequence must clear the id just inserted or the next category created
    -- through the UI collides on the primary key.
    PERFORM setval('product_category_id_seq',
                   GREATEST(v_dangling, (SELECT last_value FROM product_category_id_seq)));

    RAISE NOTICE 'CREATED (ATOM): category id % under parent %, resolving % invoice lines.',
                 v_dangling, v_parent, v_lines;

    -- Business flags (def_servicetypeid, allowed_group_bool, sub_category) are
    -- left NULL on purpose. They are configuration, nothing in the sales measure
    -- reads them, and guessing them is worse than leaving them for the UI.
END $$;

-- 2b. The invoice line with no product group.
--
-- Located by DOCUMENT NUMBER and part, never by row id -- the dbprod row id
-- means nothing here. The group is resolved by code under the Midea root, so it
-- lands in the right place whatever the local ids are.
DO $$
DECLARE
    v_group integer;
    v_rows  integer;
BEGIN
    SELECT c.id INTO v_group
    FROM product_category c
    JOIN product_category p ON p.id = c.parent_id
    WHERE trim(c.code) = 'ACVRF' AND trim(p.code) = 'MDA' AND p.parent_id IS NULL;

    IF v_group IS NULL THEN
        RAISE NOTICE 'SKIPPED (IN10133375): no ACVRF category under a Midea root.';
        RETURN;
    END IF;

    UPDATE transaction_details d
    SET trnd_groupid = v_group
    FROM transaction_header h
    WHERE h.id = d.header_id
      AND trim(h.trnh_no) = 'IN10133375'
      AND upper(trim(d.trnd_part)) = 'MKH1-V700-R4-R'
      AND d.trnd_groupid IS NULL;

    GET DIAGNOSTICS v_rows = ROW_COUNT;
    IF v_rows = 0 THEN
        RAISE NOTICE 'SKIPPED (IN10133375): document/part not present, or its group is already set.';
    ELSE
        RAISE NOTICE 'UPDATED (IN10133375): % line(s) set to category %.', v_rows, v_group;
    END IF;
END $$;

COMMIT;

\echo ''
\echo '=== 3. AFTERWARDS =========================================================='
\echo ''
\echo 'Re-run section 1: the dangling-id list should now be empty.'
\echo ''
\echo 'KNOWN TRADE-OFF, inherited from the dbprod repair: setting the group on'
\echo 'IN10133375 brings its 224 flagged units into the unit count. If this'
\echo 'database is reconciled against the same ERP report, that month will read 224'
\echo 'units HIGH -- the ERP counts that line value but not its machines. Section 2b'
\echo 'is the part to skip if that matters more than the value agreeing.'
\echo ''
\echo 'BOTH REPAIRS ARE LOCAL. The defects are in the ERP -- a deleted category and'
\echo 'an omitted product group -- so a re-sync of either record restores the'
\echo 'problem. 2b is the fragile one: it edits a transaction row, not master data.'
\echo 'See docs/erp_master_data_defects.html for what was raised upstream.'
\echo ''
