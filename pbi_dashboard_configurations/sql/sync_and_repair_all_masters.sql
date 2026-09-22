-- 1-Click Complete Master Sync & Gap Repair Pipeline
-- =========================================================================
-- Sequentially executes all data repairs, master-data taxonomy fixes,
-- performance indexes, and snapshot rebuilds in a single transaction:
--
-- 0. Repair id sequences on the tables this script inserts into
-- 1. Normalise part number casing in transaction_details
-- 2. Backfill uncatalogued parts from product templates
-- 2b. Backfill missing sub-groups in catalog
-- 2c. Synchronize product tags (02 Unit Gate & 10 AC Scope)
-- 3. Repair ATOM & AC scope product categories
-- 3b. Backfill customers with no region
-- 4. Clean orphaned salesman_type_id field definitions
-- 5. Repair target categories & sales types in sales_budget_line
-- 6. Create legacy master table join key indexes
-- 7. Refresh Materialized Views (Fact Snapshot, Budget Snap, Scope Whitelist)
-- 8. Audit & Verify 10 Master Dimensions across Target, TY Sales & LY Sales
-- 9-10. Main Category and Sales Type Group breakdowns (2026 Target vs Actuals)
--
-- Safe, idempotent, and re-runnable at any time.
-- =========================================================================

SET jit = off;
SET enable_nestloop = off;

\echo ''
\echo '=== Step 0: Repairing id sequences on the tables this script inserts into =='
\echo ''

-- Every INSERT below relies on the table's id default (nextval). On a database
-- whose rows arrived with explicit ids -- a dump restore, a table-to-table copy,
-- scripts/migrate_amc_to_dbcloud.py (which resets only three sequences), or an
-- earlier repair that inserted a chosen id -- the sequence still sits below
-- max(id) and the first insert dies with
--   duplicate key value violates unique constraint "<table>_pkey"
-- which is what staging hit on customer while the same script ran clean locally.
-- Raise each sequence to max(id), never lower it, and skip tables or sequences
-- the database does not have.
DO $$
DECLARE
    v_tbl  text;
    v_seq  text;
    v_max  bigint;
    v_last bigint;
BEGIN
    FOREACH v_tbl IN ARRAY ARRAY['customer', 'catalog', 'product_tag',
                                 'product_family', 'product_category']
    LOOP
        IF to_regclass(v_tbl) IS NULL THEN
            RAISE NOTICE 'SKIPPED (%): table does not exist.', v_tbl;
            CONTINUE;
        END IF;

        v_seq := pg_get_serial_sequence(v_tbl, 'id');
        IF v_seq IS NULL THEN
            RAISE NOTICE 'SKIPPED (%): id column has no owned sequence.', v_tbl;
            CONTINUE;
        END IF;

        EXECUTE format('SELECT COALESCE(max(id), 0) FROM %I', v_tbl) INTO v_max;
        SELECT s.last_value INTO v_last
          FROM pg_sequences s
         WHERE (quote_ident(s.schemaname) || '.' || quote_ident(s.sequencename))::regclass
               = v_seq::regclass;

        IF v_max > COALESCE(v_last, 0) THEN
            PERFORM setval(v_seq, v_max);
            RAISE NOTICE 'REPAIRED (%): % was at %, raised to max(id) = %.',
                         v_tbl, v_seq, COALESCE(v_last, 0), v_max;
        ELSE
            RAISE NOTICE 'OK (%): % at % already clears max(id) = %.',
                         v_tbl, v_seq, COALESCE(v_last, 0), v_max;
        END IF;
    END LOOP;
END $$;

\echo ''
\echo '=== Step 1: Normalising Part Number Casing ================================'
\echo ''

-- Update lower-case part numbers to upper-case in transaction_details
UPDATE transaction_details d
SET trnd_part = upper(trim(d.trnd_part))
WHERE d.trnd_part IS NOT NULL 
  AND d.trnd_part <> upper(trim(d.trnd_part));

\echo ''
\echo '=== Step 2: Backfilling Uncatalogued AC Parts =============================='
\echo ''

-- Link uncatalogued parts to their Odoo product category and bidata sub-group where template exists
WITH b_psg AS (
    SELECT DISTINCT ON (upper(btrim(bi_invpartno)))
           upper(btrim(bi_invpartno)) AS part,
           btrim(bi_psgroupcode)      AS psg
      FROM bidata
     WHERE bi_type = 'S'
       AND COALESCE(btrim(bi_psgroupcode), '') NOT IN ('', '*')
     ORDER BY upper(btrim(bi_invpartno)), id DESC
)
INSERT INTO catalog (cat_grp, cat_part, cat_pgroup, cat_psgroup, cat_desc)
SELECT DISTINCT
    'MDA' AS cat_grp,
    upper(trim(t.default_code)) AS cat_part,
    trim(pc.code) AS cat_pgroup,
    COALESCE(b.psg, ''),
    COALESCE(to_jsonb(t.name)->>'en_US', t.name::text, t.default_code) AS cat_desc
