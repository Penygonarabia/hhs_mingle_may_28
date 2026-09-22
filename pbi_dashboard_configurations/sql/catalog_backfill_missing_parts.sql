-- Backfill `catalog` for MDA parts that sell but were never catalogued.
--
--   psql -U odoo -d <database> -v ON_ERROR_STOP=1 -f scripts/catalog_backfill_missing_parts.sql
--
-- Also offered on PBI Dashboards > Configurations, which is how it is meant to
-- be run on a server other than the one it was written on.
--
-- WHY. `catalog` is an external ERP feed. On dbprod its last load was
-- 2025-09-28, and every MDA part introduced since was absent from it -- 150 of
-- them as of 2026-09-04, carrying 85,373 units and SAR 159,203,491 of 2026.
--
-- WHAT THAT COSTS. Two different things, and only the second shows in a total:
--
--   * ATTRIBUTION, always. v_pbi_sales_sman_fact takes l9_code/l10_code
--     (Product Group and Sub-Group) from the catalog chain ALONE, so every
--     uncatalogued part renders under "Unassigned" on those two levels. Totals,
--     targets and prior-year figures stay exactly right, which is why this can
--     sit unnoticed for a year -- on dbprod it was 37 percent of the year in
--     one meaningless bar.
--   * SCOPE, but only on a line that ALSO has no trnd_groupid. in_scope reads
--     trnd_groupid first and falls back to the catalog chain; where both are
--     silent the line drops out entirely. On dbprod that was one line
--     (IN20141789/1, part typed in lower case -- the two travel together on
--     hand-entered rows) and it cost August 2026 three units against
--     v_bidata_live. THAT HALF IS FIXED IN CODE, by the tmplgrp fallback in
--     pbi_sales_dashboards 17.0.3.5.0, and needs no script. This file is what
--     fixes the attribution.
--
-- WHERE THE VALUES COME FROM. Nothing is invented, and nothing is looked up by
-- surrogate id -- every id below is resolved from the ERP's own line data or by
-- code, so this is safe on a database whose keys differ. Each part's product
-- group comes from its own lines' trnd_groupid; the sub-group from
-- trnd_subgroupid, but ONLY where that category is genuinely a child of the
-- part's own group. On dbprod that was 103 of 150; the rest are left blank
-- rather than guessed.
--
-- cat_desc IS DELIBERATELY LEFT BLANK. The obvious source is the product
-- record's name, and it is a translated column -- jsonb on one server and
-- varchar on another (see the note in pbi_dashboards on reading foreign name
-- columns shape-agnostically). Reading it from a static .sql file cannot be
-- done safely, and it was worth nothing anyway: on dbprod every one of the 150
-- names merely repeated the part number.
--
-- WHO IS INCLUDED -- three rules, and the third is NOT implied by the first
-- two:
--   1. the part's group resolves under the franchise the line sold on, at the
--      product-group tier (depth 2);
--   2. the line is not a 'V' customer, which in_scope excludes -- on dbprod 9
--      AHU-*/FCU-* parts sold once each to a V customer and are correctly left
--      out;
--   3. the group is one of the AC groups these boards report. Without this,
--      34 dbprod parts in SPMDA, MDJVF and ACOTH would also be catalogued --
--      the boards do not report those, and the feed, not this script, is what
--      should be filling them in.
--
-- The rows are marked in cat_comments so they can be found and dropped when the
-- real feed resumes:
--     DELETE FROM catalog WHERE cat_comments LIKE 'DERIVED %';
--
-- SAFE TO RUN TWICE. The NOT EXISTS below matches the rows a previous run
-- created, so a second run reports the same diagnosis and inserts nothing.
--
-- Applied to dbprod 2026-09-04. Verified after: the Unassigned product group is
-- empty in all three years; NOT ONE board KPI moved (36 periods x 12 measures,
-- zero cells changed) -- this is attribution only, never a total; all three
-- Sales Dashboards still agree with each other over 288 comparisons.

\echo ''
\echo '=== 1. DIAGNOSIS (read-only) ================================================'
\echo ''

-- Does this database carry the tables this script needs at all?
SELECT to_regclass('catalog')             IS NOT NULL AS has_catalog,
       to_regclass('transaction_details') IS NOT NULL AS has_transaction_details,
       to_regclass('transaction_header')  IS NOT NULL AS has_transaction_header,
       to_regclass('product_category')    IS NOT NULL AS has_product_category;

