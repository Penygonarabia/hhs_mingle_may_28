-- Restore product_category.product_family and repopulate it from catalog/bidata.
--
--   psql -U odoo -d <database> -v ON_ERROR_STOP=1 -f scripts/restore_product_category_family_link.sql
--
-- Also offered on PBI Dashboards > Configurations.
--
-- WHY THIS EXISTS. dashboard_groups' product.family model was deliberately
-- removed (2026-09-11, restoring the module to its pre-product.family
-- baseline). Odoo's module upgrade cleaned up the ir.model/fields/views/access
-- rows for it -- correctly -- but that cleanup ALSO dropped the
-- product_category.product_family COLUMN and the product_family.pfam_ref
-- UNIQUE constraint. On a database where the model once existed, the
-- product_family TABLE itself was left alone (Odoo does not drop a whole
-- table just because its owning model vanished from code), so the data
-- survived; only the link and the constraint went.
--
-- ON A SERVER BUILT FROM SCRATCH THERE IS NO SUCH TABLE. Nothing creates it
-- any more: the owning model is gone from the code, and pbi_sales_dashboards
-- reads product_family as a plain optional foreign table it probes for rather
-- than depends on. So this script is the only thing that can put it there,
-- and Step 0 does -- with the schema dbprod carries, sequence and foreign
-- keys included. Found on staging-hhsv3 2026-09-11: an earlier run had added
-- the product_category.product_family COLUMN and then died on the foreign
-- key with `relation "product_family" does not exist`, leaving the column
-- dangling. Step 0 is what makes a re-run recover from exactly that.
--
-- That link is not dashboard_groups' business once the model is gone -- it is
-- pbi_sales_dashboards', which reads it as a plain foreign column via
-- pbi_dashboards/controllers/optional_schema.py and has never depended on the
-- Odoo model at all (see the "pbi modules stay dependency-free" rule). The
-- "Product Sub-Group" level on every ten-level board (Sales Dashboard - VQ,
-- Sales Dashboard With Salesman, Sales Analysis with Salesman, Sales Data
-- Study) is keyed on exactly this column. Losing it did not error -- it
-- degraded silently, the way an absent optional table is designed to: every
-- sale fell into "Unassigned" instead of its real family, while Target kept
-- working because it is sourced independently, straight off product_family
-- via sales_budget_line.erp_subgroup_code. This is the fix: it does not
-- touch dashboard_groups or its model, only the raw column and data
-- pbi_sales_dashboards depends on.
--
-- WHAT IT DOES, IN ORDER.
--   0. Creates the product_family table, sequence and foreign keys if this
--      database has none at all. No-op wherever it already exists.
--   1. Adds product_category.product_family back (integer, FK to
--      product_family, ON DELETE SET NULL) if it is not already there.
--   2. Restores product_family.pfam_ref's UNIQUE constraint if missing --
--      the population step below needs it for ON CONFLICT.
--   3. Repopulates the link from catalog + bidata, and creates any product
--      families it implies but does not find (mirrors
--      sync_and_repair_all_masters.sql's Step 5b exactly, so the two never
--      drift apart -- this file is not a fork of that logic, it is the same
--      logic kept runnable on its own).
--   4. Refreshes v_pbi_sales_sman_fact.
--   5. Reports what the database now holds, so a run that changed nothing is
--      distinguishable from a run that fixed something.
--
-- Idempotent throughout -- IF NOT EXISTS / ON CONFLICT DO NOTHING / only
-- fills NULLs -- so running it again once the link is already correct is a
-- fast no-op, not a re-derivation.
--
-- ONE CASE THIS SCRIPT CANNOT FIX BY ITSELF: if the column did not exist yet
-- on THIS database (step 1 actually created it, rather than finding it
-- already there) -- which is ALWAYS true on a server that needed step 0 --
-- the materialized view's COMPILED SQL was built while the
-- column was absent and has `NULL::integer` baked into it literally -- a
-- REFRESH re-runs that same stale text and will keep reporting Unassigned
-- for everything no matter how many times it runs. Diagnosed on dbprod
-- 2026-09-11 the hard way: this script's own REFRESH (step 4) only helps
-- once the view's DEFINITION already has the real column reference. If step
-- 4 does not fix the boards, the view must be recreated, not just refreshed:
--
--   docker exec cloud-web-1 odoo -c /etc/odoo/odoo.conf --db_host=db \
--     --db_user=odoo --db_password=odoo -d <database> \
--     -u pbi_sales_dashboards --stop-after-init
--
-- which calls the model's init() and rebuilds the view's SQL text against
-- the schema as it now stands. Restart the web container afterwards so the
-- live registry picks up the rebuilt view.
--
-- A REFRESH MATERIALIZED VIEW taken here without the planner hints
-- pbi_sales_sman_fact_view.py applies before its own refresh (SET LOCAL jit
-- = off, SET LOCAL enable_nestloop = off) can take upwards of twenty minutes
-- against the legacy transaction tables, which carry no planner stats -- see
-- dbprod-legacy-table-stats-and-index. This script sets both before its own
-- REFRESH for exactly that reason. If a refresh started elsewhere without
-- them is already running and stuck, `pg_cancel_backend()` it rather than
-- wait it out.

