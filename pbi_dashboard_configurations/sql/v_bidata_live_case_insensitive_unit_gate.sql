-- v_bidata_live: make the unit gate case-insensitive
-- =================================================
--
-- WHAT THIS FIXES
--
-- bi_qty is not the raw invoiced quantity. A split air conditioner ships as two
-- parts on one invoice -- condenser and fan-coil -- and only the half flagged
-- '02' in catalogflags bears the unit, so the view zeroes bi_qty on any row
-- whose (bi_franchisecode, bi_invpartno, bi_invstock) finds no '02' row.
--
-- That join was CASE-SENSITIVE, and the part number is the one key on this
-- database that is not reliably upper-cased: the ERP takes it as typed, so
-- MKH1-V700-R4-r and MKH1-V700-R4-R are the same physical part typed two ways,
-- while catalogflags holds it exactly once, upper case. The lower-cased rows
-- therefore missed the gate and were counted as ZERO UNITS while still carrying
-- their full value.
--
-- Measured on dbprod (2026-09-03), MDA AC scope, units lost by the old join:
--
--     2024      32       2025      19       2026     275
--
--   2025-10  15,803 -> 15,813      2026-01  22,263 -> 22,487  (MKH1-V700-R4-r)
--   2025-11  11,838 -> 11,845      2026-02  26,858 -> 26,909  (MSTS12CRNAG15-*-f)
--   2025-12   9,200 ->  9,202
--
-- Value is untouched: bi_amount was never gated, and this changes no other
-- column. Only bi_qty moves, and only upward, and only on rows that were always
-- units and were miscounted as none.
--
-- WHY IT MATTERS BEYOND bidata ITSELF
--
-- The four boards under "PBI Dashboards > Sales Dashboards" read
-- v_pbi_sales_sman_fact, which applies THE SAME gate keyed the same way but
-- upper-cases both sides -- so the boards were right and bidata was short, and
-- the two disagreed on quantity in exactly those five months. This is what
-- makes them agree.
--
-- Safe to normalise: no part number appears in two casings within catalogflags,
-- so upper() cannot turn one row into two. cat_grp, cat_stock and cat_flag are
-- uniformly upper case and untrimmed-clean already; they are normalised here
-- only so the whole key is treated one way.
--
-- THE REAL UPSTREAM FIX is for the ERP to stop emitting one part number in two
-- casings. Until it does, every consumer of the part number has to normalise,
-- and this view is one of them.
--
-- Idempotent: CREATE OR REPLACE, same columns, same types, same order.
-- Re-running it is a no-op.

-- THE REPORT-REGION MASTER, WHERE THE DATABASE HAS NONE
--
-- The view reads twelve legacy ERP master tables and no module creates any of
-- them. staging-hhsv3 was fed eleven: it has t_regionsdesc and t_subregionsdesc
-- but no t_rptregionsdesc, so this script used to abort with
--
--     relation "t_rptregionsdesc" does not exist
--     LINE 78: LEFT JOIN t_rptregionsdesc rd ON rd.rr_code::text = bd....
--
-- t_regionsdesc is NOT the same table and is not a substitute: it is the
-- geographic region reached through t_subregions.sr_region, keyed r_code,
-- while bidata.bi_cstregioncode is a REPORT region, keyed rr_code. So the
-- table is created here, in its own name, and seeded:
--
--   1. from bidata itself -- every (bi_cstregioncode, bi_cstregiondesc) the
--      feed carries, verbatim and untrimmed, because the join is a plain
--      equality and a trimmed code would stop matching the rows it describes;
--   2. from res_region, the Odoo report-region master (code, name), for codes
--      bidata has not carried yet. name is translatable, and in Odoo 17 that
--      makes it jsonb, so it is read through ->>'en_US' where it is.
--
-- Creation and seeding are guarded and re-runnable: an existing table is left
-- alone entirely, and a table this script created is topped up with codes it
-- does not yet hold. Nothing is ever updated or deleted.
--
-- The shape follows its sibling desc masters (t_subregionsdesc, t_regionsdesc):
-- <p>_lang, lang_flag, <p>_code, <p>_desc, user_lmd. The view reads only
-- rr_code, rr_lang and rr_desc.

BEGIN;

-- What this database holds of the twelve masters the view reads. Anything
-- reported ABSENT below has to arrive before the view can be built; this
-- script creates t_rptregionsdesc and nothing else.
SELECT t                                   AS master_table,
       CASE WHEN to_regclass(t) IS NULL
            THEN 'ABSENT'
            ELSE 'present' END             AS status
  FROM unnest(ARRAY['bidata', 'catalogflags', 'customerdesc', 'sl_salesmandesc', 't_cstclassificationdesc', 't_cstclasstypedesc', 't_groupsdesc', 't_mainproductsdesc', 't_products', 't_productsubsdescgroup', 't_rptregionsdesc', 't_subregionsdesc']) AS t
 ORDER BY (to_regclass(t) IS NOT NULL), t;