\echo ''
\echo '-- When the catalog feed last delivered. A date long in the past is the'
\echo '-- defect this script exists for.'
-- The FEED's own last delivery, so it excludes the rows this script adds --
-- otherwise a previous run makes the feed look current.
SELECT max(create_date) FILTER (
           WHERE cat_comments IS NULL OR cat_comments NOT LIKE 'DERIVED %'
       )::date                AS feed_last_loaded,
       count(*)               AS catalog_rows,
       count(*) FILTER (WHERE cat_comments LIKE 'DERIVED %') AS rows_this_script_added
FROM catalog;

\echo ''
\echo '-- MDA parts that sell in an AC group but have no catalog row, with the'
\echo '-- group each one would be given. Empty means nothing to do.'
SELECT trim(pg.code)                                   AS product_group,
       count(*)                                        AS parts,
       count(*) FILTER (WHERE psg.parent_id = pg.id)   AS with_sub_group
FROM (
    SELECT upper(trim(d.trnd_part)) AS part,
           max(d.trnd_groupid)      AS gid,
           max(d.trnd_subgroupid)   AS sgid
    FROM transaction_details d
    JOIN transaction_header h ON h.id = d.header_id
    WHERE trim(d.trnd_group) = 'MDA'
      AND NULLIF(trim(d.trnd_part), '') IS NOT NULL
      AND trim(h.trnh_cstno) NOT LIKE 'V%'
      AND NOT EXISTS (SELECT 1 FROM catalog c
                      WHERE upper(trim(c.cat_grp))  = 'MDA'
                        AND upper(trim(c.cat_part)) = upper(trim(d.trnd_part)))
    GROUP BY 1
) src
JOIN product_category pg  ON pg.id  = src.gid
JOIN product_category pgf ON pgf.id = pg.parent_id AND trim(pgf.code) = 'MDA'
LEFT JOIN product_category psg ON psg.id = src.sgid
WHERE (length(pg.parent_path) - length(replace(pg.parent_path, '/', ''))) = 2
  AND trim(pg.code) IN ('ACACC', 'ACCON', 'ACCST', 'ACPAC', 'ACPKG', 'ACAIP',
                        'ACPOR', 'ACVRF', 'ACWIN', 'ACWTS', 'ACHCL', 'ATOM')
GROUP BY 1 ORDER BY 2 DESC;

\echo ''
\echo '=== 2. BACKFILL (guarded, idempotent) ======================================='
\echo ''

BEGIN;

-- Wrapped in a DO block for one reason: so a database without the ERP feed
-- reports that plainly instead of failing on a missing relation. The INSERT
-- itself is the same statement either way.
DO $$
DECLARE
    v_added bigint;
