-- Find documents that the ERP has POSTED but the `bidata` feed never received.
--
--   psql -U odoo -d <database> -f scripts/check_bidata_feed_gaps.sql
--
-- READ-ONLY. Nothing is written; every statement is a SELECT.
--
-- WHY THIS EXISTS. On dbprod, June 2026 read 1 unit and SAR 1,194.05 BELOW the
-- ERP's own report for months. The cause was CR20112352 -- a posted credit note
-- for a customer return, present in transaction_details and absent from bidata
-- entirely. Anything reconciled against bidata inherits that: the return is not
-- subtracted, so both units and revenue read high.
--
-- The mechanism is the feed's, not the data's. bidata is populated with a status
-- filter applied AT FEED TIME and carries no status column of its own, while the
-- ERP flips documents from 'N' to 'P' IN PLACE afterwards without touching
-- write_date. A document posted after the feed ran is therefore invisible to it
-- forever, and nothing in bidata reveals that it is missing.
--
-- SCOPE. MDA franchise, AC product groups, posted/closed, non-V customers --
-- the same scope as ac_sales_by_month_cumulative.sql. Adjust the category list
-- below if the server being checked reports on a different set.
--
-- ON STAGING: bidata there is a NARROWER variant than dbprod's (no bi_invprice),
-- and v_bidata_live may not exist at all. Section 1 checks both before anything
-- else runs, and sections 2 and 3 are independent -- section 3 needs only
-- `bidata`, so it still answers even where the view is absent.

SET statement_timeout = '600s';
-- v_bidata_live LEFT JOINs ten stats-less legacy master tables; without this the
-- planner nested-loops every one of them and the query takes minutes not seconds.
SET enable_nestloop = off;

\echo ''
\echo '=== 1. WHAT THIS DATABASE HAS ==============================================='
\echo ''

SELECT to_regclass('bidata')              IS NOT NULL AS has_bidata,
       to_regclass('v_bidata_live')       IS NOT NULL AS has_v_bidata_live,
       to_regclass('transaction_details') IS NOT NULL AS has_transaction_details;

\echo ''
\echo '-- How far the feed actually reaches. A document dated after max_invdate is'
\echo '-- simply not fed yet; one dated BEFORE it and still missing is a real gap.'
SELECT MAX(bi_lastmodifieddate)                        AS feed_last_modified,
       MAX(NULLIF(TRIM(bi_invdate),''))                AS max_invoice_date,
       COUNT(*)                                        AS rows_total
FROM bidata;

\echo ''
\echo '=== 2. MONTHLY COMPARISON =================================================='
\echo '-- transaction_details (live) against v_bidata_live (fed). A month where the'
\echo '-- feed reads HIGHER is the signature of a missing credit note.'
\echo ''

