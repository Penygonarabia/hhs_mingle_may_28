-- Create the bidata table and the v_bidata_live view.
--
--   psql -U odoo -d <database> -v ON_ERROR_STOP=1 -f scripts/create_bidata_table_and_live_view.sql
--
-- Also offered on PBI Dashboards > Configurations, under Bidata Feed.
--
-- THIS SHIPS THE SHAPE, NOT THE DATA, AND THAT IS DELIBERATE. bidata on dbprod
-- is 292,682 rows across 2024, 2025 and 2026 -- roughly 86 MB of values, 160 MB
-- on disk. Committing that as INSERT statements would put it in this repo's
-- history permanently, which is the one thing .gitignore here is most explicit
-- about. The data moves server to server through the Configurations page's own
-- Move Bidata card, a year at a time, as CSV: export on the server that has it,
-- import on the one that does not. That path already exists, it diagnoses
-- before it writes, and it only ever inserts and updates.
--
-- What it could NOT do until now is run at all against a server with no bidata
-- table: both of its routes guard on to_regclass('bidata') and refuse. This is
-- the missing half.
--
-- WHY THE WIDENING STEP EXISTS. A server can have a bidata table that is
-- NARROWER than dbprod's -- staging-hhsv3's feed arrived without bi_invprice
-- (2026-08-29). Everything downstream then half-works: to_regclass('bidata')
-- passes, so the guards let it through, and the failure lands later and
-- somewhere else. v_bidata_live in particular reads bi_invprice, so on a
-- narrower table it cannot be created at all. Step 2 therefore adds every
-- column dbprod has that this database lacks, rather than assuming the table is
-- either absent or already right. A column added this way is empty until the
-- feed or a Move Bidata import fills it, which is the honest state: a missing
-- column and an empty one are different problems and should look different.
--
-- NO PRIMARY KEY, NO UNIQUE CONSTRAINT. That is dbprod's actual shape, not an
-- omission, and the import path is built around it: it UPDATEs on s.id = b.id
-- and INSERTs what did not match, rather than using ON CONFLICT, which would
-- need a unique index. `id` is unique across all 292,682 rows in practice and
-- is the key to transfer on; bi_sqlrecid is not. Adding a constraint here would
-- start failing the day the ERP feed delivered a repeat.
--
-- THE VIEW IS DROPPED AND RECREATED, not CREATE OR REPLACE. Replace refuses
-- whenever the column list or a type differs from the view already there, which
-- is exactly the case this script exists to repair: a view built over a
-- narrower bidata. Nothing depends on v_bidata_live -- checked on dbprod, no
-- dependent view or rule -- so dropping it costs nothing but the moment it is
-- absent.
--
-- ON THE PER-CENT SIGN in the view body: the bi_cstno NOT LIKE filter is a real
-- predicate and has to stay. It is safe through the Configurations page, which
-- executes each statement with no parameters, so psycopg2 never interpolates --
-- the same reason diagnose_and_clean_salesman_type_id.sql's ILIKE has always
-- been fine there. Do not double it up to escape it, or the filter silently
-- stops matching.
--
-- Safe to run any number of times.

\echo ''
\echo '=== Step 1: Creating the bidata table if this database has none ========='
\echo ''