-- WHY THE REFRESH FALLS BACK RATHER THAN FAILING
--
-- Odoo gives every cursor REPEATABLE READ (odoo/sql_db.py sets
-- ISOLATION_LEVEL_REPEATABLE_READ on the connection), and the Configurations
-- page runs this whole file inside that one request transaction. REFRESH ...
-- CONCURRENTLY applies its diff BY ctid, so if any other transaction refreshes
-- v_pbi_sales_sman_fact and commits after this transaction took its snapshot,
-- the diff's DELETE lands on tuples that refresh has already removed and the
-- script dies with
--
--     could not serialize access due to concurrent delete
--     CONTEXT: SQL statement "DELETE FROM public.v_pbi_sales_sman_fact mv
--     WHERE ctid OPERATOR(pg_catalog.=) ANY (SELECT diff.tid FROM
--     pg_temp_30.pg_temp_1149897_2 diff WHERE diff.tid IS NOT NULL AND
--     diff.newdata IS NULL)"
--
-- reported on staging-hhsv3 on 2026-09-11. NOTHING IS WRONG WITH THE DATABASE
-- when that happens. The refresh cron -- nightly at 02:30, and again whenever
-- a master-data trigger queues it, which editing product_category or
-- product_family does -- simply landed mid-script. Under READ COMMITTED the
-- row would be skipped; under REPEATABLE READ it is a hard 40001 with no
-- retry, and since the page wraps the run in a single savepoint, steps 0-3
-- roll back with it: the link repair is lost to a refresh doing its job.
--
-- So the REFRESH runs in its own subtransaction and falls back to the plain,
-- blocking form on ANY failure -- the same choice
-- pbi.sales.sman.fact.refresh_fact() makes, and it covers the other case that
-- reaches it: CONCURRENTLY is illegal on a snapshot that has never been
-- populated, which is every from-scratch server. The plain form rewrites the
-- matview instead of diffing it, so it cannot serialize-fail; the cost is an
-- ACCESS EXCLUSIVE lock held until this script commits.
--
-- The SET LOCAL hints survive the caught exception -- rolling back a
-- subtransaction does not discard settings made outside it -- so the fallback
-- still runs with the plan it needs. refresh_fact() has to re-apply them only
-- because it rolls the whole transaction back.

\echo ''
\echo '=== Step 0: Creating product_family if this database has none =========='
\echo ''

-- Mirrors dbprod's own product_family exactly, so a from-scratch server and a
-- server that once had the Odoo model end up with the same schema. `serial`
-- names the sequence product_family_id_seq and the constraint
-- product_family_pkey, which is what the model used to create. A no-op where
-- the table is already there, so dbprod never notices this step.
CREATE TABLE IF NOT EXISTS product_family (
    id               serial PRIMARY KEY,
    create_uid       integer,
    write_uid        integer,
    pfam_ref         varchar NOT NULL,
    pfam_name        varchar NOT NULL,
    pfam_name2       varchar,
    complete_name    varchar,
    create_date      timestamp without time zone,
    write_date       timestamp without time zone,
    pfam_merged_into integer
);

