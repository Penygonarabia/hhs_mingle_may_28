-- =============================================================================
-- Give a customer that sells but is not in the customer master a city, so its
-- sales carry a region.
--
--   psql -U odoo -d dbprod -f scripts/backfill_missing_selling_customers.sql
--
-- WHAT IT DOES. Two repairs, both aimed at one symptom -- in-scope sales
-- reporting under a blank Region:
--
--   1. Inserts a `customer` row for a customer that sells in scope, has no row
--      of its own, and whose sales therefore resolve no region.
--   2. Repairs a customer that HAS a row but whose cst_subregion names a city
--      res_city does not carry.
--
-- Both derive the city from the same evidence, in the same order, and both are
-- idempotent -- they only touch what is broken.
--
-- WHY. The salesman boards resolve the Region as
--
--     COALESCE(header.trnh_rptregionid, city_of(header.trnh_cityid),
--              city_of(customer.cst_subregion))
--
-- so an invoice whose header carries neither a region nor a city falls through
-- to the CUSTOMER's city -- and a customer with no master row has none. Those
-- rows report under a blank Region, which is what the sync pipeline's own
-- post-run check counts: 45 rows, SAR 286,517, of 2026 when this was written,
-- across five customers (J850, J869, K436, R1342, R1365).
--
-- WHERE THE CITY COMES FROM, in order, and nothing is guessed:
--
--   1. THE CUSTOMER'S OWN OTHER INVOICES. The feed stamps trnh_cityid on most
--      headers and misses some; K436's eleven invoices carry KHO on ten of
--      them, R1342's carry RYD on two of four. The stamped ones say where the
--      customer is, so the unstamped ones can be answered from them.
--   2. THE SALESMAN'S OWN TERRITORY, for a customer no invoice ever stamped.
--      J850 sells only through J1-006, whose 63 stamped invoices are JED; J869
--      through J1-09H, whose 19 are BAH. Both are Western Region, so this rule
--      decides the REGION for those two even where the city is arguable.
--
-- The customer-code prefix is NOT used and must not be: J looks like Jeddah and
-- is, for 639 customers -- but also Bahrah, Jizan, Medina, Khamis Mushait,
-- Tabuk, Taif and Makkah for another 173.
--
-- THE WIDER GAP IS NOT THIS SCRIPT'S TO CLOSE. 310 customers with in-scope
-- sales -- SAR 47.3m across 3,003 rows -- have no master row at all, and they
-- report under their own code at the Customer level with no classification.
-- Almost all of them resolve a Region perfectly well from their own header, so
-- they are not what the check counts and giving them invented master rows would
-- be a much larger write than the problem. They need the ERP's customer master.
--
-- WHAT IT DOES NOT SET. cst_cstclassification, which decides the Partner
-- Classification and Product Sub-Group levels' customer cut. Nothing in the
-- invoice states it and no rule infers it, so those customers keep reporting as
-- Unassigned there -- honestly -- until the master carries them.
--
-- THIS IS A STAND-IN, NOT THE FIX. These customers belong in the ERP's customer
-- master; they sell, so somebody created them somewhere. Until they arrive this
-- keeps their money on the right region rather than on a blank bar. Wired into
-- sync_and_repair_all_masters.sql for the same reason the catalog backfill is:
-- `customer` is a feed table and a reload restores the gap.
--
-- AFTERWARDS rebuild the snapshot:
--     env['pbi.sales.sman.fact'].refresh_fact()
-- =============================================================================

\echo ''
\echo '=== Before: in-scope sales whose customer is not in the master ==========='
\echo ''

SELECT f.l6_code AS customer, count(*) AS fact_rows,
       round(sum(f.amount)::numeric, 2) AS amount, sum(f.qty) AS qty
  FROM v_pbi_sales_sman_fact f
  LEFT JOIN customer c ON c.cst_no = f.l6_code
 WHERE f.in_scope AND f.part_no IS NOT NULL
   AND f.l3_code IS NULL AND c.cst_no IS NULL
 GROUP BY 1 ORDER BY 3 DESC;

