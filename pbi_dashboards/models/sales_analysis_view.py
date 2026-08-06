from odoo import models, tools


class PbiSalesAnalysisView(models.Model):
    """Backs "PBI Dashboards > Sales Analysis" (see
    ``pbi_dashboards/controllers/sales_analysis_main.py``): a single view
    over the real sales fact table ``bidata`` (the same source
    ``v_bidata_live`` reads from — ``transaction_header``/``transaction_details``
    are legacy-import test data only, effectively empty) that resolves every
    caption needed for the Region -> City -> Main -> Main Sub -> Prod Group
    -> Product Sub Group -> Customer drill-down in one place, per the report
    spec's "create a view to bring all required captions/names" instruction.

    Hierarchy mapping (confirmed against live data, Brand/Franchise
    deliberately excluded from the drill — it stays a separate filter
    elsewhere, same as the existing Sales Dashboard):
      Main             = Product Group        (bi_pgroupcode/name, e.g. "Concealed")
      Main Sub         = Sub-Group-of-Groups   (bi_psgroupcode/name, e.g. "CONCEALED R410")
      Prod Group       = finest Sub-Group      (catalog.cat_psgroup -> t_productsubsdesc.ps_desc,
                                                 e.g. "CONCEALED OUTDOOR R410" — one tier finer
                                                 than anything v_bidata_live exposes)
      Product Sub Group = individual part/SKU  (catalog.cat_desc, keyed by bi_invpartno)

    ``bi_amount``/``bi_qty`` are already the netted total (Credit Note rows
    carry negative values from the upstream ETL, so a plain SUM nets them
    against Invoices — "the regular formula", i.e. the same aggregation
    already used everywhere else in this codebase, not a new calculation).

    catalog.cat_part has 2 duplicate rows repo-wide; deduplicated via
    DISTINCT ON before the join so it can never fan out bidata's rows (a
    naive join inflates SUM(bi_amount) — verified: joining on the coarser
    cat_mainpartno rather than cat_part very nearly doubles the row count).

    ``bidata.bi_cstname`` (this view's customer_name, the Customer drill
    level) is baked into the fact table itself and shows raw Arabic script
    for 187 of 1470 distinct customers — NOT something a join in this view
    causes. ``customerdesc`` stores one row per (cst_no, cst_lang) with
    lang=1 nominally English / lang=2 Arabic, but that tagging is itself
    unreliable for a large chunk of rows (confirmed: blindly preferring
    cst_lang=1 would swap 146 *other* customers from clean English to
    Arabic, while only fixing 10 of the 187). So instead of trusting the
    lang flag, cdeng picks whichever customerdesc row (either lang) has NO
    Arabic characters at all, and it's only substituted in when bidata's
    own name is Arabic — this recovers exactly the 10 customers that do
    have a clean English name on file somewhere, and leaves everyone else
    (including the 177 with no English translation anywhere in the source
    data) untouched.
    """
    _name = 'pbi.sales.analysis.view'
    _description = 'PBI Sales Analysis — bidata + product hierarchy captions (SQL view)'
    _auto = False
    _order = 'id'

    def init(self):
        tools.drop_view_if_exists(self._cr, 'v_pbi_sales_analysis')
        self._cr.execute("""
            CREATE OR REPLACE VIEW v_pbi_sales_analysis AS (
                SELECT
                    bd.id,
                    bd.bi_year, bd.bi_month, bd.bi_monthdate,
                    bd.bi_cstregioncode    AS region_code,
                    bd.bi_cstregiondesc    AS region_name,
                    bd.bi_cstsubregioncode AS city_code,
                    bd.bi_cstsubregiondesc AS city_name,
                    bd.bi_pgroupcode       AS main_code,
                    bd.bi_pgroupname       AS main_name,
                    bd.bi_psgroupcode      AS main_sub_code,
                    bd.bi_psgroupname      AS main_sub_name,
                    COALESCE(c.cat_psgroup, bd.bi_psgroupcode) AS prod_group_code,
                    COALESCE(psd.ps_desc, bd.bi_psgroupname)   AS prod_group_name,
                    bd.bi_invpartno        AS product_sub_group_code,
                    COALESCE(c.cat_desc, bd.bi_invpartno)      AS product_sub_group_name,
                    bd.bi_cstno            AS customer_code,
                    CASE WHEN bd.bi_cstname ~ '[؀-ۿ]'
                         THEN COALESCE(cdeng.cst_name, bd.bi_cstname)
                         ELSE bd.bi_cstname END AS customer_name,
                    bd.bi_invno            AS transaction_no,
                    bd.bi_invdate          AS transaction_date,
                    bd.bi_invwhouse        AS warehouse_code,
                    bd.bi_invwhousename    AS warehouse_name,
                    bd.bi_qty              AS qty,
                    bd.bi_amount           AS amount
                FROM bidata bd
                LEFT JOIN (
                    SELECT DISTINCT ON (cat_part) cat_part, cat_grp, cat_pgroup, cat_psgroup, cat_desc
                    FROM catalog
                    ORDER BY cat_part, id
                ) c ON c.cat_part = bd.bi_invpartno
                LEFT JOIN t_productsubsdesc psd
                    ON psd.ps_grp = c.cat_grp AND psd.ps_pcode = c.cat_pgroup
                   AND psd.ps_psub = c.cat_psgroup AND psd.ps_lang = '1'
                LEFT JOIN LATERAL (
                    SELECT cst_name FROM customerdesc cd
                    WHERE cd.cst_no = bd.bi_cstno AND cd.cst_name !~ '[؀-ۿ]'
                    ORDER BY cd.cst_lang ASC LIMIT 1
                ) cdeng ON true
                WHERE bd.bi_type = 'S'
            )
        """)

        # `bidata` (~295k rows) and every *_b4webapi lookup table
        # v_bidata_live LEFT JOINs it against (sales_kpi_main.py's real
        # dashboard source) had NO indexes at all — EXPLAIN ANALYZE on a
        # single drill-down step (Customer Sub-Type -> Region) showed 13+
        # seconds, because Postgres had no choice but a Nested Loop that
        # re-Seq-Scans every one of those small lookup tables once per
        # matching bidata row instead of an index/hash lookup. The lookup
        # tables are tiny (dozens-to-low-thousands of rows), so indexing
        # their join keys is instant and turns those re-scans into O(1)
        # lookups; the bidata index matches the (bi_year, bi_month, ...)
        # WHERE-clause prefix both sales_kpi_main.py's and
        # sales_analysis_main.py's drill chain build up in, in order.
        self._cr.execute("""
            CREATE INDEX IF NOT EXISTS bidata_drill_idx ON bidata
                (bi_year, bi_month, bi_csttypecode, bi_cstsubtypecode,
                 bi_cstregioncode, bi_cstno, bi_pgroupcode, bi_psgroupcode)
        """)
        # bidata_drill_idx above doesn't help sales_mail_main.py/sales_kpi_main.py's
        # own query shape: those aggregate over a WIDE bi_month BETWEEN range
        # (multi-month YTD, sometimes all 12 months x 2 years), not an exact
        # (year, month) match — for that shape the planner correctly prefers
        # a sequential scan over bidata_drill_idx's bitmap scan once the
        # matched fraction gets much above ~10-15% of the table, which a
        # multi-month YTD range routinely does. Confirmed via EXPLAIN
        # ANALYZE: "Sales Analysis - New"'s full 17-page bundle (32 of these
        # wide-range aggregate queries per load) measured 7.4-12.3s wall
        # time, ~95% of which was raw seq-scan SQL time (Odoo's own request
        # log: "32 queries, 7.376s SQL / 0.353s Python"). A covering index
        # (bi_franchisecode, bi_year, bi_month) INCLUDE-ing every column
        # these dashboards SELECT/SUM/GROUP BY turns those into Index Only
        # Scans (Heap Fetches: 0) instead — same load measured 1.0-3.3s
        # after, scaling with date-range width as expected. Leads with
        # bi_franchisecode (not bi_year) because every one of these
        # dashboards' BASE_SCOPE_SQL/CUSTOMER_TYPE_EXPR-equivalent always
        # filters to one exact franchise first.
        self._cr.execute("""
            CREATE INDEX IF NOT EXISTS bidata_perf_covering_idx ON bidata
                (bi_franchisecode, bi_year, bi_month)
                INCLUDE (bi_qty, bi_amount, bi_budgetamount, bi_budgetqty,
                         bi_invprice, bi_invdisc, bi_invcstspldisc,
                         bi_csttypecode, bi_pgroupcode, bi_cstno,
                         bi_cstregioncode, bi_cstsubregioncode, bi_psgroupname,
                         bi_pgroupname, bi_cstregiondesc, bi_franchisename,
                         bi_salesmanname, bi_csttypedesc, bi_cstname,
                         bi_cstsubtypecode, bi_cstsubtypedesc, bi_psgroupcode,
                         bi_salesmancode)
        """)
        self._cr.execute("CREATE INDEX IF NOT EXISTS t_groupsdesc_b4webapi_grpd_code_idx ON t_groupsdesc_b4webapi (grpd_code)")
        self._cr.execute("CREATE INDEX IF NOT EXISTS t_cstclasstypedesc_b4webapi_cs_code_idx ON t_cstclasstypedesc_b4webapi (cs_code)")
        self._cr.execute("CREATE INDEX IF NOT EXISTS t_cstclassification_b4webapi_cc_idx ON t_cstclassification_b4webapi (cc_code, cc_cstclasstype)")
        self._cr.execute("CREATE INDEX IF NOT EXISTS t_cstclassificationdesc_b4webapi_cc_code_idx ON t_cstclassificationdesc_b4webapi (cc_code)")
        self._cr.execute("CREATE INDEX IF NOT EXISTS t_regionsdesc_b4webapi_r_code_idx ON t_regionsdesc_b4webapi (r_code)")
        self._cr.execute("CREATE INDEX IF NOT EXISTS t_subregions_b4webapi_sr_idx ON t_subregions_b4webapi (sr_code, sr_region)")
        self._cr.execute("CREATE INDEX IF NOT EXISTS t_subregionsdesc_b4webapi_sr_code_idx ON t_subregionsdesc_b4webapi (sr_code)")
        self._cr.execute("CREATE INDEX IF NOT EXISTS sl_salesmandesc_b4webapi_sm_code_idx ON sl_salesmandesc_b4webapi (sm_code)")
        self._cr.execute("CREATE INDEX IF NOT EXISTS customer_b4webapi_cst_no_idx ON customer_b4webapi (cst_no)")
        self._cr.execute("CREATE INDEX IF NOT EXISTS customerdesc_cst_no_idx ON customerdesc (cst_no)")
        self._cr.execute("CREATE INDEX IF NOT EXISTS t_productsdesc_b4webapi_p_idx ON t_productsdesc_b4webapi (p_grp, p_code)")
        self._cr.execute("CREATE INDEX IF NOT EXISTS t_productsubsdescgroup_b4webapi_psg_idx ON t_productsubsdescgroup_b4webapi (psg_grp, psg_pcode, psg_psub)")