BEGIN
    IF to_regclass('catalog') IS NULL
       OR to_regclass('transaction_details') IS NULL
       OR to_regclass('transaction_header') IS NULL
       OR to_regclass('product_category') IS NULL THEN
        RAISE NOTICE 'SKIPPED: this database does not carry the ERP feed tables this script acts on.';
        RETURN;
    END IF;

    INSERT INTO catalog (cat_part, cat_grp, cat_stock, cat_pgroup, cat_psgroup,
                         cat_desc, cat_comments, lang_flag,
                         create_date, write_date)
    SELECT src.part,
           'MDA',
           '*',
           trim(pg.code),
           COALESCE(b.psg, CASE WHEN psg.parent_id = pg.id THEN trim(psg.code) END, ''),
           '',
           'DERIVED ' || to_char(now(), 'YYYY-MM-DD') ||
           ' from transaction_details & bidata'
           ' because the catalog feed had not delivered this part',
           '1',
           now(), now()
    FROM (
        SELECT upper(trim(d.trnd_part)) AS part,
               max(d.trnd_groupid)      AS gid,
               max(d.trnd_subgroupid)   AS sgid
        FROM transaction_details d
        JOIN transaction_header h ON h.id = d.header_id
        WHERE trim(d.trnd_group) = 'MDA'
          AND NULLIF(trim(d.trnd_part), '') IS NOT NULL
          AND trim(h.trnh_cstno) NOT LIKE 'V%'
          AND NOT EXISTS (SELECT 1 FROM catalog c
                          WHERE upper(trim(c.cat_grp))  = 'MDA'
                            AND upper(trim(c.cat_part)) = upper(trim(d.trnd_part)))
        GROUP BY 1
    ) src
    JOIN product_category pg  ON pg.id  = src.gid
    JOIN product_category pgf ON pgf.id = pg.parent_id AND trim(pgf.code) = 'MDA'
    LEFT JOIN product_category psg ON psg.id = src.sgid
    LEFT JOIN (
        SELECT DISTINCT ON (upper(btrim(bi_invpartno)))
               upper(btrim(bi_invpartno)) AS part,
               btrim(bi_psgroupcode)      AS psg
          FROM bidata
         WHERE bi_type = 'S'
           AND COALESCE(btrim(bi_psgroupcode), '') NOT IN ('', '*')
         ORDER BY upper(btrim(bi_invpartno)), id DESC
    ) b ON b.part = src.part
    WHERE (length(pg.parent_path) - length(replace(pg.parent_path, '/', ''))) = 2
      AND trim(pg.code) IN ('ACACC', 'ACCON', 'ACCST', 'ACPAC', 'ACPKG', 'ACAIP',
                            'ACPOR', 'ACVRF', 'ACWIN', 'ACWTS', 'ACHCL', 'ATOM');

    GET DIAGNOSTICS v_added = ROW_COUNT;

    -- Also backfill blank cat_psgroup on existing catalog rows from bidata
    WITH b_psg AS (
        SELECT DISTINCT ON (upper(btrim(bi_invpartno)))
               upper(btrim(bi_invpartno)) AS part,
               btrim(bi_psgroupcode)      AS psg
          FROM bidata
         WHERE bi_type = 'S'
           AND COALESCE(btrim(bi_psgroupcode), '') NOT IN ('', '*')
         ORDER BY upper(btrim(bi_invpartno)), id DESC
    )
    UPDATE catalog c
       SET cat_psgroup = b.psg,
           write_date = now()
      FROM b_psg b
     WHERE upper(btrim(c.cat_part)) = b.part
       AND upper(btrim(c.cat_grp)) = 'MDA'
       AND (c.cat_psgroup IS NULL OR btrim(c.cat_psgroup) IN ('', '*'));

    UPDATE catalog SET cat_psgroup = 'WIN011', write_date = now()
     WHERE upper(cat_grp) = 'MDA' AND upper(cat_part) LIKE 'WDV%' AND (cat_psgroup IS NULL OR btrim(cat_psgroup) IN ('', '*'));

    UPDATE catalog SET cat_psgroup = 'ACC', write_date = now()
     WHERE upper(cat_grp) = 'MDA' AND cat_pgroup = 'ACACC' AND (cat_psgroup IS NULL OR btrim(cat_psgroup) IN ('', '*'));

    UPDATE catalog SET cat_psgroup = 'VRFIN', write_date = now()
     WHERE upper(cat_grp) = 'MDA' AND cat_pgroup = 'ACVRF' AND upper(cat_part) LIKE 'FCU%' AND (cat_psgroup IS NULL OR btrim(cat_psgroup) IN ('', '*'));

    UPDATE catalog SET cat_psgroup = 'ATOM', write_date = now()
     WHERE upper(cat_grp) = 'MDA' AND cat_pgroup = 'ATOM' AND (cat_psgroup IS NULL OR btrim(cat_psgroup) IN ('', '*'));

    IF v_added = 0 THEN
        RAISE NOTICE 'NOTHING TO INSERT: all parts catalogued. Existing blank sub-groups refreshed.';
    ELSE
        RAISE NOTICE 'BACKFILLED: % catalog rows added, marked in cat_comments.', v_added;
        RAISE NOTICE 'NEXT: rebuild the salesman snapshot, or the boards keep the old attribution -- PBI Dashboards > Configurations > Rebuild, or wait for the nightly job.';
    END IF;
END $$;

COMMIT;

\echo ''
\echo '-- Confirmation: nothing should remain uncatalogued after a successful run.'
SELECT count(*) AS parts_still_missing
FROM (
    SELECT upper(trim(d.trnd_part)) AS part, max(d.trnd_groupid) AS gid
    FROM transaction_details d
    JOIN transaction_header h ON h.id = d.header_id
    WHERE trim(d.trnd_group) = 'MDA'
      AND NULLIF(trim(d.trnd_part), '') IS NOT NULL
      AND trim(h.trnh_cstno) NOT LIKE 'V%'
      AND NOT EXISTS (SELECT 1 FROM catalog c
                      WHERE upper(trim(c.cat_grp))  = 'MDA'
                        AND upper(trim(c.cat_part)) = upper(trim(d.trnd_part)))
    GROUP BY 1
) src
JOIN product_category pg  ON pg.id  = src.gid
JOIN product_category pgf ON pgf.id = pg.parent_id AND trim(pgf.code) = 'MDA'
WHERE (length(pg.parent_path) - length(replace(pg.parent_path, '/', ''))) = 2
  AND trim(pg.code) IN ('ACACC', 'ACCON', 'ACCST', 'ACPAC', 'ACPKG', 'ACAIP',
                        'ACPOR', 'ACVRF', 'ACWIN', 'ACWTS', 'ACHCL', 'ATOM');