FROM product_template t
JOIN product_category pc ON pc.id = t.categ_id
LEFT JOIN b_psg b ON b.part = upper(trim(t.default_code))
WHERE NULLIF(trim(t.default_code), '') IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM catalog c
      WHERE upper(trim(c.cat_grp)) = 'MDA'
        AND upper(trim(c.cat_part)) = upper(trim(t.default_code))
  )
ON CONFLICT DO NOTHING;

\echo ''
\echo '=== Step 2b: Backfilling Missing Sub-Groups in Catalog ====================='
\echo ''

-- Update blank cat_psgroup in catalog from bidata
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

-- Fallback updates for specific part families
UPDATE catalog
   SET cat_psgroup = 'WIN011', write_date = now()
 WHERE upper(cat_grp) = 'MDA' AND upper(cat_part) LIKE 'WDV%' AND (cat_psgroup IS NULL OR btrim(cat_psgroup) IN ('', '*'));

UPDATE catalog
   SET cat_psgroup = 'ACC', write_date = now()
 WHERE upper(cat_grp) = 'MDA' AND cat_pgroup = 'ACACC' AND (cat_psgroup IS NULL OR btrim(cat_psgroup) IN ('', '*'));

UPDATE catalog
   SET cat_psgroup = 'VRFIN', write_date = now()
 WHERE upper(cat_grp) = 'MDA' AND cat_pgroup = 'ACVRF' AND upper(cat_part) LIKE 'FCU%' AND (cat_psgroup IS NULL OR btrim(cat_psgroup) IN ('', '*'));

UPDATE catalog
   SET cat_psgroup = 'ATOM', write_date = now()
 WHERE upper(cat_grp) = 'MDA' AND cat_pgroup = 'ATOM' AND (cat_psgroup IS NULL OR btrim(cat_psgroup) IN ('', '*'));

\echo ''
\echo '=== Step 2c: Synchronizing Product Tags (02 Unit Gate & 10 AC Scope) ======='
\echo ''

DO $$
DECLARE
    v_is_jsonb boolean := false;
    v_tag_02_id integer;
    v_tag_10_id integer;
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'product_tag') THEN
        SELECT (data_type = 'jsonb') INTO v_is_jsonb
        FROM information_schema.columns 
        WHERE table_name = 'product_tag' AND column_name = 'name';

        -- Ensure Tag '02'
        SELECT id INTO v_tag_02_id FROM product_tag 
        WHERE TRIM(COALESCE(to_jsonb(name)->>'en_US', 
                   CASE WHEN jsonb_typeof(to_jsonb(name)) = 'string' THEN name::TEXT END)) IN ('02', '2')
        ORDER BY id LIMIT 1;

        IF v_tag_02_id IS NULL THEN
            IF v_is_jsonb THEN
                EXECUTE 'INSERT INTO product_tag (name, color, create_date, write_date) VALUES ($1::jsonb, 1, NOW(), NOW()) RETURNING id'
                INTO v_tag_02_id USING '{"en_US": "02"}';
            ELSE
                EXECUTE 'INSERT INTO product_tag (name, color, create_date, write_date) VALUES ($1, 1, NOW(), NOW()) RETURNING id'
                INTO v_tag_02_id USING '02';
            END IF;
        END IF;

        -- Ensure Tag '10'
        SELECT id INTO v_tag_10_id FROM product_tag 
        WHERE TRIM(COALESCE(to_jsonb(name)->>'en_US', 
                   CASE WHEN jsonb_typeof(to_jsonb(name)) = 'string' THEN name::TEXT END)) IN ('10')
        ORDER BY id LIMIT 1;

        IF v_tag_10_id IS NULL THEN
            IF v_is_jsonb THEN
                EXECUTE 'INSERT INTO product_tag (name, color, create_date, write_date) VALUES ($1::jsonb, 2, NOW(), NOW()) RETURNING id'
                INTO v_tag_10_id USING '{"en_US": "10"}';
            ELSE
                EXECUTE 'INSERT INTO product_tag (name, color, create_date, write_date) VALUES ($1, 2, NOW(), NOW()) RETURNING id'
                INTO v_tag_10_id USING '10';
            END IF;
        END IF;

        -- Populate Tag '02' relations from catalogflags
        IF v_tag_02_id IS NOT NULL AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'catalogflags')
           AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'product_tag_product_template_rel') THEN
            INSERT INTO product_tag_product_template_rel (product_template_id, product_tag_id)
            SELECT DISTINCT pt.id, v_tag_02_id
            FROM product_template pt
            JOIN catalogflags cf ON UPPER(TRIM(cf.cat_part)) = UPPER(TRIM(pt.default_code))
            WHERE TRIM(cf.cat_flag) = '02'
              AND NULLIF(TRIM(pt.default_code), '') IS NOT NULL
            ON CONFLICT DO NOTHING;
        END IF;

        -- Populate Tag '10' relations from catalogflags
        IF v_tag_10_id IS NOT NULL AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'catalogflags')
           AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'product_tag_product_template_rel') THEN
            INSERT INTO product_tag_product_template_rel (product_template_id, product_tag_id)
            SELECT DISTINCT pt.id, v_tag_10_id
            FROM product_template pt
            JOIN catalogflags cf ON UPPER(TRIM(cf.cat_part)) = UPPER(TRIM(pt.default_code))
            WHERE TRIM(cf.cat_flag) = '10'
              AND NULLIF(TRIM(pt.default_code), '') IS NOT NULL
            ON CONFLICT DO NOTHING;
        END IF;
    END IF;
