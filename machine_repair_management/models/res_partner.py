# -*- coding: utf-8 -*-
# Part of Probuse Consulting Service Pvt. Ltd. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo import re




class Partner(models.Model):
    _inherit = 'res.partner'

    request_count = fields.Integer(
        string='# of Machine Repair',
        compute='_compute_request_count',
        readonly=True,
        default=0
    )
    # customer_city_id = fields.Many2one('res.city',string="Customer City",domain="[('country_id','=',country_id)]")
    customer_city_id = fields.Many2one('res.city', string="Customer City")

    supplier_invoice_count = fields.Boolean(string="Supplier Invoice Count")
    # hide_peppol_fields = fields.Boolean(string="hide peppol Fileds", insvisible=True)
    # is_coa_installed = fields.Boolean(string="hide peppol Fileds", insvisible=True)

    building_number = fields.Char("Building Number")
    plot_identification = fields.Char("Plot Identification")

    additional_identification_scheme = fields.Selection([
        ('TIN', 'Tax Identification Number'),
        ('CRN', 'Commercial Registration Number'),
        ('IQA', 'Iqama Number'),
        ('NAT', 'National ID'),
    ], string="Identification Scheme", help="Additional Identification scheme for Seller/Buyer")

    # additional_identification_scheme = fields.Selection([
    #     ('TIN', 'Tax Identification Number'),
    #     ('CRN', 'Commercial Registration Number'),
    #     ('MOM', 'Momra License'),
    #     ('MLS', 'MLSD License'),
    #     ('700', '700 Number'),
    #     ('SAG', 'Sagia License'),
    #     ('NAT', 'National ID'),
    #     ('GCC', 'GCC ID'),
    #     ('IQA', 'Iqama Number'),
    #     ('PAS', 'Passport ID'),
    #     ('OTH', 'Other ID')
    # ], default="TIN", string="Identification Scheme", help="Additional Identification scheme for Seller/Buyer")

    additional_identification_number = fields.Char("Identification Number",
                                                   help="Additional Identification Number for Seller/Buyer")

    blocked_customer = fields.Boolean(string="Blocked Customer", default=False)

    blocked_reason = fields.Char(string="Blocked reason")

    @api.onchange('customer_city_id')
    def _onchange_customer_city_id(self):
        if self.customer_city_id:
            self.city = self.customer_city_id.name
            self.zip = self.customer_city_id.zipcode
            self.state_id = self.customer_city_id.state_id
            self.country_id = self.customer_city_id.country_id

    @api.depends()
    def _compute_request_count(self):
        repair_support = self.env['machine.repair.support']
        for record in self:
            record.request_count = repair_support.search_count([('partner_id', 'child_of', record.id)])

    def open_repair_request(self):
        self.ensure_one()
        action = self.env.ref('machine_repair_management.action_machine_repair_support').sudo().read()[0]
        action['domain'] = [('partner_id', 'child_of', self.id)]
        return action

    @api.onchange('additional_identification_scheme')
    def _onchange_additional_identification_scheme(self):
        for rec in self:
            rec.additional_identification_number = False
            rec.vat = False

    @api.onchange('blocked_customer')
    def _onchange_blocked_customer(self):
        for rec in self:
            rec.blocked_reason = False

    @api.constrains('mobile')
    def _check_mobile(self):
        pattern = r'^\+?\d[\d\s]*$'
        for rec in self:
            if rec.mobile:
                if not re.match(pattern, rec.mobile):
                    raise ValidationError(
                        "Mobile number can contain only digits, spaces, and an optional '+' at the beginning."
                    )
                # if not rec.mobile.isdigit():
                #     raise ValidationError("Please enter only numbers not character in Mobile No.")

            # mobile_search = self.env['res.partner'].search([('mobile','=',rec.mobile),('id','!=',rec.id)])
            # if len(mobile_search) >1:
            #     raise ValidationError('This Mobile Number %s is already associated with a customer %s.Please give the New one' %(rec.mobile,rec.name))
            #
