from odoo import models, fields, tools

class ViProductCatalog(models.Model):
    _name = 'vi.product.catalog'
    _description = 'Product Catalog View'
    _auto = False
    _rec_name = 'cat_desc'

    cat_grp = fields.Char(string='Group')
    cat_pgroup = fields.Char(string='Product Group')
    cat_psgroup = fields.Char(string='Product Subgroup')  # used for domain
    cat_part = fields.Char(string='Part')
    cat_desc = fields.Char(string='Description')
    ps_psubgroup = fields.Char(string='Subgroup')

    def init(self):
        tools.drop_view_if_exists(self._cr, 'vi_product_catalog')
        self._cr.execute("""
            CREATE OR REPLACE VIEW vi_product_catalog AS (
                SELECT
                    abs(('x' || substr(md5(cat.cat_grp || cat.cat_pgroup || cat.cat_psgroup || cat.cat_part), 1, 8))::bit(32)::int) AS id,
                    cat.cat_grp,
                    cat.cat_pgroup,
                    cat.cat_psgroup,
                    cat.cat_part,
                    cat.cat_desc,
                    sub.ps_psubgroup
                FROM catalog cat
                JOIN t_productsubs sub 
                    ON cat.cat_grp = sub.ps_grp 
                   AND cat.cat_psgroup = sub.ps_psub
                WHERE cat.cat_pgroup IN ('ACCON','ACCST','ACPAC','ACPOR','ACWIN','ACWTS')
                ORDER BY cat.cat_grp, cat.cat_pgroup
            );
        """)