END $$;

\echo ''
\echo '=== Step 3: Repairing ATOM Outdoor Product Group =========================='
\echo ''

-- The ATOM system's outdoor units are catalogued under VRF while the ERP files
-- them under ATOM, which put SAR 30,670,445 of Jan-Sep 2025 on the VRF bar --
-- 241 pct of a target that was never meant for it, with Concealed left at 49
-- pct of one it should have beaten. Rows are chosen by the disagreement itself
-- (catalog says ACVRF, trnd_groupid says ATOM), never by part number: three
-- (ATB) parts are genuinely VRF. Idempotent -- once moved, they no longer
-- match. See scripts/fix_atom_outdoor_product_group.sql for the full evidence
-- and for the revert.
UPDATE catalog c
   SET cat_pgroup  = 'ACCON',
       cat_psgroup = 'CON004'
  FROM (
      SELECT DISTINCT ON (upper(trim(d.trnd_part)))
             upper(trim(d.trnd_part)) AS part, pc.code AS grp
        FROM transaction_details d
        JOIN product_category pc ON pc.id = d.trnd_groupid
       WHERE trim(d.trnd_group) = 'MDA'
       GROUP BY 1, pc.code
       ORDER BY 1, count(*) DESC
  ) e
 WHERE e.part = upper(trim(c.cat_part))
   AND trim(c.cat_grp) = 'MDA'
   AND trim(c.cat_pgroup) = 'ACVRF'
   AND e.grp = 'ATOM';

\echo ''
\echo '=== Step 3b: Backfilling Customers & Partner Classifications ============='
\echo ''

-- Backfill missing selling customers and populate partner classification
WITH missing_cust AS (
    SELECT DISTINCT trim(h.trnh_cstno) AS cst_no, max(trim(h.trnh_cstname)) AS cst_name
      FROM transaction_header h
      LEFT JOIN customer c ON c.cst_no = trim(h.trnh_cstno)
     WHERE c.cst_no IS NULL AND NULLIF(trim(h.trnh_cstno), '') IS NOT NULL
     GROUP BY 1
),
stamped AS (
    SELECT trim(h.trnh_cstno) AS cst_no, trim(h.trnh_sman) AS sman,
           ct.code AS city_code, count(*) AS n
      FROM transaction_header h JOIN res_city ct ON ct.id = h.trnh_cityid
     GROUP BY 1, 2, 3
),
own_city AS (
    SELECT DISTINCT ON (cst_no) cst_no, city_code
      FROM (SELECT cst_no, city_code, sum(n) AS n FROM stamped GROUP BY 1, 2) x
     ORDER BY cst_no, n DESC, city_code
),
cust_sman AS (
    SELECT DISTINCT trim(h.trnh_cstno) AS cst_no, trim(h.trnh_sman) AS sman
      FROM transaction_header h
     WHERE COALESCE(trim(h.trnh_sman), '') <> ''
),
sman_city AS (
    SELECT DISTINCT ON (cs.cst_no) cs.cst_no, t.city_code
      FROM cust_sman cs
      JOIN (SELECT sman, city_code, sum(n) AS n FROM stamped GROUP BY 1, 2) t
        ON t.sman = cs.sman
     ORDER BY cs.cst_no, t.n DESC, t.city_code
),
b_class AS (
    SELECT DISTINCT ON (upper(btrim(bi_cstno)))
           upper(btrim(bi_cstno)) AS cst_no,
           btrim(bi_cstsubtypecode) AS cst_classification
      FROM bidata
     WHERE COALESCE(btrim(bi_cstsubtypecode), '') NOT IN ('', '*')
     ORDER BY upper(btrim(bi_cstno)), id DESC
),
rp_class AS (
    SELECT DISTINCT ON (upper(btrim(rp.ref)))
           upper(btrim(rp.ref)) AS cst_no,
           pcl.pc_code AS cst_classification
      FROM res_partner rp
      JOIN partner_classification pcl ON pcl.id = rp.partner_classification_id
     WHERE NULLIF(btrim(rp.ref), '') IS NOT NULL
     ORDER BY upper(btrim(rp.ref)), rp.id DESC
)
INSERT INTO customer (cst_no, cst_name, cst_subregion, cst_cstclassification,
                      create_uid, create_date, write_uid, write_date)
