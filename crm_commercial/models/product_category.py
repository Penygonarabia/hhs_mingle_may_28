# -*- coding: utf-8 -*-
from odoo import fields, models, api

class ProductCategory(models.Model):
    _inherit = 'product.category'

    use_for_crm_commercial = fields.Boolean(
        string='Use for CRM Commercial',
        default=False,
        index=True,
        help='Flag to enable category for CRM Commercial selection.'
    )
    exclude_category = fields.Boolean(
        string='Yes, exclude this category',
        default=False,
        index=True,
        help='If checked, this category is excluded from CRM Commercial selection.'
    )
    default_discount_percent = fields.Float(
        string='Default Discount %',
        default=0.0,
        help='Default discount % applied to quotation lines (0-100).'
    )

    # Payment Terms Tab
    enable_payment_terms_pdf = fields.Boolean(
        string='Enable Payment Terms section in quotation PDF',
        default=False
    )
    payment_terms_content = fields.Html(
        string='Payment Terms Content'
    )

    # Warranty Terms & Conditions Tab
    enable_warranty_terms_pdf = fields.Boolean(
        string='Enable Warranty Terms section in quotation PDF',
        default=False
    )
    warranty_terms_content = fields.Html(
        string='Warranty Terms & Conditions Content'
    )

    # Salient Features Tab
    enable_salient_features_pdf = fields.Boolean(
        string='Enable Salient Features section in quotation PDF',
        default=False
    )
    salient_features_content = fields.Html(
        string='Salient Features Content'
    )

    def _compute_display_name(self):
        super()._compute_display_name()
        if self.env.context.get('show_code_only'):
            for category in self:
                if category.code:
                    category.display_name = category.code
                elif category.name:
                    category.display_name = category.name