DO $$
BEGIN
    ALTER TABLE product_family ADD CONSTRAINT product_family_create_uid_fkey
        FOREIGN KEY (create_uid) REFERENCES res_users(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object OR duplicate_table THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE product_family ADD CONSTRAINT product_family_write_uid_fkey
        FOREIGN KEY (write_uid) REFERENCES res_users(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object OR duplicate_table THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE product_family ADD CONSTRAINT product_family_pfam_merged_into_fkey
        FOREIGN KEY (pfam_merged_into) REFERENCES product_family(id) ON DELETE RESTRICT;
EXCEPTION
    WHEN duplicate_object OR duplicate_table THEN NULL;
END $$;

\echo ''
\echo '=== Step 1: Restoring product_category.product_family column ==========='
\echo ''

ALTER TABLE product_category ADD COLUMN IF NOT EXISTS product_family integer;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
         WHERE tablename = 'product_category' AND indexdef ILIKE '%(product_family)%'
    ) THEN
        CREATE INDEX ON product_category (product_family);
    END IF;
END $$;

DO $$
BEGIN
    ALTER TABLE product_category ADD CONSTRAINT product_category_product_family_fkey
        FOREIGN KEY (product_family) REFERENCES product_family(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object OR duplicate_table THEN NULL;
END $$;

\echo ''
\echo '=== Step 2: Restoring product_family.pfam_ref UNIQUE constraint ========'
\echo ''

DO $$
BEGIN
    ALTER TABLE product_family ADD CONSTRAINT product_family_pfam_ref_unique UNIQUE (pfam_ref);
EXCEPTION
    WHEN duplicate_object OR duplicate_table THEN NULL;
END $$;

-- Ensure res_partner has salesman columns and indexes
ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS is_salesman boolean DEFAULT false;
ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS salesman_ref varchar;
CREATE INDEX IF NOT EXISTS res_partner_salesman_ref_index ON res_partner (salesman_ref);

\echo ''
\echo '=== Step 3: Repopulating the link from catalog & bidata ================'
\echo ''

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

-- Backfill blank cat_psgroup in catalog from bidata
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

-- Missing budget product families -- a budget row can name a family
-- (erp_subgroup_code) that catalog/bidata never introduced.
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

-- Known alias/duplicate families -- same as sync_and_repair_all_masters.sql.
UPDATE product_family tgt
   SET pfam_merged_into = base.id
  FROM product_family base
 WHERE base.pfam_ref = 'WTSG006'
   AND tgt.pfam_ref = 'WTSG003'
   AND tgt.pfam_merged_into IS NULL;

UPDATE product_family f
   SET pfam_merged_into = p.id
  FROM product_family p
 WHERE p.pfam_name = 'Inverter'
   AND f.pfam_name IN ('WINDOW DELUXE INVERTER', 'MISSION INVERTER')
   AND f.pfam_merged_into IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS product_family_id_uindex ON product_family (id);

\echo ''
\echo '=== Step 4: Refreshing v_pbi_sales_sman_fact ============================'
\echo ''

-- SET LOCAL only survives to the end of the CURRENT transaction, and psql
-- autocommits each statement separately by default -- so these hints must
-- share an explicit transaction with the REFRESH they are for, or they are
-- silently reset before it runs.
BEGIN;
SET LOCAL jit = off;
SET LOCAL enable_nestloop = off;

DO $refresh$
BEGIN
    BEGIN
        REFRESH MATERIALIZED VIEW CONCURRENTLY v_pbi_sales_sman_fact;
        RAISE NOTICE 'v_pbi_sales_sman_fact refreshed CONCURRENTLY: no reader was blocked.';
    EXCEPTION WHEN OTHERS THEN
        -- Expected, not exceptional: a refresh committed elsewhere during this
        -- transaction (40001), or the snapshot has never been populated
        -- (0A000). Either way the diff-based refresh is impossible here and
        -- the rewrite is, so take it rather than lose steps 0-3.
        RAISE NOTICE 'CONCURRENTLY refused (%: %).', SQLSTATE, SQLERRM;
        RAISE NOTICE 'Falling back to a blocking REFRESH -- it holds an ACCESS EXCLUSIVE lock on v_pbi_sales_sman_fact until this script commits.';
        REFRESH MATERIALIZED VIEW v_pbi_sales_sman_fact;
        RAISE NOTICE 'v_pbi_sales_sman_fact refreshed the blocking way instead.';
    END;
END
$refresh$;

COMMIT;
ANALYZE v_pbi_sales_sman_fact;

\echo ''
\echo '=== Step 5: What this database holds now ================================'
\echo ''

SELECT (SELECT count(*) FROM product_family)                          AS families,
       (SELECT count(*) FROM product_category WHERE product_family IS NOT NULL)
                                                                      AS categories_linked,
       (SELECT count(*) FROM product_category WHERE product_family IS NULL)
                                                                      AS categories_unlinked,
       (SELECT count(*) FROM pg_constraint
         WHERE conname = 'product_category_product_family_fkey')       AS fkey_present,
       (SELECT count(*) FROM pg_constraint
         WHERE conname = 'product_family_pfam_ref_unique')             AS unique_present,
       -- The tell for the stale-view case in the header: the compiled text
       -- still carries NULL::integer where the real column should be.
       (SELECT CASE
                 WHEN to_regclass('v_pbi_sales_sman_fact') IS NULL THEN 'view missing'
                 WHEN pg_get_viewdef('v_pbi_sales_sman_fact'::regclass) ILIKE '%product_family%'
                   THEN 'view references the column'
                 ELSE 'VIEW IS STALE -- run -u pbi_sales_dashboards'
               END)                                                    AS view_state;

\echo ''
\echo 'Done. If Product Sub-Group still shows Target only (no This Year / Last'
\echo 'Year), the view definition itself is stale -- see view_state above, the'
\echo 'header comment, and run `-u pbi_sales_dashboards` rather than this again.'
\echo ''