SELECT m.cst_no, m.cst_name,
       COALESCE(o.city_code, s.city_code, 'JED'),
       COALESCE(bc.cst_classification, rc.cst_classification, '001'),
       1, now(), 1, now()
  FROM missing_cust m
  LEFT JOIN own_city  o ON o.cst_no = m.cst_no
  LEFT JOIN sman_city s ON s.cst_no = m.cst_no
  LEFT JOIN b_class  bc ON bc.cst_no = upper(m.cst_no)
  LEFT JOIN rp_class rc ON rc.cst_no = upper(m.cst_no)
 WHERE NOT EXISTS (SELECT 1 FROM customer c_ex WHERE c_ex.cst_no = m.cst_no);

-- Populate blank partner classification on existing customer rows
WITH b_class AS (
    SELECT DISTINCT ON (upper(btrim(bi_cstno)))
           upper(btrim(bi_cstno)) AS cst_no,
           btrim(bi_cstsubtypecode) AS cst_classification
      FROM bidata
     WHERE COALESCE(btrim(bi_cstsubtypecode), '') NOT IN ('', '*')
     ORDER BY upper(btrim(bi_cstno)), id DESC
),
rp_class AS (
    SELECT DISTINCT ON (upper(btrim(rp.ref)))
           upper(btrim(rp.ref)) AS cst_no,
           pcl.pc_code AS cst_classification
      FROM res_partner rp
      JOIN partner_classification pcl ON pcl.id = rp.partner_classification_id
     WHERE NULLIF(btrim(rp.ref), '') IS NOT NULL
     ORDER BY upper(btrim(rp.ref)), rp.id DESC
)
UPDATE customer c
   SET cst_cstclassification = COALESCE(bc.cst_classification, rc.cst_classification, '001'),
       write_date = now()
  FROM customer c2
  LEFT JOIN b_class  bc ON bc.cst_no = upper(btrim(c2.cst_no))
  LEFT JOIN rp_class rc ON rc.cst_no = upper(btrim(c2.cst_no))
 WHERE c.id = c2.id
   AND (c.cst_cstclassification IS NULL OR btrim(c.cst_cstclassification) IN ('', '*'));

-- Sync res_partner partner_classification_id from customer / partner_classification
UPDATE res_partner rp
   SET partner_classification_id = pcl.id,
       write_date = now()
  FROM customer c
  JOIN partner_classification pcl ON pcl.pc_code = trim(c.cst_cstclassification)
 WHERE rp.ref = c.cst_no
   AND (rp.partner_classification_id IS NULL OR rp.partner_classification_id != pcl.id);

-- Repair invalid city subregion codes on customer
WITH bad AS (
    SELECT c.cst_no FROM customer c
      LEFT JOIN res_city ct ON ct.code = upper(btrim(c.cst_subregion))
     WHERE COALESCE(btrim(c.cst_subregion), '') NOT IN ('', '*')
       AND upper(btrim(c.cst_subregion)) NOT IN ('KHM', 'TAB')
       AND ct.id IS NULL
),
stamped AS (
    SELECT trim(h.trnh_cstno) AS cst_no, trim(h.trnh_sman) AS sman,
           ct.code AS city_code, count(*) AS n
      FROM transaction_header h JOIN res_city ct ON ct.id = h.trnh_cityid
     GROUP BY 1, 2, 3
),
own_city AS (
    SELECT DISTINCT ON (cst_no) cst_no, city_code
      FROM (SELECT cst_no, city_code, sum(n) AS n FROM stamped GROUP BY 1, 2) x
     WHERE cst_no IN (SELECT cst_no FROM bad) ORDER BY cst_no, n DESC, city_code
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
UPDATE customer c SET cst_subregion = COALESCE(o.city_code, s.city_code)
  FROM bad b
  LEFT JOIN own_city  o ON o.cst_no = b.cst_no
  LEFT JOIN sman_city s ON s.cst_no = b.cst_no
 WHERE c.cst_no = b.cst_no AND COALESCE(o.city_code, s.city_code) IS NOT NULL;

\echo ''
\echo '=== Step 4: Cleaning Orphaned Definitions & Ensuring Salesman Fields Exist ==='
\echo ''

DELETE FROM ir_model_fields
WHERE model = 'res.users' 
  AND name = 'salesman_type_id'
  AND state = 'manual';

-- Ensure res_partner and res_users have salesman columns and indexes across all servers
ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS is_salesman boolean DEFAULT false;
ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS salesman_ref varchar;
CREATE INDEX IF NOT EXISTS res_partner_salesman_ref_index ON res_partner (salesman_ref);

ALTER TABLE res_users ADD COLUMN IF NOT EXISTS is_salesman boolean DEFAULT false;

\echo ''
\echo '=== Step 5: Repairing Target Categories & Sales Types in sales_budget_line ==='
\echo ''

-- Populate sales_budget_line Main/Sub categories from product_category hierarchy
UPDATE sales_budget_line l
SET sub_category_code = sc.subcat_ref,
    sub_category_name = sc.subcat_name,
    main_category_code = mc.maincat_ref,
    main_category_name = mc.maincat_name,
    merged_subcategory_code = COALESCE(scm.subcat_ref, sc.subcat_ref),
    merged_subcategory_name = COALESCE(scm.subcat_name, sc.subcat_name)
FROM product_category pc
LEFT JOIN sub_category sc ON sc.id = pc.sub_category
LEFT JOIN main_category mc ON mc.id = sc.subcat_maincategory_id
LEFT JOIN sub_category scm ON scm.id = pc.merged_subcategory
WHERE pc.id = COALESCE(l.product_subgroup_id, l.product_group_id)
  AND (NULLIF(trim(l.main_category_code), '') IS NULL 
       OR NULLIF(trim(l.sub_category_code), '') IS NULL
       OR l.main_category_code <> mc.maincat_ref);

-- Sales Type Groups on sales_budget_line are LEFT ALONE, deliberately.
--
-- This step used to rewrite Key Accounts ('03') to Dealers ('01') on every
-- run. That was safe only while no sale type belonged to Key Accounts and
-- nothing was ever budgeted under it. Both stopped being true in September
-- 2026, when sale types 101 Modern Trade and 102 Wholesale were created under
-- that group: a target captured for either of them would have been moved to
-- Dealers by the next master sync, quietly, with the sales left where they
-- were -- a Dealers target inflated by somebody else's budget and two sale
-- types showing sales against none.
--
-- Nothing replaces it. A budget line's sales type group is set by the import
-- from the file's own column (see CST_TYPE_TO_SALESTYPE_REF in
-- sales_budget/models/sales_budget_import.py) or by hand, and a repair script
-- is not the place to second-guess either. Verified before removal: no
-- sales_budget_line on dbprod carries '03', so this deletes no work.