\echo ''
\echo '=== Inserting them ======================================================='
\echo ''

-- Written as set-based aggregates rather than correlated subqueries. The
-- readable form -- "for each missing customer, look up its own city" -- rescans
-- 63,813 headers once per customer and did not finish in ten minutes. These
-- three CTEs each scan the table once.
WITH gap AS (
    -- SCOPED TO THE SYMPTOM, and the scoping is the important part. "Every
    -- customer on any header that has no master row" is 310 customers and SAR
    -- 47.3m -- but most of them resolve a region perfectly well from their own
    -- header, and inserting them would write 334 rows (V-prefixed project
    -- customers among them, which the boards exclude from scope entirely) to
    -- fix 45. This takes only the customers whose sales actually report under a
    -- blank Region.
    SELECT DISTINCT f.l6_code AS cst_no
      FROM v_pbi_sales_sman_fact f
      LEFT JOIN customer c ON c.cst_no = f.l6_code
     WHERE f.in_scope AND f.part_no IS NOT NULL
       AND f.l3_code IS NULL
       AND c.cst_no IS NULL
       AND COALESCE(f.l6_code, '') <> ''
),
missing AS (
    SELECT trim(h.trnh_cstno) AS cst_no,
           max(trim(h.trnh_cstname)) AS cst_name
      FROM transaction_header h
      JOIN gap g ON g.cst_no = trim(h.trnh_cstno)
     GROUP BY 1
),
stamped AS (
    SELECT trim(h.trnh_cstno) AS cst_no, trim(h.trnh_sman) AS sman,
           ct.code AS city_code, count(*) AS n
      FROM transaction_header h
      JOIN res_city ct ON ct.id = h.trnh_cityid
     GROUP BY 1, 2, 3
),
-- Rule 1: the city this customer's own stamped invoices carry.
own_city AS (
    SELECT DISTINCT ON (cst_no) cst_no, city_code
      FROM (SELECT cst_no, city_code, sum(n) AS n FROM stamped GROUP BY 1, 2) x
     WHERE cst_no IN (SELECT cst_no FROM missing)
     ORDER BY cst_no, n DESC, city_code
),
-- Rule 2: the city this customer's salesmen mostly sell in.
cust_sman AS (
    SELECT DISTINCT trim(h.trnh_cstno) AS cst_no, trim(h.trnh_sman) AS sman
      FROM transaction_header h
     WHERE trim(h.trnh_cstno) IN (SELECT cst_no FROM missing)
       AND COALESCE(trim(h.trnh_sman), '') <> ''
),
sman_city AS (
    SELECT DISTINCT ON (cs.cst_no) cs.cst_no, t.city_code
      FROM cust_sman cs
      JOIN (SELECT sman, city_code, sum(n) AS n FROM stamped GROUP BY 1, 2) t
        ON t.sman = cs.sman
     ORDER BY cs.cst_no, t.n DESC, t.city_code
)
INSERT INTO customer (cst_no, cst_name, cst_subregion,
                      create_uid, create_date, write_uid, write_date)
SELECT m.cst_no, m.cst_name,
       COALESCE(o.city_code, s.city_code),
       1, now(), 1, now()
  FROM missing m
  LEFT JOIN own_city  o ON o.cst_no = m.cst_no
  LEFT JOIN sman_city s ON s.cst_no = m.cst_no
 WHERE COALESCE(o.city_code, s.city_code) IS NOT NULL;

\echo ''
\echo '=== Repairing customers whose own city code resolves to nothing =========='
\echo ''