CREATE TABLE IF NOT EXISTS bidata (
    id                       integer NOT NULL,
    bi_sqlrecid              integer,
    bi_year                  integer,
    bi_csttypecode           varchar,
    bi_csttypedesc           varchar,
    bi_cstsubtypecode        varchar,
    bi_cstsubtypedesc        varchar,
    bi_cstregioncode         varchar,
    bi_cstregiondesc         varchar,
    bi_cstsubregioncode      varchar,
    bi_cstsubregiondesc      varchar,
    bi_salesmancode          varchar,
    bi_salesmanname          varchar,
    bi_cstno                 varchar,
    bi_cstname               varchar,
    bi_pgroupcode            varchar,
    bi_pgroupname            varchar,
    bi_psgroupcode           varchar,
    bi_psgroupname           varchar,
    bi_catmodelcode          varchar,
    bi_catmainpartno         varchar,
    bi_monthdate             date,
    bi_invoicecost           double precision,
    bi_qty                   integer,
    bi_amount                double precision,
    bi_budgetqty             numeric,
    bi_budgetamount          double precision,
    bi_lastmodifieddate      date,
    bi_month                 integer,
    bi_franchisecode         varchar(20),
    bi_franchisename         varchar(200),
    bi_invslno               numeric,
    bi_invwhouse             varchar(3),
    bi_invno                 varchar(12),
    bi_invdate               varchar(8),
    bi_invstock              varchar(8),
    bi_invpartno             varchar(25),
    bi_invwhousename         varchar(40),
    bi_userlmt               varchar(9),
    bi_type                  varchar(1),
    bi_monthdate_dummy       date,
    bi_pyqty                 integer,
    bi_pyamount              double precision,
    create_uid               integer,
    create_date              timestamp,
    write_uid                integer,
    write_date               timestamp,
    bi_invprice              numeric,
    bi_invdisc               numeric,
    bi_invcstspldisc         numeric,
    bi_invcashbkproamt       numeric,
    bi_invparttype           varchar(5)
);

\echo ''
\echo '=== Step 2: Widening an existing table to the full column set =========='
\echo ''

ALTER TABLE bidata ADD COLUMN IF NOT EXISTS id integer;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_sqlrecid integer;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_year integer;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_csttypecode varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_csttypedesc varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_cstsubtypecode varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_cstsubtypedesc varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_cstregioncode varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_cstregiondesc varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_cstsubregioncode varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_cstsubregiondesc varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_salesmancode varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_salesmanname varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_cstno varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_cstname varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_pgroupcode varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_pgroupname varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_psgroupcode varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_psgroupname varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_catmodelcode varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_catmainpartno varchar;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_monthdate date;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_invoicecost double precision;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_qty integer;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_amount double precision;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_budgetqty numeric;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_budgetamount double precision;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_lastmodifieddate date;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_month integer;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_franchisecode varchar(20);
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_franchisename varchar(200);
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_invslno numeric;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_invwhouse varchar(3);
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_invno varchar(12);
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_invdate varchar(8);
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_invstock varchar(8);
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_invpartno varchar(25);
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_invwhousename varchar(40);
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_userlmt varchar(9);
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_type varchar(1);
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_monthdate_dummy date;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_pyqty integer;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_pyamount double precision;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS create_uid integer;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS create_date timestamp;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS write_uid integer;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS write_date timestamp;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_invprice numeric;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_invdisc numeric;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_invcstspldisc numeric;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_invcashbkproamt numeric;
ALTER TABLE bidata ADD COLUMN IF NOT EXISTS bi_invparttype varchar(5);

\echo ''
\echo '=== Step 3: Indexes ===================================================='
\echo ''

CREATE INDEX IF NOT EXISTS bidata_drill_idx ON bidata
    (bi_year, bi_month, bi_csttypecode, bi_cstsubtypecode, bi_cstregioncode,
     bi_cstno, bi_pgroupcode, bi_psgroupcode);

CREATE INDEX IF NOT EXISTS bidata_perf_covering_idx ON bidata
    (bi_franchisecode, bi_year, bi_month)
    INCLUDE (bi_qty, bi_amount, bi_budgetamount, bi_budgetqty, bi_invprice,
             bi_invdisc, bi_invcstspldisc, bi_csttypecode, bi_pgroupcode,
             bi_cstno, bi_cstregioncode, bi_cstsubregioncode, bi_psgroupname,
             bi_pgroupname, bi_cstregiondesc, bi_franchisename, bi_salesmanname,
             bi_csttypedesc, bi_cstname, bi_cstsubtypecode, bi_cstsubtypedesc,
             bi_psgroupcode, bi_salesmancode);