\echo ''
\echo '=== Step 5b: Syncing Product Category Families & Budget Families =========='
\echo ''

-- Both the column and the constraint below are dropped if dashboard_groups'
-- product.family model is ever uninstalled (Odoo cleans up the ir.model.fields
-- row, which drops the underlying column, even though it leaves the
-- product_family TABLE itself alone). Guarded so this step still runs rather
-- than failing with "column product_family does not exist" -- see
-- restore_product_category_family_link.sql for the full story and the
-- standalone version of this repair.
ALTER TABLE product_category ADD COLUMN IF NOT EXISTS product_family integer;
DO $$
BEGIN
    ALTER TABLE product_family ADD CONSTRAINT product_family_pfam_ref_unique UNIQUE (pfam_ref);
EXCEPTION
    WHEN duplicate_object OR duplicate_table THEN NULL;
END $$;

-- Ensure known core product families exist
INSERT INTO product_family (pfam_ref, pfam_name, pfam_name2, complete_name, create_uid, create_date, write_uid, write_date)
VALUES 
    ('WIN011', 'WINDOW INVERTER (R32)', 'WINDOW INVERTER (R32)', '[WIN011]-WINDOW INVERTER (R32)', 1, now(), 1, now()),
    ('CONG004', 'CONCEALED R32', 'CONCEALED R32', '[CONG004]-CONCEALED R32', 1, now(), 1, now()),
    ('CSTG004', 'CASSETTE R32', 'CASSETTE R32', '[CSTG004]-CASSETTE R32', 1, now(), 1, now()),
    ('ACC', 'AC ACCESSORIES', 'AC ACCESSORIES', '[ACC]-AC ACCESSORIES', 1, now(), 1, now()),
    ('ATOM', 'ATOM', 'ATOM', '[ATOM]-ATOM', 1, now(), 1, now()),
    ('WTSG017', 'BIG CAPACITY', 'BIG CAPACITY', '[WTSG017]-BIG CAPACITY', 1, now(), 1, now()),
    ('WTSG021', 'AIR ECO', 'AIR ECO', '[WTSG021]-AIR ECO', 1, now(), 1, now()),
    ('WTSG022', 'AIR PRO', 'AIR PRO', '[WTSG022]-AIR PRO', 1, now(), 1, now()),
    ('WTSG023', 'AIR LUX', 'AIR LUX', '[WTSG023]-AIR LUX', 1, now(), 1, now()),
    ('WTSG024', 'AIR MAX', 'AIR MAX', '[WTSG024]-AIR MAX', 1, now(), 1, now())
ON CONFLICT (pfam_ref) DO UPDATE 
SET pfam_name = EXCLUDED.pfam_name,
    pfam_name2 = EXCLUDED.pfam_name2,
    complete_name = EXCLUDED.complete_name;

-- Ensure depth-3 categories exist under their respective depth-2 parent category
DO $$
DECLARE
    rec RECORD;
    v_parent_id integer;
    v_parent_path varchar;
    v_pf_id integer;
    v_cat_id integer;
