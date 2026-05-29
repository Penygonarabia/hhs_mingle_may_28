# -*- coding: utf-8 -*

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Repairtype(models.Model):
    _name = 'repair.type'
    _description = "Repair Type"
    _rec_name = 'service_complete_name'
    _order = "name Asc"

    name = fields.Char(
        string="Name",
        required=True,
    )
    code = fields.Char(
        string="Code",
        required=True,
    )
    service_id = fields.Many2one(
        'service.nature',
        string="Service Types", required=True,
        ondelete="cascade",
    )
    service_complete_name = fields.Char(string="Complete Name", compute="_compute_service_type_complete_name",
                                        store=True)
    service_product_category_id = fields.Many2one('product.category', string="Product Category")
    
    '''Code Added on April 24 2026 by Vijaya Bhaskar'''
    mins_required = fields.Float(string = "Mins Required")
    
    '''Code Added on May 06 2026 by Vijaya Bhaskar'''
    service_required_applicable_bool = fields.Boolean(
        string="Quantity Applicable Y/N",
        default=False,
        help = "When Ready to Invoice Service Required is Mandatory"
    )
    
    @api.constrains('code')
    def dupl_code(self):
        exiting_code = self.env['repair.type'].search([('code', '=', self.code)])
        if len(exiting_code) > 1:
            raise ValidationError('Already Code %s is existing' % self.code)

    @api.depends('code', 'name')
    def _compute_service_type_complete_name(self):
        for rec in self:
            if rec.code and rec.name:
                rec.service_complete_name = '[%s] %s' % (rec.code, rec.name)
            else:
                rec.service_complete_name = rec.name
