# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FinancialStatementBase(models.AbstractModel):
    _name = 'financial.statement.base'
    _description = 'Base Financial Statement Model'

    name = fields.Char(string='Reference', required=True, default=lambda self: self._default_name())
    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    notes = fields.Text(string='Notes')

    def _default_name(self):
        return self.env['ir.sequence'].next_by_code('financial.statement.seq') or 'New'