BEGIN
    FOR rec IN 
        SELECT * FROM (VALUES
            ('ACWIN', 'WIN011', 'WINDOW INVERTER (R32)', 'WIN011'),
            ('ACACC', 'ACC', 'AC ACCESSORIES', 'ACC'),
            ('ATOM', 'ATOM', 'ATOM', 'ATOM'),
            ('ACWTS', 'WTSG017', 'BIG CAPACITY', 'WTSG017'),
            ('ACWTS', 'WTSG021', 'AIR ECO', 'WTSG021'),
            ('ACWTS', 'WTSG022', 'AIR PRO', 'WTSG022'),
            ('ACWTS', 'WTSG023', 'AIR LUX', 'WTSG023'),
            ('ACWTS', 'WTSG024', 'AIR MAX', 'WTSG024')
        ) AS t(pg_code, cat_code, cat_name, pfam_ref)
    LOOP
        SELECT d2.id, d2.parent_path, pf.id
          INTO v_parent_id, v_parent_path, v_pf_id
          FROM product_category d2
          JOIN product_category d1 ON d1.id = d2.parent_id AND d1.code = 'MDA'
          JOIN product_family pf ON pf.pfam_ref = rec.pfam_ref
         WHERE d2.code = rec.pg_code;

        IF v_parent_id IS NOT NULL THEN
            SELECT id INTO v_cat_id FROM product_category WHERE parent_id = v_parent_id AND code = rec.cat_code;
            IF v_cat_id IS NULL THEN
                INSERT INTO product_category (name, complete_name, parent_id, code, product_family, create_uid, create_date, write_uid, write_date)
                VALUES (rec.cat_name, rec.cat_name, v_parent_id, rec.cat_code, v_pf_id, 1, now(), 1, now())
                RETURNING id INTO v_cat_id;
                UPDATE product_category SET parent_path = v_parent_path || v_cat_id || '/' WHERE id = v_cat_id;
            ELSE
                UPDATE product_category SET product_family = v_pf_id WHERE id = v_cat_id;
            END IF;
        END IF;
    END LOOP;
END $$;

-- Update CON007, CON008, CST007, CST008 product_family links
UPDATE product_category c
   SET product_family = pf.id
  FROM product_category p, product_family pf
 WHERE p.id = c.parent_id AND p.code = 'ACCON' AND c.code IN ('CON007', 'CON008')
   AND pf.pfam_ref = 'CONG004';

UPDATE product_category c
   SET product_family = pf.id
  FROM product_category p, product_family pf
 WHERE p.id = c.parent_id AND p.code = 'ACCST' AND c.code IN ('CST007', 'CST008')
   AND pf.pfam_ref = 'CSTG004';

-- Link unlinked product categories to product families based on catalog & bidata
WITH fam AS (
    SELECT DISTINCT ON (upper(btrim(bi_catmainpartno)))
           upper(btrim(bi_catmainpartno)) AS mainpart,
           btrim(bi_psgroupcode)          AS ref,
           btrim(bi_psgroupname)          AS name
      FROM bidata
     WHERE bi_type = 'S'
       AND COALESCE(btrim(bi_catmainpartno), '') <> ''
       AND COALESCE(btrim(bi_psgroupcode), '') NOT IN ('', '*')
     GROUP BY 1, 2, 3
     ORDER BY 1, count(*) DESC
),
hit AS (
    SELECT pc.id AS category_id, f.ref, f.name, count(*) AS lines
      FROM catalog c
      JOIN fam f ON f.mainpart = upper(btrim(c.cat_mainpartno))
      JOIN product_category parent ON parent.code = btrim(c.cat_pgroup)
      JOIN product_category pc ON pc.parent_id = parent.id
                              AND pc.code = btrim(c.cat_psgroup)
     WHERE COALESCE(btrim(c.cat_psgroup), '') <> ''
     GROUP BY 1, 2, 3
)
INSERT INTO product_family (pfam_ref, pfam_name, pfam_name2, complete_name, create_uid, create_date, write_uid, write_date)
SELECT DISTINCT ON (ref) ref, name, name, '[' || ref || ']-' || name, 1, now(), 1, now()
FROM hit
ON CONFLICT (pfam_ref) DO NOTHING;

UPDATE product_category c
   SET product_family = f.id
  FROM product_family f, (
      SELECT DISTINCT ON (category_id) category_id, ref
        FROM (
            SELECT pc.id AS category_id, f.ref, count(*) AS lines
              FROM catalog c
              JOIN (SELECT DISTINCT ON (upper(btrim(bi_catmainpartno)))
                           upper(btrim(bi_catmainpartno)) AS mainpart,
                           btrim(bi_psgroupcode) AS ref
                      FROM bidata
                     WHERE bi_type = 'S'
                       AND COALESCE(btrim(bi_catmainpartno), '') <> ''
                       AND COALESCE(btrim(bi_psgroupcode), '') NOT IN ('', '*')
                     GROUP BY 1, 2 ORDER BY 1, count(*) DESC) f
                ON f.mainpart = upper(btrim(c.cat_mainpartno))
              JOIN product_category parent ON parent.code = btrim(c.cat_pgroup)
              JOIN product_category pc ON pc.parent_id = parent.id AND pc.code = btrim(c.cat_psgroup)
             WHERE COALESCE(btrim(c.cat_psgroup), '') <> ''
             GROUP BY 1, 2
        ) h ORDER BY category_id, lines DESC
  ) m
 WHERE f.pfam_ref = m.ref
   AND c.id = m.category_id
   AND c.product_family IS NULL;

