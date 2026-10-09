# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class CustomerType(models.Model):
    _name = 'crm.commercial.customer.type'
    _description = 'Customer Type Master'
    _order = 'name'

    code = fields.Char(string='Code', required=True, index=True)
    name = fields.Char(string='Description', required=True, index=True)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The Code must be unique!')
    ]


class ProjectCategory(models.Model):
    _name = 'crm.commercial.project.category'
    _description = 'Project Category Master'
    _order = 'name'

    code = fields.Char(string='Code', required=True, index=True)
    name = fields.Char(string='Description', required=True, index=True)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The Code must be unique!')
    ]


class QuotationType(models.Model):
    _name = 'crm.commercial.quotation.type'
    _description = 'Quotation Type Master'
    _order = 'name'

    code = fields.Char(string='Code', required=True, index=True)
    name = fields.Char(string='Description', required=True, index=True)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The Code must be unique!')
    ]


class SaleType(models.Model):
    _name = 'crm.commercial.sale.type'
    _description = 'Sale Type Master'
    _order = 'name'

    code = fields.Char(string='Code', required=True, index=True)
    name = fields.Char(string='Description', required=True, index=True)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The Code must be unique!')
    ]


class ProjectStatus(models.Model):
    _name = 'crm.commercial.project.status'
    _description = 'Project Status Master'
    _order = 'name'

    code = fields.Char(string='Code', required=True, index=True)
    name = fields.Char(string='Name', required=True, index=True)
    probability = fields.Float(string='Probability %', default=0.0)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The Code must be unique!')
    ]

    @api.constrains('probability')
    def _check_probability(self):
        for rec in self:
            if rec.probability < 0.0 or rec.probability > 100.0:
                from odoo.exceptions import ValidationError
                raise ValidationError(_("Probability % must be between 0 and 100!"))



class ProjectDetailStatus(models.Model):
    _name = 'crm.commercial.project.detail.status'
    _description = 'Project Detail Status Master'
    _order = 'name'

    code = fields.Char(string='Code', required=True, index=True)
    name = fields.Char(string='Name', required=True, index=True)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The Code must be unique!')
    ]


class Consultant(models.Model):
    _name = 'crm.commercial.consultant'
    _description = 'Consultant Master'
    _order = 'name'

    code = fields.Char(string='Code', required=True, index=True)
    name = fields.Char(string='Name', required=True, index=True)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The Code must be unique!')
    ]


class LinkedProduct(models.Model):
    _name = 'crm.commercial.linked.product'
    _description = 'Catalog Linked Products'
    _rec_name = 'source_product_id'
    _order = 'id desc'

    source_product_id = fields.Many2one(
        'product.product',
        string='Source Part No',
        required=True,
        index=True,
        domain="[('active', '=', True)]",
        help='The F unit (fan/indoor unit) part number'
    )
    linked_product_id = fields.Many2one(
        'product.product',
        string='Linked Part No',
        required=True,
        index=True,
        domain="[('active', '=', True)]",
        help='The C unit (condensing/outdoor unit) part number'
    )
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ], string='Status', default='active', required=True, index=True)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('unique_source_linked_pair', 'unique(source_product_id, linked_product_id)', 'The linked product pair must be unique!')
    ]

    @api.constrains('source_product_id', 'linked_product_id')
    def _check_different_products(self):
        for rec in self:
            if rec.source_product_id and rec.linked_product_id and rec.source_product_id == rec.linked_product_id:
                from odoo.exceptions import ValidationError
                raise ValidationError(_("Source Part No and Linked Part No cannot be the same product!"))

    @api.onchange('status')
    def _onchange_status(self):
        if self.status:
            self.active = (self.status == 'active')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'status' in vals and 'active' not in vals:
                vals['active'] = (vals['status'] == 'active')
        return super(LinkedProduct, self).create(vals_list)

    def write(self, vals):
        if 'status' in vals and 'active' not in vals:
            vals['active'] = (vals['status'] == 'active')
        return super(LinkedProduct, self).write(vals)