-- THE OTHER WAY A REGION GOES BLANK. A customer can be in the master and still
-- have no region, because its cst_subregion names a city res_city does not
-- carry. Only one value on this database does that -- 'STH' on J686, four rows
-- of 2024 -- and the two the feed spells differently, KHM and TAB, are already
-- aliased to KMH and TBK inside the snapshot, so they resolve and are left
-- alone. The '*' sentinel is excluded: it means "not applicable", and a
-- customer that says so is not a customer we should be picking a city for.
--
-- Same two rules and the same order as above: the customer's own stamped
-- invoices first, then its salesmen's territory. J686 has neither a stamped
-- invoice nor a real city, and its one salesman J1-066 has 304 stamped
-- invoices, every one of them JED.
WITH bad AS (
    SELECT c.cst_no
      FROM customer c
      LEFT JOIN res_city ct ON ct.code = upper(btrim(c.cst_subregion))
     WHERE COALESCE(btrim(c.cst_subregion), '') NOT IN ('', '*')
       AND upper(btrim(c.cst_subregion)) NOT IN ('KHM', 'TAB')
       AND ct.id IS NULL
),
stamped AS (
    SELECT trim(h.trnh_cstno) AS cst_no, trim(h.trnh_sman) AS sman,
           ct.code AS city_code, count(*) AS n
      FROM transaction_header h
      JOIN res_city ct ON ct.id = h.trnh_cityid
     GROUP BY 1, 2, 3
),
own_city AS (
    SELECT DISTINCT ON (cst_no) cst_no, city_code
      FROM (SELECT cst_no, city_code, sum(n) AS n FROM stamped GROUP BY 1, 2) x
     WHERE cst_no IN (SELECT cst_no FROM bad)
     ORDER BY cst_no, n DESC, city_code
),
cust_sman AS (
    SELECT DISTINCT trim(h.trnh_cstno) AS cst_no, trim(h.trnh_sman) AS sman
      FROM transaction_header h
     WHERE trim(h.trnh_cstno) IN (SELECT cst_no FROM bad)
       AND COALESCE(trim(h.trnh_sman), '') <> ''
),
sman_city AS (
    SELECT DISTINCT ON (cs.cst_no) cs.cst_no, t.city_code
      FROM cust_sman cs
      JOIN (SELECT sman, city_code, sum(n) AS n FROM stamped GROUP BY 1, 2) t
        ON t.sman = cs.sman
     ORDER BY cs.cst_no, t.n DESC, t.city_code
)
UPDATE customer c
   SET cst_subregion = COALESCE(o.city_code, s.city_code)
  FROM bad b
  LEFT JOIN own_city  o ON o.cst_no = b.cst_no
  LEFT JOIN sman_city s ON s.cst_no = b.cst_no
 WHERE c.cst_no = b.cst_no
   AND COALESCE(o.city_code, s.city_code) IS NOT NULL;

\echo ''
\echo '=== After: what was added and the region it resolves to =================='
\echo ''

SELECT c.cst_no, c.cst_name, c.cst_subregion AS city,
       r.name->>'en_US' AS region
  FROM customer c
  LEFT JOIN res_city ct ON ct.code = upper(btrim(c.cst_subregion))
  LEFT JOIN res_region r ON r.id = ct.report_region
 WHERE c.create_uid = 1 AND c.cst_cstclassification IS NULL
 ORDER BY c.cst_no;

\echo ''
\echo '=== Still unresolved: selling customers with no city from either rule ===='
\echo ''

SELECT f.l6_code AS customer, count(*) AS fact_rows
  FROM v_pbi_sales_sman_fact f
  LEFT JOIN customer c ON c.cst_no = f.l6_code
 WHERE f.in_scope AND f.part_no IS NOT NULL
   AND f.l3_code IS NULL AND c.cst_no IS NULL
 GROUP BY 1 ORDER BY 2 DESC;

-- To revert (removes only the rows this added -- they are the ones with no
-- classification that the ERP feed has never touched):
--   DELETE FROM customer WHERE create_uid = 1 AND cst_cstclassification IS NULL;