-- Create missing budget product families
INSERT INTO product_family (pfam_ref, pfam_name, pfam_name2, complete_name, create_uid, create_date, write_uid, write_date)
SELECT c.code, COALESCE(n.name, c.code), n.name, '[' || c.code || ']-' || COALESCE(n.name, c.code), 1, now(), 1, now()
FROM (
    SELECT DISTINCT btrim(l.erp_subgroup_code) AS code
      FROM sales_budget_line l
     WHERE COALESCE(btrim(l.erp_subgroup_code), '') NOT IN ('', '*')
       AND NOT EXISTS (SELECT 1 FROM product_family f WHERE f.pfam_ref = btrim(l.erp_subgroup_code))
       AND NOT EXISTS (
           SELECT 1
             FROM product_category gc
             JOIN product_family gf ON gf.id = gc.product_family
            WHERE gc.parent_id = l.product_group_id
            GROUP BY gc.parent_id
           HAVING count(DISTINCT COALESCE(gf.pfam_merged_into, gf.id)) = 1)
       AND (l.val_01+l.val_02+l.val_03+l.val_04+l.val_05+l.val_06+l.val_07+l.val_08+l.val_09+l.val_10+l.val_11+l.val_12) <> 0
) c
LEFT JOIN LATERAL (
    SELECT btrim(b.bi_psgroupname) AS name
      FROM bidata b
     WHERE btrim(b.bi_psgroupcode) = c.code AND COALESCE(btrim(b.bi_psgroupname), '') NOT IN ('', c.code)
     GROUP BY 1 ORDER BY count(*) DESC LIMIT 1
) n ON true
ON CONFLICT (pfam_ref) DO NOTHING;

-- Merge duplicate / alias families
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

UPDATE product_family f
   SET pfam_merged_into = p.id
  FROM product_family p
 WHERE p.pfam_name = 'Inverter'
   AND f.pfam_name IN ('WINDOW DELUXE INVERTER', 'MISSION INVERTER')
   AND f.pfam_merged_into IS NULL;

-- Resolve 2026 Windows '*' budget to WIN011 (WINDOW INVERTER (R32))
UPDATE sales_budget_line l
   SET erp_subgroup_code = 'WIN011'
  FROM product_category pc
 WHERE pc.id = l.product_group_id
   AND pc.code = 'ACWIN'
   AND l.year = 2026
   AND (l.erp_subgroup_code IS NULL OR btrim(l.erp_subgroup_code) IN ('', '*'));

\echo ''
\echo '=== Step 6: Ensuring Legacy Master Join Indexes Exist ====================='
\echo ''

CREATE UNIQUE INDEX IF NOT EXISTS salestypes_group_id_uindex ON salestypes_group (id);
CREATE UNIQUE INDEX IF NOT EXISTS partner_classification_id_uindex ON partner_classification (id);
CREATE UNIQUE INDEX IF NOT EXISTS res_region_id_uindex ON res_region (id);
CREATE UNIQUE INDEX IF NOT EXISTS res_city_id_uindex ON res_city (id);
CREATE UNIQUE INDEX IF NOT EXISTS main_category_id_uindex ON main_category (id);
CREATE UNIQUE INDEX IF NOT EXISTS sub_category_id_uindex ON sub_category (id);
CREATE UNIQUE INDEX IF NOT EXISTS product_category_id_uindex ON product_category (id);
CREATE UNIQUE INDEX IF NOT EXISTS product_family_id_uindex ON product_family (id);

\echo ''
\echo '=== Step 7: Refreshing Dashboard Materialized Views & Statistics =========='
\echo ''

REFRESH MATERIALIZED VIEW v_pbi_sales_sman_fact;
ANALYZE v_pbi_sales_sman_fact;

REFRESH MATERIALIZED VIEW v_pbi_sales_budget_snap;
ANALYZE v_pbi_sales_budget_snap;

REFRESH MATERIALIZED VIEW v_pbi_sales_scope_groups;
ANALYZE v_pbi_sales_scope_groups;

\echo ''
\echo '=== Step 8: Post-Sync Verification — Target vs TY Sales vs LY Sales ======='
\echo ''

SELECT
    '2026 This Year Sales' AS dataset,
    count(*) AS total_rows,
    count(*) FILTER (WHERE in_scope) AS in_scope_rows,
    round(sum(amount) FILTER (WHERE in_scope)::numeric, 2) AS total_amount,
    round(sum(qty) FILTER (WHERE in_scope)::numeric, 0) AS total_units,
    count(*) FILTER (WHERE in_scope AND (l1_code IS NULL OR l7_code IS NULL OR l3_code IS NULL)) AS unassigned_rows,
    CASE WHEN count(*) FILTER (WHERE in_scope AND (l1_code IS NULL OR l7_code IS NULL OR l3_code IS NULL)) = 0 
         THEN 'ALIGNED (0 Gaps)' ELSE 'Gaps Remaining' END AS status
