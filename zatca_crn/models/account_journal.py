# -*- coding: utf-8 -*-
from odoo import models, fields, service, _, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_sa_additional_identification_scheme = fields.Selection([
        ('TIN', 'Tax Identification Number'),
        ('CRN', 'Commercial Registration Number'),
        ('MOM', 'Momra License'),
        ('MLS', 'MLSD License'),
        ('700', '700 Number'),
        ('SAG', 'Sagia License'),
        ('NAT', 'National ID'),
        ('GCC', 'GCC ID'),
        ('IQA', 'Iqama Number'),
        ('PAS', 'Passport ID'),
        ('OTH', 'Other ID')
    ], default="CRN", string="Identification Scheme", help="Additional Identification scheme for Seller/Buyer")

    l10n_sa_additional_identification_number = fields.Char("Identification Number (SA)",
                                                           help="Additional Identification Number for Seller/Buyer")