WITH unitpart AS MATERIALIZED (
    SELECT DISTINCT UPPER(TRIM(cat_grp)) AS grp, UPPER(TRIM(cat_stock)) AS stock,
           UPPER(TRIM(cat_part)) AS part
    FROM catalogflags
    WHERE TRIM(cat_flag) = '02' AND NULLIF(TRIM(cat_part), '') IS NOT NULL
),
cat AS MATERIALIZED (
    SELECT DISTINCT ON (UPPER(TRIM(cat_part)))
        UPPER(TRIM(cat_part)) AS part, TRIM(cat_grp) AS fr, TRIM(cat_pgroup) AS pg
    FROM catalog ORDER BY 1, id
),
d1 AS MATERIALIZED (
    SELECT DISTINCT ON (TRIM(code)) id, TRIM(code) AS code FROM product_category
    WHERE (LENGTH(parent_path)-LENGTH(REPLACE(parent_path,'/',''))) = 1
      AND NULLIF(TRIM(code),'') IS NOT NULL ORDER BY TRIM(code), id
),
d2 AS MATERIALIZED (
    SELECT DISTINCT ON (parent_id, TRIM(code)) id, parent_id, TRIM(code) AS code
    FROM product_category
    WHERE (LENGTH(parent_path)-LENGTH(REPLACE(parent_path,'/',''))) = 2
      AND NULLIF(TRIM(code),'') IS NOT NULL ORDER BY parent_id, TRIM(code), id
),
live AS (
    SELECT SUBSTRING(h.trnh_date,1,4)::INT AS yr, SUBSTRING(h.trnh_date,5,2)::INT AS mth,
        SUM(CASE WHEN u.part IS NULL THEN 0
                 WHEN LPAD(TRIM(h.trnh_type),2,'0')='02' THEN -COALESCE(d.trnd_ret,0)
                 ELSE COALESCE(d.trnd_qtyiss,0) END)::NUMERIC AS qty,
        ROUND(SUM((CASE WHEN LPAD(TRIM(h.trnh_type),2,'0')='02' THEN -COALESCE(d.trnd_ret,0)
                        ELSE COALESCE(d.trnd_qtyiss,0) END)
          * (COALESCE(d.trnd_price,0)
             - (COALESCE(d.trnd_disc,0)+COALESCE(d.trnd_promodisc,0)+COALESCE(d.trnd_campaign,0)
                + CASE WHEN COALESCE(h.trnh_total,0)>0
                       THEN (COALESCE(d.trnd_price,0)-COALESCE(d.trnd_disc,0)
                             -COALESCE(d.trnd_promodisc,0)-COALESCE(d.trnd_campaign,0))
                            * COALESCE(h.trnh_headdisc,0)/h.trnh_total ELSE 0 END)
             - COALESCE(d.trnd_cstspldisc,0)))::numeric, 2) AS amount
    FROM transaction_details d
    JOIN transaction_header h ON h.id = d.header_id
    LEFT JOIN product_category pcg ON pcg.id = d.trnd_groupid
    LEFT JOIN unitpart u ON u.grp = TRIM(d.trnd_group) AND u.stock = TRIM(d.trnd_stock)
       AND u.part = UPPER(TRIM(d.trnd_part))
    LEFT JOIN cat ON cat.part = UPPER(TRIM(d.trnd_part))
    LEFT JOIN d1 ON d1.code = cat.fr
    LEFT JOIN d2 ON d2.parent_id = d1.id AND d2.code = cat.pg
    WHERE LPAD(TRIM(h.trnh_type),2,'0') IN ('01','02')
      AND TRIM(d.trnd_group) = 'MDA'
      AND TRIM(h.trnh_status) IN ('C','P')
      AND TRIM(h.trnh_cstno) NOT LIKE 'V%'
      AND COALESCE(TRIM(pcg.code), TRIM(d2.code), '') IN (
          'ACACC','ACCON','ACCST','ACPAC','ACPKG','ACAIP',
          'ACPOR','ACVRF','ACWIN','ACWTS','ACHCL','ATOM')
    GROUP BY 1,2
),
fed AS (
    SELECT bi_year AS yr, bi_month AS mth,
           SUM(bi_qty)::numeric AS qty, ROUND(SUM(bi_amount)::numeric,2) AS amount
    FROM v_bidata_live
    WHERE TRIM(bi_type) = 'S' AND TRIM(bi_franchisecode) = 'MDA'
      AND TRIM(bi_pgroupcode) IN (
          'ACACC','ACCON','ACCST','ACPAC','ACPKG','ACAIP',
          'ACPOR','ACVRF','ACWIN','ACWTS','ACHCL','ATOM')
    GROUP BY 1,2
)
SELECT COALESCE(l.yr, f.yr) AS yr, COALESCE(l.mth, f.mth) AS mth,
       l.qty AS live_qty, f.qty AS fed_qty, f.qty - l.qty AS qty_gap,
       l.amount AS live_amount, f.amount AS fed_amount, f.amount - l.amount AS amount_gap
FROM live l FULL JOIN fed f ON f.yr = l.yr AND f.mth = l.mth
WHERE COALESCE(l.yr, f.yr) >= 2025
  AND (l.qty IS DISTINCT FROM f.qty OR l.amount IS DISTINCT FROM f.amount)
ORDER BY 1,2;

\echo ''
\echo '=== 3. DOCUMENTS THE FEED NEVER RECEIVED ==================================='
\echo '-- In scope and posted in the ERP, but with no row in bidata at all.'
\echo '-- CREDIT NOTES (type 02) are the ones that distort a total upward: the feed'
\echo '-- cannot subtract a return it never saw. Compare trnh_date against the'
\echo '-- max_invoice_date from section 1 before calling any of these a defect.'
\echo ''

SELECT LPAD(TRIM(h.trnh_type),2,'0')      AS typ,
       TRIM(h.trnh_no)                    AS doc_no,
       h.trnh_date                        AS doc_date,
       TRIM(h.trnh_status)                AS status,
       TRIM(h.trnh_cstno)                 AS customer,
       COUNT(*)                           AS lines,
       h.create_date::timestamp(0)        AS created,
       h.write_date::timestamp(0)         AS last_written
FROM transaction_details d
JOIN transaction_header h ON h.id = d.header_id
WHERE SUBSTRING(h.trnh_date,1,4)::INT >= 2025
  AND LPAD(TRIM(h.trnh_type),2,'0') IN ('01','02')
  AND TRIM(d.trnd_group) = 'MDA'
  AND TRIM(h.trnh_status) IN ('C','P')
  AND TRIM(h.trnh_cstno) NOT LIKE 'V%'
  AND NOT EXISTS (SELECT 1 FROM bidata b WHERE TRIM(b.bi_invno) = TRIM(h.trnh_no))
GROUP BY 1,2,3,4,5,7,8
ORDER BY typ DESC, h.trnh_date;

\echo ''
\echo '-- A document listed above and dated BEFORE max_invoice_date was posted after'
\echo '-- the feed ran and will never appear in it. That is the defect to raise: the'
\echo '-- bidata extract needs to pick up documents whose status changed after'
\echo '-- extraction, not only those created since.'
\echo ''