FROM v_pbi_sales_sman_fact
WHERE yr = 2026
UNION ALL
SELECT
    '2025 Prior Year Sales' AS dataset,
    count(*) AS total_rows,
    count(*) FILTER (WHERE in_scope) AS in_scope_rows,
    round(sum(amount) FILTER (WHERE in_scope)::numeric, 2) AS total_amount,
    round(sum(qty) FILTER (WHERE in_scope)::numeric, 0) AS total_units,
    count(*) FILTER (WHERE in_scope AND (l1_code IS NULL OR l7_code IS NULL OR l3_code IS NULL)) AS unassigned_rows,
    CASE WHEN count(*) FILTER (WHERE in_scope AND (l1_code IS NULL OR l7_code IS NULL OR l3_code IS NULL)) = 0 
         THEN 'ALIGNED (0 Gaps)' ELSE 'Gaps Remaining' END AS status
FROM v_pbi_sales_sman_fact
WHERE yr = 2025
UNION ALL
SELECT
    '2026 Target / Budget' AS dataset,
    count(*) AS total_rows,
    count(*) AS in_scope_rows,
    round(sum(budget_value)::numeric, 2) AS total_amount,
    round(sum(budget_qty)::numeric, 0) AS total_units,
    count(*) FILTER (WHERE budget_l1_code IS NULL OR l7_code IS NULL OR l3_code IS NULL) AS unassigned_rows,
    CASE WHEN count(*) FILTER (WHERE budget_l1_code IS NULL OR l7_code IS NULL OR l3_code IS NULL) = 0 
         THEN 'ALIGNED (0 Gaps)' ELSE 'Gaps Remaining' END AS status
FROM v_pbi_sales_budget_live
WHERE yr = 2026;

\echo ''
\echo '=== Step 9: Main Category Breakdown (2026 Target vs Actuals) =============='
\echo ''

SELECT
    COALESCE(b.l7_label, f.l7_label, 'Unassigned') AS main_category,
    round(COALESCE(sum(f.amount), 0)::numeric, 2)  AS actual_amount_ytd,
    round(COALESCE(b.target_val, 0)::numeric, 2)   AS target_amount_ytd,
    CASE WHEN COALESCE(b.target_val, 0) > 0 AND COALESCE(sum(f.amount), 0) > 0 THEN 'OK (Aligned)'
         WHEN COALESCE(b.target_val, 0) = 0 THEN 'NO TARGET'
         ELSE 'NO ACTUALS' END AS alignment_status
FROM (
    SELECT DISTINCT l7_code, l7_label, sum(amount) AS amount
    FROM v_pbi_sales_sman_fact
    WHERE yr = 2026 AND in_scope
    GROUP BY l7_code, l7_label
) f
FULL OUTER JOIN (
    SELECT
        l7_code,
        max(l7_label) AS l7_label,
        sum(budget_value) AS target_val
    FROM v_pbi_sales_budget_live
    WHERE yr = 2026
    GROUP BY l7_code
) b ON b.l7_code = f.l7_code
GROUP BY b.l7_label, f.l7_label, b.target_val
ORDER BY actual_amount_ytd DESC;

\echo ''
\echo '=== Step 10: Sales Type Group Breakdown (2026 Target vs Actuals) ==========='
\echo ''

SELECT
    COALESCE(f.l1_label, b.budget_l1_label, 'Unassigned') AS sales_type_group,
    round(COALESCE(sum(f.amount), 0)::numeric, 2)         AS actual_amount_ytd,
    round(COALESCE(b.target_val, 0)::numeric, 2)          AS target_amount_ytd,
    CASE WHEN COALESCE(b.target_val, 0) > 0 AND COALESCE(sum(f.amount), 0) > 0 THEN 'OK (Aligned)'
         WHEN COALESCE(b.target_val, 0) = 0 THEN 'NO TARGET'
         ELSE 'NO ACTUALS' END AS alignment_status
FROM (
    SELECT DISTINCT l1_code, l1_label, sum(amount) AS amount
    FROM v_pbi_sales_sman_fact
    WHERE yr = 2026 AND in_scope
    GROUP BY l1_code, l1_label
) f
FULL OUTER JOIN (
    SELECT
        budget_l1_code,
        max(budget_l1_label) AS budget_l1_label,
        sum(budget_value)    AS target_val
    FROM v_pbi_sales_budget_live
    WHERE yr = 2026
    GROUP BY budget_l1_code
) b ON b.budget_l1_code = f.l1_code
GROUP BY b.budget_l1_label, f.l1_label, b.target_val
ORDER BY actual_amount_ytd DESC;
