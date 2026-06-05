# -*- coding: utf-8 -*-
"""
Abstract model for the Customer List Report QWeb renderer.
Receives the pre-computed data dict from the wizard and passes it
to the template unchanged.
"""

from odoo import models


class CustomerListReport(models.AbstractModel):
    _name = 'report.hhs_loyalty_management.report_customer_list'
    _description = 'Customer List Report Renderer'
    _table = 'rpt_customer_list'  # avoid PG 63-char limit on auto-derived name

    def _get_report_values(self, docids, data=None):
        """
        Called by Odoo report framework.
        `data` contains the dict built by the wizard's action_print_pdf().
        """
        data = data or {}
        return {
            'doc_ids': docids,
            'doc_model': 'customer.list.report.wizard',
            'docs': data,
            'grouped': data.get('grouped', {}),
            'flat_rows': data.get('flat_rows', []),
            'filters': data.get('filters', {}),
            'company_dict': data.get('company_dict', {}),
            'user_name': data.get('user_name', ''),
            'printed_at': data.get('printed_at', ''),
        }
