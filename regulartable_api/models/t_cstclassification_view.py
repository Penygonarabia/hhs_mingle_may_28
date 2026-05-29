# models/cst_class_view.py
from odoo import models, fields, tools, api

class CstClassTypeDescView(models.Model):
    _name = 'v.cstclasstypedesc'
    _description = 'CST Class Type Description View'
    _auto = False  # IMPORTANT: Indicates this is a view, not a regular table
    cs_name = fields.Char()
    cs_code = fields.Char()
    cs_desc = fields.Char()
    cs_lang = fields.Char()
    lang_flag = fields.Char()
    user_lmd = fields.Char()

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () as id,  -- Required by Odoo
                    'Ramesh' as cs_name,
                    cs_code,
                    cs_desc,
                    cs_lang,
                    lang_flag,
                    user_lmd
                FROM t_cstclasstypedesc
            )
        """)
