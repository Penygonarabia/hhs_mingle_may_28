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
                    bd.bi_cstname          AS customer_name,
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
                WHERE bd.bi_type = 'S'
            )
        """)
