# -*- coding: utf-8 -*-
from hashlib import sha256
from base64 import b64encode
from lxml import etree
from odoo import models, fields
from odoo.tools.misc import file_path
import re
import logging
import threading

_logger = logging.getLogger(__name__)
_thread_local = threading.local()

class AccountEdiXmlUBL21Zatca(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_21.zatca'

    def _export_invoice_vals(self, invoice):
        """Override to store the invoice in thread-local storage."""
        # Store the invoice for access in other methods
        _thread_local.current_invoice = invoice
        try:
            # Call the parent method to get the export values
            return super()._export_invoice_vals(invoice)
        finally:
            # Clear the storage to prevent memory leaks
            _thread_local.current_invoice = None

    def _get_partner_party_identification_vals_list(self, partner):
        """ Override to include/update values specific to ZATCA's UBL 2.1 specs """
        # Optional: Use _get_delivery_vals_list to get delivery info
        # Retrieve the current active ID from the context

        invoice = getattr(_thread_local, 'current_invoice', None)
        if invoice and invoice.exists():
           print(f"Processing invoice: {invoice.name} (ID: {invoice.id})")
           journal = invoice.journal_id if invoice else None
            # You can now use invoice.id or other invoice fields as needed
        else:
            print("No current invoice found in thread-local storage")
            # Fallback behavior if no invoice is available
            return []

        pos_shops = partner.pos_shop_ids
        print(
            f"POS Shops for partner {partner.name}: {[(shop.id, shop.name, shop.invoice_journal_id.name) for shop in pos_shops]}")

        # Filter shops where `invoice_journal_id` matches the invoice's `journal_id`
        matching_shop = pos_shops.filtered(lambda shop: shop.invoice_journal_id == invoice.journal_id)
        print(
            f"Matching shop(s) for invoice journal {invoice.journal_id.name}: {[(shop.id, shop.name) for shop in matching_shop]}")

        if matching_shop:
            journal = matching_shop.invoice_journal_id
            print(f"Journal from matching shop: {journal.name if journal else 'None'}")
            if journal and journal.l10n_sa_additional_identification_scheme:
                print(
                    f"Using scheme: {journal.l10n_sa_additional_identification_scheme}, ID: {journal.l10n_sa_additional_identification_number or partner.vat}")
                return [{
                    'id_attrs': {'schemeID': journal.l10n_sa_additional_identification_scheme},
                    'id': journal.l10n_sa_additional_identification_number or partner.vat,
                }]
        else:
            print(f"No matching shop found for invoice journal: {invoice.journal_id.name}")

        # Fallback to partner's additional identification
        print(
            f"Fallback - Partner scheme: {partner.l10n_sa_additional_identification_scheme}, ID: {partner.l10n_sa_additional_identification_number or partner.vat}")

        return [{
            'id_attrs': {'schemeID': partner.l10n_sa_additional_identification_scheme},
            'id': (
                partner.l10n_sa_additional_identification_number
                if partner.l10n_sa_additional_identification_scheme != 'TIN' and partner.country_code == 'SA'
                else partner.vat
            ),
        }]

