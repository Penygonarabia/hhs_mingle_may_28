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
    dsi_amount = fields.Float('DSI Amount')

    def write(self, vals):
        if self.env.context.get('skip_sync_dsi'):
            return super(ProductTemplate, self).write(vals)
        res = super(ProductTemplate, self).write(vals)
        if 'dsi_amount' in vals:
            for rec in self:
                variants = rec.product_variant_ids.filtered(lambda p: p.dsi_amount != vals['dsi_amount'])
                if variants:
                    variants.with_context(skip_sync_dsi=True).write({'dsi_amount': vals['dsi_amount']})
        return res

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

    dsi_amount = fields.Float(
        string='DSI Amount',
        related='product_tmpl_id.dsi_amount',
        store=True,
        readonly=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ProductProduct, self).create(vals_list)
        if not self.env.context.get('skip_sync_dsi'):
            for rec, vals in zip(records, vals_list):
                if 'dsi_amount' in vals and rec.product_tmpl_id and rec.product_tmpl_id.dsi_amount != vals['dsi_amount']:
                    rec.product_tmpl_id.with_context(skip_sync_dsi=True).write({'dsi_amount': vals['dsi_amount']})
        return records

    def write(self, vals):
        if self.env.context.get('skip_sync_dsi'):
            return super(ProductProduct, self).write(vals)
        res = super(ProductProduct, self).write(vals)
        if 'dsi_amount' in vals:
            for rec in self:
                if rec.product_tmpl_id and rec.product_tmpl_id.dsi_amount != vals['dsi_amount']:
                    rec.product_tmpl_id.with_context(skip_sync_dsi=True).write({'dsi_amount': vals['dsi_amount']})
        return res


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
