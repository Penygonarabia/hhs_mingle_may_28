# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    category_discontinued = fields.Boolean(
        string='Category Discontinued Y/N (Outdated Model)',
        readonly=True,
        default=False
    )
    discontinued_date = fields.Date(
        string='Discontinued Date',
        readonly=True
    )
    long_description = fields.Text(
        string='Long Description'
    )
    project_name = fields.Char(
        string='Project Name',
        index=True
    )
    sync_price_from_erp = fields.Boolean(
        string='Sync Price from ERP',
        readonly=True,
        default=False
    )
    non_stock_item = fields.Boolean(
        string='Non Stock Item',
        default=False,
        index=True
    )
    approval_state = fields.Selection([
        ('draft', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Item Approval Status', default='approved', index=True)

    def action_approve_item(self):
        self.write({'approval_state': 'approved'})

    def action_reject_item(self):
        self.write({'approval_state': 'rejected'})

    def action_open_import_non_stock(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Import Non-Stock Items',
            'res_model': 'crm.commercial.import.non.stock.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {},
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_approve_item(self):
        self.product_tmpl_id.action_approve_item()

    def action_reject_item(self):
        self.product_tmpl_id.action_reject_item()

    def action_open_import_non_stock(self):
        return self.product_tmpl_id.action_open_import_non_stock()

    def name_get(self):
        if self.env.context.get('crm_commercial_code'):
            return [(rec.id, rec.default_code) for rec in self]
        return super().name_get()

    def _compute_display_name(self):
        super()._compute_display_name()
        if self.env.context.get('crm_commercial_code'):
            for rec in self:
                rec.display_name = rec.default_code
