-- Unique indexes on the join keys of the ten legacy master tables that
-- v_bidata_live LEFT JOINs, plus fresh statistics for them.
--
-- Applied to dbprod 2026-08-27. Before this, nine of the ten had a primary
-- key on `id` and nothing else, so Postgres had neither a usable index nor
-- any idea how many rows they held. Every "Sales Dashboard - New" /
-- "Sales Analysis - New" query full-scans the view, and each of those joins
-- was re-scanning a master table it could not size.
--
-- Every key below was verified unique on live data before creating the
-- index, so none of these can fail on current content. Re-runnable:
-- IF NOT EXISTS makes it a no-op once applied.
--
-- Measured effect on initial dashboard load (live dbprod, through the real
-- controller code): Sales Dashboard - New 1.45s -> 0.77s, Sales Analysis -
-- New 4.88s -> 2.82s. Part of that is join elimination: with a unique index
-- proving the join key unique, Postgres can drop a LEFT JOIN outright when
-- the query reads none of its columns.
--
-- This does NOT make _planner_hints' "SET LOCAL enable_nestloop = off"
-- redundant — see the comment on PbiSalesMailNewController. Removing the
-- hint after these indexes existed measured 50s on Sales Analysis - New.
--
--   docker exec -i cloud-db-1 psql -U odoo -d dbprod -v ON_ERROR_STOP=1 \
--     -f scripts/legacy_master_join_key_indexes.sql

BEGIN;
CREATE UNIQUE INDEX IF NOT EXISTS t_cstclassificationdesc_code_lang_unique ON t_cstclassificationdesc (cc_code, cc_lang);
CREATE UNIQUE INDEX IF NOT EXISTS t_rptregionsdesc_code_lang_unique       ON t_rptregionsdesc (rr_code, rr_lang);
CREATE UNIQUE INDEX IF NOT EXISTS t_subregionsdesc_code_lang_unique       ON t_subregionsdesc (sr_code, sr_lang);
CREATE UNIQUE INDEX IF NOT EXISTS sl_salesmandesc_code_lang_unique        ON sl_salesmandesc (sm_code, sm_lang);
CREATE UNIQUE INDEX IF NOT EXISTS customerdesc_no_lang_unique             ON customerdesc (cst_no, cst_lang);
CREATE UNIQUE INDEX IF NOT EXISTS t_groupsdesc_code_lang_unique           ON t_groupsdesc (grpd_code, grpd_lang);
CREATE UNIQUE INDEX IF NOT EXISTS t_products_grp_code_unique              ON t_products (p_grp, p_code);
CREATE UNIQUE INDEX IF NOT EXISTS t_mainproductsdesc_grp_code_lang_unique ON t_mainproductsdesc (mp_grp, mp_code, mp_lang);
CREATE UNIQUE INDEX IF NOT EXISTS t_productsubsdescgroup_key_unique       ON t_productsubsdescgroup (psg_grp, psg_pcode, psg_psub, psg_lang);
-- t_cstclasstypedesc already carries t_cstclasstypedesc_code_lang_unique.
COMMIT;

-- These tables are never ANALYZEd by autovacuum (they are bulk-loaded, not
-- written through Odoo), so their stats must be refreshed by hand here.
ANALYZE t_cstclassificationdesc, t_rptregionsdesc, t_subregionsdesc, sl_salesmandesc,
        customerdesc, t_groupsdesc, t_products, t_mainproductsdesc, t_productsubsdescgroup,
        t_cstclasstypedesc, catalogflags, bidata;