DO $rptregions$
DECLARE
    name_expr text;
    from_bidata integer := 0;
    from_region integer := 0;
BEGIN
    IF to_regclass('public.t_rptregionsdesc') IS NOT NULL THEN
        RAISE NOTICE 't_rptregionsdesc already present: left untouched.';
    ELSE
        CREATE TABLE public.t_rptregionsdesc (
            id        serial PRIMARY KEY,
            rr_lang   integer,
            lang_flag integer,
            rr_code   character varying,
            rr_desc   character varying,
            user_lmd  character varying
        );
        CREATE UNIQUE INDEX t_rptregionsdesc_code_lang_unique
            ON public.t_rptregionsdesc (rr_code, rr_lang);
        RAISE NOTICE 't_rptregionsdesc created -- the report-region master this database was fed without.';
    END IF;

    -- Seed 1: the codes bidata actually carries, with the description the feed
    -- carries for them. One row per code: a code whose rows disagree on the
    -- description takes the last one alphabetically, which is a tie-break, not
    -- a judgement -- the ERP master is the authority when it arrives.
    IF to_regclass('public.bidata') IS NOT NULL THEN
        INSERT INTO public.t_rptregionsdesc (rr_lang, lang_flag, rr_code, rr_desc)
        SELECT 1, 1, b.bi_cstregioncode, max(b.bi_cstregiondesc)
          FROM bidata b
         WHERE b.bi_cstregioncode IS NOT NULL
           AND btrim(b.bi_cstregioncode::text) <> ''
           AND NOT EXISTS (SELECT 1 FROM public.t_rptregionsdesc d
                            WHERE d.rr_code::text = b.bi_cstregioncode::text
                              AND d.rr_lang = 1)
         GROUP BY b.bi_cstregioncode;
        GET DIAGNOSTICS from_bidata = ROW_COUNT;
    END IF;

    -- Seed 2: report regions Odoo knows and bidata has not billed into yet.
    IF to_regclass('public.res_region') IS NOT NULL THEN
        SELECT CASE WHEN c.data_type = 'jsonb'
                    THEN 'coalesce(r.name->>''en_US'', (SELECT e.value FROM jsonb_each_text(r.name) e LIMIT 1))'
                    ELSE 'r.name::text' END
          INTO name_expr
          FROM information_schema.columns c
         WHERE c.table_schema = 'public' AND c.table_name = 'res_region'
           AND c.column_name = 'name';

        IF name_expr IS NOT NULL THEN
            EXECUTE format($seed$
                INSERT INTO public.t_rptregionsdesc (rr_lang, lang_flag, rr_code, rr_desc)
                SELECT DISTINCT ON (r.code) 1, 1, r.code, %s
                  FROM res_region r
                 WHERE r.code IS NOT NULL AND btrim(r.code) <> ''
                   AND NOT EXISTS (SELECT 1 FROM public.t_rptregionsdesc d
                                    WHERE d.rr_code::text = r.code::text
                                      AND d.rr_lang = 1)
                 ORDER BY r.code, r.id
            $seed$, name_expr);
            GET DIAGNOSTICS from_region = ROW_COUNT;
        END IF;
    END IF;

    RAISE NOTICE 't_rptregionsdesc seeded: % code(s) from bidata, % from res_region. % row(s) now.',
                 from_bidata, from_region,
                 (SELECT count(*) FROM public.t_rptregionsdesc);
END
$rptregions$;

CREATE OR REPLACE VIEW public.v_bidata_live AS
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
  WHERE 1 = 1 AND bd.bi_year >= 2024 AND bd.bi_cstno::text !~~ 'V%'::text AND bd.bi_franchisecode::text = 'MDA'::text AND (bd.bi_pgroupcode::text = ANY (ARRAY['ACACC'::text, 'ACAIP'::text, 'ACCON'::text, 'ACCST'::text, 'ACHCL'::text, 'ACPAC'::text, 'ACPKG'::text, 'ACPOR'::text, 'ACVRF'::text, 'ACWIN'::text, 'ACWTS'::text, 'ATOM'::text]));


COMMIT;

-- ---------------------------------------------------------------------------
-- VERIFY. Expect the gated units to equal the ungated units of every row that
-- matches catalogflags case-insensitively, and to be HIGHER than they were:
--
--     bi_year | units
--     --------+--------
--        2024 | 245,143
--        2025 | 271,569
--        2026 | 142,614     (bidata feed lands only to early July 2026)
--
SET enable_nestloop = off;
SELECT bi_year, sum(bi_qty) AS units, round(sum(bi_amount)::numeric, 2) AS value
FROM v_bidata_live
WHERE bi_year >= 2024
GROUP BY 1 ORDER BY 1;
RESET enable_nestloop;
