from odoo import models, fields, tools

class ViProductSubgroup(models.Model):
    _name = 'vi.product.subgroup'
    _description = 'Subgroup View (Joined Data)'
    _auto = False
    _rec_name = 'psubgroup_desc'
    _table = 'vi_product_subgroup'

    id = fields.Integer()
    psubgroup_code = fields.Char()
    group_code = fields.Char()
    psubgroup_desc = fields.Char()
    lang = fields.Char()
    pcode = fields.Char()

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT DISTINCT
                    row_number() OVER () AS id,
                    ps.PS_PSUBGROUP AS psubgroup_code,
                    ps.PS_GRP AS group_code,
                    psgdesc.psg_desc AS psubgroup_desc,
                    psgdesc.psg_lang AS lang,
                    psgdesc.psg_pcode AS pcode
                FROM
                    t_productsubs ps
                JOIN
                    t_productsubsdescgroup psgdesc
                        ON ps.PS_GRP = psgdesc.psg_grp
                       AND ps.PS_PCODE = psgdesc.psg_pcode
                       AND ps.PS_PSUBGROUP = psgdesc.psg_psub
                WHERE
                    psgdesc.psg_lang = '1'
                    AND ps.PS_GRP = 'MDA'
                    AND psgdesc.psg_pcode IN ('ACCON','ACCST','ACPAC','ACPOR','ACWIN','ACWTS')
            )
        """)