\echo ''
\echo '=== Step 4: v_bidata_live =============================================='
\echo ''

-- GUARDED, because the view reads the legacy ERP master tables and no module
-- creates any of them. On a database that has not been fed yet, an unguarded
-- CREATE VIEW aborts the whole script at the last step, after the table it came
-- to build is already right. Reported and skipped instead: the table is what
-- the Move Bidata import needs, and the view can be built the moment the
-- masters arrive by running this again.
DO $bidatalive$
DECLARE
    absent text;
BEGIN
    SELECT string_agg(t, ', ' ORDER BY t) INTO absent
      FROM unnest(ARRAY['bidata', 'catalogflags', 'customerdesc', 'sl_salesmandesc', 't_cstclassificationdesc', 't_cstclasstypedesc', 't_groupsdesc', 't_mainproductsdesc', 't_products', 't_productsubsdescgroup', 't_rptregionsdesc', 't_subregionsdesc']) AS t
     WHERE to_regclass(t) IS NULL;

    IF absent IS NOT NULL THEN
        RAISE NOTICE 'v_bidata_live NOT created: this database has no %', absent;
        RETURN;
    END IF;

    DROP VIEW IF EXISTS v_bidata_live;
    EXECUTE $view$CREATE VIEW v_bidata_live AS
SELECT bd.id,
    bd.bi_sqlrecid,
    bd.bi_year,
    COALESCE(bd.bi_csttypecode, '*'::character varying) AS bi_csttypecode,
    COALESCE(bd.bi_csttypedesc, '*'::character varying) AS bi_csttypedesc_direct,
    COALESCE(ctd.cs_desc, '*'::character varying) AS bi_csttypedesc,
    COALESCE(bd.bi_cstsubtypecode, '*'::character varying) AS bi_cstsubtypecode,
    COALESCE(bd.bi_cstsubtypedesc, '*'::character varying) AS bi_cstsubtypedesc_direct,
    COALESCE(ccd.cc_desc, '*'::character varying) AS bi_cstsubtypedesc,
    COALESCE(bd.bi_cstregioncode, '*'::character varying) AS bi_cstregioncode,
    COALESCE(bd.bi_cstregiondesc, '*'::character varying) AS bi_cstregiondesc_direct,
    COALESCE(rd.rr_desc, '*'::character varying) AS bi_cstregiondesc,
    COALESCE(bd.bi_cstsubregioncode, '*'::character varying) AS bi_cstsubregioncode,
    COALESCE(bd.bi_cstsubregiondesc, '*'::character varying) AS bi_cstsubregiondesc_direct,
    COALESCE(srd.sr_desc, '*'::character varying) AS bi_cstsubregiondesc,
    COALESCE(bd.bi_salesmancode, '*'::character varying) AS bi_salesmancode,
    COALESCE(bd.bi_salesmanname, '*'::character varying) AS bi_salesmanname_direct,
    COALESCE(smd.sm_name, '*'::character varying) AS bi_salesmanname,
    COALESCE(bd.bi_cstno, '*'::character varying) AS bi_cstno,
    COALESCE(bd.bi_cstname, '*'::character varying) AS bi_cstname_direct,
    COALESCE(cstd.cst_name, '*'::character varying) AS bi_cstname,
    COALESCE(bd.bi_pgroupcode, '*'::character varying) AS bi_pgroupcode,
    COALESCE(bd.bi_pgroupname, '*'::character varying) AS bi_pgroupname_direct,
    COALESCE(pr.p_desc, '*'::character varying) AS bi_pgroupname,
    COALESCE(mpd.mp_code, '*'::character varying) AS bi_mpcode,
    COALESCE(mpd.mp_desc, '*'::character varying) AS bi_mpdesc,
    COALESCE(bd.bi_psgroupcode, '*'::character varying) AS bi_psgroupcode,
    COALESCE(bd.bi_psgroupname, '*'::character varying) AS bi_psgroupname_direct,
    COALESCE(prsgd.psg_desc, '*'::character varying) AS bi_psgroupname,
    COALESCE(bd.bi_catmodelcode, '*'::character varying) AS bi_catmodelcode,
    COALESCE(bd.bi_catmainpartno, '*'::character varying) AS bi_catmainpartno,
    bd.bi_monthdate,
    COALESCE(bd.bi_invoicecost, 0::double precision) AS bi_invoicecost,
    COALESCE(bd.bi_qty, 0) AS bi_qty_direct,
    COALESCE(
        CASE
            WHEN cfj.cat_part IS NOT NULL THEN bd.bi_qty
            ELSE 0
        END, 0) AS bi_qty,
    COALESCE(bd.bi_qty::numeric * (bd.bi_invprice - bd.bi_invdisc - bd.bi_invcstspldisc), 0::numeric) AS bi_amount,
    COALESCE(bd.bi_budgetqty, 0::numeric) AS bi_budgetqty,
    COALESCE(bd.bi_budgetamount, 0::double precision) AS bi_budgetamount,
    bd.bi_lastmodifieddate,
    bd.bi_month,
    COALESCE(bd.bi_franchisecode, '*'::character varying) AS bi_franchisecode,
    COALESCE(bd.bi_franchisename, '*'::character varying) AS bi_franchisename_direct,
    COALESCE(gd.grpd_desc, '*'::character varying) AS bi_franchisename,
    COALESCE(bd.bi_invslno, 0::numeric) AS bi_invslno,
    COALESCE(bd.bi_invwhouse, '*'::character varying) AS bi_invwhouse,
    COALESCE(bd.bi_invno, '*'::character varying) AS bi_invno,
    bd.bi_invdate,
    COALESCE(bd.bi_invstock, '*'::character varying) AS bi_invstock,
    COALESCE(bd.bi_invpartno, '*'::character varying) AS bi_invpartno,
    COALESCE(bd.bi_invwhousename, '*'::character varying) AS bi_invwhousename,
    bd.bi_userlmt,
    COALESCE(bd.bi_type, '*'::character varying) AS bi_type,
    bd.bi_monthdate_dummy,
    COALESCE(bd.bi_pyqty, 0) AS bi_pyqty,
    COALESCE(bd.bi_pyamount, 0::double precision) AS bi_pyamount,
    COALESCE(bd.create_uid, 0) AS create_uid,
    bd.create_date,
    COALESCE(bd.write_uid, 0) AS write_uid,
    bd.write_date,
    COALESCE(bd.bi_invprice, 0::numeric) AS bi_invprice,
    COALESCE(bd.bi_invdisc, 0::numeric) AS bi_invdisc,
    COALESCE(bd.bi_invcstspldisc, 0::numeric) AS bi_invcstspldisc,
    COALESCE(bd.bi_invcashbkproamt, 0::numeric) AS bi_invcashbkproamt,
    COALESCE(bd.bi_invparttype, '*'::character varying) AS bi_invparttype
   FROM bidata bd
     LEFT JOIN ( SELECT DISTINCT upper(btrim(catalogflags.cat_grp::text)) AS cat_grp,
            upper(btrim(catalogflags.cat_part::text)) AS cat_part,
            upper(btrim(catalogflags.cat_stock::text)) AS cat_stock
           FROM catalogflags
          WHERE btrim(catalogflags.cat_flag::text) = '02'::text) cfj ON cfj.cat_grp = upper(btrim(bd.bi_franchisecode::text)) AND cfj.cat_part = upper(btrim(bd.bi_invpartno::text)) AND cfj.cat_stock = upper(btrim(bd.bi_invstock::text))
     LEFT JOIN t_cstclasstypedesc ctd ON ctd.cs_code::text = bd.bi_csttypecode::text AND ctd.cs_lang::text = '1'::text
     LEFT JOIN t_cstclassificationdesc ccd ON ccd.cc_code::text = bd.bi_cstsubtypecode::text AND ccd.cc_lang::text = '1'::text
     LEFT JOIN t_rptregionsdesc rd ON rd.rr_code::text = bd.bi_cstregioncode::text AND rd.rr_lang = 1
     LEFT JOIN t_subregionsdesc srd ON srd.sr_code::text = bd.bi_cstsubregioncode::text AND srd.sr_lang = 1
     LEFT JOIN sl_salesmandesc smd ON smd.sm_code::text = bd.bi_salesmancode::text AND smd.sm_lang::text = '1'::text
     LEFT JOIN customerdesc cstd ON cstd.cst_no::text = bd.bi_cstno::text AND cstd.cst_lang = 1
     LEFT JOIN t_groupsdesc gd ON gd.grpd_code::text = bd.bi_franchisecode::text AND gd.grpd_lang::text = '1'::text
     LEFT JOIN t_products pr ON pr.p_grp::text = bd.bi_franchisecode::text AND pr.p_code::text = bd.bi_pgroupcode::text
     LEFT JOIN t_mainproductsdesc mpd ON mpd.mp_grp::text = bd.bi_franchisecode::text AND mpd.mp_code::text = pr.p_mpcode::text AND mpd.mp_lang = 1
     LEFT JOIN t_productsubsdescgroup prsgd ON prsgd.psg_grp::text = bd.bi_franchisecode::text AND prsgd.psg_pcode::text = bd.bi_pgroupcode::text AND prsgd.psg_psub::text = bd.bi_psgroupcode::text AND prsgd.psg_lang::text = '1'::text
  WHERE 1 = 1 AND bd.bi_year >= 2024 AND bd.bi_cstno::text !~~ 'V%'::text AND bd.bi_franchisecode::text = 'MDA'::text AND (bd.bi_pgroupcode::text = ANY (ARRAY['ACACC'::text, 'ACAIP'::text, 'ACCON'::text, 'ACCST'::text, 'ACHCL'::text, 'ACPAC'::text, 'ACPKG'::text, 'ACPOR'::text, 'ACVRF'::text, 'ACWIN'::text, 'ACWTS'::text, 'ATOM'::text]))$view$;
    RAISE NOTICE 'v_bidata_live created over % source tables.',
                 array_length(ARRAY['bidata', 'catalogflags', 'customerdesc', 'sl_salesmandesc', 't_cstclassificationdesc', 't_cstclasstypedesc', 't_groupsdesc', 't_mainproductsdesc', 't_products', 't_productsubsdescgroup', 't_rptregionsdesc', 't_subregionsdesc'], 1);
END
$bidatalive$;

\echo ''
\echo '=== Step 5: What this database now holds ==============================='
\echo ''

SELECT y.yr                              AS year,
       coalesce(c.rows, 0)               AS bidata_rows,
       CASE WHEN coalesce(c.rows, 0) = 0
            THEN 'EMPTY -- import this year with Move Bidata'
            ELSE 'present' END           AS status
  FROM (VALUES (2024), (2025), (2026)) AS y(yr)
  LEFT JOIN (SELECT bi_year AS yr, count(*) AS rows FROM bidata GROUP BY 1) c
         ON c.yr = y.yr
 ORDER BY 1;

SELECT (SELECT count(*) FROM bidata)                      AS bidata_rows_total,
       (SELECT count(*) FROM information_schema.columns
         WHERE table_name = 'bidata')                     AS bidata_columns,
       (SELECT CASE WHEN to_regclass('v_bidata_live') IS NULL THEN -1
                    ELSE (SELECT count(*) FROM v_bidata_live) END)
                                                          AS live_view_rows,
       'Table and view are in place. Rows arrive through Move Bidata, one year at a time.'
                                                          AS next_step;
