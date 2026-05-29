# -*- coding: utf-8 -*-
from odoo import models, fields, tools

class VIProjectTaskRefName(models.Model):
    _name = 'vi.project.task.refname'
    _description = 'VI project Task RefName'
    _auto = False  # View-backed model

    id = fields.Integer()
    contract_id = fields.Integer()
    ref = fields.Char()    

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
               select a.id,0 as contract_id,b.ref from project_task a,res_partner b where a.partner_id=b.id
            );
        """)